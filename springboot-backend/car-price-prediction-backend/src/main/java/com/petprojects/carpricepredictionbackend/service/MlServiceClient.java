package com.petprojects.carpricepredictionbackend.service;

import com.petprojects.car_price_prediction_backend.dto.MlPredictionRequest;
import com.petprojects.car_price_prediction_backend.dto.MlPredictionResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Service
@RequiredArgsConstructor
public class MlServiceClient {

    private final RestTemplate restTemplate;

    @Value("${ml.service.url}")
    private String mlServiceUrl;

    public MlPredictionResponse predict(MlPredictionRequest request) {
        try {
            String url = mlServiceUrl + "/predict";
            log.debug("Calling ML service: {}", url);
            return restTemplate.postForObject(url, request, MlPredictionResponse.class);
        } catch (Exception e) {
            log.error("ML service call failed: {}", e.getMessage());
            throw new RuntimeException("ML service unavailable: " + e.getMessage());
        }
    }
}
