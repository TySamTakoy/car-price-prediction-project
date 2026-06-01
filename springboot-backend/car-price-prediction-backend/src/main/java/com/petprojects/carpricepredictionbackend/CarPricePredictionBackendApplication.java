package com.petprojects.car_price_prediction_backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync
@SpringBootApplication
public class CarPricePredictionBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(CarPricePredictionBackendApplication.class, args);
    }

}
