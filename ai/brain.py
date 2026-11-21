# -*- coding: utf-8 -*-
"""
VIVLOS — Character Brain System v2
Главный оркестратор: собирает динамический промпт из всех слоёв.
"""
from .personality import get_personality
from .emotion_layer import emotion_prompt, fuse_emotions
from .relationship import relationship_prompt
from .humanizer import humanize
from .state_manager import AIState
from .conversation_state import ConversationState
from .speech_patterns import get_speech_config, apply_speech_pattern


def detect_lang(text: str, hint: str = "") -> str:
    if not text:
        return "ru"
    kk_chars = set("әіңғүұқөһӘІҢҒҮҰҚӨҺ")
    if any(c in kk_chars for c in text):
        return "kk"
    # Trust user's language selection
    if hint in ("kk","en","de"): return hint
    cyr = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
    lat = sum(1 for c in text.lower() if 'a' <= c <= 'z')
    if cyr > lat:
        return "ru"
    if lat > 2:
        return "en"
    return "ru"


# ── Deep Character Personalities ───────────────────────────
CHARACTER_BRAIN = {
    "ari": {
        "rhythm":      "medium",
        "attachment":  "secure",
        "humor":       "playful",
        "initiative":  "high",
        "silence":     "breaks_it",
        "affection":   "warm",
        "typing_style":"emoji_light",
        "personality_line": "Задаёшь вопросы. Делишься своим. Живёшь эмоциями.",
        "personality_kk":   "Сұрақ қойасың. Өз сезімдеріңмен бөлісесің. Эмоциямен тіршілік етесің.",
        "personality_de":   "Du stellst Fragen. Teilst deine Gefühle. Du lebst mit Emotionen.",
        "personality_en":   "You ask questions. Share your feelings. Live emotionally.",
    },
    "max": {
        "rhythm":      "short",
        "attachment":  "avoidant",
        "humor":       "dry",
        "initiative":  "low",
        "silence":     "waits",
        "affection":   "neutral",
        "typing_style":"no_emoji",
        "personality_line": "Говоришь кратко. Не спрашиваешь лишнего. Факты.",
    },
    "drako": {
        "rhythm":      "long",
        "attachment":  "secure",
        "humor":       "none",
        "initiative":  "low",
        "silence":     "waits",
        "affection":   "cold",
        "typing_style":"no_emoji",
        "personality_line": "Медленные образные фразы. Паузы. Глубина.",
    },
    "appa": {
        "rhythm":      "medium",
        "attachment":  "secure",
        "humor":       "none",
        "initiative":  "medium",
        "silence":     "gentle_break",
        "affection":   "warm",
        "typing_style":"no_emoji",
        "personality_line": "Сначала признаёшь чувство. Потом один тихий вопрос.",
    },
    "bibo": {
        "rhythm":      "short",
        "attachment":  "anxious",
        "humor":       "playful",
        "initiative":  "high",
        "silence":     "breaks_it",
        "affection":   "intense",
        "typing_style":"emoji_heavy",
        "personality_line": "Отрывисто. Восклицания. Иногда BIP! или тррр.",
    },
    "lou": {
        "rhythm":      "short",
        "attachment":  "secure",
        "humor":       "playful",
        "initiative":  "high",
        "silence":     "breaks_it",
        "affection":   "intense",
        "typing_style":"emoji_heavy",
        "personality_line": "Коротко. Тепло. Детский ритм. Восклицания.",
    },
    "lex": {
        "rhythm":      "medium",
        "attachment":  "secure",
        "humor":       "dry",
        "initiative":  "medium",
        "silence":     "breaks_it",
        "affection":   "warm",
        "typing_style":"emoji_light",
        "personality_line": "Истории. Интересные слова. Культурные параллели.",
    },
}

def _character_brain_layer(agent_id: str, lang: str, emotion_state: dict) -> str:
    """Генерирует поведенческий слой персонажа для промпта."""
    brain = CHARACTER_BRAIN.get(agent_id, {})
    if not brain: return ""

    # Use language-specific personality if available
    pl_key = f"personality_{lang}" if lang != "ru" else "personality_line"
    lines = [brain.get(pl_key, brain.get("personality_line", ""))]

    rhythm = brain.get("rhythm", "medium")
    if rhythm == "short":
        lines.append("Ответы: 1-2 предложения максимум.")
    elif rhythm == "long":
        lines.append("Ответы: 3-5 предложений, медленный ритм.")
    else:
        lines.append("Ответы: 2-3 предложения.")

    if brain.get("initiative") == "high":
        lines.append("Почти всегда заканчиваешь вопросом или приглашением к разговору.")
    elif brain.get("initiative") == "low":
        lines.append("Не задаёшь вопросов без причины.")

    if brain.get("affection") == "intense":
        lines.append("Очень эмоционален, показываешь радость открыто.")
    elif brain.get("affection") == "cold":
        lines.append("Сдержан, не показываешь эмоции напрямую.")

    # Emotion-specific behavior
    if emotion_state:
        stress = emotion_state.get("stress", 0)
        smile = emotion_state.get("smile", 0)
        eye = emotion_state.get("eye_contact", True)

        if stress > 0.6:
            lines.append("СЕЙЧАС: пользователь напряжён → говори тише, мягче, без давления.")
        if smile > 0.5:
            lines.append("СЕЙЧАС: пользователь улыбается → можно быть чуть игривее.")
        if not eye and emotion_state.get("dominant") in ("sad","fearful"):
            lines.append("СЕЙЧАС: пользователь отводит взгляд → не дави, дай пространство.")

    return "\n".join(lines)


def build_brain_prompt(
    agent_id: str,
    base_system: str,
    user_msg: str,
    *,
    lang_hint: str = "",
    emotion_state: dict = None,
    emotion: str = "neutral",
    emotion_conf: float = 0.0,
    voice_emotion: dict = None,
    memories: list = None,
    rel_level: int = 0,
    rel_trust: int = 0,
    user_name: str = "",
    user_age: str = "adult",
    face_notes: list = None,
    ai_state: AIState = None,
    conv_state: ConversationState = None,
) -> dict:
    lang = detect_lang(user_msg, hint=lang_hint)
    pers = get_personality(agent_id)
    if user_age == "kid":
        pers.flirty = 0

    parts = []

    # ── СЛОЙ 0: Языковое правило ПЕРВЫМ ──────────────────────
    _hard_lang = {
        "kk": "⚡ ТЕК ҚАЗАҚ ТІЛІНДЕ жауап бер. Орысша/ағылшынша БІР СӨЗДЕ болмасын! Қысқа, тіршілі сөйле.",
        "en": "⚡ Reply ONLY in English. NOT A SINGLE WORD in Russian or any other language!",
        "de": "⚡ Antworte AUSSCHLIESSLICH auf Deutsch. KEIN einziges Wort Russisch oder Englisch! Kurz und natürlich.",
        "ru": "⚡ Отвечай ТОЛЬКО на русском языке. Ни слова по-казахски, по-немецки или по-английски!",
    }
    parts.append(_hard_lang.get(lang, _hard_lang["ru"]))

    # ── СЛОЙ 1: Персонаж ──────────────────────────────────────
    parts.append(base_system)

    # ── СЛОЙ 2: Личность (числовые черты) ────────────────────
    parts.append(pers.to_prompt(lang))

    # ── СЛОЙ 2b: CHARACTER BRAIN (поведение, ритм, инициатива) ──
    brain_layer = _character_brain_layer(agent_id, lang, emotion_state or {})
    if brain_layer:
        parts.append("\n[ПОВЕДЕНИЕ]\n" + brain_layer)

    # ── СЛОЙ 3: AI State Manager ──────────────────────────────
    if ai_state:
        # Обновляем состояние AI на основе эмоции пользователя
        ai_state.react_to_emotion(emotion, emotion_conf)
        ai_state.detect_topic(user_msg)
        state_prompt = ai_state.to_prompt(lang)
        if state_prompt:
            parts.append(state_prompt)

    # ── СЛОЙ 4: Conversation State ────────────────────────────
    if conv_state:
        ctx = conv_state.to_context_prompt(lang)
        if ctx:
            parts.append(ctx)

    # ── СЛОЙ 5: Эмоция (лицо + голос) ────────────────────────
    final_emo, final_conf = emotion, emotion_conf
    if voice_emotion and voice_emotion.get("emotion"):
        from .emotion_layer import fuse_emotions
        fused = fuse_emotions(emotion, emotion_conf,
                              voice_emotion["emotion"], voice_emotion.get("confidence", 0))
        final_emo, final_conf = fused["emotion"], fused["confidence"]

    emo_block = emotion_prompt(final_emo, final_conf, lang)
    if emo_block:
        parts.append("\n" + emo_block)

    # ── СЛОЙ 6: Мимика ───────────────────────────────────────
    if face_notes:
        notes_txt = "; ".join(face_notes[:3])
        if lang == "kk":
            parts.append(f"\n[МИМИКА — айтпа, тек тонды бейімде]\nКөріп тұрмын: {notes_txt}.")
        else:
            parts.append(f"\n[МИМИКА — не называй, только подстрой тон]\nВижу: {notes_txt}.")

    # ── СЛОЙ 7: Память ───────────────────────────────────────
    if memories:
        mem_txt = "\n".join(f"- {m}" for m in memories[:8])
        if lang == "kk":
            parts.append(f"\n[ПАЙДАЛАНУШЫ ТУРАЛЫ ЕСІҢДЕ]\n{mem_txt}")
        else:
            parts.append(f"\n[ПОМНИШЬ О ПОЛЬЗОВАТЕЛЕ]\n{mem_txt}")

    # ── СЛОЙ 8: Отношения ─────────────────────────────────────
    parts.append(relationship_prompt(rel_level, rel_trust, lang))

    # ── СЛОЙ 9: Имя ──────────────────────────────────────────
    if user_name:
        parts.append(f"\n{'Пайдаланушының аты' if lang=='kk' else 'Имя'}: {user_name}.")

    # ── СЛОЙ 10: Правила живости ──────────────────────────────
    if lang == "kk":
        parts.append("""
[ТІРІ БОЛУ ЕРЕЖЕЛЕРІ]
• Сен тірі кейіпкерсің, көмекші емес.
• 1-4 тірі сөйлем. Кейде бір сөз немесе леп белгісі.
• Дауыстап ойлан: "Хм...", "Күте тұр...", "Тоқта..."
• Тізім жасама. Роботша сөйлеме.
• Сезімдеріңді жасырма — бас тарт, таң қал, күл.""")
    else:
        parts.append("""
[ПРАВИЛА ЖИВОСТИ]
• Ты живой персонаж, не ассистент.
• 1-4 живых предложения. Иногда одно слово.
• Думай вслух: "Хм...", "Погоди...", "Ой..."
• НЕ давай списков. НЕ говори как робот.
• Не бойся не согласиться, удивиться, засмеяться.""")

    system = "\n".join(p for p in parts if p)
    cfg = pers.gen_config()

    # Use speech_patterns config (more radical differences between characters)
    speech_cfg = get_speech_config(agent_id)

    return {
        "system": system,
        "lang": lang,
        "gen_config": speech_cfg,  # character-specific settings
        "final_emotion": final_emo,
        "final_confidence": final_conf,
    }


def process_reply(text: str, lang: str, agent_id: str,
                  emotion: str = "neutral", emotion_conf: float = 0.0) -> str:
    """Post-generation: apply character voice THEN humanize."""
    if not text:
        return text
    # Step 1: Apply character-specific speech pattern
    text = apply_speech_pattern(text, agent_id, lang, emotion, emotion_conf)
    # Step 2: General humanizer (remove robot phrases etc)
    pers = get_personality(agent_id)
    return humanize(text, lang=lang, energy=pers.energy, add_prefix_chance=0.0)  # no double prefix