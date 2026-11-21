# -*- coding: utf-8 -*-
"""
ai/memory_engine.py
Умная selective memory system.

Архитектура (по инструкции):
  SHORT-TERM: последние 8 сообщений (200-400 токенов)
  LONG-TERM:  3-8 фактов с importance score (max 150 токенов)
  CHARACTER-SPECIFIC: каждый персонаж запоминает разное
  DYNAMIC INJECTION: только релевантные факты для текущего сообщения
"""
import re
from datetime import datetime


# ── Что каждый персонаж запоминает ───────────────────────────
# Ключи = категории памяти. Значения = триггерные слова для детекции.
CHARACTER_MEMORY_FOCUS = {
    "ari": {
        "emotions":    ["чувствую", "грустно", "радостно", "страшно", "переживаю", "боюсь",
                        "сезінемін", "мұңлымын", "қорқамын", "қуаныштымын"],
        "dreams":      ["мечта", "хочу стать", "мечтаю", "нравится", "люблю",
                        "арман", "болғым келеді", "ұнайды"],
        "mood":        ["настроение", "сегодня", "устал", "энергия",
                        "көңіл", "бүгін", "шаршадым"],
    },
    "max": {
        "goals":       ["цель", "хочу", "планирую", "собираюсь", "намерен",
                        "мақсат", "жоспар", "ойладым"],
        "progress":    ["получилось", "сделал", "достиг", "удалось", "прогресс",
                        "болды", "жасадым", "ілгерілеу"],
        "failures":    ["не получилось", "облажался", "провалил", "сдался",
                        "болмады", "жаңылыстым"],
    },
    "appa": {
        "pain":        ["тяжело", "больно", "плачу", "одиноко", "не могу",
                        "ауыр", "жылаймын", "жалғыз"],
        "relationships": ["мама", "папа", "друг", "парень", "девушка", "семья",
                          "анам", "әкем", "дос", "жігіт", "қыз", "отбасы"],
        "history":     ["раньше", "в детстве", "когда-то", "было время",
                        "бұрын", "балалықта"],
    },
    "drako": {
        "fears":       ["боюсь", "страх", "тревога", "беспокоит",
                        "қорқамын", "үрей", "алаңдаймын"],
        "philosophy":  ["смысл", "жизнь", "зачем", "почему", "вечность",
                        "мән", "өмір", "неліктен", "мәңгілік"],
        "loneliness":  ["одиноко", "никто не понимает", "один", "пусто",
                        "жалғыз", "ешкім түсінбейді"],
    },
    "lex": {
        "languages":   ["язык", "учу", "изучаю", "слово", "говорю",
                        "тіл", "үйренемін", "сөз"],
        "travel":      ["страна", "город", "путешествие", "был в", "побывал",
                        "ел", "қала", "саяхат", "болдым"],
        "culture":     ["традиция", "культура", "обычай", "менталитет",
                        "дәстүр", "мәдениет", "салт"],
    },
    "tim": {
        "money":       ["деньги", "зарплата", "доход", "трачу", "откладываю",
                        "ақша", "жалақы", "кіріс", "жинаймын"],
        "goals_fin":   ["хочу купить", "накопить", "инвестиция", "бизнес",
                        "сатып алғым", "жинағым", "инвестиция"],
    },
    "nura": {
        "school":      ["школа", "учёба", "экзамен", "оценка", "класс",
                        "мектеп", "оқу", "емтихан", "баға"],
        "peers":       ["друзья", "одноклассники", "конфликт", "популярный",
                        "достар", "сыныптастар", "жанжал"],
        "social":      ["тикток", "инстаграм", "соцсети", "хайп",
                        "тіктік", "инстаграм"],
    },
    "kod": {
        "tech":        ["программирую", "код", "python", "javascript", "ошибка", "баг",
                        "бағдарламалаймын", "код", "қате"],
        "learning":    ["изучаю", "учусь", "понял", "не понимаю",
                        "үйренемін", "түсіндім", "түсінбеймін"],
    },
}

# Дефолтные категории для остальных персонажей
_DEFAULT_FOCUS = {
    "interests": ["нравится", "люблю", "увлекаюсь", "интересно", "ұнайды", "жақсы көремін"],
    "important":  ["важно", "главное", "всегда", "никогда", "маңызды", "әрдайым"],
}


def get_focus(agent_id: str) -> dict:
    return CHARACTER_MEMORY_FOCUS.get(agent_id, _DEFAULT_FOCUS)


# ── Умное извлечение фактов из сообщения ─────────────────────
def extract_facts(user_msg: str, agent_id: str) -> list[dict]:
    """
    Извлекает короткие факты из сообщения пользователя.
    Возвращает список {content, category, importance}.
    """
    facts = []
    msg_lower = user_msg.lower()
    focus = get_focus(agent_id)

    for category, keywords in focus.items():
        if any(kw in msg_lower for kw in keywords):
            # Берём первые 80 символов как факт
            fact = user_msg.strip()[:80]
            # Очищаем
            fact = re.sub(r'\s+', ' ', fact).strip()
            if len(fact) < 5:
                continue
            # Importance: чем эмоциональнее — тем важнее
            importance = _calc_importance(user_msg, category)
            facts.append({
                "content":    fact,
                "category":   category,
                "importance": importance,
            })
            break  # одного факта за раз достаточно

    return facts


def _calc_importance(text: str, category: str) -> int:
    """Рассчитывает важность факта 1-10."""
    score = 5
    emotional_words = [
        "всегда", "никогда", "очень", "сильно", "ненавижу", "обожаю",
        "страшно", "мечта", "главное", "важно",
        "әрдайым", "ешқашан", "өте", "қатты", "жек көремін", "сүйемін",
        "маңызды", "арман"
    ]
    if any(w in text.lower() for w in emotional_words):
        score += 2
    if category in ("fears", "pain", "dreams", "goals"):
        score += 1
    if len(text) > 50:
        score += 1
    return min(10, score)


# ── Релевантные факты для текущего сообщения ─────────────────
def get_relevant_memories(memories: list[dict], current_msg: str,
                          agent_id: str, max_facts: int = 5) -> list[str]:
    """
    Выбирает только релевантные факты для текущего сообщения.
    НЕ вставляет всю память — только нужное.
    """
    if not memories:
        return []

    msg_lower = current_msg.lower()
    focus = get_focus(agent_id)

    # Определяем активные категории текущего сообщения
    active_cats = set()
    for category, keywords in focus.items():
        if any(kw in msg_lower for kw in keywords):
            active_cats.add(category)

    # Сортируем: релевантные + высокая важность первыми
    def score_mem(m):
        cat_match = 3 if m.get("category") in active_cats else 0
        return m.get("importance", 5) + cat_match

    sorted_mems = sorted(memories, key=score_mem, reverse=True)

    # Берём только топ N, каждый не длиннее 60 символов
    result = []
    for m in sorted_mems[:max_facts]:
        content = m.get("content", "").strip()
        if len(content) > 60:
            content = content[:60] + "..."
        if content:
            result.append(content)

    return result


# ── Форматируем memory block для промпта ─────────────────────
def format_memory_block(facts: list[str], lang: str = "ru") -> str:
    """Форматирует память. MAX 150 токенов."""
    if not facts:
        return ""
    facts = facts[:5]
    joined = "\n".join(f"- {f}" for f in facts)
    labels = {
        "kk": "[ЕСІҢДЕ]",
        "en": "[YOU REMEMBER]",
        "de": "[DU ERINNERST DICH]",
        "ru": "[ПОМНИШЬ]",
    }
    return f"{labels.get(lang, labels['ru'])}\n{joined}"


# ── Short-term context (последние N сообщений) ────────────────
def format_short_term(messages: list[dict], max_messages: int = 8) -> list[dict]:
    """
    Возвращает последние N сообщений для контекста.
    Это short-term memory — не более 8 сообщений.
    """
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    return recent


# ── Авто-сохранение фактов ────────────────────────────────────
def should_save_fact(text: str, agent_id: str) -> bool:
    """Проверяет стоит ли сохранять факт из этого сообщения."""
    if len(text.strip()) < 8:
        return False
    focus = get_focus(agent_id)
    t = text.lower()
    return any(
        any(kw in t for kw in kws)
        for kws in focus.values()
    )