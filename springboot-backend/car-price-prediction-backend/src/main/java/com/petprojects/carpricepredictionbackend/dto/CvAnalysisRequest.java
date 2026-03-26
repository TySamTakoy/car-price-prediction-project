package com.petprojects.carpricepredictionbackend.dto;

import lombok.Data;

import java.util.List;

@Data
public class CvAnalysisRequest {
    private Long appraisalId;
    private List<String> images; // base64
}
