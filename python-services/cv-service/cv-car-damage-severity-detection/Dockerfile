# cv_service_2/Dockerfile — UNet + EfficientNet-B4
# Требует предварительно собранный образ torch-base:
#   docker build -f Dockerfile.base -t torch-base .

FROM torch-base

RUN pip install --no-cache-dir \
    "segmentation-models-pytorch>=0.3.3" \
    "albumentations>=1.3.0" \
    && rm -rf /root/.cache/pip/*

COPY main.py .
COPY predictor.py .
COPY rle_utils.py .

RUN mkdir -p /app/checkpoints

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=30s --retries=5 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]