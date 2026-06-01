"""
iou_matcher.py — связывание кузовных элементов с повреждениями через IoU масок.

Логика:
  Для каждого обнаруженного элемента (CV Service #1) вычисляем
  процент его площади, покрытый маской повреждений (CV Service #2).

  Используем compute_damage_pct_of_element из rle_utils:
    damage_pct = intersection(element_mask, damage_mask) / element_area * 100

  Порог: если damage_pct >= MIN_DAMAGE_PCT → элемент считается повреждённым.

  Почему не стандартный IoU (0.5):
    Повреждение (царапина) занимает 3-5% площади двери.
    Стандартный IoU = 3% / (97% + 3%) = 0.03 — всегда будет близко к нулю.
    Нам важна не площадь пересечения относительно объединения,
    а доля повреждённой площади от площади конкретного элемента.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np

from rle_utils import smart_decode, compute_damage_pct_of_element, damage_pct_to_level

logger = logging.getLogger("orchestrator.iou_matcher")

# Минимальный порог — элемент считается повреждённым
MIN_DAMAGE_PCT = 1.0


@dataclass
class MatchedElement:
    """Результат matching одного элемента с маской повреждений."""
    element_id:      int
    name:            str
    confidence:      float
    bbox:            List[float]
    area_px:         int
    area_pct:        float
    damage_detected: bool
    damage_pct:      float    # % площади элемента покрытый повреждением
    damage_level:    str      # Нет / Слабые / Умеренные / Сильные


def match_elements_with_damage(
    elements:     List[Dict[str, Any]],   # из CV Service #1
    damage_mask_encoded: Dict,             # из CV Service #2
    image_shape:  tuple,                   # (H, W) оригинального изображения
) -> List[MatchedElement]:
    """
    Для каждого элемента вычисляет степень повреждения через маски.

    Args:
        elements:            список элементов от CV Service #1
                             каждый содержит: element_id, name, confidence,
                             bbox, area_px, area_pct, mask_encoded
        damage_mask_encoded: RLE маска повреждений от CV Service #2
        image_shape:         (H, W) для проверки совместимости масок

    Returns:
        список MatchedElement с заполненными полями damage_*
    """
    H, W = image_shape

    # Декодируем маску повреждений
    damage_mask = smart_decode(damage_mask_encoded).astype(np.uint8)

    # Если маска повреждений другого размера — ресайзим
    if damage_mask.shape != (H, W):
        import cv2
        damage_mask = cv2.resize(
            damage_mask, (W, H), interpolation=cv2.INTER_NEAREST
        ).astype(np.uint8)
        logger.debug(
            "Маска повреждений под ресайз: %s → (%d, %d)",
            damage_mask.shape, H, W
        )

    results: List[MatchedElement] = []

    for el in elements:
        element_mask_encoded = el.get("mask_encoded", {})

        # Декодируем маску элемента
        element_mask = smart_decode(element_mask_encoded).astype(np.uint8)

        # Ресайзим если нужно
        if element_mask.shape != (H, W):
            import cv2
            element_mask = cv2.resize(
                element_mask, (W, H), interpolation=cv2.INTER_NEAREST
            ).astype(np.uint8)

        # Считаем % повреждения элемента
        damage_pct = compute_damage_pct_of_element(element_mask, damage_mask)
        damage_detected = damage_pct >= MIN_DAMAGE_PCT
        damage_level = damage_pct_to_level(damage_pct) if damage_detected else "Нет"

        if damage_detected:
            logger.info(
                "Повреждение: %s  %.1f%%  [%s]",
                el["name"], damage_pct, damage_level
            )

        results.append(MatchedElement(
            element_id      = el["element_id"],
            name            = el["name"],
            confidence      = el["confidence"],
            bbox            = el["bbox"],
            area_px         = el["area_px"],
            area_pct        = el["area_pct"],
            damage_detected = damage_detected,
            damage_pct      = round(damage_pct, 3),
            damage_level    = damage_level,
        ))

    damaged_count = sum(1 for r in results if r.damage_detected)
    logger.info(
        "Matching завершён: %d элементов, %d повреждено",
        len(results), damaged_count
    )

    return results