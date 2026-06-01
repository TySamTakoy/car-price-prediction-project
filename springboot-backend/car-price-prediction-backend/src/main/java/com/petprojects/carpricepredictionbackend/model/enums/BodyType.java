package com.petprojects.car_price_prediction_backend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum BodyType {
    SEDAN("Седан"),
    HATCHBACK("Хэтчбек"),
    WAGON("Универсал"),
    SUV("Внедорожник"),
    COUPE("Купе"),
    MINIVAN("Минивэн"),
    PICKUP("Пикап");

    private final String displayName;

    BodyType(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static BodyType fromValue(String value) {
        for (BodyType type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown BodyType: " + value);
    }
}
