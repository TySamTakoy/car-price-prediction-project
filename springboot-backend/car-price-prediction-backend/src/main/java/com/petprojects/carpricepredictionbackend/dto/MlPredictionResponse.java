package com.petprojects.car_price_prediction_backend.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class MlPredictionResponse {
    private BigDecimal priceMin;
    private BigDecimal priceMax;
    private Double confidence;
}
