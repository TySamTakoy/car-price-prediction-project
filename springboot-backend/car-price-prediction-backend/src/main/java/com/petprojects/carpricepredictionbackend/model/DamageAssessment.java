package com.petprojects.car_price_prediction_backend.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "damage_assessments")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DamageAssessment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "appraisal_id", nullable = false)
    private Appraisal appraisal;

    @Column(name = "car_part", nullable = false)
    private String carPart;

    @Column(name = "side")
    private String side;

    @Column(name = "damage_type", nullable = false)
    private String damageType;

    @Column(nullable = false)
    private String severity;

    @Column(name = "repair_cost", nullable = false)
    private BigDecimal repairCost;

    @Column(nullable = false)
    private Double confidence;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() { this.createdAt = LocalDateTime.now(); }
}