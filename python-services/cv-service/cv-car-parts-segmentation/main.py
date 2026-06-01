"""
main.py — CV Service #1: FastAPI обёртка вокруг YOLOv12-seg (infer.py).

Эндпоинты:
  POST /infer   — принимает base64 фото, возвращает кузовные элементы + RLE маски
  GET  /health  — healthcheck для Docker

Переменные окружения:
  WEIGHTS_PATH   путь к .pt файлу   (по умолчанию /app/weights/best.pt)
  CONF_THRESH    порог уверенности  (по умолчанию 0.35)
  DEVICE         cuda / cpu / ""    (по умолчанию "" — автовыбор)
  PORT           порт сервиса       (по умолчанию 8001)

Запуск локально:
  uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Запуск в Docker:
  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# rle_utils лежит рядом с main.py в том же сервисе
from rle_utils import smart_encode, damage_pct_to_level

# infer.py лежит рядом с main.py
from infer import CarPartInferencer, Detection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("cv_service_1")

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ ИЗ ENV
# ─────────────────────────────────────────────────────────────────────────────

WEIGHTS_PATH = os.getenv("WEIGHTS_PATH", "/app/weights/best.pt")
CONF_THRESH  = float(os.getenv("CONF_THRESH", "0.35"))
DEVICE       = os.getenv("DEVICE", "")
PORT         = int(os.getenv("PORT", "8001"))

# ─────────────────────────────────────────────────────────────────────────────
# ГЛОБАЛЬНАЯ МОДЕЛЬ (загружается один раз при старте)
# ─────────────────────────────────────────────────────────────────────────────

inferencer: Optional[CarPartInferencer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загружаем модель при старте сервиса, освобождаем при остановке."""
    global inferencer
    logger.info("Загрузка модели: %s", WEIGHTS_PATH)

    if not os.path.exists(WEIGHTS_PATH):
        logger.error("Файл весов не найден: %s", WEIGHTS_PATH)
        sys.exit(1)

    # === GPU + CPU optimizations ===
    import torch
    # import os

    # Ограничиваем количество потоков (важно даже на GPU)
    torch.set_num_threads(6)
    os.environ.setdefault("OMP_NUM_THREADS", "6")
    os.environ.setdefault("MKL_NUM_THREADS", "6")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "6")

    # Явно указываем устройство (если в ENV не задано — используем GPU)
    device = DEVICE or "cuda"

    logger.info("Инициализация модели на устройстве: %s", device)

    inferencer = CarPartInferencer(
        weights         = WEIGHTS_PATH,
        conf_thresh     = CONF_THRESH,
        device          = device,
    )

    logger.info("Выполняется fuse модели (однократно при старте)...")
    inferencer.model.fuse()

    logger.info("Модель YOLOv12-seg успешно загружена и fused. "
                "Устройство: %s | Классов: %d",
                inferencer.model.device, len(inferencer.model.names))

    yield
    logger.info("Сервис cv_service_1 остановлен.")

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "CV Service #1 — Кузовные элементы",
    description = "YOLOv12-seg: определение кузовных элементов автомобиля",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC СХЕМЫ
# ─────────────────────────────────────────────────────────────────────────────

class InferRequest(BaseModel):
    photo_id:     str   = Field(..., description="Идентификатор фото (например: 'front')")
    image_base64: str   = Field(..., description="Base64 строка изображения (без data:image/...;base64, префикса)")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_id":     "front",
                "image_base64": "/9j/4AAQSkZJRgAB...",
            }
        }


class ElementResult(BaseModel):
    element_id:   int
    name:         str
    confidence:   float
    bbox:         List[float]          # [x1, y1, x2, y2]
    area_px:      int
    area_pct:     float
    mask_encoded: dict                 # {"rle": "...", "shape": [H, W]}


class InferResponse(BaseModel):
    photo_id:         str
    image_width:      int
    image_height:     int
    inference_time_ms: float
    elements:         List[ElementResult]
    elements_count:   int


class HealthResponse(BaseModel):
    status:        str
    model_loaded:  bool
    weights_path:  str
    conf_thresh:   float
    device:        str

    model_config = {"protected_namespaces": ()}

# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def base64_to_numpy(image_base64: str) -> np.ndarray:
    """
    Декодирует base64 строку в numpy BGR массив (формат OpenCV).

    Принимает строку как с префиксом 'data:image/...;base64,' так и без.
    Поддерживает .jpg, .jpeg, .png, .heic (после конвертации на фронте).

    Returns:
        np.ndarray форма (H, W, 3) BGR uint8

    Raises:
        HTTPException 400: если строка не является валидным изображением
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

    return img_bgr


def detection_to_response(det: Detection, idx: int) -> ElementResult:
    """
    Конвертирует объект Detection в Pydantic схему для ответа.
    Маска кодируется через smart_encode (RLE или zlib+base64).
    """
    return ElementResult(
        element_id   = idx,
        name         = det.class_name,
        confidence   = round(det.confidence, 4),
        bbox         = [round(v, 1) for v in det.bbox],
        area_px      = det.area_px,
        area_pct     = round(det.area_pct, 3),
        mask_encoded = smart_encode(det.mask),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    """
    Healthcheck для Docker.
    Возвращает статус сервиса и информацию о загруженной модели.
    """
    return HealthResponse(
        status       = "ok" if inferencer is not None else "model_not_loaded",
        model_loaded = inferencer is not None,
        weights_path = WEIGHTS_PATH,
        conf_thresh  = CONF_THRESH,
        device       = DEVICE or "auto",
    )


@app.post("/infer", response_model=InferResponse, tags=["Inference"])
def infer(request: InferRequest):
    """
    Запускает YOLOv12-seg на переданном изображении.

    Принимает:
      · photo_id     — строковый идентификатор (front/back/left/right)
      · image_base64 — base64 строка изображения

    Возвращает:
      · список обнаруженных кузовных элементов
      · для каждого элемента: имя, уверенность, bbox, площадь, RLE маска
      · время инференса в мс

    Маски кодируются через smart_encode:
      · разреженные маски → RLE строка (компактно, быстро декодируется)
      · плотные маски     → zlib+base64 (меньший размер для больших областей)

    Оркестратор декодирует маски через smart_decode() из rle_utils.py.
    """
    if inferencer is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")

    # Декодируем изображение
    img_bgr = base64_to_numpy(request.image_base64)
    H, W    = img_bgr.shape[:2]

    logger.info(
        "Инференс photo_id=%s  размер=%dx%d",
        request.photo_id, W, H
    )

    # Инференс
    t0         = time.perf_counter()
    detections = inferencer.predict(img_bgr)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "photo_id=%s  обнаружено=%d  время=%.1f мс",
        request.photo_id, len(detections), elapsed_ms
    )

    # Сериализуем результаты
    elements = [
        detection_to_response(det, idx=i + 1)
        for i, det in enumerate(detections)
    ]

    return InferResponse(
        photo_id          = request.photo_id,
        image_width       = W,
        image_height      = H,
        inference_time_ms = round(elapsed_ms, 2),
        elements          = elements,
        elements_count    = len(elements),
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