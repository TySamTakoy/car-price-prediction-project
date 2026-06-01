"""
infer.py — Инференс YOLOv12-seg: изображение → размеченное фото + текстовый отчёт.

Выходные файлы для каждого входного изображения car.jpg:
  outputs/car_masked.jpg   — оригинал с наложенными цветными масками и подписями
  outputs/car_report.txt   — текстовый отчёт по каждому обнаруженному элементу

Гауссово сглаживание применяется к каждой маске перед отрисовкой и записью в отчёт
(устраняет «зубчатые» края, возникающие из-за вариативности разметки).

Использование:
  # Одно изображение
  python infer.py --weights best.pt --source car.jpg
  python infer.py --weights runs/segment/runs/segment/car_parts_yolov12_phase2/weights/best.pt --source img_test/car_front.jpg

  # Папка
  python infer.py --weights best.pt --source images/

  # С настройкой порогов
  python infer.py --weights best.pt --source car.jpg --conf 0.4 --mask-thresh 0.45
"""
from __future__ import annotations

import argparse
import colorsys
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ─── Классы из вашего dataset.yaml ────────────────────────────────────────────

CLASS_NAMES = [
    "Капот",
    "Фара",
    "Крышка бензобака",
    "Решётка радиатора",
    "Окно",
    "Задний фонарь",
    "Лобовое стекло",
    "Задний бампер",
    "Передний бампер",
    "Переднее крыло",
    "Заднее крыло",
    "Номерной знак",
    "Шина",
    "Дверь",
    "Зеркало заднего вида",
    "Колесный диск",
    "Крышка багажника",
    "Крыша",
    "Эмблема",
    "ПТФ",
]

# ─── Цветовая палитра ─────────────────────────────────────────────────────────

def _build_palette(n: int) -> List[tuple]:
    """
    Генерирует n визуально различимых BGR-цветов.
    Использует равномерный HSV-обход с высокой насыщенностью.
    """
    colors = []
    for i in range(n):
        h = i / n
        r, g, b = colorsys.hsv_to_rgb(h, 0.85, 0.92)
        colors.append((int(b * 255), int(g * 255), int(r * 255)))
    return colors

PALETTE = _build_palette(max(len(CLASS_NAMES), 32))


# ─── Датакласс результата ─────────────────────────────────────────────────────

@dataclass
class Detection:
    class_id:   int
    class_name: str
    confidence: float
    bbox:       List[float]          # [x1, y1, x2, y2] пиксельные
    mask:       np.ndarray           # uint8 {0,1}, размер оригинала
    area_px:    int                  # площадь маски в пикселях
    area_pct:   float                # % от площади изображения


# ─── Гауссово сглаживание маски ───────────────────────────────────────────────

def smooth_mask_gaussian(
    mask: np.ndarray,
    kernel_size: int = 15,
    sigma: float = 5.0,
    threshold: float = 0.45,
) -> np.ndarray:
    """
    Сглаживает бинарную маску через ядро Гаусса.

    Алгоритм (метод Финолаб):
      1. mask float [0,1] → GaussianBlur → размытые края
      2. перебинаризация по threshold → плавный контур

    Args:
        mask:        uint8 {0,1}
        kernel_size: нечётное; если чётное — автоматически +1
        sigma:       стандартное отклонение Гаусса
        threshold:   порог перебинаризации (0.45 = слегка расширяет маску)

    Returns:
        uint8 {0,1} — сглаженная маска
    """
    if kernel_size % 2 == 0:
        kernel_size += 1

    mask_f = mask.astype(np.float32)
    blurred = cv2.GaussianBlur(mask_f, (kernel_size, kernel_size),
                               sigmaX=sigma, sigmaY=sigma)
    return (blurred >= threshold).astype(np.uint8)


# ─── Основной пайплайн ────────────────────────────────────────────────────────

class CarPartInferencer:
    """
    Загружает YOLOv12-seg и выполняет инференс с Гауссовым постпроцессингом.
    """

    def __init__(
            self,
            weights: str,
            conf_thresh: float = 0.35,
            iou_thresh: float = 0.45,
            imgsz: int = 640,
            mask_bin_thresh: float = 0.5,
            gauss_kernel: int = 15,
            gauss_sigma: float = 5.0,
            gauss_thresh: float = 0.45,
            min_area_ratio: float = 0.001,
            device: str = "",
    ):
        from ultralytics import YOLO
        logger.info("Загрузка модели: %s", weights)

        self.model = YOLO(weights)

        if device:
            self.model.to(device)

        # Fuse модели — обязательно один раз при старте
        logger.info("Выполняется fuse модели для стабильной и быстрой работы...")
        self.model.fuse()  # ← без verbose

        self.conf = conf_thresh
        self.iou = iou_thresh
        self.imgsz = imgsz
        self.mask_bin_thresh = mask_bin_thresh
        self.gauss_kernel = gauss_kernel
        self.gauss_sigma = gauss_sigma
        self.gauss_thresh = gauss_thresh
        self.min_area_ratio = min_area_ratio

        logger.info("Модель YOLOv12-seg успешно fused и готова. Классов: %d",
                    len(self.model.names))

    # ── Инференс одного изображения ───────────────────────────────────────────

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Запускает модель, применяет Гаусс, возвращает список Detection.
        """
        H, W = image.shape[:2]
        img_area = H * W

        raw = self.model.predict(
            source=image,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            verbose=False,
        )

        result = raw[0]
        if result.masks is None:
            return []

        detections: List[Detection] = []

        for box, mask_tensor in zip(result.boxes, result.masks.data):
            cls_id    = int(box.cls[0].item())
            conf      = float(box.conf[0].item())
            bbox      = box.xyxy[0].tolist()
            cls_name  = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"

            # ── Бинаризация: YOLO даёт float32 [0..1] в уменьшенном разрешении
            mask_f = mask_tensor.cpu().numpy()  # float32, (mH, mW)
            mask_bin = (mask_f > self.mask_bin_thresh).astype(np.uint8)

            # ── Ресайз к оригиналу (mask_ratio уменьшает, нужно вернуть)
            mH, mW = mask_bin.shape
            if mH != H or mW != W:
                mask_bin = cv2.resize(
                    mask_bin, (W, H), interpolation=cv2.INTER_NEAREST
                )

            # ── Фильтр шума по площади (в пикселях оригинала)
            area_px = int(mask_bin.sum())
            if area_px < self.min_area_ratio * img_area:
                continue

            # ── Гауссово сглаживание
            mask_smooth = smooth_mask_gaussian(
                mask_bin,
                kernel_size=self.gauss_kernel,
                sigma=self.gauss_sigma,
                threshold=self.gauss_thresh,
            )

            # Пересчитываем площадь после сглаживания
            area_px  = int(mask_smooth.sum())
            area_pct = 100.0 * area_px / img_area

            detections.append(Detection(
                class_id   = cls_id,
                class_name = cls_name,
                confidence = conf,
                bbox       = bbox,
                mask       = mask_smooth,
                area_px    = area_px,
                area_pct   = area_pct,
            ))

        # Сортируем по убыванию площади (крупные детали — первыми)
        detections.sort(key=lambda d: d.area_px, reverse=True)
        return detections


# ─── Визуализация ─────────────────────────────────────────────────────────────

from PIL import Image, ImageDraw, ImageFont

def put_text_ru(img, text, xy, color=(255, 255, 255), font_path="C:/Windows/Fonts/Arial.ttf",
                font_size=16, bg_color=(0, 0, 0, 160), padding=4):
    """
    Рисует кириллический текст поверх OpenCV изображения с контрастным фоном.
    """
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, font_size)

    # Размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x, y = xy
    rect = [x - padding, y - padding, x + tw + padding, y + th + padding]

    # Рисуем полупрозрачный фон
    draw.rectangle(rect, fill=bg_color)

    # Рисуем текст
    draw.text((x, y), text, font=font, fill=color[::-1])  # BGR -> RGB
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR), th + 2*padding  # возвращаем высоту блока


def draw_detections(
        image: np.ndarray,
        detections: List[Detection],
        alpha_fill: float = 0.35,
        draw_contour: bool = True,
        contour_thickness: int = 2,
        font_size: int = 14,
        font_path: str = "C:/Windows/Fonts/Arial.ttf",
) -> np.ndarray:
    """
    Отрисовка масок, контуров и текста с контрастным фоном.
    Текст и фон размещаются примерно в середине маски.
    """
    overlay = image.copy()
    canvas = image.copy()
    text_blocks = []  # [(x0,y0,x1,y1), ...]

    font = ImageFont.truetype(font_path, font_size)

    for det in detections:
        color = PALETTE[det.class_id % len(PALETTE)]
        mask = det.mask

        # Заливка маски
        colored = np.zeros_like(image)
        colored[mask == 1] = color
        overlay = cv2.addWeighted(overlay, 1.0, colored, alpha_fill, 0)

        if draw_contour:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(canvas, contours, -1, (255, 255, 255), contour_thickness+1)
            cv2.drawContours(canvas, contours, -1, color, contour_thickness)

    result = cv2.addWeighted(overlay, 1.0, canvas, 1.0, 0)

    # ── Подписи в середине маски ──────────────────────────────────────────────
    for det in detections:
        label = f"{det.class_name}  {det.confidence:.0%}"

        # Размер блока текста через PIL
        img_pil_dummy = Image.new("RGBA", (1, 1))
        draw_dummy = ImageDraw.Draw(img_pil_dummy)
        bbox = draw_dummy.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        padding = 4
        bbox_w = tw + 2*padding
        bbox_h = th + 2*padding

        # Находим центр маски
        ys, xs = np.where(det.mask == 1)
        if len(xs) == 0 or len(ys) == 0:
            continue  # пустая маска
        cx, cy = int(xs.mean()), int(ys.mean())

        # Позиция текста: центрируем
        tx = max(0, cx - bbox_w // 2)
        ty = max(0, cy - bbox_h // 2)

        # Ограничение по границам изображения
        tx = min(tx, result.shape[1] - bbox_w)
        ty = min(ty, result.shape[0] - bbox_h)

        # Отрисовка текста
        result, _ = put_text_ru(
            result, label, xy=(tx, ty),
            color=PALETTE[det.class_id % len(PALETTE)],
            font_size=font_size, font_path=font_path,
            bg_color=(0, 0, 0, 160), padding=padding
        )

        text_blocks.append([tx, ty, tx + bbox_w, ty + bbox_h])

    return result


# ─── Текстовый отчёт ──────────────────────────────────────────────────────────

def build_report(
    image_path: str,
    detections: List[Detection],
    inference_ms: float,
    gauss_kernel: int,
    gauss_sigma: float,
    gauss_thresh: float,
) -> str:
    """
    Формирует текстовый отчёт об обнаруженных элементах.

    Структура:
      - Заголовок с путём к файлу и временем обработки
      - Параметры постобработки (Гаусс)
      - Таблица обнаруженных элементов
      - Сводка (количество уникальных классов, общая площадь)
    """
    lines = []
    sep   = "─" * 72

    lines.append("╔" + "═" * 70 + "╗")
    lines.append("║  ОТЧЁТ ОБ ОБНАРУЖЕННЫХ КУЗОВНЫХ ЭЛЕМЕНТАХ" + " " * 26 + "║")
    lines.append("╚" + "═" * 70 + "╝")
    lines.append("")
    lines.append(f"Файл:              {image_path}")
    lines.append(f"Время инференса:   {inference_ms:.1f} мс")
    lines.append(f"Обнаружено:        {len(detections)} объектов")
    lines.append("")
    lines.append("Параметры Гауссова сглаживания контуров:")
    lines.append(f"  kernel_size = {gauss_kernel}  |  sigma = {gauss_sigma}  |  threshold = {gauss_thresh}")
    lines.append(sep)
    lines.append("")

    if not detections:
        lines.append("  Элементы не обнаружены.")
    else:
        # Заголовок таблицы
        lines.append(
            f"  {'№':>3}  {'Элемент':<25}  {'Уверенность':>12}  "
            f"{'Площадь px':>11}  {'Площадь %':>10}  {'BBox (x1,y1,x2,y2)'}"
        )
        lines.append("  " + sep)

        seen_classes = {}

        for i, det in enumerate(detections, 1):
            bbox_str = "({:.0f},{:.0f},{:.0f},{:.0f})".format(*det.bbox)
            lines.append(
                f"  {i:>3}  {det.class_name:<25}  {det.confidence:>11.1%}  "
                f"{det.area_px:>11,}  {det.area_pct:>9.2f}%  {bbox_str}"
            )
            # Для сводки — запоминаем лучшую уверенность по классу
            if det.class_name not in seen_classes or \
               det.confidence > seen_classes[det.class_name]:
                seen_classes[det.class_name] = det.confidence

        lines.append("")
        lines.append(sep)
        lines.append("")
        lines.append("СВОДКА:")
        lines.append(f"  Уникальных классов:    {len(seen_classes)}")
        lines.append(f"  Всего объектов:        {len(detections)}")
        lines.append("")
        lines.append("  Обнаруженные элементы (лучшая уверенность):")
        for cls_name in sorted(seen_classes):
            conf = seen_classes[cls_name]
            lines.append(f"    • {cls_name:<28} {conf:.1%}")

    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


# ─── Основная функция ─────────────────────────────────────────────────────────

def process_image(
    inferencer: CarPartInferencer,
    img_path: Path,
    out_dir: Path,
    save_json: bool = False,
) -> Optional[dict]:
    """
    Обрабатывает одно изображение: инференс → визуализация → отчёт.

    Args:
        inferencer: инициализированный CarPartInferencer
        img_path:   путь к входному изображению
        out_dir:    папка для сохранения результатов
        save_json:  также сохранять JSON с сырыми данными

    Returns:
        dict с ключами results, inference_ms, output_image, output_report
        или None если изображение не удалось прочитать
    """
    image = cv2.imread(str(img_path))
    if image is None:
        logger.warning("Не удалось прочитать: %s", img_path)
        return None

    H, W = image.shape[:2]
    logger.info("Обрабатываем: %s  (%dx%d)", img_path.name, W, H)

    t0 = time.perf_counter()
    detections = inferencer.predict(image)
    t1 = time.perf_counter()
    inference_ms = (t1 - t0) * 1000

    logger.info(
        "  Обнаружено: %d элементов  |  %.1f мс",
        len(detections), inference_ms
    )

    # ── Визуализация ──────────────────────────────────────────────────────────
    vis = draw_detections(image, detections)
    out_img = out_dir / (img_path.stem + "_masked" + img_path.suffix)
    cv2.imwrite(str(out_img), vis)

    # ── Текстовый отчёт ───────────────────────────────────────────────────────
    report_text = build_report(
        image_path   = str(img_path),
        detections   = detections,
        inference_ms = inference_ms,
        gauss_kernel = inferencer.gauss_kernel,
        gauss_sigma  = inferencer.gauss_sigma,
        gauss_thresh = inferencer.gauss_thresh,
    )
    out_txt = out_dir / (img_path.stem + "_report.txt")
    out_txt.write_text(report_text, encoding="utf-8")

    # ── JSON (опционально) ────────────────────────────────────────────────────
    if save_json:
        json_data = {
            "file":         str(img_path),
            "image_size":   [W, H],
            "inference_ms": round(inference_ms, 2),
            "detections": [
                {
                    "class_id":   d.class_id,
                    "class_name": d.class_name,
                    "confidence": round(d.confidence, 4),
                    "bbox":       [round(v, 1) for v in d.bbox],
                    "area_px":    d.area_px,
                    "area_pct":   round(d.area_pct, 3),
                }
                for d in detections
            ],
        }
        out_json = out_dir / (img_path.stem + "_detections.json")
        out_json.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    print(report_text)
    print(f"\nИзображение → {out_img}")
    print(f"Отчёт       → {out_txt}\n")

    return {
        "detections":    detections,
        "inference_ms":  inference_ms,
        "output_image":  out_img,
        "output_report": out_txt,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="YOLOv12-seg инференс: изображение → маски + отчёт",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Основные
    p.add_argument("--weights",  required=True,
                   help="Путь к .pt файлу (например: runs/segment/best.pt)")
    p.add_argument("--source",   required=True,
                   help="Путь к изображению или папке с изображениями")
    p.add_argument("--output",   default="outputs",
                   help="Папка для результатов")

    # Инференс
    p.add_argument("--conf",       type=float, default=0.35,
                   help="Порог уверенности детекции")
    p.add_argument("--iou",        type=float, default=0.45,
                   help="IoU порог для NMS")
    p.add_argument("--imgsz",      type=int,   default=640,
                   help="Размер входа модели (640 / 896 / 1024)")
    p.add_argument("--device",     default="",
                   help="Устройство: '0' (GPU), 'cpu', '' = авто")

    # Маска
    p.add_argument("--mask-thresh", type=float, default=0.5,
                   help="Порог бинаризации float32 маски YOLO (снизьте до 0.4 для тонких краёв)")

    # Гауссово сглаживание
    p.add_argument("--gauss-kernel", type=int,   default=15,
                   help="Размер ядра Гаусса (нечётное; авто-корректируется если чётное)")
    p.add_argument("--gauss-sigma",  type=float, default=5.0,
                   help="σ Гаусса — сила сглаживания")
    p.add_argument("--gauss-thresh", type=float, default=0.45,
                   help="Порог перебинаризации после размытия (0.45 = слегка расширяет маску)")

    # Дополнительно
    p.add_argument("--min-area",  type=float, default=0.001,
                   help="Минимальная площадь маски как доля кадра (фильтр шума)")
    p.add_argument("--save-json", action="store_true",
                   help="Сохранять JSON с результатами детекции")
    p.add_argument("--no-contour", action="store_true",
                   help="Не рисовать контур поверх маски")
    p.add_argument("--alpha",     type=float, default=0.35,
                   help="Прозрачность заливки маски [0..1]")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    source = Path(args.source)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Собираем список изображений
    if source.is_file():
        images = [source]
    elif source.is_dir():
        images = sorted(
            list(source.glob("*.jpg"))  +
            list(source.glob("*.jpeg")) +
            list(source.glob("*.png"))  +
            list(source.glob("*.webp"))
        )
        logger.info("Найдено %d изображений в %s", len(images), source)
    else:
        logger.error("--source не существует: %s", source)
        sys.exit(1)

    if not images:
        logger.error("Изображений не найдено в %s", source)
        sys.exit(1)

    # Инициализация модели
    inferencer = CarPartInferencer(
        weights         = args.weights,
        conf_thresh     = args.conf,
        iou_thresh      = args.iou,
        imgsz           = args.imgsz,
        mask_bin_thresh = args.mask_thresh,
        gauss_kernel    = args.gauss_kernel,
        gauss_sigma     = args.gauss_sigma,
        gauss_thresh    = args.gauss_thresh,
        min_area_ratio  = args.min_area,
        device          = args.device,
    )

    # Обработка
    total_ms = 0.0
    processed = 0

    for img_path in images:
        res = process_image(
            inferencer = inferencer,
            img_path   = img_path,
            out_dir    = out_dir,
            save_json  = args.save_json,
        )
        if res:
            total_ms += res["inference_ms"]
            processed += 1

    if processed > 1:
        avg_ms = total_ms / processed
        logger.info(
            "Готово. Обработано: %d  |  среднее время: %.1f мс  |  %.1f FPS",
            processed, avg_ms, 1000 / avg_ms
        )
    elif processed == 1:
        logger.info("Готово. Результаты в: %s", out_dir)


if __name__ == "__main__":
    main()