package com.petprojects.carpricepredictionbackend.model.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum EquipmentLevel {
    BASE("Базовая"),
    COMFORT("Комфорт"),
    BUSINESS("Бизнес"),
    PREMIUM("Премиум"),
    LUXURY("Люкс");

    private final String displayName;

    EquipmentLevel(String displayName) {
        this.displayName = displayName;
    }

    @JsonValue
    public String getDisplayName() {
        return displayName;
    }

    @JsonCreator
    public static EquipmentLevel fromValue(String value) {
        for (EquipmentLevel type : values()) {
            if (type.name().equalsIgnoreCase(value) ||
                    type.displayName.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown EquipmentLevel: " + value);
    }
}
