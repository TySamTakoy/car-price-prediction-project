package com.petprojects.car_price_prediction_backend.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "appraisals")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Appraisal {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "car_id", nullable = false)
    private Car car;

    @Column(name = "price_min", nullable = false)
    private BigDecimal priceMin;

    @Column(name = "price_max", nullable = false)
    private BigDecimal priceMax;

    @Column(name = "adjusted_price_min")
    private BigDecimal adjustedPriceMin;

    @Column(name = "adjusted_price_max")
    private BigDecimal adjustedPriceMax;

    @Column(name = "has_damage_assessment")
    private Boolean hasDamageAssessment = false;

    @Column(name = "total_repair_cost")
    private BigDecimal totalRepairCost;

    @OneToMany(mappedBy = "appraisal", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<DamageAssessment> damages;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() { this.createdAt = LocalDateTime.now(); }
}
