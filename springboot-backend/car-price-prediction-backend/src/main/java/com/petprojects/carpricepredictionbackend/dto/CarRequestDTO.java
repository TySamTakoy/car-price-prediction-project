package com.petprojects.car_price_prediction_backend.dto;

import com.petprojects.car_price_prediction_backend.model.enums.*;
import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class CarRequestDTO {

    @NotBlank
    private String brand;

    @NotBlank
    private String model;

    private String generation;

    @Min(1990) @Max(2026)
    private int year;

    @Min(0)
    private int mileage;

    @NotNull
    private Double engineVolume;

    @NotNull
    private Double enginePower;

    @NotNull
    private EngineType engineType;

    @NotNull
    private Transmission transmission;

    @NotNull
    private DriveType driveType;

    @NotNull
    private BodyType bodyType;

    @NotBlank
    private String color;

    @NotNull
    private Condition condition;

    @Min(1) @Max(10)
    private int ownersCount;

    private String complectation;
}