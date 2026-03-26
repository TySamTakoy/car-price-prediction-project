package com.petprojects.carpricepredictionbackend.repository;

import com.petprojects.car_price_prediction_backend.model.Appraisal;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AppraisalRepository extends JpaRepository<Appraisal, Long> {
    List<Appraisal> findByCarIdOrderByCreatedAtDesc(Long carId);
}

