"""
predictor.py — предсказание стоимости ремонта кузовных элементов.

Адаптирован из ноутбука Google Colab (lgbm_price_model_final.pkl).

Логика:
  1. Принимает список повреждённых элементов с уровнем повреждения
  2. Маппит YOLO классы → названия деталей в PART_MAP
  3. Определяет тип работы по уровню повреждения:
       Слабые    → Ремонт
       Умеренные → Покраска
       Сильные   → Замена
  4. Для каждой пары (деталь, работа) предсказывает стоимость через LightGBM
  5. Возвращает список стоимостей и итоговую сумму

Элементы без ремонтной стоимости (пропускаются):
  Шина, Колесный диск, Номерной знак, Эмблема,
  Крышка бензобака, ПТФ, Лобовое стекло (→ Стекло лобовое есть в модели)
"""

from __future__ import annotations

import logging
import os
import pickle
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("ml_service_2.predictor")

# ─────────────────────────────────────────────────────────────────────────────
# МАППИНГ: YOLO классы → PART_MAP ключи
# ─────────────────────────────────────────────────────────────────────────────

# Ключи должны совпадать с тем что возвращает CV Service #1 (class_name)
# Значения — ключи для PART_MAP ниже (lowercase)
YOLO_TO_PART_KEY: Dict[str, str] = {
    "Капот":                "капот",
    "Фара":                 "фара",
    "Крышка бензобака":     None,           # нет в модели ремонта
    "Решётка радиатора":    "решётка радиатора",
    "Окно":                 "боковое стекло",
    "Задний фонарь":        "задний фонарь",
    "Лобовое стекло":       "лобовое стекло",
    "Задний бампер":        "задний бампер",
    "Передний бампер":      "передний бампер",
    "Переднее крыло":       "переднее крыло",
    "Заднее крыло":         "заднее крыло",
    "Номерной знак":        None,           # нет в модели ремонта
    "Шина":                 None,           # нет в модели ремонта
    "Дверь":                "передняя дверь",  # усредняем — нет разделения
    "Зеркало заднего вида": "боковое зеркало",
    "Колесный диск":        None,           # нет в модели ремонта
    "Крышка багажника":     "крышка багажника",
    "Крыша":                "крыша",
    "Эмблема":              None,           # нет в модели ремонта
    "ПТФ":                  None,           # нет в модели ремонта
}

# Маппинг уровня повреждения → тип работы
DAMAGE_LEVEL_TO_WORK: Dict[str, str] = {
    "Слабые":    "ремонт",
    "Умеренные": "покраска",
    "Сильные":   "замена",
}

# PART_MAP из ноутбука Colab — нормализация названий деталей
PART_MAP: Dict[str, str] = {
    "передний бампер":     "Бампер передний",
    "бампер передний":     "Бампер передний",
    "задний бампер":       "Бампер задний",
    "бампер задний":       "Бампер задний",
    "переднее крыло":      "Крыло переднее",
    "крыло переднее":      "Крыло переднее",
    "заднее крыло":        "Крыло заднее",
    "крыло заднее":        "Крыло заднее",
    "передняя дверь":      "Дверь передняя",
    "дверь передняя":      "Дверь передняя",
    "задняя дверь":        "Дверь задняя",
    "дверь задняя":        "Дверь задняя",
    "капот":               "Капот",
    "крышка багажника":    "Крышка багажника",
    "лобовое стекло":      "Стекло лобовое",
    "стекло лобовое":      "Стекло лобовое",
    "заднее стекло":       "Стекло заднее",
    "боковое стекло":      "Стекло боковое",
    "фара":                "Фара",
    "задний фонарь":       "Фонарь задний",
    "фонарь задний":       "Фонарь задний",
    "боковое зеркало":     "Зеркало боковое",
    "зеркало":             "Зеркало боковое",
    "решётка радиатора":   "Решётка радиатора",
    "решетка радиатора":   "Решётка радиатора",
    "порог":               "Порог",
    "крыша":               "Крыша",
    "молдинг":             "Молдинг",
    "спойлер":             "Спойлер",
    "подкрылок":           "Подкрылок",
    "стойка":              "Стойка",
    "панель передняя":     "Панель передняя",
    "передняя панель":     "Панель передняя",
    "панель задняя":       "Панель задняя",
    "задняя панель":       "Панель задняя",
    "панель боковая":      "Панель боковая",
    "боковая панель":      "Панель боковая",
}

# WORK_MAP из ноутбука Colab
WORK_MAP: Dict[str, str] = {
    "покраска":         "Покраска",
    "замена":           "Замена",
    "снятие/установка": "Снятие/Установка",
    "снятие":           "Снятие/Установка",
    "установка":        "Снятие/Установка",
    "жестяные работы":  "Жестяные работы",
    "жесть":            "Жестяные работы",
    "ремонт":           "Ремонт",
    "капремонт":        "Капремонт",
}


# ─────────────────────────────────────────────────────────────────────────────
# ДАТАКЛАССЫ
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DamagedElement:
    """Входные данные — повреждённый элемент от оркестратора."""
    part:         str    # YOLO class_name, например "Передний бампер"
    damage_level: str    # "Слабые" / "Умеренные" / "Сильные"


@dataclass
class RepairItem:
    """Результат — стоимость ремонта одного элемента."""
    element:       str           # нормализованное название детали
    yolo_name:     str           # оригинальное имя из YOLO
    procedure:     str           # тип работы: Ремонт / Покраска / Замена
    cost_min:      int           # нижняя граница (−12%)
    cost_mid:      int           # центральная оценка
    cost_max:      int           # верхняя граница (+12%)
    damage_level:  str           # уровень повреждения


@dataclass
class RepairPrediction:
    """Итоговый результат предсказания ремонта."""
    repair_items:      List[RepairItem]
    total_cost_min:    int
    total_cost_mid:    int
    total_cost_max:    int
    skipped_elements:  List[str]   # элементы без стоимости ремонта


# ─────────────────────────────────────────────────────────────────────────────
# ПРЕДИКТОР
# ─────────────────────────────────────────────────────────────────────────────

class RepairCostPredictor:
    """
    Загружает LightGBM модель и предсказывает стоимость ремонта.

    Использование:
        predictor = RepairCostPredictor("artifacts/lgbm_price_model_final.pkl")
        result = predictor.predict(
            brand="Toyota", model_name="Camry", year=2018,
            damaged_elements=[
                DamagedElement("Передний бампер", "Умеренные"),
                DamagedElement("Переднее крыло",  "Слабые"),
            ]
        )
    """

    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Файл модели не найден: {model_path}")

        logger.info("Загрузка модели: %s", model_path)

        with open(model_path, "rb") as f:
            saved = pickle.load(f)

        self.model    = saved["model"]
        self.encoders = saved["encoders"]
        self.features = saved["features"]

        # Загружаем справочник медианных нормо-часов если есть датасет
        # Если датасета нет — используем захардкоженные дефолты
        self.hq_median: Optional[pd.DataFrame] = None
        self._load_hq_median()

        logger.info("Модель загружена. Features: %s", self.features)

    def _load_hq_median(self) -> None:
        """
        Пытается загрузить справочник медианных нормо-часов из CSV.
        Если CSV недоступен — используем дефолтные значения.
        """
        csv_path = os.getenv(
            "HQ_CSV_PATH",
            "/app/artifacts/price_dataset_model_ready_v2.csv"
        )
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                self.hq_median = (
                    df.groupby(["PART_CLEAN", "WORK_TYPE"])["HQ"]
                    .median()
                    .reset_index()
                    .rename(columns={"HQ": "HQ_MEDIAN"})
                )
                logger.info("Справочник нормо-часов загружен из %s", csv_path)
            except Exception as e:
                logger.warning("Не удалось загрузить HQ CSV: %s", e)
        else:
            logger.info(
                "CSV справочник не найден (%s) — используем дефолтные HQ",
                csv_path
            )

    def _get_hq(self, part_clean: str, work_type: str) -> float:
        """
        Возвращает медианное значение нормо-часов для пары (деталь, работа).
        Если справочника нет — возвращает разумный дефолт.
        """
        if self.hq_median is not None:
            row = self.hq_median[
                (self.hq_median["PART_CLEAN"] == part_clean) &
                (self.hq_median["WORK_TYPE"]  == work_type)
            ]
            if len(row) > 0:
                return float(row["HQ_MEDIAN"].values[0])

        # Дефолтные нормо-часы если справочника нет
        defaults: Dict[str, float] = {
            "Покраска":           2.0,
            "Замена":             1.5,
            "Ремонт":             1.5,
            "Жестяные работы":    2.5,
            "Снятие/Установка":   1.0,
            "Капремонт":          4.0,
        }
        return defaults.get(work_type, 1.5)

    def _safe_encode(self, encoder_key: str, value: str) -> int:
        """
        Безопасное кодирование категории.
        Если значение не в обучающем словаре — берём первый класс.
        """
        encoder = self.encoders[encoder_key]
        classes = list(encoder.classes_)
        if value in classes:
            return int(encoder.transform([value])[0])
        logger.warning(
            "Неизвестное значение '%s' для энкодера '%s', используем '%s'",
            value, encoder_key, classes[0]
        )
        return int(encoder.transform([classes[0]])[0])

    def _predict_one(
        self,
        brand:      str,
        model_name: str,
        year:       int,
        part_clean: str,
        work_type:  str,
        hq:         Optional[float] = None,
    ) -> int:
        """
        Предсказывает стоимость одной операции ремонта.

        Returns:
            int — стоимость в рублях
        """
        if hq is None:
            hq = self._get_hq(part_clean, work_type)

        row = pd.DataFrame([{
            "BRAND_ENC":      self._safe_encode("BRAND",      brand),
            "MODEL_ENC":      self._safe_encode("MODEL",      model_name),
            "PART_CLEAN_ENC": self._safe_encode("PART_CLEAN", part_clean),
            "WORK_TYPE_ENC":  self._safe_encode("WORK_TYPE",  work_type),
            "YEAR":           year,
            "HQ":             hq,
        }])

        log_pred = self.model.predict(row[self.features])[0]
        return int(np.expm1(log_pred))

    def predict(
        self,
        brand:             str,
        model_name:        str,
        year:              int,
        damaged_elements:  List[DamagedElement],
    ) -> RepairPrediction:
        """
        Предсказывает стоимость ремонта для всех повреждённых элементов.

        Args:
            brand:            марка автомобиля ("Toyota")
            model_name:       модель автомобиля ("Camry")
            year:             год выпуска (2018)
            damaged_elements: список повреждённых элементов

        Returns:
            RepairPrediction с детализацией по каждому элементу и итогами
        """
        repair_items: List[RepairItem] = []
        skipped:      List[str]        = []

        for elem in damaged_elements:
            # Пропускаем элементы без повреждений
            if elem.damage_level == "Нет":
                continue

            # Маппинг YOLO класса → ключ PART_MAP
            part_key = YOLO_TO_PART_KEY.get(elem.part)
            if part_key is None:
                logger.info(
                    "Элемент '%s' пропущен — нет стоимости ремонта", elem.part
                )
                skipped.append(elem.part)
                continue

            # Нормализация названия детали
            part_clean = PART_MAP.get(part_key.lower())
            if part_clean is None:
                logger.warning("Деталь '%s' не найдена в PART_MAP", part_key)
                skipped.append(elem.part)
                continue

            # Тип работы по уровню повреждения
            work_key = DAMAGE_LEVEL_TO_WORK.get(elem.damage_level)
            if work_key is None:
                logger.warning(
                    "Неизвестный уровень повреждения: '%s'", elem.damage_level
                )
                skipped.append(elem.part)
                continue

            work_type = WORK_MAP.get(work_key)
            if work_type is None:
                skipped.append(elem.part)
                continue

            # Предсказываем стоимость
            try:
                cost_mid = self._predict_one(
                    brand      = brand,
                    model_name = model_name,
                    year       = year,
                    part_clean = part_clean,
                    work_type  = work_type,
                )
                cost_min = int(cost_mid * 0.88)
                cost_max = int(cost_mid * 1.12)

                repair_items.append(RepairItem(
                    element      = part_clean,
                    yolo_name    = elem.part,
                    procedure    = work_type,
                    cost_min     = cost_min,
                    cost_mid     = cost_mid,
                    cost_max     = cost_max,
                    damage_level = elem.damage_level,
                ))

                logger.info(
                    "%s | %s | %s → %s руб (%s–%s)",
                    elem.part, elem.damage_level, work_type,
                    f"{cost_mid:,}", f"{cost_min:,}", f"{cost_max:,}"
                )

            except Exception as e:
                logger.error(
                    "Ошибка предсказания для '%s': %s", elem.part, e
                )
                skipped.append(elem.part)

        # Итоговые суммы
        total_mid = sum(item.cost_mid for item in repair_items)
        total_min = sum(item.cost_min for item in repair_items)
        total_max = sum(item.cost_max for item in repair_items)

        return RepairPrediction(
            repair_items     = repair_items,
            total_cost_min   = total_min,
            total_cost_mid   = total_mid,
            total_cost_max   = total_max,
            skipped_elements = skipped,
        )