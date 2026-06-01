"""
main.py — CV Service #2: FastAPI обёртка вокруг UNet + EfficientNet-B4.

Эндпоинты:
  POST /predict  — принимает base64 фото, возвращает маску повреждений в RLE
  GET  /health   — healthcheck для Docker

Переменные окружения:
  CHECKPOINT_PATH  путь к .pth файлу  (по умолчанию /app/checkpoints/best_model.pth)
  THRESHOLD        порог бинаризации  (по умолчанию 0.5)
  DEVICE           cuda / cpu / ""    (по умолчанию "" — автовыбор)
  PORT             порт сервиса       (по умолчанию 8002)

Запуск локально:
  $env:CHECKPOINT_PATH="./checkpoints/best_model.pth"
  uvicorn main:app --host 0.0.0.0 --port 8002
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predictor import DamagePredictor
from rle_utils import smart_encode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("cv_service_2")

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ ИЗ ENV
# ─────────────────────────────────────────────────────────────────────────────

CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/app/checkpoints/best_model.pth")
THRESHOLD       = float(os.getenv("THRESHOLD", "0.5"))
DEVICE          = os.getenv("DEVICE", "")
PORT            = int(os.getenv("PORT", "8002"))

# ─────────────────────────────────────────────────────────────────────────────
# ГЛОБАЛЬНЫЙ ПРЕДИКТОР
# ─────────────────────────────────────────────────────────────────────────────

predictor: Optional[DamagePredictor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загружаем модель при старте, освобождаем при остановке."""
    global predictor
    logger.info("Загрузка модели: %s", CHECKPOINT_PATH)

    if not os.path.exists(CHECKPOINT_PATH):
        logger.error("Файл весов не найден: %s", CHECKPOINT_PATH)
        sys.exit(1)

    predictor = DamagePredictor(
        checkpoint_path = CHECKPOINT_PATH,
        threshold       = THRESHOLD,
        device          = DEVICE,
    )
    logger.info("Модель загружена. Сервис готов на порту %d", PORT)
    yield
    logger.info("Сервис остановлен.")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI ПРИЛОЖЕНИЕ
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "CV Service #2 — Повреждения",
    description = "UNet + EfficientNet-B4: сегментация повреждений автомобиля",
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

class PredictRequest(BaseModel):
    photo_id:     str   = Field(..., description="Идентификатор фото (front/back/left/right)")
    image_base64: str   = Field(..., description="Base64 строка изображения")
    threshold:    float = Field(0.5, ge=0.0, le=1.0, description="Порог бинаризации маски")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "photo_id":     "front",
                "image_base64": "/9j/4AAQSkZJRgAB...",
                "threshold":    0.5,
            }
        }
    }


class PredictResponse(BaseModel):
    photo_id:           str
    image_width:        int
    image_height:       int
    inference_time_ms:  float
    damage_mask_encoded: dict    # {"rle": "...", "shape": [H, W]}
    damage_pct_total:   float    # % от всего изображения
    level:              str      # Нет / Слабые / Умеренные / Сильные
    threshold_used:     float

    model_config = {"protected_namespaces": ()}


class HealthResponse(BaseModel):
    status:          str
    model_loaded:    bool
    checkpoint_path: str
    threshold:       float
    device:          str
    img_size:        int

    model_config = {"protected_namespaces": ()}


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def base64_to_numpy_rgb(image_base64: str) -> np.ndarray:
    """
    Декодирует base64 строку в numpy RGB массив.

    Принимает строку с префиксом 'data:image/...;base64,' или без.
    Поддерживает .jpg, .jpeg, .png (после конвертации .heic на фронте).

    Returns:
        np.ndarray (H, W, 3) RGB uint8

    Raises:
        HTTPException 400: если изображение не удалось декодировать
    """
    # Убираем data URI префикс если есть
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img_bgr   = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка декодирования изображения: {e}"
        )

    if img_bgr is None:
        raise HTTPException(
            status_code=400,
            detail="Не удалось декодировать изображение. "
                   "Убедитесь что передаётся валидный base64 .jpg/.png"
        )

    # Конвертируем BGR → RGB (модель обучалась на RGB)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return img_rgb


# ─────────────────────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    """
    Healthcheck для Docker.
    Возвращает статус сервиса и параметры загруженной модели.
    """
    return HealthResponse(
        status          = "ok" if predictor is not None else "model_not_loaded",
        model_loaded    = predictor is not None,
        checkpoint_path = CHECKPOINT_PATH,
        threshold       = THRESHOLD,
        device          = str(predictor.device) if predictor else DEVICE or "auto",
        img_size        = predictor.img_size if predictor else 384,
    )


@app.post("/predict", response_model=PredictResponse, tags=["Inference"])
def predict(request: PredictRequest):
    """
    Запускает UNet на переданном изображении.

    Принимает:
      · photo_id     — идентификатор фото
      · image_base64 — base64 строка изображения
      · threshold    — порог бинаризации (по умолчанию 0.5)

    Возвращает:
      · маску повреждений в RLE формате
      · процент повреждённых пикселей от всего изображения
      · уровень повреждений: Нет / Слабые / Умеренные / Сильные
      · время инференса в мс

    Маска кодируется через smart_encode из rle_utils.py.
    Оркестратор декодирует её через smart_decode() и вычисляет
    пересечение с масками элементов от CV Service #1.
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    # Декодируем изображение
    img_rgb = base64_to_numpy_rgb(request.image_base64)
    H, W    = img_rgb.shape[:2]

    logger.info(
        "Инференс photo_id=%s  размер=%dx%d  threshold=%.2f",
        request.photo_id, W, H, request.threshold
    )

    # Инференс
    t0 = time.perf_counter()
    prob_map, mask_bin, damage_pct, level = predictor.predict(
        image_np  = img_rgb,
        threshold = request.threshold,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "photo_id=%s  повреждения=%.2f%%  уровень=%s  время=%.1f мс",
        request.photo_id, damage_pct, level, elapsed_ms
    )

    # Кодируем маску
    mask_encoded = smart_encode(mask_bin)

    return PredictResponse(
        photo_id            = request.photo_id,
        image_width         = W,
        image_height        = H,
        inference_time_ms   = round(elapsed_ms, 2),
        damage_mask_encoded = mask_encoded,
        damage_pct_total    = round(damage_pct, 3),
        level               = level,
        threshold_used      = request.threshold,
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