# -*- coding: utf-8 -*-
"""
VIVLOS — Conversation State Engine
Отслеживает тему, эмоциональный контекст, ход разговора.
Без этого AI не помнит "о чём мы говорили минуту назад".
"""
import time


class ConversationState:
    """Состояние текущего разговора — одна сессия звонка."""

    def __init__(self):
        self.topic              = "general"
        self.prev_topic         = None
        self.emotion_arc        = []     # история эмоций за сессию
        self.energy_level       = 5.0    # разговорная энергия (0-10)
        self.depth              = 0      # глубина в теме (0-10)
        self.turn_count         = 0
        self.started_at         = time.time()
        self.last_question      = None   # последний вопрос AI
        self.unresolved_topics  = []     # темы которые подняли но не закрыли
        self.key_facts          = []     # факты узнанные в этой сессии

    def update(self, user_text: str, ai_response: str,
               user_emotion: str, detected_lang: str):
        """Обновляем состояние после каждого обмена."""
        self.turn_count += 1
        if user_emotion != "neutral":
            self.emotion_arc.append(user_emotion)
            if len(self.emotion_arc) > 10:
                self.emotion_arc.pop(0)

        # Определяем тему
        new_topic = self._detect_topic(user_text)
        if new_topic != self.topic:
            self.prev_topic = self.topic
            self.topic = new_topic
            self.depth = 0
        else:
            self.depth = min(10, self.depth + 1)

        # Извлекаем ключевые факты (имена, числа)
        self._extract_facts(user_text)

    def _detect_topic(self, text: str) -> str:
        t = text.lower()
        topics = {
            "career":   ["работа","карьера","бизнес","жұмыс","кәсіп","зарплата"],
            "study":    ["учёба","экзамен","школа","университет","оқу","мектеп"],
            "health":   ["здоровье","боль","болею","врач","денсаулық","ауырады"],
            "love":     ["любовь","отношения","парень","девушка","махаббат"],
            "family":   ["семья","мама","папа","брат","отбасы","анам","әкем"],
            "emotions": ["грустно","тяжело","плохо","хорошо","счастлив","мұңды"],
            "future":   ["будущее","планы","мечта","болашақ","арман","жоспар"],
        }
        for topic, kws in topics.items():
            if any(kw in t for kw in kws):
                return topic
        return self.topic

    def _extract_facts(self, text: str):
        """Простое извлечение фактов из фраз."""
        triggers = ["меня зовут","я работаю","мне","я живу","мой","моя",
                    "менің атым","мен жұмыс","маған"]
        if any(t in text.lower() for t in triggers):
            fact = text[:120].strip()
            if fact not in self.key_facts:
                self.key_facts.append(fact)
                if len(self.key_facts) > 10:
                    self.key_facts.pop(0)

    def dominant_emotion(self) -> str:
        """Доминирующая эмоция за последние 5 ходов."""
        recent = self.emotion_arc[-5:]
        if not recent:
            return "neutral"
        return max(set(recent), key=recent.count)

    def to_context_prompt(self, lang: str = "ru") -> str:
        """Краткий контекст разговора для промпта."""
        lines = []
        dom = self.dominant_emotion()

        if lang == "kk":
            if dom not in ("neutral",) and len(self.emotion_arc) >= 2:
                emo_kk = {"sad":"мұңды","angry":"ашулы","happy":"қуанышты",
                          "fearful":"үрейленген","surprised":"таңданған"}
                lines.append(f"Бұл сессияда: {emo_kk.get(dom, dom)}.")
            if self.depth > 3:
                lines.append(f"'{self.topic}' тақырыбын тереңірек зерттеп жатырсыңдар.")
            if self.key_facts:
                lines.append("Білетін ақпарат: " + "; ".join(self.key_facts[-3:]))
        else:
            if dom not in ("neutral",) and len(self.emotion_arc) >= 2:
                emo_ru = {"sad":"грустно","angry":"злится","happy":"радостно",
                          "fearful":"тревожно","surprised":"удивлён"}
                lines.append(f"В этой сессии человеку {emo_ru.get(dom, dom)}.")
            if self.depth > 3:
                lines.append(f"Вы глубоко погружены в тему: {self.topic}.")
            if self.key_facts:
                lines.append("Известно из разговора: " + "; ".join(self.key_facts[-3:]))

        if not lines:
            return ""
        return "\n[КОНТЕКСТ РАЗГОВОРА]\n" + "\n".join(lines)


# ── Хранилище состояний разговора ──
_conv_states: dict = {}

def get_conv_state(session_key: str) -> ConversationState:
    if session_key not in _conv_states:
        _conv_states[session_key] = ConversationState()
    return _conv_states[session_key]

def reset_conv_state(session_key: str):
    if session_key in _conv_states:
        del _conv_states[session_key]