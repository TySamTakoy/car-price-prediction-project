"""
predictor.py — логика инференса модели повреждений (UNet + EfficientNet-B4).

Адаптирован из demo.py:
  · Убрана визуализация (matplotlib) — не нужна в сервисе
  · Добавлен возврат prob_map и mask_bin как numpy массивов
  · Модель загружается один раз при старте сервиса
  · Поддержка CPU и GPU автоматически
"""

from __future__ import annotations

import os
import logging
from typing import Tuple

import numpy as np
import torch
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from PIL import Image

logger = logging.getLogger("cv_service_2.predictor")

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ ПО УМОЛЧАНИЮ
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_IMG_SIZE  = 384
DEFAULT_THRESHOLD = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# КЛАСС ПРЕДИКТОРА
# ─────────────────────────────────────────────────────────────────────────────

class DamagePredictor:
    """
    Загружает UNet + EfficientNet-B4 и выполняет инференс повреждений.

    Использование:
        predictor = DamagePredictor(checkpoint_path="checkpoints/best_model.pth")
        prob_map, mask_bin, damage_pct, level = predictor.predict(image_np)
    """

    def __init__(
        self,
        checkpoint_path: str,
        threshold: float = DEFAULT_THRESHOLD,
        device: str = "",
    ):
        """
        Args:
            checkpoint_path: путь к .pth файлу с весами
            threshold:       порог бинаризации маски [0, 1]
            device:          "cuda" / "cpu" / "" (авто)
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(
                f"Файл весов не найден: {checkpoint_path}"
            )

        # Определяем устройство
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )

        logger.info("Устройство: %s", self.device)

        # Загружаем чекпоинт
        ckpt = torch.load(checkpoint_path, map_location=self.device)
        cfg  = ckpt.get("config", {})

        self.img_size  = cfg.get("img_size", DEFAULT_IMG_SIZE)
        self.threshold = threshold

        saved_epoch    = ckpt.get("epoch", "?")
        saved_dice     = ckpt.get("val_dice", "?")
        logger.info(
            "Загрузка чекпоинта: эпоха=%s  val_dice=%s", saved_epoch, saved_dice
        )

        # Строим модель
        self.model = smp.Unet(
            encoder_name    = "efficientnet-b4",
            encoder_weights = None,
            in_channels     = 3,
            classes         = 1,
            activation      = None,
        ).to(self.device)

        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()

        # Трансформация для инференса
        self.transform = A.Compose([
            A.Resize(self.img_size, self.img_size),
            A.Normalize(
                mean=(0.485, 0.456, 0.406),
                std =(0.229, 0.224, 0.225),
            ),
            ToTensorV2(),
        ])

        logger.info(
            "Модель загружена. img_size=%d  threshold=%.2f  device=%s",
            self.img_size, self.threshold, self.device
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ИНФЕРЕНС
    # ─────────────────────────────────────────────────────────────────────────

    @torch.no_grad()
    def predict(
        self,
        image_np: np.ndarray,
        threshold: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray, float, str]:
        """
        Запускает модель на изображении.

        Args:
            image_np:  np.ndarray (H, W, 3) RGB uint8
            threshold: порог бинаризации, если None — используется self.threshold

        Returns:
            prob_map   np.ndarray (H, W) float32 [0, 1] — карта вероятностей
            mask_bin   np.ndarray (H, W) uint8 {0, 1}   — бинарная маска
            damage_pct float — процент повреждённых пикселей от всего изображения
            level      str   — "Нет" / "Слабые" / "Умеренные" / "Сильные"
        """
        if threshold is None:
            threshold = self.threshold

        orig_h, orig_w = image_np.shape[:2]

        # Предобработка
        augmented = self.transform(image=image_np)
        tensor    = augmented["image"].unsqueeze(0).to(self.device)

        # Инференс
        logits = self.model(tensor)
        prob   = torch.sigmoid(logits)[0, 0].cpu().numpy()  # (img_size, img_size)

        # Возвращаем к исходному размеру
        prob_resized = np.array(
            Image.fromarray(prob).resize(
                (orig_w, orig_h), Image.BILINEAR
            )
        ).astype(np.float32)

        # Бинаризация
        mask_bin   = (prob_resized > threshold).astype(np.uint8)

        # Метрики
        damage_pct = float(mask_bin.sum()) / float(mask_bin.size) * 100.0
        level      = self._pct_to_level(damage_pct)

        return prob_resized, mask_bin, damage_pct, level

    @staticmethod
    def _pct_to_level(pct: float) -> str:
        """Переводит процент повреждения изображения в текстовый уровень."""
        if pct < 1.0:
            return "Нет"
        elif pct < 5.0:
            return "Слабые"
        elif pct < 15.0:
            return "Умеренные"
        else:
            return "Сильные"