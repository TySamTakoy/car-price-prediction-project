package com.petprojects.car_price_prediction_backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrchestratorCallback {

    @JsonProperty("job_id")
    private String jobId;

    @JsonProperty("appraisal_id")
    private Long appraisalId;

    private String status;
    private String error;

    @JsonProperty("total_time_ms")
    private Double totalTimeMs;

    private List<PhotoResult> photos;
    private List<DamagedElement> damagedElements;

    @JsonProperty("repair_result")
    private RepairResult repairResult;

    private Summary summary;

    // ==================== PhotoResult ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PhotoResult {

        private String side;

        @JsonProperty("file_path")
        private String filePath;

        @JsonProperty("image_width")
        private Integer imageWidth;

        @JsonProperty("image_height")
        private Integer imageHeight;

        @JsonProperty("cv1_time_ms")
        private Double cv1TimeMs;

        @JsonProperty("cv2_time_ms")
        private Double cv2TimeMs;

        @JsonProperty("damage_pct_total")
        private Double damagePctTotal;

        private List<ElementResult> elements;
    }

    // ==================== ElementResult ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ElementResult {

        @JsonProperty("element_id")
        private Integer elementId;

        private String name;
        private Double confidence;
        private List<Double> bbox;

        @JsonProperty("area_px")
        private Integer areaPx;

        @JsonProperty("area_pct")
        private Double areaPct;

        @JsonProperty("damage_detected")
        private Boolean damageDetected;

        @JsonProperty("damage_pct")
        private Double damagePct;

        @JsonProperty("damage_level")
        private String damageLevel;
    }

    // ==================== DamagedElement ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class DamagedElement {
        private String part;
        private String damageLevel;
        private String side;
    }

    // ==================== RepairResult ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class RepairResult {

        @JsonProperty("repair_items")
        private List<RepairItem> repairItems;

        @JsonProperty("total_cost_min")
        private Integer totalCostMin;

        @JsonProperty("total_cost_mid")
        private Integer totalCostMid;

        @JsonProperty("total_cost_max")
        private Integer totalCostMax;

        @JsonProperty("total_range")
        private String totalRange;

        @JsonProperty("skipped_elements")
        private List<String> skippedElements;

        @JsonProperty("repaired_count")
        private Integer repairedCount;

        @JsonProperty("skipped_count")
        private Integer skippedCount;
    }

    // ==================== RepairItem ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class RepairItem {

        private String element;

        @JsonProperty("yolo_name")
        private String yoloName;

        private String procedure;

        @JsonProperty("cost_min")
        private Integer costMin;

        @JsonProperty("cost_mid")
        private Integer costMid;

        @JsonProperty("cost_max")
        private Integer costMax;

        @JsonProperty("damage_level")
        private String damageLevel;

        @JsonProperty("price_range")
        private String priceRange;
    }

    // ==================== Summary ====================
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Summary {

        @JsonProperty("total_elements_detected")
        private Integer totalElementsDetected;

        @JsonProperty("damaged_elements_count")
        private Integer damagedElementsCount;

        @JsonProperty("overall_condition")
        private String overallCondition;

        @JsonProperty("total_repair_cost_min")
        private Integer totalRepairCostMin;

        @JsonProperty("total_repair_cost_mid")
        private Integer totalRepairCostMid;

        @JsonProperty("total_repair_cost_max")
        private Integer totalRepairCostMax;
    }
}