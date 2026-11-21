# -*- coding: utf-8 -*-
"""
ai/streaming.py
Стримит текст по словам через SocketIO (как ChatGPT печатает).
"""
import time


def stream_text(text: str, socketio, delay: float = 0.045):
    """
    Отправляет текст по словам через SocketIO событие 'ai_stream'.
    delay — задержка между словами в секундах (0.04-0.08 = реалистично).
    """
    if not text:
        return

    words = text.split()
    current = ""

    for i, word in enumerate(words):
        current += word + " "
        socketio.emit("ai_stream", {"text": current.strip()})
        # Реалистичная задержка: длинные слова — чуть дольше
        word_delay = delay + len(word) * 0.003
        time.sleep(min(word_delay, 0.12))

    # Финальный emit с полным текстом
    socketio.emit("ai_stream_done", {"text": text.strip()})


def stream_thinking_delay():
    """Имитирует задержку 'обдумывания' перед ответом (1.0-1.5 сек)."""
    import random
    time.sleep(random.uniform(0.8, 1.4))