-- V6__add_side_to_damage_assessments.sql

ALTER TABLE damage_assessments
    ADD COLUMN IF NOT EXISTS side VARCHAR(50);