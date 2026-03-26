package com.petprojects.carpricepredictionbackend.repository;

import com.petprojects.carpricepredictionbackend.model.Car;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CarRepository extends JpaRepository<Car, Long> {

}