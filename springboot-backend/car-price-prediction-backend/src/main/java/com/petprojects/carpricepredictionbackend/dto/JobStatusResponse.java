package com.petprojects.car_price_prediction_backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class JobStatusResponse {
    private String jobId;
    private String status;    // PROCESSING / DONE / FAILED
    private String message;
    private Long   appraisalId;
}