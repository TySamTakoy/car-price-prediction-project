"""
rle_utils.py — кодирование и декодирование бинарных масок в формат RLE.

Используется во всех Python-сервисах:
  · cv_service_1   — кодирует маски кузовных элементов от YOLOv12
  · cv_service_2   — кодирует маску повреждений от UNet
  · orchestrator   — декодирует маски обоих сервисов для IoU matching

Формат RLE (Run-Length Encoding):
  Бинарная маска построчно разворачивается в одномерный массив,
  затем записывается как чередующиеся пары (count_zeros, count_ones).

  Пример:
    маска (2×4):  [[0,0,1,1],
                   [1,0,0,1]]
    flat:         [0,0,1,1,1,0,0,1]
    RLE пары:     [(2,3),(2,1)]  → "2,3,2,1"

  Декодирование — обратная операция: разворачиваем пары обратно в flat,
  затем reshape по оригинальному shape.

Передача по HTTP:
  encode_mask()  → строка "2,3,2,1" + shape [H, W] → кладём в JSON
  decode_mask()  → принимает строку + shape → возвращает np.ndarray uint8

Почему не pycocotools:
  pycocotools требует нативную компиляцию C и проблематична в Docker
  на Windows. Своя реализация не имеет зависимостей кроме numpy и
  показывает достаточную скорость для масок до 4K разрешения.
"""

from __future__ import annotations

import base64
import zlib
from typing import Tuple

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# ОСНОВНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def encode_mask(mask: np.ndarray) -> dict:
    """
    Кодирует бинарную маску в компактный RLE-словарь.

    Args:
        mask: np.ndarray, dtype uint8 или bool, значения {0, 1}.
              Форма (H, W).

    Returns:
        dict с ключами:
          "rle"   — строка вида "2,3,2,1" (чередующиеся runs нулей и единиц)
          "shape" — [H, W] оригинального массива

    Raises:
        ValueError: если маска не двумерная или содержит значения вне {0,1}

    Example:
        >>> mask = np.array([[0,0,1],[1,1,0]], dtype=np.uint8)
        >>> enc = encode_mask(mask)
        >>> enc["shape"]
        [2, 3]
    """
    if mask.ndim != 2:
        raise ValueError(f"Ожидается 2D маска, получено: {mask.ndim}D")

    mask_bin = mask.astype(np.uint8)
    unique = np.unique(mask_bin)
    if not set(unique.tolist()).issubset({0, 1}):
        raise ValueError(f"Маска должна содержать только 0 и 1, найдено: {unique}")

    H, W = mask_bin.shape
    flat = mask_bin.flatten()  # построчно (row-major)

    # Считаем runs через diff
    # padded: добавляем -1 по краям для корректного подсчёта крайних runs
    padded = np.concatenate([[2], flat, [2]])
    change_points = np.where(padded[1:] != padded[:-1])[0]

    runs = np.diff(change_points).tolist()

    # Определяем, начинается ли с нулей или единиц
    starts_with_ones = bool(flat[0] == 1)

    # Формат: всегда начинаем с count_zeros
    # Если маска начинается с единиц — prepend 0 (нулевой run нулей)
    if starts_with_ones:
        runs = [0] + runs

    # Убеждаемся что длина чётная (пары zeros+ones)
    if len(runs) % 2 != 0:
        runs.append(0)

    rle_str = ",".join(map(str, runs))

    return {
        "rle":   rle_str,
        "shape": [H, W],
    }


def decode_mask(encoded: dict) -> np.ndarray:
    """
    Декодирует RLE-словарь обратно в бинарную маску.

    Args:
        encoded: dict с ключами "rle" (str) и "shape" ([H, W])

    Returns:
        np.ndarray, dtype uint8, форма (H, W), значения {0, 1}

    Raises:
        ValueError: если формат rle некорректен или shape не совпадает

    Example:
        >>> mask = np.array([[0,0,1],[1,1,0]], dtype=np.uint8)
        >>> assert np.array_equal(mask, decode_mask(encode_mask(mask)))
    """
    rle_str = encoded["rle"]
    H, W    = encoded["shape"]
    total   = H * W

    if not rle_str:
        return np.zeros((H, W), dtype=np.uint8)

    runs = list(map(int, rle_str.split(",")))

    if len(runs) % 2 != 0:
        raise ValueError(f"RLE должен содержать чётное число элементов, получено: {len(runs)}")

    flat = np.zeros(total, dtype=np.uint8)
    pos = 0

    for i in range(0, len(runs), 2):
        zeros_count = runs[i]
        ones_count  = runs[i + 1]

        pos += zeros_count  # пропускаем нули

        end = pos + ones_count
        if end > total:
            raise ValueError(
                f"RLE выходит за границы массива: pos={pos}, ones={ones_count}, total={total}"
            )
        flat[pos:end] = 1
        pos = end

    return flat.reshape(H, W)


# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────────────────────

def encode_mask_compact(mask: np.ndarray) -> dict:
    """
    Альтернативное кодирование: бинарные данные маски сжимаются zlib
    и кодируются в base64. Быстрее для больших масок с плавными областями.

    Используй вместо encode_mask() если размер JSON критичен
    (например, 4K фото с большими масками).

    Returns:
        dict с ключами:
          "data"     — base64 строка сжатых байт
          "shape"    — [H, W]
          "encoding" — "zlib+base64" (маркер для decode_mask_compact)
    """
    H, W = mask.shape
    compressed = zlib.compress(mask.astype(np.uint8).tobytes(), level=6)
    b64 = base64.b64encode(compressed).decode("ascii")
    return {
        "data":     b64,
        "shape":    [H, W],
        "encoding": "zlib+base64",
    }


def decode_mask_compact(encoded: dict) -> np.ndarray:
    """
    Декодирует маску из формата zlib+base64.
    """
    H, W = encoded["shape"]
    compressed = base64.b64decode(encoded["data"])
    flat = np.frombuffer(zlib.decompress(compressed), dtype=np.uint8)
    return flat.reshape(H, W)


def smart_encode(mask: np.ndarray) -> dict:
    """
    Выбирает оптимальное кодирование автоматически:
      · RLE    — если маска разреженная (< 30% единиц или > 70%)
      · zlib   — если маска плотная (много связных областей)

    Рекомендуется использовать этот метод в продакшне.
    """
    density = mask.mean()
    if density < 0.30 or density > 0.70:
        return encode_mask(mask)
    else:
        return encode_mask_compact(mask)


def smart_decode(encoded: dict) -> np.ndarray:
    """
    Декодирует маску независимо от формата кодирования.
    Определяет формат по наличию ключа "encoding".
    """
    if encoded.get("encoding") == "zlib+base64":
        return decode_mask_compact(encoded)
    return decode_mask(encoded)


def compute_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    """
    Вычисляет IoU (Intersection over Union) двух бинарных масок.

    Используется в оркестраторе для matching элементов и повреждений.

    Args:
        mask_a: np.ndarray uint8 {0,1}, форма (H, W)
        mask_b: np.ndarray uint8 {0,1}, форма (H, W)

    Returns:
        float [0.0, 1.0]

    Note:
        Если обе маски пустые — возвращает 0.0 (не 1.0),
        чтобы не считать "пустое с пустым" как совпадение.
    """
    if mask_a.shape != mask_b.shape:
        raise ValueError(
            f"Формы масок не совпадают: {mask_a.shape} vs {mask_b.shape}"
        )

    intersection = np.logical_and(mask_a, mask_b).sum()
    union        = np.logical_or(mask_a, mask_b).sum()

    if union == 0:
        return 0.0

    return float(intersection) / float(union)


def compute_damage_pct_of_element(
    element_mask: np.ndarray,
    damage_mask:  np.ndarray,
) -> float:
    """
    Вычисляет процент площади элемента, покрытого повреждением.

    Это ключевая метрика оркестратора: не IoU (который был бы мал,
    так как повреждение маленькое относительно всего изображения),
    а именно доля повреждённой площади от площади конкретного элемента.

    Args:
        element_mask: маска кузовного элемента от CV Service #1
        damage_mask:  маска повреждений от CV Service #2

    Returns:
        float [0.0, 100.0] — процент площади элемента с повреждением

    Example:
        Дверь занимает 20% изображения.
        Царапина на двери занимает 2% изображения.
        → damage_pct_of_element = 2% / 20% * 100 = 10%
        → уровень: "Слабые" (< 5% даст "Слабые", здесь 10% → "Умеренные")
    """
    element_area = element_mask.sum()
    if element_area == 0:
        return 0.0

    intersection = np.logical_and(element_mask, damage_mask).sum()
    return float(intersection) / float(element_area) * 100.0


def damage_pct_to_level(pct: float) -> str:
    """
    Переводит процент повреждения элемента в текстовый уровень.

    Пороги считаются от площади самого элемента (не всего изображения).

    Args:
        pct: float, процент площади элемента покрытый повреждением

    Returns:
        str: "Нет" | "Слабые" | "Умеренные" | "Сильные"
    """
    if pct < 1.0:
        return "Нет"
    elif pct < 5.0:
        return "Слабые"
    elif pct < 15.0:
        return "Умеренные"
    else:
        return "Сильные"


# ─────────────────────────────────────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    """Базовые тесты корректности кодирования/декодирования."""
    print("Запуск тестов rle_utils...")

    # Тест 1: простая маска
    mask1 = np.array([[0, 0, 1, 1],
                      [1, 0, 0, 1]], dtype=np.uint8)
    assert np.array_equal(mask1, decode_mask(encode_mask(mask1))), \
        "FAIL: простая маска"
    print("  [OK] Тест 1: простая маска encode→decode")

    # Тест 2: полностью нулевая маска
    mask2 = np.zeros((100, 100), dtype=np.uint8)
    assert np.array_equal(mask2, decode_mask(encode_mask(mask2))), \
        "FAIL: нулевая маска"
    print("  [OK] Тест 2: нулевая маска")

    # Тест 3: полностью единичная маска
    mask3 = np.ones((50, 80), dtype=np.uint8)
    assert np.array_equal(mask3, decode_mask(encode_mask(mask3))), \
        "FAIL: единичная маска"
    print("  [OK] Тест 3: единичная маска")

    # Тест 4: реалистичная маска (прямоугольник внутри)
    mask4 = np.zeros((480, 640), dtype=np.uint8)
    mask4[100:300, 150:450] = 1
    assert np.array_equal(mask4, decode_mask(encode_mask(mask4))), \
        "FAIL: прямоугольная маска"
    print("  [OK] Тест 4: прямоугольная маска 480×640")

    # Тест 5: случайная маска
    rng = np.random.default_rng(42)
    mask5 = rng.integers(0, 2, size=(720, 1280), dtype=np.uint8)
    assert np.array_equal(mask5, decode_mask(encode_mask(mask5))), \
        "FAIL: случайная маска"
    print("  [OK] Тест 5: случайная маска 720×1280")

    # Тест 6: compact encoding
    mask6 = np.zeros((480, 640), dtype=np.uint8)
    mask6[50:200, 100:400] = 1
    assert np.array_equal(mask6, decode_mask_compact(encode_mask_compact(mask6))), \
        "FAIL: compact encode→decode"
    print("  [OK] Тест 6: compact (zlib+base64) encode→decode")

    # Тест 7: smart_encode / smart_decode
    assert np.array_equal(mask4, smart_decode(smart_encode(mask4))), \
        "FAIL: smart encode→decode разреженная"
    assert np.array_equal(mask6, smart_decode(smart_encode(mask6))), \
        "FAIL: smart encode→decode плотная"
    print("  [OK] Тест 7: smart_encode / smart_decode")

    # Тест 8: IoU
    a = np.zeros((10, 10), dtype=np.uint8)
    b = np.zeros((10, 10), dtype=np.uint8)
    a[2:6, 2:6] = 1  # 4×4 = 16 пикселей
    b[4:8, 4:8] = 1  # 4×4 = 16 пикселей, пересечение 2×2 = 4
    iou = compute_iou(a, b)
    # intersection=4, union=16+16-4=28, iou=4/28≈0.1429
    assert abs(iou - 4/28) < 1e-6, f"FAIL: IoU={iou}"
    print(f"  [OK] Тест 8: IoU = {iou:.4f} (ожидается {4/28:.4f})")

    # Тест 9: damage_pct_of_element
    elem = np.zeros((100, 100), dtype=np.uint8)
    elem[0:50, 0:100] = 1   # нижняя половина = 5000 пикселей
    dmg = np.zeros((100, 100), dtype=np.uint8)
    dmg[0:10, 0:100] = 1    # узкая полоса = 1000 пикселей, пересечение = 1000
    pct = compute_damage_pct_of_element(elem, dmg)
    assert abs(pct - 20.0) < 1e-6, f"FAIL: damage_pct={pct}"
    print(f"  [OK] Тест 9: damage_pct_of_element = {pct:.1f}% (ожидается 20.0%)")

    # Тест 10: damage_pct_to_level
    assert damage_pct_to_level(0.5)  == "Нет"
    assert damage_pct_to_level(2.0)  == "Слабые"
    assert damage_pct_to_level(10.0) == "Умеренные"
    assert damage_pct_to_level(20.0) == "Сильные"
    print("  [OK] Тест 10: damage_pct_to_level")

    print("\nВсе тесты пройдены успешно.")


if __name__ == "__main__":
    _run_tests()