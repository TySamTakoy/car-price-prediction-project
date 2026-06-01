-- V3__add_appraisal_photos.sql
-- Таблица для хранения фотографий привязанных к оценке

CREATE TABLE appraisal_photos (
                                  id             BIGSERIAL PRIMARY KEY,
                                  appraisal_id   BIGINT NOT NULL REFERENCES appraisals(id),
                                  side           VARCHAR(10) NOT NULL,
    -- Стороны: front, back, left, right
                                  original_name  VARCHAR(255),
                                  file_path      TEXT NOT NULL,
                                  file_size_kb   INTEGER,
                                  width_px       INTEGER,
                                  height_px      INTEGER,
                                  created_at     TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_appraisal_photos_appraisal ON appraisal_photos(appraisal_id);