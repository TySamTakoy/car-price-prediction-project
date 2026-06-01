package com.petprojects.car_price_prediction_backend.controller;

import com.petprojects.car_price_prediction_backend.dto.OrchestratorCallback;
import com.petprojects.car_price_prediction_backend.service.PhotoAnalysisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/orchestrator")
@RequiredArgsConstructor
public class CallbackController {

    private final PhotoAnalysisService photoAnalysisService;

    /**
     * Вызывается оркестратором когда анализ завершён.
     * Внутренний эндпоинт — не предназначен для фронтенда.
     */
    @PostMapping("/callback")
    public ResponseEntity<Void> handleCallback(@RequestBody OrchestratorCallback callback) {
        log.info("Получен callback от оркестратора: job_id={} status={}",
                callback.getJobId(), callback.getStatus());
        try {
            photoAnalysisService.handleCallback(callback);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            log.error("Ошибка обработки callback job_id={}: {}",
                    callback.getJobId(), e.getMessage(), e);
            return ResponseEntity.internalServerError().build();
        }
    }
}