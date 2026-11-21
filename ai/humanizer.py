# -*- coding: utf-8 -*-
"""
VIVLOS — Humanizer Layer.
Делает ответы AI менее "роботными": добавляет естественные паузы,
заминки, реакции. Применяется ПОСЛЕ генерации.
"""
import random
import re


# Естественные вводные реакции (не каждый раз!)
HUMAN_PREFIXES = {
    "ru": ["Хм...", "Ой,", "Слушай,", "Знаешь,", "Ну,", "Так,", "О,", "Погоди,"],
    "kk": ["Хм...", "Ой,", "Тыңда,", "Білесің бе,", "Сонымен,", "О,"],
}

# Заполнители-задержки (имитация раздумий)
THINKING_FILLERS = {
    "ru": ["дай подумаю...", "как бы сказать...", "честно говоря,"],
    "kk": ["ойланайын...", "қалай айтсам...", "шынымды айтсам,"],
}


def humanize(text: str, lang: str = "ru",
             energy: int = 6, add_prefix_chance: float = 0.18) -> str:
    """
    Очеловечивает текст.
    - Иногда (18%) добавляет вводную реакцию.
    - Чистит роботные конструкции.
    - НЕ трогает короткие ответы (они и так живые).
    """
    if not text:
        return text

    text = text.strip()

    # Убираем роботные начала
    robotic_starts = {
        "ru": ["Конечно!", "Конечно,", "Безусловно,", "Отличный вопрос!",
               "Я рад помочь", "Как ИИ", "Как искусственный интеллект",
               "Я понимаю ваш вопрос", "Хороший вопрос!"],
        "kk": ["Әрине!", "Әрине,", "Тамаша сұрақ!", "Мен қуаныштымын",
               "Жасанды интеллект ретінде", "Жақсы сұрақ!"],
    }
    for bad in robotic_starts.get(lang, []):
        if text.startswith(bad):
            text = text[len(bad):].strip()
            text = text[0].upper() + text[1:] if text else text

    # Убираем нумерованные списки (1. 2. 3.) — превращаем в живую речь
    if re.search(r'^\s*\d+\.\s', text, re.MULTILINE):
        lines = [re.sub(r'^\s*\d+\.\s*', '', l).strip()
                 for l in text.split('\n') if l.strip()]
        text = ' '.join(lines)

    # Иногда добавляем вводную реакцию (только если ответ длиннее 4 слов)
    word_count = len(text.split())
    if word_count > 4 and random.random() < add_prefix_chance:
        prefix = random.choice(HUMAN_PREFIXES.get(lang, HUMAN_PREFIXES["ru"]))
        # Не дублируем если уже начинается похоже
        if not any(text.startswith(p) for p in HUMAN_PREFIXES.get(lang, [])):
            text = f"{prefix} {text[0].lower() + text[1:]}"

    return text


def add_typing_delay(text: str) -> float:
    """
    Возвращает реалистичную задержку перед ответом (сек).
    Имитирует время на 'обдумывание' + 'печать'.
    Чем длиннее ответ — тем дольше, но с разбросом.
    """
    word_count = len(text.split())
    base = 0.4 + random.uniform(0, 0.6)         # раздумье
    typing = word_count * random.uniform(0.04, 0.08)  # печать
    return round(min(3.5, base + typing), 2)


def split_into_chunks(text: str):
    """
    Разбивает длинный ответ на части как в реальном чате
    (человек пишет несколькими сообщениями).
    Возвращает список кусков для последовательной отправки.
    """
    # Разбиваем по предложениям
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= 2:
        return [text]

    chunks = []
    current = ""
    for s in sentences:
        current += (" " if current else "") + s
        # Случайно решаем закончить кусок
        if len(current) > 40 and random.random() < 0.4:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]