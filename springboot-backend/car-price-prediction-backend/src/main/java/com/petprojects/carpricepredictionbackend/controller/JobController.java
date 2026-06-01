package com.petprojects.car_price_prediction_backend.controller;

import com.petprojects.car_price_prediction_backend.dto.JobStatusResponse;
import com.petprojects.car_price_prediction_backend.model.AnalysisJob;
import com.petprojects.car_price_prediction_backend.repository.AnalysisJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/jobs")
@RequiredArgsConstructor
public class JobController {

    private final AnalysisJobRepository analysisJobRepository;

    /**
     * Polling эндпоинт — фронтенд опрашивает каждые 2 секунды.
     * Возвращает текущий статус job.
     */
    @GetMapping("/{jobId}/status")
    public ResponseEntity<JobStatusResponse> getJobStatus(@PathVariable String jobId) {
        AnalysisJob job = analysisJobRepository.findByJobId(jobId)
                .orElse(null);

        if (job == null) {
            return ResponseEntity.notFound().build();
        }

        String message = switch (job.getStatus()) {
            case "PROCESSING" -> "Анализ выполняется...";
            case "DONE"       -> "Анализ завершён";
            case "FAILED"     -> "Ошибка анализа: " + job.getErrorMessage();
            default           -> job.getStatus();
        };

        return ResponseEntity.ok(JobStatusResponse.builder()
                .jobId(job.getJobId())
                .status(job.getStatus())
                .message(message)
                .appraisalId(job.getAppraisal().getId())
                .build());
    }
}