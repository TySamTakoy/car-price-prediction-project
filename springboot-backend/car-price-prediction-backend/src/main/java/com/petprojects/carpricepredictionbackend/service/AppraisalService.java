package com.petprojects.car_price_prediction_backend.service;

import com.petprojects.car_price_prediction_backend.dto.*;
import com.petprojects.car_price_prediction_backend.model.Appraisal;
import com.petprojects.car_price_prediction_backend.model.Car;
import com.petprojects.car_price_prediction_backend.model.DamageAssessment;
import com.petprojects.car_price_prediction_backend.repository.AppraisalRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AppraisalService {

    private final CarService carService;
    private final AppraisalRepository appraisalRepository;
    private final MlServiceClient mlServiceClient;
    private final CvServiceClient cvServiceClient;

    @Transactional
    public AppraisalResponseDTO appraiseCarByCharacteristics(CarRequestDTO dto) {
        // 1. Сохранить авто
        Car car = carService.saveCar(dto);

        // 2. Запросить ML сервис
        MlPredictionRequest mlRequest = buildMlRequest(car);
        MlPredictionResponse mlResponse = mlServiceClient.predict(mlRequest);
        log.info("ML result: {} — {}", mlResponse.getPriceMin(), mlResponse.getPriceMax());

        // 3. Сохранить оценку
        Appraisal appraisal = Appraisal.builder()
                .car(car)
                .priceMin(mlResponse.getPriceMin())
                .priceMax(mlResponse.getPriceMax())
                .hasDamageAssessment(false)
                .damages(new ArrayList<>())
                .build();
        appraisal = appraisalRepository.save(appraisal);

        return AppraisalResponseDTO.builder()
                .appraisalId(appraisal.getId())
                .priceMin(appraisal.getPriceMin())
                .priceMax(appraisal.getPriceMax())
                .hasDamageAssessment(false)
                .build();
    }

    @Transactional
    public AppraisalResponseDTO analyzeDamages(CvAnalysisRequest request) {
        // 1. Найти существующую оценку
        Appraisal appraisal = appraisalRepository.findById(request.getAppraisalId())
                .orElseThrow(() -> new RuntimeException(
                        "Appraisal not found: " + request.getAppraisalId()));

        // 2. Запросить CV сервис
        CvAnalysisResponse cvResponse = cvServiceClient.analyze(request);
        log.info("CV result: {} damages, total repair: {}",
                cvResponse.getDamages().size(), cvResponse.getTotalRepairCost());

        // 3. Собрать список повреждений
        List<DamageAssessment> damages = cvResponse.getDamages().stream()
                .map(d -> DamageAssessment.builder()
                        .appraisal(appraisal)
                        .carPart(d.getCarPart())
                        .damageType(d.getDamageType())
                        .severity(d.getSeverity())
                        .repairCost(d.getRepairCost())
                        .confidence(d.getConfidence())
                        .build())
                .collect(Collectors.toList());

        // 4. Скорректировать цену
        BigDecimal totalRepair = cvResponse.getTotalRepairCost();
        BigDecimal adjustedMin = appraisal.getPriceMin()
                .subtract(totalRepair).max(BigDecimal.ZERO);
        BigDecimal adjustedMax = appraisal.getPriceMax()
                .subtract(totalRepair).max(BigDecimal.ZERO);

        appraisal.getDamages().addAll(damages);
        appraisal.setTotalRepairCost(totalRepair);
        appraisal.setAdjustedPriceMin(adjustedMin);
        appraisal.setAdjustedPriceMax(adjustedMax);
        appraisal.setHasDamageAssessment(true);
        appraisalRepository.save(appraisal);

        // 5. Собрать ответ
        List<AppraisalResponseDTO.DamageDTO> damageDTOs = damages.stream()
                .map(d -> AppraisalResponseDTO.DamageDTO.builder()
                        .carPart(d.getCarPart())
                        .damageType(d.getDamageType())
                        .severity(d.getSeverity())
                        .repairCost(d.getRepairCost())
                        .confidence(d.getConfidence())
                        .build())
                .collect(Collectors.toList());

        return AppraisalResponseDTO.builder()
                .appraisalId(appraisal.getId())
                .priceMin(appraisal.getPriceMin())
                .priceMax(appraisal.getPriceMax())
                .adjustedPriceMin(adjustedMin)
                .adjustedPriceMax(adjustedMax)
                .totalRepairCost(totalRepair)
                .hasDamageAssessment(true)
                .damages(damageDTOs)
                .build();
    }

    private MlPredictionRequest buildMlRequest(Car car) {
        int vehicleAge = Math.max(2026 - car.getYear(), 1);

        return MlPredictionRequest.builder()
                .brand(car.getBrand())
                .model(car.getModel())
                .generation(car.getGeneration())
                .year(car.getYear())
                .mileage(car.getMileage())
                .engineVolume(car.getEngineVolume())
                .enginePower(car.getEnginePower())
                .engineType(car.getEngineType().name())
                .transmission(car.getTransmission().name())
                .driveType(car.getDriveType().name())
                .bodyType(car.getBodyType().name())
                .color(car.getColor())
                .condition(car.getCondition().name())
                .ownersCount(car.getOwnersCount())
                .vehicleAge(vehicleAge)
                .mileagePerYear((double) car.getMileage() / vehicleAge)
                .complectation(car.getComplectation())
                .build();
    }
}