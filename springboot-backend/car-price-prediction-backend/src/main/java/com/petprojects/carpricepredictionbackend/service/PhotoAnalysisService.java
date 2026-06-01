package com.petprojects.car_price_prediction_backend.service;

import com.petprojects.car_price_prediction_backend.dto.OrchestratorCallback;
import com.petprojects.car_price_prediction_backend.dto.OrchestratorRequest;
import com.petprojects.car_price_prediction_backend.model.*;
import com.petprojects.car_price_prediction_backend.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class PhotoAnalysisService {

    private final AppraisalRepository       appraisalRepository;
    private final AnalysisJobRepository     analysisJobRepository;
    private final AppraisalPhotoRepository  appraisalPhotoRepository;
    private final DetectedElementRepository detectedElementRepository;
    private final OrchestratorClient        orchestratorClient;
    private final DamageAssessmentRepository damageAssessmentRepository;

    @Value("${uploads.dir:/app/uploads}")
    private String uploadsDir;

    // ─────────────────────────────────────────────────────────────────────────
    // СОХРАНЕНИЕ ФОТО И ЗАПУСК АНАЛИЗА
    // ─────────────────────────────────────────────────────────────────────────

    @Transactional
    public String savePhotosAndStartAnalysis(
            Long appraisalId,
            Map<String, MultipartFile> photosBySide
    ) throws IOException {
        Appraisal appraisal = appraisalRepository.findById(appraisalId)
                .orElseThrow(() -> new RuntimeException("Appraisal not found: " + appraisalId));

        // Создаём папку для загрузок
        Path uploadPath = Paths.get(uploadsDir, String.valueOf(appraisalId));
        Files.createDirectories(uploadPath);

        // Сохраняем фото на диск и в БД
        List<AppraisalPhoto> savedPhotos = new ArrayList<>();
        List<OrchestratorRequest.PhotoInput> photoInputs = new ArrayList<>();

        for (Map.Entry<String, MultipartFile> entry : photosBySide.entrySet()) {
            String side = entry.getKey();
            MultipartFile file = entry.getValue();

            // Конвертируем .heic если нужно (уже должно быть конвертировано на фронте)
            String originalName = file.getOriginalFilename();
            String extension    = getExtension(originalName);
            String fileName     = side + "_" + UUID.randomUUID() + "." + extension;
            Path   filePath     = uploadPath.resolve(fileName);

            // Сохраняем файл
            Files.write(filePath, file.getBytes());

            long fileSizeKb = file.getSize() / 1024;

            AppraisalPhoto photo = AppraisalPhoto.builder()
                    .appraisal(appraisal)
                    .side(side)
                    .originalName(originalName)
                    .filePath(filePath.toString())
                    .fileSizeKb((int) fileSizeKb)
                    .build();

            savedPhotos.add(appraisalPhotoRepository.save(photo));
            photoInputs.add(OrchestratorRequest.PhotoInput.builder()
                    .side(side)
                    .filePath(filePath.toString())
                    .build());

            log.info("Фото сохранено: {} → {}", side, filePath);
        }

        // Создаём job
        String jobId = UUID.randomUUID().toString();
        AnalysisJob job = AnalysisJob.builder()
                .jobId(jobId)
                .appraisal(appraisal)
                .status("PROCESSING")
                .build();
        analysisJobRepository.save(job);

        // Запускаем оркестратор асинхронно
        OrchestratorRequest request = OrchestratorRequest.builder()
                .jobId(jobId)
                .appraisalId(appraisalId)
                .carInfo(OrchestratorRequest.CarInfo.builder()
                        .brand(appraisal.getCar().getBrand())
                        .model(appraisal.getCar().getModel())
                        .year(appraisal.getCar().getYear())
                        .build())
                .photos(photoInputs)
                .build();

        launchOrchestration(request);

        log.info("Анализ запущен: appraisalId={} jobId={}", appraisalId, jobId);
        return jobId;
    }

    @Async
    public void launchOrchestration(OrchestratorRequest request) {
        try {
            orchestratorClient.startOrchestration(request);
        } catch (Exception e) {
            log.error("Ошибка запуска оркестрации job_id={}: {}", request.getJobId(), e.getMessage());
            // Помечаем job как FAILED
            analysisJobRepository.findByJobId(request.getJobId()).ifPresent(job -> {
                job.setStatus("FAILED");
                job.setErrorMessage(e.getMessage());
                job.setFinishedAt(LocalDateTime.now());
                analysisJobRepository.save(job);
            });
        }
    }

// ─────────────────────────────────────────────────────────────────────────
// ОБРАБОТКА CALLBACK ОТ ОРКЕСТРАТОРА
// ─────────────────────────────────────────────────────────────────────────

    @Transactional
    public void handleCallback(OrchestratorCallback callback) {
        log.info("Callback получен: job_id={} status={}", callback.getJobId(), callback.getStatus());

        AnalysisJob job = analysisJobRepository.findByJobId(callback.getJobId())
                .orElseThrow(() -> new RuntimeException("Job not found: " + callback.getJobId()));

        if ("FAILED".equals(callback.getStatus())) {
            job.setStatus("FAILED");
            job.setErrorMessage(callback.getError());
            job.setFinishedAt(LocalDateTime.now());
            analysisJobRepository.save(job);
            return;
        }

        Appraisal appraisal = job.getAppraisal();

        // ── Сохраняем детектированные элементы для каждого фото ──────────────
        if (callback.getPhotos() != null) {
            for (OrchestratorCallback.PhotoResult photoResult : callback.getPhotos()) {
                appraisalPhotoRepository
                        .findByAppraisalId(appraisal.getId())
                        .stream()
                        .filter(p -> p.getSide().equals(photoResult.getSide()))
                        .findFirst()
                        .ifPresent(photo -> {
                            photo.setWidthPx(photoResult.getImageWidth());
                            photo.setHeightPx(photoResult.getImageHeight());
                            appraisalPhotoRepository.save(photo);

                            if (photoResult.getElements() != null) {
                                for (OrchestratorCallback.ElementResult el : photoResult.getElements()) {
                                    String bboxStr = el.getBbox() != null
                                            ? formatBbox(el.getBbox())
                                            : null;
                                    DetectedElement element = DetectedElement.builder()
                                            .photo(photo)
                                            .elementName(el.getName())
                                            .confidence(el.getConfidence())
                                            .bbox(bboxStr)
                                            .areaPx(el.getAreaPx())
                                            .areaPct(el.getAreaPct())
                                            .damageDetected(el.getDamageDetected())
                                            .damagePct(el.getDamagePct())
                                            .damageLevel(el.getDamageLevel())
                                            .build();
                                    detectedElementRepository.save(element);
                                }
                            }
                        });
            }
        }

        // ── Сохраняем повреждения и стоимости ремонта ─────────────────────────
        int savedDamages = 0;
        OrchestratorCallback.RepairResult repairResult = callback.getRepairResult();

        if (repairResult != null && repairResult.getRepairItems() != null && !repairResult.getRepairItems().isEmpty()) {
            log.info("✅ RepairResult получен: {} элементов", repairResult.getRepairItems().size());

            for (OrchestratorCallback.RepairItem item : repairResult.getRepairItems()) {
                String elementName = item.getElement() != null ? item.getElement() : item.getYoloName();

                // Получаем сторону через реальную связь в БД
                String side = detectedElementRepository
                        .findSideByAppraisalIdAndElementName(appraisal.getId(), elementName)
                        .orElse("—");

                DamageAssessment assessment = DamageAssessment.builder()
                        .appraisal(appraisal)
                        .carPart(elementName)
                        .side(side)
                        .damageType(mapDamageLevelToType(item.getDamageLevel()))
                        .severity(item.getDamageLevel())
                        .repairCost(BigDecimal.valueOf(item.getCostMid()))
                        .confidence(0.85)
                        .build();

                damageAssessmentRepository.save(assessment);
                savedDamages++;

                log.info("Сохранено → '{}' | {} | {} руб | сторона = '{}'",
                        elementName, item.getDamageLevel(), item.getCostMid(), side);
            }
        }


        // ── Обновляем цену оценки ─────────────────────────────────────────────
        long repairMid = 0L;

        if (repairResult != null && repairResult.getTotalCostMid() != null) {
            repairMid = repairResult.getTotalCostMid();
        } else if (callback.getSummary() != null && callback.getSummary().getTotalRepairCostMid() != null) {
            repairMid = callback.getSummary().getTotalRepairCostMid();
        }

        BigDecimal totalRepair = BigDecimal.valueOf(repairMid);
        String condition = Optional.ofNullable(callback.getSummary())
                .map(OrchestratorCallback.Summary::getOverallCondition)
                .orElse("");

        BigDecimal priceMin = appraisal.getPriceMin();
        BigDecimal range = appraisal.getPriceMax().subtract(priceMin);

        double[] factors = condition.contains("Сильные")  ? new double[]{0.2, 0.4} :
                condition.contains("Умеренные") ? new double[]{0.4, 0.6} :
                        condition.contains("Слабые")    ? new double[]{0.6, 0.8} :
                                new double[]{0.8, 1.0};

        BigDecimal adjustedMin = range.multiply(BigDecimal.valueOf(factors[0]))
                .add(priceMin).subtract(totalRepair).max(BigDecimal.ZERO);
        BigDecimal adjustedMax = range.multiply(BigDecimal.valueOf(factors[1]))
                .add(priceMin).subtract(totalRepair).max(BigDecimal.ZERO);

        appraisal.setTotalRepairCost(totalRepair);
        appraisal.setAdjustedPriceMin(adjustedMin);
        appraisal.setAdjustedPriceMax(adjustedMax);
        appraisal.setHasDamageAssessment(true);

        log.info("Цена скорректирована: condition='{}' repair={} adjusted={}-{}",
                condition, totalRepair, adjustedMin, adjustedMax);

        appraisalRepository.save(appraisal);

        job.setStatus("DONE");
        job.setFinishedAt(LocalDateTime.now());
        analysisJobRepository.save(job);

        log.info("Callback обработан успешно: appraisalId={} job_id={} damages_saved={}",
                appraisal.getId(), callback.getJobId(), savedDamages);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    // ─────────────────────────────────────────────────────────────────────────

    private String getExtension(String filename) {
        if (filename == null) return "jpg";
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "jpg";
    }

    private String formatBbox(List<Double> bbox) {
        if (bbox == null || bbox.size() < 4) return null;
        return String.format("%.0f,%.0f,%.0f,%.0f",
                bbox.get(0), bbox.get(1), bbox.get(2), bbox.get(3));
    }

    private String mapDamageLevelToType(String level) {
        return switch (level) {
            case "Слабые"    -> "Царапины / Сколы";
            case "Умеренные" -> "Деформация / Вмятины";
            case "Сильные"   -> "Серьёзные повреждения";
            default          -> "Повреждение";
        };
    }
}