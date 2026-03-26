CREATE TABLE cars (
                      id            BIGSERIAL PRIMARY KEY,
                      brand         VARCHAR(100) NOT NULL,
                      model         VARCHAR(100) NOT NULL,
                      generation    VARCHAR(100),
                      year          INTEGER NOT NULL,
                      mileage       INTEGER NOT NULL,
                      engine_volume DOUBLE PRECISION NOT NULL,
                      engine_power  DOUBLE PRECISION NOT NULL,
                      engine_type   VARCHAR(50) NOT NULL,
                      transmission  VARCHAR(50) NOT NULL,
                      drive_type    VARCHAR(50) NOT NULL,
                      body_type     VARCHAR(50) NOT NULL,
                      color         VARCHAR(100) NOT NULL,
                      condition     VARCHAR(50) NOT NULL,
                      owners_count  INTEGER NOT NULL,
                      complectation TEXT,
                      created_at    TIMESTAMP
);

CREATE TABLE appraisals (
                            id                   BIGSERIAL PRIMARY KEY,
                            car_id               BIGINT NOT NULL REFERENCES cars(id),
                            price_min            NUMERIC(15,2) NOT NULL,
                            price_max            NUMERIC(15,2) NOT NULL,
                            adjusted_price_min   NUMERIC(15,2),
                            adjusted_price_max   NUMERIC(15,2),
                            total_repair_cost    NUMERIC(15,2),
                            has_damage_assessment BOOLEAN DEFAULT FALSE,
                            created_at           TIMESTAMP
);

CREATE TABLE damage_assessments (
                                    id           BIGSERIAL PRIMARY KEY,
                                    appraisal_id BIGINT NOT NULL REFERENCES appraisals(id),
                                    car_part     VARCHAR(100) NOT NULL,
                                    damage_type  VARCHAR(100) NOT NULL,
                                    severity     VARCHAR(50) NOT NULL,
                                    repair_cost  NUMERIC(15,2) NOT NULL,
                                    confidence   DOUBLE PRECISION NOT NULL,
                                    created_at   TIMESTAMP
);