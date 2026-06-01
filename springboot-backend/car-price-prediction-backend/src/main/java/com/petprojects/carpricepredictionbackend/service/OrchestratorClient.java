package com.petprojects.car_price_prediction_backend.service;

import com.petprojects.car_price_prediction_backend.dto.OrchestratorRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Component
public class OrchestratorClient {

    private final RestTemplate restTemplate;

    @Value("${orchestrator.url:http://localhost:8003}")
    private String orchestratorUrl;

    public OrchestratorClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public void startOrchestration(OrchestratorRequest request) {
        try {
            String url = orchestratorUrl + "/orchestrate";
            log.debug("Вызов оркестратора: {}", url);
            restTemplate.postForObject(url, request, Object.class);
            log.info("Оркестрация запущена: job_id={}", request.getJobId());
        } catch (Exception e) {
            log.error("Ошибка вызова оркестратора: {}", e.getMessage());
            throw new RuntimeException("Orchestrator unavailable: " + e.getMessage());
        }
    }
}