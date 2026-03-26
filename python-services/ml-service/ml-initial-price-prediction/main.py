import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from predictor import CarPricePredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

predictor: CarPricePredictor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    logger.info("Starting ML service — loading models...")
    predictor = CarPricePredictor(models_dir="models", artifacts_dir="artifacts")
    logger.info("ML service ready.")
    yield
    logger.info("ML service shutdown.")


app = FastAPI(
    title="Car Price ML Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Схемы запроса / ответа ──────────────────────────────────────────────────

class PredictRequest(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    engineVolume: float
    enginePower: float
    engineType: str
    transmission: str
    driveType: str
    bodyType: str
    color: str
    condition: str
    ownersCount: int
    vehicleAge: int
    mileagePerYear: float
    generation: Optional[str] = None
    complectation: Optional[str] = None


class PredictResponse(BaseModel):
    priceMin: float
    priceMax: float
    confidence: float


# ── Эндпоинты ────────────────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    try:
        result = predictor.predict(request.model_dump())
        return PredictResponse(
            priceMin=result["priceMin"],
            priceMax=result["priceMax"],
            confidence=result["confidence"],
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": predictor is not None}