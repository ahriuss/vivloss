# -*- coding: utf-8 -*-
"""
websocket/chat_socket.py
Realtime Chat Events через SocketIO.
Подключается к app.py через register_socket_events(socketio).
"""
import time
import os
from ai.streaming import stream_text
from ai.prompt_builder import build_prompt
from ai.humanizer import humanize
from emotions.emotion_engine import emotion_behavior


def register_socket_events(socketio, app, db, get_gemini, _call_openai,
                            AGENT_PERSONAS, UserMemory, _offline_fallback):
    """Регистрируем все SocketIO события."""

    @socketio.on("connect")
    def on_connect():
        print("🔌 Client connected")

    @socketio.on("disconnect")
    def on_disconnect():
        print("🔌 Client disconnected")

    @socketio.on("send_message")
    def handle_message(data):
        """Главный обработчик — принимает сообщение, стримит ответ AI."""
        user_message = (data.get("message") or "").strip()
        agent_id     = data.get("agent_id", "ari")
        lang         = data.get("lang", "ru")
        user_id      = data.get("user_id", 1)
        emotion      = data.get("emotion", "neutral")
        emotion_conf = float(data.get("emotion_conf", 0.0))

        if not user_message:
            return

        # 1. Показываем typing indicator
        socketio.emit("typing", {"status": True, "agent_id": agent_id})

        # 2. Грузим память
        with app.app_context():
            mems = UserMemory.query.filter_by(user_id=user_id)\
                .order_by(UserMemory.importance.desc()).limit(8).all()
            memory_text = "\n".join(f"- {m.content}" for m in mems) if mems else ""

        # 3. Строим умный промпт
        emotion_hint = emotion_behavior(emotion, lang)
        persona      = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS["ari"])
        full_prompt  = build_prompt(
            base_system=persona["system"],
            memory=memory_text,
            emotion_hint=emotion_hint,
            message=user_message,
            lang=lang,
        )

        # 4. Получаем ответ AI
        ai_response = ""
        try:
            if os.getenv("OPENAI_API_KEY"):
                few_shot = []
                ai_response = _call_openai(full_prompt, [{"role":"user","content":user_message}],
                                           few_shot, lang, agent_id)
            else:
                model = get_gemini(sys_inst=full_prompt)
                import google.generativeai as genai
                gc = genai.types.GenerationConfig(temperature=0.97, max_output_tokens=250)
                resp = model.generate_content(user_message, generation_config=gc)
                ai_response = (resp.text or "").strip()
        except Exception as e:
            ai_response = _offline_fallback(agent_id, lang)

        # 5. Очеловечиваем
        ai_response = humanize(ai_response, lang=lang)

        # 6. Стримим токен за токеном
        stream_text(ai_response, socketio)

        # 7. Убираем typing и отправляем финальный
        socketio.emit("typing", {"status": False})
        socketio.emit("receive_message", {
            "message":  ai_response,
            "agent_id": agent_id,
            "emotion":  emotion,
        })