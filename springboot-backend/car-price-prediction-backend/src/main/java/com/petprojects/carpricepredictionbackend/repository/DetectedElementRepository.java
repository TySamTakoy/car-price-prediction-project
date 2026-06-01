package com.petprojects.car_price_prediction_backend.repository;

import com.petprojects.car_price_prediction_backend.model.DetectedElement;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface DetectedElementRepository extends JpaRepository<DetectedElement, Long> {
    List<DetectedElement> findByPhotoId(Long photoId);
    List<DetectedElement> findByPhotoIdAndDamageDetectedTrue(Long photoId);

    @Query("""
    SELECT p.side 
    FROM DetectedElement de 
    JOIN de.photo p 
    WHERE p.appraisal.id = :appraisalId 
      AND (
           LOWER(de.elementName) = LOWER(:name)
        OR LOWER(de.elementName) LIKE LOWER(CONCAT('%', :name, '%'))
        OR LOWER(:name) LIKE LOWER(CONCAT('%', de.elementName, '%'))
      )
    ORDER BY de.confidence DESC 
    LIMIT 1
    """)
    Optional<String> findSideByAppraisalIdAndElementName(
            @Param("appraisalId") Long appraisalId,
            @Param("name") String name);

}
