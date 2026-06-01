-- V2__add_analysis_jobs.sql
-- Таблица для отслеживания статуса асинхронной обработки фотографий

CREATE TABLE analysis_jobs (
                               id            BIGSERIAL PRIMARY KEY,
                               job_id        VARCHAR(36) NOT NULL UNIQUE,   -- UUID
                               appraisal_id  BIGINT NOT NULL REFERENCES appraisals(id),
                               status        VARCHAR(20) NOT NULL DEFAULT 'PROCESSING',
    -- Возможные статусы: PROCESSING, DONE, FAILED
                               error_message TEXT,
                               created_at    TIMESTAMP DEFAULT now(),
                               finished_at   TIMESTAMP
);

CREATE INDEX idx_analysis_jobs_job_id      ON analysis_jobs(job_id);
CREATE INDEX idx_analysis_jobs_appraisal   ON analysis_jobs(appraisal_id);
CREATE INDEX idx_analysis_jobs_status      ON analysis_jobs(status);