package com.petprojects.carpricepredictionbackend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum EngineType {
    PETROL("Бензин"),
    DIESEL("Дизель"),
    HYBRID("Гибрид"),
    ELECTRIC("Электро");

    private final String displayName;

    EngineType(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static EngineType fromValue(String value) {
        if (value == null) {
            throw new IllegalArgumentException("EngineType cannot be null");
        }

        // Попытка найти по англ. имени enum (PETROL, DIESEL…)
        for (EngineType type : values()) {
            if (type.name().equalsIgnoreCase(value)) {
                return type;
            }
        }

        // Попытка найти по русскому отображению ("Бензин", "Дизель”…)
        for (EngineType type : values()) {
            if (type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }

        throw new IllegalArgumentException("Unknown EngineType: " + value);
    }
}
