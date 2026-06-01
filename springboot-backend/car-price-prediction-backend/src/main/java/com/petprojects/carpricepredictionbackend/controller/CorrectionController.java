package com.petprojects.car_price_prediction_backend.controller;

import com.petprojects.car_price_prediction_backend.dto.CorrectionRequest;
import com.petprojects.car_price_prediction_backend.model.*;
import com.petprojects.car_price_prediction_backend.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

@Slf4j
@RestController
@RequiredArgsConstructor
public class CorrectionController {

    private final AppraisalRepository            appraisalRepository;
    private final AppraisalPhotoRepository       appraisalPhotoRepository;
    private final UserDamageCorrectionRepository correctionRepository;

    // ─── Отдача файлов фотографий ────────────────────────────────────────────
    /**
     * GET /api/photos/file?path=/app/uploads/1/front_xxx.png
     * Отдаёт файл фотографии из shared volume.
     * Фронтенд использует этот эндпоинт для отображения фото в дашборде.
     */
    @GetMapping("/api/photos/file")
    public ResponseEntity<Resource> getPhotoFile(@RequestParam String path) {
        try {
            Path filePath = Paths.get(path);
            Resource resource = new UrlResource(filePath.toUri());

            if (!resource.exists() || !resource.isReadable()) {
                log.warn("Файл не найден или недоступен: {}", path);
                return ResponseEntity.notFound().build();
            }

            // Определяем Content-Type по расширению
            String contentType = "image/jpeg";
            String lower = path.toLowerCase();
            if (lower.endsWith(".png"))  contentType = "image/png";
            if (lower.endsWith(".webp")) contentType = "image/webp";

            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType(contentType))
                    .body(resource);

        } catch (MalformedURLException e) {
            log.error("Неверный путь к файлу: {}", path, e);
            return ResponseEntity.badRequest().build();
        }
    }

    // ─── Сохранение корректировок пользователя ───────────────────────────────
    /**
     * POST /api/appraisals/{id}/corrections
     * Сохраняет пользовательские корректировки повреждений.
     * Данные идут в отдельную таблицу для дообучения моделей.
     */
    @PostMapping("/api/appraisals/{id}/corrections")
    public ResponseEntity<Void> saveCorrections(
            @PathVariable Long id,
            @RequestBody CorrectionRequest request
    ) {
        Appraisal appraisal = appraisalRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Appraisal not found: " + id));

        if (request.getCorrections() == null || request.getCorrections().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }

        for (CorrectionRequest.CorrectionItem item : request.getCorrections()) {
            AppraisalPhoto photo = null;
            if (item.getPhotoId() != null) {
                photo = appraisalPhotoRepository.findById(item.getPhotoId()).orElse(null);
            }

            UserDamageCorrection correction = UserDamageCorrection.builder()
                    .appraisal(appraisal)
                    .photo(photo)
                    .elementName(item.getElementName())
                    .correctionType(item.getCorrectionType())
                    .originalLevel(item.getOriginalLevel())
                    .correctedLevel(item.getCorrectedLevel())
                    .userBbox(item.getUserBbox())
                    .comment(item.getComment())
                    .build();

            correctionRepository.save(correction);
        }

        log.info("Сохранено {} корректировок для appraisalId={}",
                request.getCorrections().size(), id);
        return ResponseEntity.ok().build();
    }

    // ─── Получение корректировок для дашборда ────────────────────────────────
    /**
     * GET /api/appraisals/{id}/corrections
     * Возвращает все корректировки пользователя для данной оценки.
     */
    @GetMapping("/api/appraisals/{id}/corrections")
    public ResponseEntity<List<UserDamageCorrection>> getCorrections(@PathVariable Long id) {
        List<UserDamageCorrection> corrections = correctionRepository.findByAppraisalId(id);
        return ResponseEntity.ok(corrections);
    }
}