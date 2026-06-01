package com.petprojects.car_price_prediction_backend.model;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "detected_elements")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DetectedElement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "photo_id", nullable = false)
    private AppraisalPhoto photo;

    @Column(name = "element_name", nullable = false, length = 100)
    private String elementName;

    @Column(name = "confidence", nullable = false)
    private Double confidence;

    @Column(name = "bbox", length = 60)
    private String bbox;   // "x1,y1,x2,y2"

    @Column(name = "area_px")
    private Integer areaPx;

    @Column(name = "area_pct")
    private Double areaPct;

    @Column(name = "damage_detected")
    private Boolean damageDetected;

    @Column(name = "damage_pct")
    private Double damagePct;

    @Column(name = "damage_level", length = 20)
    private String damageLevel;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}

