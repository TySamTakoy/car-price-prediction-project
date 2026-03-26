package com.petprojects.carpricepredictionbackend.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MlPredictionRequest {
    private String brand;
    private String model;
    private String generation;
    private int year;
    private int mileage;
    private double engineVolume;
    private double enginePower;
    private String engineType;
    private String transmission;
    private String driveType;
    private String bodyType;
    private String color;
    private String condition;
    private int ownersCount;
    private int vehicleAge;
    private double mileagePerYear;
    private String complectation;
}
