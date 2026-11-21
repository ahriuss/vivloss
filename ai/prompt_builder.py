# -*- coding: utf-8 -*-
"""
ai/prompt_builder.py
Dynamic Prompt Builder — собирает финальный промпт из всех слоёв.
Используется и в websocket/chat_socket.py и в app.py.
"""


def build_prompt(
    base_system: str,
    memory: str = "",
    emotion_hint: str = "",
    message: str = "",
    lang: str = "ru",
    personality_traits: dict = None,
    relationship_level: int = 0,
) -> str:
    """
    Собирает полный системный промпт.

    base_system      — персонаж (его характер)
    memory           — что AI помнит о пользователе
    emotion_hint     — инструкция на основе эмоции
    message          — последнее сообщение пользователя (для контекста)
    lang             — язык ответа
    personality_traits — числовые черты {kindness, humor, empathy, ...}
    relationship_level — 0-100 уровень знакомства
    """

    parts = []

    # 1. Языковое правило — ПЕРВЫМ (иначе AI забудет)
    if lang == "kk":
        parts.append("⚡ ТЕК ҚАЗАҚ ТІЛІНДЕ жауап бер. Бір сөз де орысша болмасын.")
    else:
        parts.append("⚡ Отвечай ТОЛЬКО на русском языке. Ни слова на казахском.")

    # 2. Базовый персонаж
    parts.append(base_system)

    # 3. Черты личности (если переданы)
    if personality_traits:
        k = personality_traits.get("kindness", 7)
        h = personality_traits.get("humor", 5)
        e = personality_traits.get("empathy", 7)
        if lang == "kk":
            parts.append(
                f"[МІНЕЗ]\nМейірімділік: {k}/10, Юмор: {h}/10, Эмпатия: {e}/10"
            )
        else:
            parts.append(
                f"[ЛИЧНОСТЬ]\nДоброта: {k}/10, Юмор: {h}/10, Эмпатия: {e}/10"
            )

    # 4. Отношения
    if relationship_level > 0:
        if lang == "kk":
            if relationship_level >= 50:
                parts.append("Сен осы адамды жақсы білесің — жылы, ашық сөйле.")
            else:
                parts.append("Бұл адаммен енді таныстың — сыпайы бол.")
        else:
            if relationship_level >= 50:
                parts.append("Ты хорошо знаешь этого человека — говори теплее и ближе.")
            else:
                parts.append("Вы ещё не очень знакомы — будь вежливым но тёплым.")

    # 5. Эмоциональная инструкция
    if emotion_hint:
        parts.append(f"\n[ЭМОЦИЯ ПОЛЬЗОВАТЕЛЯ]\n{emotion_hint}")

    # 6. Память
    if memory:
        if lang == "kk":
            parts.append(f"\n[ЕСІҢДЕ]\n{memory}")
        else:
            parts.append(f"\n[ПОМНИШЬ О ПОЛЬЗОВАТЕЛЕ]\n{memory}")

    # 7. Правила живости
    if lang == "kk":
        parts.append("""
[ТІРІ БОЛУ ЕРЕЖЕЛЕРІ]
Ты живой AI companion.
Сен табиғи сөйлейсің.
Сен эмоционалды.
Робот сияқты жауап бермейсің.
Сен әңгімені қолдайсың.
Сен сұрақтар қоясың.
Сен пайдаланушыны есіңде сақтайсың.""")
    else:
        parts.append("""
[ПРАВИЛА ЖИВОСТИ]
Ты живой AI companion.
Ты говоришь естественно.
Ты эмоциональный.
Ты не отвечаешь как робот.
Ты поддерживаешь разговор.
Ты задаёшь вопросы.
Ты помнишь пользователя.""")

    return "\n\n".join(p for p in parts if p)