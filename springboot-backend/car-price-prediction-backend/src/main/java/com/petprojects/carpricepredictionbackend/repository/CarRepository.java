package com.petprojects.carpricepredictionbackend.repository;

import com.petprojects.car_price_prediction_backend.model.Car;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CarRepository extends JpaRepository<Car, Long> {

}