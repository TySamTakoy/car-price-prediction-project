"""
main.py — Orchestrator: координирует CV Service #1, CV Service #2,
          ML Service #2 и отправляет результат обратно в Backend.

Эндпоинты:
  POST /orchestrate  — запускает полный пайплайн анализа фотографий
  GET  /health       — healthcheck

Переменные окружения:
  CV1_URL      URL CV Service #1  (по умолчанию http://cv_service_1:8001)
  CV2_URL      URL CV Service #2  (по умолчанию http://cv_service_2:8002)
  ML2_URL      URL ML Service #2  (по умолчанию http://ml_service_2:8004)
  BACKEND_URL  URL Backend        (по умолчанию http://backend:8080)
  PORT         порт сервиса       (по умолчанию 8003)

Пайплайн для каждого фото:
  1. Читаем файл → base64
  2. Параллельно: POST /infer к CV1 + POST /predict к CV2
  3. IoU matching масок элементов × маска повреждений
  4. Собираем повреждённые элементы для ML Service #2
  5. POST /predict-repair к ML2
  6. POST /api/orchestrator/callback к Backend
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from iou_matcher import match_elements_with_damage, MatchedElement
from part_mapper import is_repairable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ
# ─────────────────────────────────────────────────────────────────────────────

CV1_URL     = os.getenv("CV1_URL",     "http://cv_service_1:8001")
CV2_URL     = os.getenv("CV2_URL",     "http://cv_service_2:8002")
ML2_URL     = os.getenv("ML2_URL",     "http://ml_service_2:8004")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")
PORT        = int(os.getenv("PORT",    "8003"))

# Таймаут для CV сервисов (инференс может быть долгим на CPU)
CV_TIMEOUT  = httpx.Timeout(300.0, connect=10.0)
# Таймаут для ML сервиса и Backend
API_TIMEOUT = httpx.Timeout(30.0,  connect=10.0)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP КЛИЕНТ (один на всё приложение)
# ─────────────────────────────────────────────────────────────────────────────

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient()
    logger.info(
        "Orchestrator запущен. CV1=%s CV2=%s ML2=%s Backend=%s",
        CV1_URL, CV2_URL, ML2_URL, BACKEND_URL
    )
    yield
    await http_client.aclose()
    logger.info("Orchestrator остановлен.")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title    = "Orchestrator",
    version  = "1.0.0",
    lifespan = lifespan,
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

class CarInfo(BaseModel):
    brand: str
    model: str
    year:  int

    model_config = {"protected_namespaces": ()}


class PhotoInput(BaseModel):
    side:      str   # front / back / left / right
    file_path: str   # путь к файлу в shared volume


class OrchestrateRequest(BaseModel):
    job_id:       str
    appraisal_id: int
    car_info:     CarInfo
    photos:       List[PhotoInput]

    model_config = {"protected_namespaces": ()}


class HealthResponse(BaseModel):
    status:     str
    cv1_url:    str
    cv2_url:    str
    ml2_url:    str
    backend_url: str

    model_config = {"protected_namespaces": ()}


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def file_to_base64(file_path: str) -> str:
    """Читает файл и возвращает base64 строку."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def call_cv1(photo_id: str, image_base64: str) -> Dict[str, Any]:
    """Вызывает CV Service #1 для определения кузовных элементов."""
    response = await http_client.post(
        f"{CV1_URL}/infer",
        json={"photo_id": photo_id, "image_base64": image_base64},
        timeout=CV_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def call_cv2(photo_id: str, image_base64: str) -> Dict[str, Any]:
    """Вызывает CV Service #2 для определения повреждений."""
    response = await http_client.post(
        f"{CV2_URL}/predict",
        json={
            "photo_id":     photo_id,
            "image_base64": image_base64,
            "threshold":    0.5,
        },
        timeout=CV_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def call_ml2(
    car_info:         CarInfo,
    damaged_elements: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    """
    Вызывает ML Service #2 для расчёта стоимости ремонта.
    Возвращает None если нет повреждённых элементов с известной стоимостью.
    """
    repairable = [
        e for e in damaged_elements
        if is_repairable(e["part"]) and e["damage_level"] != "Нет"
    ]
    if not repairable:
        logger.info("Нет элементов для расчёта стоимости ремонта")
        return None

    response = await http_client.post(
        f"{ML2_URL}/predict-repair",
        json={
            "brand":             car_info.brand,
            "model":             car_info.model,
            "year":              car_info.year,
            "damaged_elements":  repairable,
        },
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def send_callback(payload: Dict[str, Any]) -> None:
    """Отправляет результат анализа в Backend."""
    try:
        response = await http_client.post(
            f"{BACKEND_URL}/api/orchestrator/callback",
            json=payload,
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        logger.info("Callback отправлен в Backend: job_id=%s", payload.get("job_id"))
    except Exception as e:
        logger.error("Ошибка отправки callback: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# ОСНОВНОЙ ПАЙПЛАЙН
# ─────────────────────────────────────────────────────────────────────────────

async def process_photo(
    photo: PhotoInput,
) -> Dict[str, Any]:
    """
    Обрабатывает одно фото:
      1. Читает файл → base64
      2. Параллельно вызывает CV1 + CV2
      3. IoU matching масок
      4. Возвращает элементы с информацией о повреждениях
    """
    photo_id = photo.side
    logger.info("Обработка фото: %s (%s)", photo_id, photo.file_path)

    # Читаем файл
    try:
        image_base64 = file_to_base64(photo.file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Файл не найден: {photo.file_path}"
        )

    # Параллельный запрос к CV1 и CV2
    t0 = time.perf_counter()
    try:
        cv1_result, cv2_result = await asyncio.gather(
            call_cv1(photo_id, image_base64),
            call_cv2(photo_id, image_base64),
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка CV сервиса: {e}"
        )
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=503,
            detail=f"CV сервис недоступен: {e}"
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "CV инференс %s: CV1=%.0fмс CV2=%.0fмс  параллельно=%.0fмс",
        photo_id,
        cv1_result.get("inference_time_ms", 0),
        cv2_result.get("inference_time_ms", 0),
        elapsed_ms,
    )

    # IoU matching
    elements = cv1_result.get("elements", [])
    damage_mask_encoded = cv2_result.get("damage_mask_encoded", {})

    image_w = cv1_result.get("image_width",  640)
    image_h = cv1_result.get("image_height", 640)

    matched: List[MatchedElement] = []
    if elements and damage_mask_encoded:
        matched = match_elements_with_damage(
            elements            = elements,
            damage_mask_encoded = damage_mask_encoded,
            image_shape         = (image_h, image_w),
        )
    else:
        # Если нет масок — заполняем без повреждений
        for el in elements:
            from iou_matcher import MatchedElement
            matched.append(MatchedElement(
                element_id      = el["element_id"],
                name            = el["name"],
                confidence      = el["confidence"],
                bbox            = el["bbox"],
                area_px         = el["area_px"],
                area_pct        = el["area_pct"],
                damage_detected = False,
                damage_pct      = 0.0,
                damage_level    = "Нет",
            ))

    return {
        "side":             photo.side,
        "file_path":        photo.file_path,
        "image_width":      image_w,
        "image_height":     image_h,
        "cv1_time_ms":      cv1_result.get("inference_time_ms", 0),
        "cv2_time_ms":      cv2_result.get("inference_time_ms", 0),
        "damage_pct_total": cv2_result.get("damage_pct_total", 0),
        "elements": [
            {
                "element_id":      m.element_id,
                "name":            m.name,
                "confidence":      m.confidence,
                "bbox":            m.bbox,
                "area_px":         m.area_px,
                "area_pct":        m.area_pct,
                "damage_detected": m.damage_detected,
                "damage_pct":      m.damage_pct,
                "damage_level":    m.damage_level,
            }
            for m in matched
        ],
    }


async def run_orchestration(request: OrchestrateRequest) -> None:
    """
    Полный пайплайн оркестрации — запускается как background task.

    1. Обрабатываем все фото параллельно
    2. Собираем все повреждённые элементы
    3. Запрашиваем стоимость ремонта у ML2
    4. Отправляем callback в Backend
    """
    t_start = time.perf_counter()
    logger.info(
        "Начало оркестрации: job_id=%s appraisal_id=%d фото=%d",
        request.job_id, request.appraisal_id, len(request.photos)
    )

    try:
        # ─────────────────────────────────────────────────────────────
        # ОБРАБОТКА ФОТО С ОГРАНИЧЕННЫМ ПАРАЛЛЕЛИЗМОМ
        # ─────────────────────────────────────────────────────────────
        sem = asyncio.Semaphore(1)  # 2 — хороший баланс для GPU. 1, если GPU слабая

        async def bounded_process_photo(photo: PhotoInput):
            async with sem:
                return await process_photo(photo)

        logger.info("Запуск обработки %d фото (max %d одновременно)",
                    len(request.photos), sem._value)

        photo_tasks = [bounded_process_photo(photo) for photo in request.photos]
        photo_results = await asyncio.gather(*photo_tasks, return_exceptions=True)

        # Проверяем ошибки
        processed_photos = []
        for i, result in enumerate(photo_results):
            if isinstance(result, Exception):
                logger.error(
                    "Ошибка обработки фото %s: %s",
                    request.photos[i].side, result
                )
            else:
                processed_photos.append(result)

        if not processed_photos:
            await send_callback({
                "job_id": request.job_id,
                "appraisal_id": request.appraisal_id,
                "status": "FAILED",
                "error": "Все фото не удалось обработать",
            })
            return

        # Собираем все повреждённые элементы со всех фото
        all_damaged: List[Dict[str, str]] = []
        for photo_result in processed_photos:
            for el in photo_result["elements"]:
                if el["damage_detected"] and el["damage_level"] != "Нет":
                    all_damaged.append({
                        "part":         el["name"],
                        "damage_level": el["damage_level"],
                        "side":         photo_result["side"],
                    })

        # Дедупликация — если один и тот же элемент повреждён на нескольких фото,
        # берём максимальный уровень повреждения
        level_order = {"Нет": 0, "Слабые": 1, "Умеренные": 2, "Сильные": 3}
        deduped: Dict[str, Dict] = {}
        for item in all_damaged:
            key = item["part"]
            if key not in deduped:
                deduped[key] = item
            else:
                current_level = level_order.get(deduped[key]["damage_level"], 0)
                new_level     = level_order.get(item["damage_level"], 0)
                if new_level > current_level:
                    deduped[key] = item

        unique_damaged = list(deduped.values())
        logger.info(
            "Повреждённых элементов: %d уникальных (из %d всего)",
            len(unique_damaged), len(all_damaged)
        )

        # Запрашиваем стоимость ремонта
        repair_result = None
        if unique_damaged:
            try:
                repair_result = await call_ml2(
                    car_info         = request.car_info,
                    damaged_elements = unique_damaged,
                )
            except Exception as e:
                logger.error("Ошибка ML2: %s", e)

        elapsed_total = (time.perf_counter() - t_start) * 1000

        # Определяем общее состояние
        if not unique_damaged:
            overall_condition = "Повреждений не обнаружено"
        else:
            max_level = max(
                unique_damaged,
                key=lambda x: level_order.get(x["damage_level"], 0)
            )["damage_level"]
            overall_condition = f"{max_level} повреждения"

        # Формируем callback payload
        callback_payload = {
            "job_id":       request.job_id,
            "appraisal_id": request.appraisal_id,
            "status":       "DONE",
            "total_time_ms": round(elapsed_total, 1),
            "photos":       processed_photos,
            "damaged_elements": unique_damaged,
            "repair_result":    repair_result,
            "summary": {
                "total_elements_detected": sum(
                    len(p["elements"]) for p in processed_photos
                ),
                "damaged_elements_count": len(unique_damaged),
                "overall_condition":      overall_condition,
                "total_repair_cost_min":  repair_result["total_cost_min"] if repair_result else 0,
                "total_repair_cost_mid":  repair_result["total_cost_mid"] if repair_result else 0,
                "total_repair_cost_max":  repair_result["total_cost_max"] if repair_result else 0,
            },
        }

        logger.info(
            "Оркестрация завершена: job_id=%s  %.0f мс  повреждено=%d  ремонт=%s руб",
            request.job_id,
            elapsed_total,
            len(unique_damaged),
            repair_result["total_cost_mid"] if repair_result else 0,
        )

        await send_callback(callback_payload)

    except Exception as e:
        logger.error("Критическая ошибка оркестрации job_id=%s: %s", request.job_id, e, exc_info=True)
        await send_callback({
            "job_id":       request.job_id,
            "appraisal_id": request.appraisal_id,
            "status":       "FAILED",
            "error":        str(e),
        })


# ─────────────────────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(
        status      = "ok",
        cv1_url     = CV1_URL,
        cv2_url     = CV2_URL,
        ml2_url     = ML2_URL,
        backend_url = BACKEND_URL,
    )


@app.post("/orchestrate", status_code=202, tags=["Orchestration"])
async def orchestrate(
    request:          OrchestrateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Запускает полный пайплайн анализа фотографий автомобиля.

    Возвращает 202 Accepted немедленно.
    Результат отправляется асинхронно через POST /api/orchestrator/callback
    в Backend когда обработка завершена.

    Пайплайн:
      1. Для каждого фото параллельно: CV1 (элементы) + CV2 (повреждения)
      2. IoU matching масок → damage per element
      3. ML2 → стоимость ремонта
      4. Callback в Backend
    """
    logger.info(
        "Получен запрос оркестрации: job_id=%s  фото=%d",
        request.job_id, len(request.photos)
    )
    background_tasks.add_task(run_orchestration, request)
    return {
        "job_id":  request.job_id,
        "status":  "ACCEPTED",
        "message": "Анализ запущен",
    }


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