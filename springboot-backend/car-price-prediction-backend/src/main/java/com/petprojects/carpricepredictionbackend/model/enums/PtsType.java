package com.petprojects.car_price_prediction_backend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum PtsType {
    ORIGINAL("Оригинал"),
    DUPLICATE("Дубликат");

    private final String displayName;

    PtsType(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static PtsType fromValue(String value) {
        for (PtsType type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown PtsType: " + value);
    }
}
