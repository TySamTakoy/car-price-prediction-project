package com.petprojects.car_price_prediction_backend.repository;

import com.petprojects.car_price_prediction_backend.model.AnalysisJob;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {
    Optional<AnalysisJob> findByJobId(String jobId);
}
