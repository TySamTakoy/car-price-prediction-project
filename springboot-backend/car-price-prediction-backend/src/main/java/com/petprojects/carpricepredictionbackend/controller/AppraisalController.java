package com.petprojects.carpricepredictionbackend.controller;

import com.petprojects.car_price_prediction_backend.dto.*;
import com.petprojects.car_price_prediction_backend.service.AppraisalService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/appraisal")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AppraisalController {

    private final AppraisalService appraisalService;

    @PostMapping("/car")
    public ResponseEntity<AppraisalResponseDTO> appraiseCar(
            @Valid @RequestBody CarRequestDTO request) {
        log.info("Received appraisal request for {} {}", request.getBrand(), request.getModel());
        AppraisalResponseDTO response = appraisalService.appraiseCarByCharacteristics(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/damage")
    public ResponseEntity<AppraisalResponseDTO> analyzeDamage(
            @RequestBody CvAnalysisRequest request) {
        log.info("Received damage analysis for appraisalId={}", request.getAppraisalId());
        AppraisalResponseDTO response = appraisalService.analyzeDamages(request);
        return ResponseEntity.ok(response);
    }
}
