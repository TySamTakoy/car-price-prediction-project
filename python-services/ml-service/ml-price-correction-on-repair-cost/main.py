"""
main.py — ML Service #2: FastAPI обёртка для предсказания стоимости ремонта.

Эндпоинты:
  POST /predict-repair  — принимает данные авто + повреждённые элементы
  GET  /health          — healthcheck для Docker

Переменные окружения:
  MODEL_PATH   путь к .pkl файлу  (по умолчанию /app/artifacts/lgbm_price_model_final.pkl)
  PORT         порт сервиса       (по умолчанию 8004)

Запуск локально:
  $env:MODEL_PATH="./artifacts/lgbm_price_model_final.pkl"
  uvicorn main:app --host 0.0.0.0 --port 8004
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predictor import RepairCostPredictor, DamagedElement, RepairItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ml_service_2")

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ ИЗ ENV
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH = os.getenv(
    "MODEL_PATH",
    "/app/artifacts/lgbm_price_model_final.pkl"
)
PORT = int(os.getenv("PORT", "8004"))

# ─────────────────────────────────────────────────────────────────────────────
# ГЛОБАЛЬНЫЙ ПРЕДИКТОР
# ─────────────────────────────────────────────────────────────────────────────

predictor: Optional[RepairCostPredictor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    logger.info("Загрузка модели: %s", MODEL_PATH)

    if not os.path.exists(MODEL_PATH):
        logger.error("Файл модели не найден: %s", MODEL_PATH)
        sys.exit(1)

    predictor = RepairCostPredictor(model_path=MODEL_PATH)
    logger.info("Модель загружена. Сервис готов на порту %d", PORT)
    yield
    logger.info("Сервис остановлен.")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI ПРИЛОЖЕНИЕ
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "ML Service #2 — Стоимость ремонта",
    description = "LightGBM: предсказание стоимости ремонта кузовных элементов",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC СХЕМЫ
# ─────────────────────────────────────────────────────────────────────────────

class DamagedElementDTO(BaseModel):
    part:         str = Field(..., description="Название элемента из YOLO (например: 'Передний бампер')")
    damage_level: str = Field(..., description="Уровень повреждения: Слабые / Умеренные / Сильные")

    model_config = {"protected_namespaces": ()}


class RepairPredictRequest(BaseModel):
    brand:             str                    = Field(..., description="Марка авто")
    model:             str                    = Field(..., description="Модель авто")
    year:              int                    = Field(..., ge=1990, le=2030)
    damaged_elements:  List[DamagedElementDTO] = Field(..., description="Список повреждённых элементов")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "brand": "Toyota",
                "model": "Camry",
                "year":  2018,
                "damaged_elements": [
                    {"part": "Передний бампер", "damage_level": "Умеренные"},
                    {"part": "Переднее крыло",  "damage_level": "Слабые"},
                ]
            }
        }
    }


class RepairItemDTO(BaseModel):
    element:      str
    yolo_name:    str
    procedure:    str
    cost_min:     int
    cost_mid:     int
    cost_max:     int
    damage_level: str
    price_range:  str    # форматированная строка "30,105 – 38,316 руб"

    model_config = {"protected_namespaces": ()}


class RepairPredictResponse(BaseModel):
    repair_items:      List[RepairItemDTO]
    total_cost_min:    int
    total_cost_mid:    int
    total_cost_max:    int
    total_range:       str       # "88,000 – 112,000 руб"
    skipped_elements:  List[str]
    repaired_count:    int
    skipped_count:     int

    model_config = {"protected_namespaces": ()}


class HealthResponse(BaseModel):
    status:       str
    model_loaded: bool
    model_path:   str

    model_config = {"protected_namespaces": ()}


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def repair_item_to_dto(item: RepairItem) -> RepairItemDTO:
    price_range = f"{item.cost_min:,} – {item.cost_max:,} руб".replace(",", " ")
    return RepairItemDTO(
        element      = item.element,
        yolo_name    = item.yolo_name,
        procedure    = item.procedure,
        cost_min     = item.cost_min,
        cost_mid     = item.cost_mid,
        cost_max     = item.cost_max,
        damage_level = item.damage_level,
        price_range  = price_range,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(
        status       = "ok" if predictor is not None else "model_not_loaded",
        model_loaded = predictor is not None,
        model_path   = MODEL_PATH,
    )


@app.post("/predict-repair", response_model=RepairPredictResponse, tags=["Prediction"])
def predict_repair(request: RepairPredictRequest):
    """
    Предсказывает стоимость ремонта для каждого повреждённого элемента.

    Принимает:
      · brand / model / year     — данные автомобиля
      · damaged_elements         — список элементов с уровнем повреждения

    Логика определения типа работы:
      Слабые    → Ремонт        (жестяные работы, незначительные повреждения)
      Умеренные → Покраска      (царапины, сколы, требуется перекраска)
      Сильные   → Замена        (деформация, трещины, требуется замена)

    Возвращает:
      · детализацию по каждому элементу с диапазоном цен
      · итоговую стоимость ремонта (min / mid / max)
      · список пропущенных элементов (Шина, Диск и т.д.)
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    if not request.damaged_elements:
        raise HTTPException(
            status_code=400,
            detail="Список damaged_elements пуст"
        )

    logger.info(
        "Запрос: %s %s %d  элементов=%d",
        request.brand, request.model, request.year,
        len(request.damaged_elements)
    )

    # Конвертируем DTO → датаклассы
    elements = [
        DamagedElement(part=e.part, damage_level=e.damage_level)
        for e in request.damaged_elements
    ]

    # Предсказываем
    result = predictor.predict(
        brand            = request.brand,
        model_name       = request.model,
        year             = request.year,
        damaged_elements = elements,
    )

    logger.info(
        "Результат: %d элементов  итого=%s руб  пропущено=%d",
        len(result.repair_items),
        f"{result.total_cost_mid:,}",
        len(result.skipped_elements),
    )

    # Формируем ответ
    total_range = (
        f"{result.total_cost_min:,} – {result.total_cost_max:,} руб"
        .replace(",", " ")
    )

    return RepairPredictResponse(
        repair_items     = [repair_item_to_dto(i) for i in result.repair_items],
        total_cost_min   = result.total_cost_min,
        total_cost_mid   = result.total_cost_mid,
        total_cost_max   = result.total_cost_max,
        total_range      = total_range,
        skipped_elements = result.skipped_elements,
        repaired_count   = len(result.repair_items),
        skipped_count    = len(result.skipped_elements),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = "0.0.0.0",
        port    = PORT,
        reload  = False,
        workers = 1,
    )