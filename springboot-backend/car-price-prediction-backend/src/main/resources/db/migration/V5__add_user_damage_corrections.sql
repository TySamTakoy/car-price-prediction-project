-- V5__add_user_damage_corrections.sql
-- Таблица для хранения пользовательских корректировок повреждений
-- Используется для дообучения моделей

CREATE TABLE user_damage_corrections (
                                         id                BIGSERIAL PRIMARY KEY,
                                         appraisal_id      BIGINT NOT NULL REFERENCES appraisals(id),
                                         photo_id          BIGINT REFERENCES appraisal_photos(id),
                                         element_name      VARCHAR(100),
    -- Тип корректировки:
    -- CONFIRMED     — пользователь подтвердил повреждение от модели
    -- REJECTED      — пользователь отклонил повреждение от модели
    -- ADDED         — пользователь добавил повреждение которое модель не нашла
                                         correction_type   VARCHAR(20) NOT NULL,
                                         original_level    VARCHAR(20),           -- уровень от модели
                                         corrected_level   VARCHAR(20),           -- уровень от пользователя
    -- Bounding box нарисованный пользователем (x1,y1,x2,y2 в пикселях)
                                         user_bbox         VARCHAR(60),
                                         comment           TEXT,
                                         created_at        TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_user_corrections_appraisal ON user_damage_corrections(appraisal_id);
CREATE INDEX idx_user_corrections_type      ON user_damage_corrections(correction_type);