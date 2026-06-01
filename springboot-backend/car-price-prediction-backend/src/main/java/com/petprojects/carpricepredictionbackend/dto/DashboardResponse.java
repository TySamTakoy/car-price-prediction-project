package com.petprojects.car_price_prediction_backend.dto;

import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardResponse {

    // Данные автомобиля
    private CarData car;

    // Данные оценки
    private AppraisalData appraisal;

    // Фотографии с элементами
    private List<PhotoData> photos;

    // Повреждённые элементы (агрегировано по всем фото)
    private List<DamageData> damages;

    // Стоимости ремонта
    private List<RepairCostData> repairCosts;

    // Итоговые цены
    private PriceData prices;

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class CarData {
        private Long    id;
        private String  brand;
        private String  model;
        private String  generation;
        private Integer year;
        private Integer mileage;
        private Double  engineVolume;
        private Double  enginePower;
        private String  engineType;
        private String  transmission;
        private String  driveType;
        private String  bodyType;
        private String  color;
        private String  condition;
        private Integer ownersCount;
        private String  complectation;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class AppraisalData {
        private Long          id;
        private String        status;
        private LocalDateTime createdAt;
        private Boolean       hasDamageAssessment;
        private String        overallCondition;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class PhotoData {
        private Long   id;
        private String side;
        private String filePath;
        private String originalName;
        private List<ElementData> elements;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class ElementData {
        private String  name;
        private Double  confidence;
        private String  bbox;
        private Double  areaPct;
        private Boolean damageDetected;
        private Double  damagePct;
        private String  damageLevel;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class DamageData {
        private String carPart;
        private String severity;
        private Double damagePct;
        private String side;
        private Double repairCost;
        private Double confidence;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class RepairCostData {
        private String     element;
        private String     procedure;
        private BigDecimal costMin;
        private BigDecimal costMid;
        private BigDecimal costMax;
        private String     damageLevel;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class PriceData {
        private BigDecimal initialMin;
        private BigDecimal initialMax;
        private BigDecimal repairCostMin;
        private BigDecimal repairCostMax;
        private BigDecimal adjustedMin;
        private BigDecimal adjustedMax;
        private BigDecimal totalRepairCost;
    }
}
