# cv_service_1/Dockerfile — YOLOv12-seg
# Требует предварительно собранный образ torch-base:
#   docker build -f Dockerfile.base -t torch-base .
# (запускать из папки где лежит docker-compose.yaml)

FROM torch-base

RUN pip install --no-cache-dir \
    "ultralytics>=8.2.0" \
    && rm -rf /root/.cache/pip/*

COPY main.py .
COPY infer.py .
COPY rle_utils.py .
COPY font_patch.py .

RUN mkdir -p /app/weights

ENV FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=30s --retries=5 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]