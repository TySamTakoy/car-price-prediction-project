package com.petprojects.carpricepredictionbackend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class CvAnalysisResponse {
    private List<DamageItem> damages;
    private BigDecimal totalRepairCost;

    @Data
    public static class DamageItem {
        private String carPart;
        private String damageType;
        private String severity;
        private BigDecimal repairCost;
        private Double confidence;
    }
}