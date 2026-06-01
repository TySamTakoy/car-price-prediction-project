package com.petprojects.car_price_prediction_backend.service;

import com.petprojects.car_price_prediction_backend.dto.CvAnalysisRequest;
import com.petprojects.car_price_prediction_backend.dto.CvAnalysisResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Service
@RequiredArgsConstructor
public class CvServiceClient {

    private final RestTemplate restTemplate;

    @Value("${cv.service.url}")
    private String cvServiceUrl;

    public CvAnalysisResponse analyze(CvAnalysisRequest request) {
        try {
            String url = cvServiceUrl + "/analyze";
            log.debug("Calling CV service: {}", url);
            return restTemplate.postForObject(url, request, CvAnalysisResponse.class);
        } catch (Exception e) {
            log.error("CV service call failed: {}", e.getMessage());
            throw new RuntimeException("CV service unavailable: " + e.getMessage());
        }
    }
}
