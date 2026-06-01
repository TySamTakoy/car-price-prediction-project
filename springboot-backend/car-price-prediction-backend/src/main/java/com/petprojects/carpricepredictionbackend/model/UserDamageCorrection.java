package com.petprojects.car_price_prediction_backend.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_damage_corrections")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserDamageCorrection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "appraisal_id", nullable = false)
    private Appraisal appraisal;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "photo_id")
    private AppraisalPhoto photo;

    @Column(name = "element_name", length = 100)
    private String elementName;

    // CONFIRMED / REJECTED / ADDED
    @Column(name = "correction_type", nullable = false, length = 20)
    private String correctionType;

    @Column(name = "original_level", length = 20)
    private String originalLevel;

    @Column(name = "corrected_level", length = 20)
    private String correctedLevel;

    @Column(name = "user_bbox", length = 60)
    private String userBbox;

    @Column(name = "comment", columnDefinition = "TEXT")
    private String comment;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}