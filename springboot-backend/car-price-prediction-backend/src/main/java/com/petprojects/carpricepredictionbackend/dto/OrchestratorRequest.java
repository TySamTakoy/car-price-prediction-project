package com.petprojects.car_price_prediction_backend.dto;

import lombok.*;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrchestratorRequest {

    @JsonProperty("job_id")
    private String jobId;

    @JsonProperty("appraisal_id")
    private Long appraisalId;

    @JsonProperty("car_info")
    private CarInfo carInfo;

    private List<PhotoInput> photos;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CarInfo {
        private String brand;
        private String model;
        private Integer year;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PhotoInput {
        private String side;

        @JsonProperty("file_path")
        private String filePath;
    }
}
