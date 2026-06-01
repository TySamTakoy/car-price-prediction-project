package com.petprojects.car_price_prediction_backend.repository;

import com.petprojects.car_price_prediction_backend.model.UserDamageCorrection;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface UserDamageCorrectionRepository extends JpaRepository<UserDamageCorrection, Long> {
    List<UserDamageCorrection> findByAppraisalId(Long appraisalId);
}
