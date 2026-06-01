package com.petprojects.car_price_prediction_backend.dto;

import lombok.Builder;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class AppraisalResponseDTO {
    private Long appraisalId;
    private BigDecimal priceMin;
    private BigDecimal priceMax;
    private BigDecimal adjustedPriceMin;
    private BigDecimal adjustedPriceMax;
    private BigDecimal totalRepairCost;
    private boolean hasDamageAssessment;
    private List<DamageDTO> damages;

    @Data
    @Builder
    public static class DamageDTO {
        private String carPart;
        private String damageType;
        private String severity;
        private BigDecimal repairCost;
        private Double confidence;
    }
}
