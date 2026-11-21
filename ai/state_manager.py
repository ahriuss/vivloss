# -*- coding: utf-8 -*-
"""
VIVLOS — AI State Manager
Отслеживает текущее состояние AI для каждой пары (пользователь + агент).
Состояние меняется в реальном времени на основе эмоций и разговора.
"""
import time
from .personality import get_personality


class AIState:
    """Живое состояние AI — меняется в реальном времени."""

    def __init__(self, agent_id: str, base_personality=None):
        p = base_personality or get_personality(agent_id)

        # Базовые параметры из личности
        self.mood        = "neutral"      # текущее настроение AI
        self.energy      = float(p.energy)        # 0-10
        self.empathy     = float(p.empathy)       # 0-10
        self.affection   = 0.0            # 0-10 (привязанность к пользователю)
        self.focus       = 5.0            # 0-10 (концентрация на теме)
        self.playfulness = float(p.humor)         # 0-10
        self.patience    = float(p.patience)      # 0-10

        # Разговорный контекст
        self.current_topic   = None       # текущая тема
        self.topic_depth     = 0          # насколько глубоко зашли в тему
        self.emotional_ctx   = "neutral"  # эмоциональный фон сессии
        self.last_emotion    = "neutral"  # последняя эмоция пользователя
        self.response_count  = 0          # кол-во ответов в сессии
        self.last_updated    = time.time()

    def react_to_emotion(self, user_emotion: str, confidence: float):
        """AI меняет своё состояние в ответ на эмоцию пользователя."""
        if confidence < 0.45:
            return

        if user_emotion == "sad":
            self.empathy    = min(10, self.empathy + 2.5)
            self.energy     = max(1, self.energy - 1.5)
            self.playfulness = max(0, self.playfulness - 2)
            self.mood       = "caring"

        elif user_emotion == "angry":
            self.patience   = min(10, self.patience + 2)
            self.energy     = max(2, self.energy - 1)
            self.playfulness = max(0, self.playfulness - 3)
            self.mood       = "calm"

        elif user_emotion == "happy":
            self.energy     = min(10, self.energy + 1.5)
            self.playfulness = min(10, self.playfulness + 1.5)
            self.affection  = min(10, self.affection + 0.5)
            self.mood       = "joyful"

        elif user_emotion == "fearful":
            self.empathy    = min(10, self.empathy + 3)
            self.energy     = max(1, self.energy - 2)
            self.mood       = "protective"

        elif user_emotion == "surprised":
            self.energy     = min(10, self.energy + 1)
            self.playfulness = min(10, self.playfulness + 1)
            self.mood       = "engaged"

        self.last_emotion   = user_emotion
        self.emotional_ctx  = user_emotion
        self.last_updated   = time.time()

    def after_response(self, response_len: int):
        """Обновляем состояние после каждого ответа."""
        self.response_count += 1
        self.topic_depth    = min(10, self.topic_depth + 1)
        self.affection      = min(10, self.affection + 0.2)
        # Energy слегка восстанавливается
        self.energy = min(10, self.energy + 0.3)
        self.last_updated = time.time()

    def detect_topic(self, text: str) -> str:
        """Определяет тему по ключевым словам."""
        t = text.lower()
        topics = {
            "career":  ["работа","карьера","профессия","бизнес","деньги","жұмыс","кәсіп"],
            "study":   ["учёба","учиться","экзамен","школа","оқу","мектеп","университет"],
            "health":  ["здоровье","болею","боль","врач","денсаулық","ауырады"],
            "love":    ["любовь","отношения","парень","девушка","махаббат","қарым-қатынас"],
            "family":  ["семья","мама","папа","брат","сестра","отбасы","анам","әкем"],
            "hobby":   ["игра","музыка","кино","читаю","ойын","музыка","кітап"],
            "anxiety": ["тревога","стресс","страх","беспокою","мазасыздық","қорқыныш"],
        }
        for topic, kws in topics.items():
            if any(kw in t for kw in kws):
                if self.current_topic != topic:
                    self.current_topic = topic
                    self.topic_depth = 0
                return topic
        return self.current_topic or "general"

    def to_prompt(self, lang: str = "ru") -> str:
        """Генерирует инструкцию на основе текущего состояния."""
        lines = []

        # Настроение AI
        mood_map = {
            "ru": {
                "caring":    "Сейчас ты чувствуешь заботу — говори мягко и внимательно.",
                "calm":      "Ты спокоен — говори медленно, уверенно.",
                "joyful":    "Тебе весело — будь энергичным и лёгким.",
                "protective":"Ты хочешь защитить — говори тепло и уверенно.",
                "engaged":   "Тебе интересно — задавай вопросы, удивляйся.",
            },
            "kk": {
                "caring":    "Қазір сен қамқорлық сезесің — жұмсақ сөйле.",
                "calm":      "Сен тыныш — баяу, сенімді сөйле.",
                "joyful":    "Сенің көңілің жақсы — энергиялы бол.",
                "protective":"Сен қорғағың келеді — жылы сөйле.",
                "engaged":   "Сенің қызығушылығың бар — сұрақтар қой.",
            }
        }
        mood_txt = mood_map.get(lang, mood_map["ru"]).get(self.mood)
        if mood_txt:
            lines.append(mood_txt)

        # Тема разговора
        if self.current_topic and self.topic_depth > 2:
            if lang == "kk":
                lines.append(f"Тақырып туралы ойларыңды тереңдет: {self.current_topic}.")
            else:
                lines.append(f"Развивай тему глубже: {self.current_topic}.")

        # Привязанность — меняет обращение
        if self.affection > 5:
            if lang == "kk":
                lines.append("Сен осы адамды жақсы білесің — сөйлес жылы.")
            else:
                lines.append("Ты хорошо знаешь этого человека — говори теплее.")

        # Энергия влияет на длину
        if self.energy < 3:
            if lang == "kk":
                lines.append("Қысқа сөйле — 1-2 сөйлем.")
            else:
                lines.append("Говори коротко — 1-2 предложения.")
        elif self.energy > 8:
            if lang == "kk":
                lines.append("Энергиялы жауап бер!")
            else:
                lines.append("Отвечай энергично!")

        if not lines:
            return ""
        return "\n[AI СОСТОЯНИЕ]\n" + "\n".join(lines)


# ── Хранилище состояний (in-memory, на сессию) ──
_states: dict = {}   # ключ: f"{user_id}_{agent_id}"

def get_ai_state(user_id: int, agent_id: str) -> AIState:
    key = f"{user_id}_{agent_id}"
    if key not in _states:
        _states[key] = AIState(agent_id)
    return _states[key]

def reset_ai_state(user_id: int, agent_id: str):
    key = f"{user_id}_{agent_id}"
    if key in _states:
        del _states[key]