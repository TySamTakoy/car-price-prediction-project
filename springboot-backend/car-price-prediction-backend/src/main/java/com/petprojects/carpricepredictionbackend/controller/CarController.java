package com.petprojects.carpricepredictionbackend.controller;

import com.petprojects.car_price_prediction_backend.dto.CarRequestDTO;
import com.petprojects.car_price_prediction_backend.service.CarService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequestMapping("/api/cars")
@RequiredArgsConstructor
public class CarController {

    private final CarService carService;

    @GetMapping("/{id}")
    public ResponseEntity<CarRequestDTO> getById(@PathVariable Long id) {
        log.info("Get car by id={}", id);
        return ResponseEntity.ok(carService.findById(id));
    }
}