package com.petprojects.car_price_prediction_backend.controller;

import com.petprojects.car_price_prediction_backend.dto.DashboardResponse;
import com.petprojects.car_price_prediction_backend.model.*;
import com.petprojects.car_price_prediction_backend.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/appraisals")
@RequiredArgsConstructor
public class DashboardController {

    private final AppraisalRepository           appraisalRepository;
    private final AppraisalPhotoRepository      appraisalPhotoRepository;
    private final DamageAssessmentRepository    damageAssessmentRepository;

    @GetMapping("/{id}/dashboard")
    public ResponseEntity<DashboardResponse> getDashboard(@PathVariable Long id) {
        Appraisal appraisal = appraisalRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Appraisal not found: " + id));

        Car car = appraisal.getCar();

        DashboardResponse.CarData carData = DashboardResponse.CarData.builder()
                .id(car.getId()).brand(car.getBrand()).model(car.getModel())
                .generation(car.getGeneration()).year(car.getYear())
                .mileage(car.getMileage()).engineVolume(car.getEngineVolume())
                .enginePower(car.getEnginePower()).engineType(car.getEngineType().name())
                .transmission(car.getTransmission().name()).driveType(car.getDriveType().name())
                .bodyType(car.getBodyType().name()).color(car.getColor())
                .condition(car.getCondition().name()).ownersCount(car.getOwnersCount())
                .complectation(car.getComplectation()).build();

        DashboardResponse.AppraisalData appraisalData = DashboardResponse.AppraisalData.builder()
                .id(appraisal.getId()).hasDamageAssessment(appraisal.getHasDamageAssessment())
                .createdAt(appraisal.getCreatedAt()).build();

        List<AppraisalPhoto> photos = appraisalPhotoRepository.findByAppraisalId(id);
        List<DashboardResponse.PhotoData> photoData = photos.stream()
                .map(photo -> DashboardResponse.PhotoData.builder()
                        .id(photo.getId()).side(photo.getSide())
                        .filePath(photo.getFilePath()).originalName(photo.getOriginalName())
                        .elements(photo.getElements().stream()
                                .map(el -> DashboardResponse.ElementData.builder()
                                        .name(el.getElementName()).confidence(el.getConfidence())
                                        .bbox(el.getBbox()).areaPct(el.getAreaPct())
                                        .damageDetected(el.getDamageDetected())
                                        .damagePct(el.getDamagePct()).damageLevel(el.getDamageLevel())
                                        .build())
                                .collect(Collectors.toList()))
                        .build())
                .collect(Collectors.toList());

        // Агрегируем повреждения
        List<DamageAssessment> savedDamages = damageAssessmentRepository.findByAppraisalId(id);
        List<DashboardResponse.DamageData> damages = new ArrayList<>();

        if (!savedDamages.isEmpty()) {
            damages = savedDamages.stream()
                    .map(d -> DashboardResponse.DamageData.builder()
                            .carPart(d.getCarPart())
                            .severity(d.getSeverity())
                            .side(getSideDisplay(d.getSide()))
                            .repairCost(d.getRepairCost() != null ? d.getRepairCost().doubleValue() : 0.0)
                            .confidence(d.getConfidence())
                            .build())
                    .collect(Collectors.toList());

            log.info("Для appraisalId={} загружено {} повреждений из damage_assessments", id, damages.size());
        } else {
            // Fallback: агрегируем из элементов фото
            for (DashboardResponse.PhotoData photo : photoData) {
                for (DashboardResponse.ElementData el : photo.getElements()) {
                    if (Boolean.TRUE.equals(el.getDamageDetected())) {
                        damages.add(DashboardResponse.DamageData.builder()
                                .carPart(el.getName())
                                .severity(el.getDamageLevel())
                                .damagePct(el.getDamagePct())
                                .side(photo.getSide())
                                .repairCost(0.0)
                                .build());
                    }
                }
            }
            log.warn("damage_assessments пуст для appraisalId={}, используем fallback из фото", id);
        }

        BigDecimal totalRepair = appraisal.getTotalRepairCost() != null
                ? appraisal.getTotalRepairCost() : BigDecimal.ZERO;

        DashboardResponse.PriceData prices = DashboardResponse.PriceData.builder()
                .initialMin(appraisal.getPriceMin())
                .initialMax(appraisal.getPriceMax())
                .repairCostMin(totalRepair.compareTo(BigDecimal.ZERO) > 0
                        ? totalRepair.multiply(BigDecimal.valueOf(0.88)) : null)
                .repairCostMax(totalRepair.compareTo(BigDecimal.ZERO) > 0
                        ? totalRepair.multiply(BigDecimal.valueOf(1.12)) : null)
                .adjustedMin(appraisal.getAdjustedPriceMin())
                .adjustedMax(appraisal.getAdjustedPriceMax())
                .totalRepairCost(totalRepair)
                .build();

        return ResponseEntity.ok(DashboardResponse.builder()
                .car(carData)
                .appraisal(appraisalData)
                .photos(photoData)
                .damages(damages)
                .prices(prices)
                .build());
    }


    private String getSideDisplay(String side) {
        if (side == null || side.isBlank() || side.equals("—")) {
            return "—";
        }
        return side;
    }
}