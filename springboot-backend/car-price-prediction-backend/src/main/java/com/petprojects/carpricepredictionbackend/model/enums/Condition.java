package com.petprojects.car_price_prediction_backend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Condition {
    EXCELLENT("Отличное"),
    GOOD("Хорошее"),
    SATISFACTORY("Удовлетворительное"),
    POOR("Плохое");

    private final String displayName;

    Condition(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static Condition fromValue(String value) {
        for (Condition type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown Condition: " + value);
    }
}
