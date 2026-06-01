-- V4__add_detected_elements.sql
-- Таблица для хранения обнаруженных кузовных элементов с результатами анализа

CREATE TABLE detected_elements (
                                   id               BIGSERIAL PRIMARY KEY,
                                   photo_id         BIGINT NOT NULL REFERENCES appraisal_photos(id),
                                   element_name     VARCHAR(100) NOT NULL,
                                   confidence       DOUBLE PRECISION NOT NULL,
                                   bbox             VARCHAR(60),
    -- Формат: "x1,y1,x2,y2"
                                   area_px          INTEGER,
                                   area_pct         DOUBLE PRECISION,
                                   damage_detected  BOOLEAN DEFAULT FALSE,
                                   damage_pct       DOUBLE PRECISION,
    -- % площади элемента покрытый повреждением
                                   damage_level     VARCHAR(20),
    -- Нет / Слабые / Умеренные / Сильные
                                   created_at       TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_detected_elements_photo    ON detected_elements(photo_id);
CREATE INDEX idx_detected_elements_damage   ON detected_elements(damage_detected);