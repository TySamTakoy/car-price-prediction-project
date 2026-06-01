package com.petprojects.car_price_prediction_backend.controller;

import com.petprojects.car_price_prediction_backend.dto.AppraisalResponseDTO;
import com.petprojects.car_price_prediction_backend.dto.CarRequestDTO;
import com.petprojects.car_price_prediction_backend.dto.CvAnalysisRequest;
import com.petprojects.car_price_prediction_backend.dto.JobStatusResponse;
import com.petprojects.car_price_prediction_backend.service.AppraisalService;
import com.petprojects.car_price_prediction_backend.service.PhotoAnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/appraisals")
@RequiredArgsConstructor
public class AppraisalController {

    private final AppraisalService     appraisalService;
    private final PhotoAnalysisService photoAnalysisService;

    /**
     * Шаг 1 — оценка по характеристикам авто.
     * Возвращает первичный диапазон цен от ML Service #1.
     */
    @PostMapping("/car")
    public ResponseEntity<AppraisalResponseDTO> appraiseCar(
            @Valid @RequestBody CarRequestDTO request) {
        log.info("Запрос оценки: {} {}", request.getBrand(), request.getModel());
        AppraisalResponseDTO response = appraisalService.appraiseCarByCharacteristics(request);
        return ResponseEntity.ok(response);
    }

    /**
     * Шаг 2 — загрузка фотографий и запуск CV анализа.
     *
     * Принимает multipart/form-data с 4 фото.
     * Каждое фото передаётся с ключом = сторона (front/back/left/right).
     *
     * Пример из фронтенда:
     *   formData.append('front', frontFile)
     *   formData.append('back',  backFile)
     *   formData.append('left',  leftFile)
     *   formData.append('right', rightFile)
     *
     * Возвращает jobId для polling.
     */
    @PostMapping("/{id}/photos")
    public ResponseEntity<JobStatusResponse> uploadPhotos(
            @PathVariable Long id,
            @RequestParam(value = "front", required = false) MultipartFile front,
            @RequestParam(value = "back",  required = false) MultipartFile back,
            @RequestParam(value = "left",  required = false) MultipartFile left,
            @RequestParam(value = "right", required = false) MultipartFile right
    ) throws IOException {
        log.info("Загрузка фото для appraisalId={}", id);

        Map<String, MultipartFile> photos = new HashMap<>();
        if (front != null) photos.put("front", front);
        if (back  != null) photos.put("back",  back);
        if (left  != null) photos.put("left",  left);
        if (right != null) photos.put("right", right);

        if (photos.isEmpty()) {
            return ResponseEntity.badRequest().build();
        }

        String jobId = photoAnalysisService.savePhotosAndStartAnalysis(id, photos);

        return ResponseEntity.accepted().body(JobStatusResponse.builder()
                .jobId(jobId)
                .status("PROCESSING")
                .message("Анализ запущен")
                .appraisalId(id)
                .build());
    }

    /**
     * Старый эндпоинт — для обратной совместимости.
     */
    @PostMapping("/damage")
    public ResponseEntity<AppraisalResponseDTO> analyzeDamage(
            @RequestBody CvAnalysisRequest request) {
        log.info("Анализ повреждений для appraisalId={}", request.getAppraisalId());
        AppraisalResponseDTO response = appraisalService.analyzeDamages(request);
        return ResponseEntity.ok(response);
    }
}
