package com.petprojects.car_price_prediction_backend.dto;

import lombok.*;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CorrectionRequest {
    private List<CorrectionItem> corrections;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CorrectionItem {
        private Long   photoId;
        private String elementName;
        // CONFIRMED / REJECTED / ADDED
        private String correctionType;
        private String originalLevel;
        private String correctedLevel;
        // "x1,y1,x2,y2" — bounding box нарисованный пользователем
        private String userBbox;
        private String comment;
    }
}
