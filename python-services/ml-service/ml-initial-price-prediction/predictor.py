import os
import numpy as np
import pandas as pd
import joblib
import logging
from catboost import CatBoostRegressor

from mappings import (
    ENGINE_TYPE_MAP,
    TRANSMISSION_MAP,
    DRIVE_MAP,
    BODY_TYPE_MAP,
    CONDITION_MAP,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def comma_tokenizer(text):
    if not text:
        return []
    tokens = [t.strip() for t in text.split(',')]
    return [t for t in tokens if len(t) > 2]


class CarPricePredictor:

    CAT_COLS = [
        "brand", "model", "generation", "body_type", "color",
        "fuel_type", "transmission", "drive", "wheel", "state",
    ]
    NUM_COLS = [
        "year", "mileage", "engine_volume", "engine_power",
        "owners_count", "vehicle_age", "mileage_per_year", "options_count",
    ]
    SVD_COLS = [f"complect_svd_{i}" for i in range(15)]
    ALL_FEATURES = CAT_COLS + NUM_COLS + SVD_COLS

    def __init__(self, models_dir: str = "models", artifacts_dir: str = "artifacts"):
        models_path    = os.path.join(BASE_DIR, models_dir)
        artifacts_path = os.path.join(BASE_DIR, artifacts_dir)

        logger.info("Loading models...")
        self.models = {
            "low":  CatBoostRegressor().load_model(f"{models_path}/car_price_low.cbm"),
            "mid":  CatBoostRegressor().load_model(f"{models_path}/car_price_mid.cbm"),
            "high": CatBoostRegressor().load_model(f"{models_path}/car_price_high.cbm"),
        }

        logger.info("Loading artifacts...")
        import __main__
        __main__.comma_tokenizer = comma_tokenizer
        self.tfidf = joblib.load(f"{artifacts_path}/tfidf.pkl")
        self.svd   = joblib.load(f"{artifacts_path}/svd.pkl")
        logger.info("Predictor ready.")

    def _map(self, mapping: dict, value: str) -> str:
        return mapping.get(value, value)

    def _build_features(self, req: dict) -> pd.DataFrame:
        year        = int(req["year"])
        mileage     = int(req["mileage"])
        vehicle_age = int(req.get("vehicleAge") or max(2025 - year, 1))
        mileage_per_year = float(req.get("mileagePerYear") or mileage / max(vehicle_age, 1))

        complectation = req.get("complectation") or ""
        options_count = len([o for o in complectation.split(",") if o.strip()]) if complectation.strip() else 0

        text      = complectation.lower().strip()
        tfidf_vec = self.tfidf.transform([text])
        svd_vec   = self.svd.transform(tfidf_vec)[0]

        row = {
            "brand":        req["brand"],
            "model":        req["model"],
            "generation":   req.get("generation") or "Unknown",
            "body_type":    self._map(BODY_TYPE_MAP,    req["bodyType"]),
            "color":        req.get("color") or "Unknown",
            "fuel_type":    self._map(ENGINE_TYPE_MAP,  req["engineType"]),
            "transmission": self._map(TRANSMISSION_MAP, req["transmission"]),
            "drive":        self._map(DRIVE_MAP,        req["driveType"]),
            "wheel":        "левый",
            "state":        self._map(CONDITION_MAP,    req["condition"]),
            "year":             year,
            "mileage":          mileage,
            "engine_volume":    float(req["engineVolume"]),
            "engine_power":     float(req.get("enginePower") or 150.0),
            "owners_count":     int(req["ownersCount"]),
            "vehicle_age":      vehicle_age,
            "mileage_per_year": mileage_per_year,
            "options_count":    options_count,
        }

        for i, val in enumerate(svd_vec):
            row[f"complect_svd_{i}"] = float(val)

        return pd.DataFrame([row])[self.ALL_FEATURES]

    def predict(self, req: dict) -> dict:
        features = self._build_features(req)

        price_low  = float(np.expm1(self.models["low"].predict(features)[0]))
        price_mid  = float(np.expm1(self.models["mid"].predict(features)[0]))
        price_high = float(np.expm1(self.models["high"].predict(features)[0]))

        complectation = req.get("complectation") or ""
        options_count = len([o for o in complectation.split(",") if o.strip()]) if complectation.strip() else 0

        if options_count > 0:
            narrowing  = min(options_count / 50, 0.4)
            spread     = price_high - price_low
            price_low  = price_low  + spread * narrowing * 0.5
            price_high = price_high - spread * narrowing * 0.5

        price_low  = max(price_low, 0)
        price_high = max(price_high, price_low)
        price_mid  = max(price_mid, price_low)
        price_mid  = min(price_mid, price_high)

        spread     = price_high - price_low
        confidence = round(max(0.70, min(0.95, 1.0 - spread / max(price_mid, 1) * 0.5)), 3)

        logger.info(
            f"Prediction: {req['brand']} {req['model']} {req['year']} → "
            f"₽{price_low:,.0f} — ₽{price_high:,.0f} (mid: ₽{price_mid:,.0f})"
        )

        return {
            "priceMin":   round(price_low),
            "priceMid":   round(price_mid),
            "priceMax":   round(price_high),
            "confidence": confidence,
        }