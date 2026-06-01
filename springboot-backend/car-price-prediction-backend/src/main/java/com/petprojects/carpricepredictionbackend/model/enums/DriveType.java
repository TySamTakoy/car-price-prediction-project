package com.petprojects.car_price_prediction_backend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum DriveType {
    FWD("Передний"),
    RWD("Задний"),
    AWD("Полный");

    private final String displayName;

    DriveType(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static DriveType fromValue(String value) {
        for (DriveType type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown DriveType: " + value);
    }
}
