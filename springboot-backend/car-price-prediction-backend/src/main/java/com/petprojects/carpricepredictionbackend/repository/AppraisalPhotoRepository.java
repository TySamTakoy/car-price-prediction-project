package com.petprojects.car_price_prediction_backend.repository;

import com.petprojects.car_price_prediction_backend.model.AppraisalPhoto;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AppraisalPhotoRepository extends JpaRepository<AppraisalPhoto, Long> {
    List<AppraisalPhoto> findByAppraisalId(Long appraisalId);
}
