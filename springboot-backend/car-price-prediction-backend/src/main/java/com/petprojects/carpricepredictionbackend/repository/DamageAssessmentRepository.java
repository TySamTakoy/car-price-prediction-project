package com.petprojects.car_price_prediction_backend.repository;

import com.petprojects.car_price_prediction_backend.model.DamageAssessment;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DamageAssessmentRepository extends JpaRepository<DamageAssessment, Long> {
    List<DamageAssessment> findByAppraisalId(Long appraisalId);
    void deleteByAppraisalId(Long appraisalId);
}