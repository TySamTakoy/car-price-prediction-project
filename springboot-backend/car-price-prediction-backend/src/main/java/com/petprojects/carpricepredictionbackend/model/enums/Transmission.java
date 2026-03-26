package com.petprojects.carpricepredictionbackend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Transmission {
    MANUAL("Механика"),
    AUTOMATIC("Автомат"),
    ROBOT("Робот"),
    VARIATOR("Вариатор");

    private final String displayName;

    Transmission(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static Transmission fromValue(String value) {
        for (Transmission type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown Transmission: " + value);
    }
}
