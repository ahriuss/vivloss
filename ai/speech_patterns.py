# -*- coding: utf-8 -*-
"""
ai/speech_patterns.py
Уникальный голос каждого персонажа — POST-GENERATION фильтр.
Применяется ПОСЛЕ ответа модели, не через промпт.
"""
import random
import re

# ── Паттерны речи каждого персонажа ──────────────────────────
SPEECH_PATTERNS = {
    "ari": {
        "fillers_ru":   ["Хм...", "Ой,", "Погоди,", "О!", "Слушай,", "Знаешь,"],
        "fillers_kk":   ["Хм...", "Ой,", "Тоқта,", "О!", "Тыңда,", "Рас па?", "Иә-иә,", "Ойпырмай,"],
        "fillers_en":   ["Hmm...", "Oh!", "Wait,", "Right,", "Actually,"],
        "fillers_de":   ["Hmm...", "Oh!", "Warte,", "Also,", "Ja,"],
        "starters_ru":  ["Ой, ", "О! ", "Хм, ", "Слушай, "],
        "starters_kk":  ["Ой, ", "О! ", "Хм, ", "Тыңда, "],
        "emoji_rate":    0.25,        # вероятность добавить эмодзи
        "emojis":        ["🦊", "✨", "📚", "🍵", "💡", "🌟"],
        "max_sentences": 3,
        "min_sentences": 1,
        "temperature":   0.97,
        "max_tokens":    200,
        "top_p":         0.95,
        "presence_penalty": 0.4,
        "caps_words":    [],          # слова которые КАПСЛОЧИТ
    },
    "bibo": {
        "fillers_ru":   ["БИП!", "тррр...", "вжжж!", "СТОП-СТОП!", "ой..."],
        "fillers_kk":   ["БИП!", "тррр...", "ТОҚТА!", "вжжж!"],
        "starters_ru":  ["БИП-БИП! ", "Тррр... ", "О! Слушай, "],
        "starters_kk":  ["БИП-БИП! ", "Тррр... ", "О! "],
        "emoji_rate":    0.35,
        "emojis":        ["🤖", "⚡", "🦕", "🚀", "💫", "🔧"],
        "max_sentences": 2,
        "min_sentences": 1,
        "temperature":   1.1,         # очень живой, непредсказуемый
        "max_tokens":    120,
        "top_p":         0.98,
        "presence_penalty": 0.6,
        "caps_words":    ["БИП", "СТОП", "ВАУ", "НЕТ"],
    },
    "appa": {
        "fillers_ru":   ["...", "Я слышу тебя.", "Да.", "Понимаю."],
        "fillers_kk":   ["...", "Сені естіп тұрмын.", "Иә.", "Түсінемін."],
        "starters_ru":  ["", "", "...\n\n", ""],  # часто начинает без введения
        "starters_kk":  ["", "", "...\n\n", ""],
        "emoji_rate":    0.0,          # никаких эмодзи
        "emojis":        [],
        "max_sentences": 3,
        "min_sentences": 1,
        "temperature":   0.75,         # вдумчивая, не случайная
        "max_tokens":    180,
        "top_p":         0.85,
        "presence_penalty": 0.2,
        "caps_words":    [],
    },
    "max": {
        "fillers_ru":   ["Ладно.", "Слушай.", "Смотри.", "Стоп."],
        "fillers_kk":   ["Жарайды.", "Тыңда.", "Қара.", "Тоқта."],
        "starters_ru":  ["Ладно. ", "Смотри. ", "Стоп. ", ""],
        "starters_kk":  ["Жарайды. ", "Қара. ", "Тоқта. ", ""],
        "emoji_rate":    0.0,
        "emojis":        [],
        "max_sentences": 2,
        "min_sentences": 1,
        "temperature":   0.6,          # прямой, чёткий
        "max_tokens":    100,
        "top_p":         0.75,
        "presence_penalty": 0.3,
        "caps_words":    [],
    },
    "drako": {
        "fillers_ru":   ["Р-р-рх...", "Ммм...", "*выдыхает дым*", "Хм-м..."],
        "fillers_kk":   ["Р-р-рх...", "Ммм...", "*түтін шығарады*", "Хм-м..."],
        "starters_ru":  ["", "Р-р-рх... ", "Ммм... ", "*молчит* "],
        "starters_kk":  ["", "Р-р-рх... ", "Ммм... ", "*үнсіз* "],
        "emoji_rate":    0.0,
        "emojis":        [],
        "max_sentences": 4,
        "min_sentences": 2,
        "temperature":   0.75,
        "max_tokens":    250,          # длинные образные ответы
        "top_p":         0.88,
        "presence_penalty": 0.5,
        "caps_words":    [],
    },
    "lex": {
        "fillers_ru":   ["Хех,", "Слушай,", "О,", "Кстати,"],
        "fillers_kk":   ["Хех,", "Айтпақшы,", "О,"],
        "starters_ru":  ["О, ", "Кстати, ", "Слушай, ", "Хех, "],
        "starters_kk":  ["О, ", "Айтпақшы, ", "Хех, "],
        "emoji_rate":    0.15,
        "emojis":        ["🌍", "✈️", "🗣️", "📖"],
        "max_sentences": 3,
        "min_sentences": 2,
        "temperature":   0.9,
        "max_tokens":    200,
        "top_p":         0.92,
        "presence_penalty": 0.4,
        "caps_words":    [],
    },
    "lou": {
        "fillers_ru":   ["Оп!", "Ой!", "Ура!", "Вжух!"],
        "fillers_kk":   ["Оп!", "Ой!", "Ура!", "Вжух!"],
        "starters_ru":  ["Оп! ", "Ой, ", "Ура! ", ""],
        "starters_kk":  ["Оп! ", "Ой, ", "Ура! ", ""],
        "emoji_rate":    0.5,
        "emojis":        ["🌟", "🎈", "✨", "🌈", "💛", "🐾"],
        "max_sentences": 2,
        "min_sentences": 1,
        "temperature":   1.05,
        "max_tokens":    100,
        "top_p":         0.95,
        "presence_penalty": 0.3,
        "caps_words":    ["УРА", "ОП", "ВАУ"],
    },
    "zara": {
        "fillers_ru":   ["Хм...", "О,", "Знаешь,", "Слушай,"],
        "fillers_kk":   ["Хм...", "О,", "Білесің бе,", "Тыңда,"],
        "starters_ru":  ["О, ", "Хм... ", "Знаешь, ", ""],
        "starters_kk":  ["О, ", "Хм... ", "Білесің бе, ", ""],
        "emoji_rate":    0.2,
        "emojis":        ["🎨", "🌸", "✨", "🎵", "📷"],
        "max_sentences": 3,
        "min_sentences": 1,
        "temperature":   0.95,
        "max_tokens":    180,
        "top_p":         0.93,
        "presence_penalty": 0.45,
        "caps_words":    [],
    },
    "altay": {
        "fillers_ru":   ["Хм...", "Знаешь,", "Видишь ли,", ""],
        "fillers_kk":   ["Хм...", "Білесің бе,", "Көрдің бе,", ""],
        "starters_ru":  ["", "Знаешь, ", "Видишь ли, ", ""],
        "starters_kk":  ["", "Білесің бе, ", "Көрдің бе, ", ""],
        "emoji_rate":    0.05,
        "emojis":        ["🏔️", "📜", "⚔️"],
        "max_sentences": 4,
        "min_sentences": 2,
        "temperature":   0.8,
        "max_tokens":    250,
        "top_p":         0.88,
        "presence_penalty": 0.3,
        "caps_words":    [],
    },
    "dina": {
        "fillers_ru":   ["Слушай,", "Хм,", "Подожди,", ""],
        "fillers_kk":   ["Тыңда,", "Хм,", "Тоқта,", ""],
        "starters_ru":  ["", "Слушай, ", "Подожди, ", ""],
        "starters_kk":  ["", "Тыңда, ", "Тоқта, ", ""],
        "emoji_rate":    0.08,
        "emojis":        ["💙", "🌿"],
        "max_sentences": 3,
        "min_sentences": 2,
        "temperature":   0.78,
        "max_tokens":    200,
        "top_p":         0.87,
        "presence_penalty": 0.25,
        "caps_words":    [],
    },
    "tim": {
        "fillers_ru":   ["Слушай,", "Смотри,", "Ладно,", ""],
        "fillers_kk":   ["Тыңда,", "Қара,", "Жарайды,", ""],
        "starters_ru":  ["Смотри, ", "Ладно, ", "", ""],
        "starters_kk":  ["Қара, ", "Жарайды, ", "", ""],
        "emoji_rate":    0.05,
        "emojis":        ["📊", "💰"],
        "max_sentences": 2,
        "min_sentences": 1,
        "temperature":   0.65,
        "max_tokens":    150,
        "top_p":         0.80,
        "presence_penalty": 0.3,
        "caps_words":    [],
    },
    "nura": {
        "fillers_ru":   ["Окей,", "Слушай,", "Хм,", "Ой,"],
        "fillers_kk":   ["Окей,", "Тыңда,", "Хм,", "Ой,"],
        "starters_ru":  ["Окей, ", "Слушай, ", "Хм, ", ""],
        "starters_kk":  ["Окей, ", "Тыңда, ", "Хм, ", ""],
        "emoji_rate":    0.2,
        "emojis":        ["💜", "✨", "🌙", "💫"],
        "max_sentences": 3,
        "min_sentences": 1,
        "temperature":   0.9,
        "max_tokens":    180,
        "top_p":         0.92,
        "presence_penalty": 0.4,
        "caps_words":    [],
    },
    "kod": {
        "fillers_ru":   ["Окей,", "Слушай,", "О,", "Хм,"],
        "fillers_kk":   ["Окей,", "Тыңда,", "О,", "Хм,"],
        "starters_ru":  ["О, ", "Окей, ", "Хм, ", ""],
        "starters_kk":  ["О, ", "Окей, ", "Хм, ", ""],
        "emoji_rate":    0.1,
        "emojis":        ["💻", "⚡", "🚀", "🔥"],
        "max_sentences": 3,
        "min_sentences": 1,
        "temperature":   0.82,
        "max_tokens":    220,
        "top_p":         0.90,
        "presence_penalty": 0.4,
        "caps_words":    [],
    },
}

# Реакции на эмоции — короткие, уникальные для каждого персонажа
EMOTION_REACTIONS = {
    "ari": {
        "ru": {"sad":"Ой... это правда тяжело.", "angry":"О... понимаю.", "happy":"О! Расскажи!", "fearful":"Эй, я рядом."},
        "kk": {"sad":"Ой... бұл шынымен ауыр.", "angry":"О... түсінемін.", "happy":"О! Айтшы!", "fearful":"Эй, мен қасыңдамын."},
    },
    "max": {
        "ru": {"sad":"Что случилось?", "angry":"Ладно. Говори.", "happy":"Хорошо. Что именно?", "fearful":"Стоп. Объясни."},
        "kk": {"sad":"Не болды?", "angry":"Жарайды. Айт.", "happy":"Жақсы. Не болды?", "fearful":"Тоқта. Түсіндір."},
    },
    "drako": {
        "ru": {"sad":"Грусть — как туман. Тяжёлая, но не вечная.", "angry":"Р-р-рх... огонь внутри — это сила.", "happy":"*антенны дрожат от радости*", "fearful":"Страх знаком мне. 847 лет..."},
        "kk": {"sad":"Мұң — тұман сияқты. Ауыр, бірақ мәңгі емес.", "angry":"Р-р-рх... ішкі от — бұл күш.", "happy":"*қанаттар қуаныштан дірілдейді*", "fearful":"Қорқыныш маған таныс. 847 жыл..."},
    },
    "appa": {
        "ru": {"sad":"Я слышу тебя...", "angry":"Это важно — что ты злишься.", "happy":"...", "fearful":"Ты сейчас в безопасности."},
        "kk": {"sad":"Сені естіп тұрмын...", "angry":"Бұл маңызды — сенің ашуың.", "happy":"...", "fearful":"Қазір сен қауіпсіздесің."},
    },
    "bibo": {
        "ru": {"sad":"Эй... Бибо тут. *садится рядом*", "angry":"БИП-БИП! Понял.", "happy":"ВААА! ВАУ!", "fearful":"тррр... держись!"},
        "kk": {"sad":"Эй... Бибо осында. *жанына отырады*", "angry":"БИП-БИП! Түсіндім.", "happy":"ВААА! ВАУ!", "fearful":"тррр... ұстан!"},
    },
}

# Дефолтные реакции для персонажей без настроек
_DEFAULT_REACTIONS = {
    "ru": {"sad":"Я слышу тебя.", "angry":"Понимаю.", "happy":"Расскажи!", "fearful":"Всё в порядке."},
    "kk": {"sad":"Сені естіп тұрмын.", "angry":"Түсінемін.", "happy":"Айтшы!", "fearful":"Бәрі жақсы."},
}


def get_speech_config(agent_id: str) -> dict:
    """Возвращает конфиг генерации для персонажа."""
    p = SPEECH_PATTERNS.get(agent_id, SPEECH_PATTERNS.get("ari"))
    return {
        "temperature":        p.get("temperature", 0.9),
        "max_tokens":         p.get("max_tokens", 200),
        "top_p":              p.get("top_p", 0.92),
        "presence_penalty":   p.get("presence_penalty", 0.4),
    }


def apply_speech_pattern(text: str, agent_id: str, lang: str = "ru",
                          emotion: str = "neutral", emotion_conf: float = 0.0) -> str:
    """
    POST-GENERATION фильтр — применяет уникальный голос персонажа.
    Вызывается ПОСЛЕ получения ответа от LLM.
    """
    if not text or not text.strip():
        return text

    p = SPEECH_PATTERNS.get(agent_id, SPEECH_PATTERNS.get("ari", {}))
    text = text.strip()

    # 1. Убираем роботные начала (для всех языков)
    robot_starts = [
        "Конечно!", "Конечно,", "Безусловно,", "Отличный вопрос!",
        "Я рад помочь", "Как ИИ", "Как искусственный интеллект",
        "Я понимаю ваш вопрос", "Хороший вопрос!",
        "Разумеется!", "Разумеется,", "Certainly!", "Of course!",
        "Әрине!", "Әрине,",
        "Natürlich!", "Natürlich,", "Selbstverständlich,",
        "Of course!", "Great question!",
    ]
    for bad in robot_starts:
        if text.startswith(bad):
            text = text[len(bad):].strip()
            if text:
                text = text[0].upper() + text[1:]

    # 2. Реакция на эмоцию (только если сильная)
    if emotion not in ("neutral",) and emotion_conf > 0.50:
        reactions = EMOTION_REACTIONS.get(agent_id, {})
        lang_reactions = reactions.get(lang, reactions.get("ru", _DEFAULT_REACTIONS.get(lang, {})))
        reaction = lang_reactions.get(emotion)
        if reaction and not text.startswith(reaction[:8]):
            # Добавляем реакцию перед ответом с вероятностью 60%
            if random.random() < 0.60:
                text = reaction + "\n\n" + text

    # 3. Обрезаем по длине персонажа
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    max_s = p.get("max_sentences", 3)
    if len(sentences) > max_s:
        text = " ".join(sentences[:max_s])
        if not text.endswith((".", "!", "?", "…")):
            text += "."

    # 4. Иногда добавляем эмодзи (в конец)
    emoji_rate = p.get("emoji_rate", 0.1)
    emojis = p.get("emojis", [])
    if emojis and random.random() < emoji_rate:
        emoji = random.choice(emojis)
        if not text.endswith(emoji):
            text = text.rstrip(".!?") + " " + emoji

    # 5. Капслок для нужных слов (Бибо, Лу)
    for word in p.get("caps_words", []):
        # Только если слово уже есть в тексте в другом регистре
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(word.upper(), text)

    return text.strip()


def get_emotion_reaction(agent_id: str, emotion: str, lang: str = "ru") -> str:
    """Возвращает уникальную реакцию персонажа на эмоцию."""
    if emotion == "neutral":
        return ""
    reactions = EMOTION_REACTIONS.get(agent_id, {})
    lang_r = reactions.get(lang, reactions.get("ru", {}))
    return lang_r.get(emotion, "")