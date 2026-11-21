# -*- coding: utf-8 -*-
"""
websocket/realtime_audio.py
Realtime Audio Loop через SocketIO.

Поток данных:
  Client AudioWorklet → socket(audio_chunk) →
  VAD accumulate → silence detected →
  Whisper transcribe → AI generate (stream) →
  socket(ai_token) → TTS → socket(tts_chunk) →
  Client AudioContext plays

Interruption:
  Client говорит пока AI отвечает →
  socket(interrupt) → сервер останавливает генерацию
"""
import io
import os
import json
import wave
import struct
import threading
import logging

from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)

# Max 4 concurrent audio processing threads — prevents thread explosion
_RT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rt_audio")

# ── Состояние сессии для каждого клиента ──────────────────────
class AudioSession:
    def __init__(self, sid):
        self.sid          = sid
        self.chunks       = []          # накопленные PCM-чанки
        self.is_speaking  = False       # VAD: пользователь говорит
        self.silence_ms   = 0           # миллисекунды тишины
        self.ai_speaking  = False       # AI сейчас говорит
        self.interrupted  = False       # флаг прерывания
        self.lang         = "ru"
        self.agent_id     = "ari"
        self.lock         = threading.Lock()

    def add_chunk(self, pcm_bytes: bytes, is_speech: bool):
        with self.lock:
            if is_speech:
                self.chunks.append(pcm_bytes)
                self.is_speaking = True
                self.silence_ms  = 0
            else:
                if self.is_speaking:
                    self.silence_ms += 160  # ~10ms at 16kHz

    def take_audio(self) -> bytes:
        with self.lock:
            if not self.chunks:
                return b""
            data = b"".join(self.chunks)
            self.chunks = []
            self.is_speaking = False
            self.silence_ms = 0
            return data

    def ready_to_transcribe(self) -> bool:
        """Тишина > 600ms после речи → готово к распознаванию."""
        return self.is_speaking and self.silence_ms >= 600

    def interrupt(self):
        self.interrupted = True
        self.ai_speaking = False


# Global sessions
_sessions: dict[str, AudioSession] = {}


def pcm_to_wav(pcm: bytes, sample_rate=16000, channels=1) -> bytes:
    """Конвертирует сырой PCM (int16) в WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def register_realtime_events(socketio, app):
    """Регистрирует события realtime audio loop."""

    @socketio.on("rt_init")
    def on_rt_init(data):
        """Клиент инициализирует realtime сессию."""
        sid = _get_sid()
        session = AudioSession(sid)
        session.lang     = data.get("lang", "ru")
        session.agent_id = data.get("agent_id", "ari")
        _sessions[sid] = session
        socketio.emit("rt_ready", {"ok": True, "sid": sid}, to=sid)
        log.info(f"RT session init: {sid} lang={session.lang} agent={session.agent_id}")

    @socketio.on("rt_lang")
    def on_rt_lang(data):
        """Смена языка в реальном времени."""
        sid = _get_sid()
        if sid in _sessions:
            _sessions[sid].lang = data.get("lang", "ru")
            socketio.emit("rt_lang_ok", {"lang": data.get("lang")}, to=sid)

    @socketio.on("rt_audio_chunk")
    def on_audio_chunk(data):
        """
        Получаем аудио-чанк от клиента.
        data = {
            pcm_b64: base64 int16 PCM,
            is_speech: bool (VAD результат от клиента),
            sample_rate: 16000,
        }
        """
        import base64
        sid = _get_sid()
        if sid not in _sessions:
            return

        session = _sessions[sid]
        is_speech = bool(data.get("is_speech", False))
        pcm_b64   = data.get("pcm_b64", "")

        if not pcm_b64:
            return

        pcm = base64.b64decode(pcm_b64)
        session.add_chunk(pcm, is_speech)

        # Emit live transcript indicator
        if is_speech:
            socketio.emit("rt_listening", {"active": True}, to=sid)

        # Check if we should transcribe
        if session.ready_to_transcribe():
            audio_data = session.take_audio()
            if len(audio_data) > 1600:  # min ~50ms
                socketio.emit("rt_listening", {"active": False}, to=sid)
                socketio.emit("rt_processing", {"status": "transcribing"}, to=sid)
                # Run transcription + AI in background thread
                _RT_EXECUTOR.submit(_process_audio, app, socketio, sid, session, audio_data)

    @socketio.on("rt_interrupt")
    def on_interrupt(data):
        """Пользователь прервал AI — останавливаем генерацию."""
        sid = _get_sid()
        if sid in _sessions:
            _sessions[sid].interrupt()
            socketio.emit("rt_interrupted", {"ok": True}, to=sid)
            log.info(f"RT interrupted: {sid}")

    @socketio.on("rt_vad_result")
    def on_vad_result(data):
        """VAD результат от клиента (энергия, is_speech)."""
        sid = _get_sid()
        if sid not in _sessions:
            return
        session = _sessions[sid]
        is_speech = bool(data.get("is_speech", False))
        # If user speaks while AI is responding → interrupt
        if is_speech and session.ai_speaking:
            session.interrupt()
            socketio.emit("rt_interrupted", {"reason": "user_spoke"}, to=sid)

    @socketio.on("disconnect")
    def on_disconnect():
        sid = _get_sid()
        _sessions.pop(sid, None)


def _get_sid():
    """Получаем SID текущего подключения."""
    from flask_socketio import ConnectionRefusedError
    import flask
    try:
        from flask import request
        return request.sid
    except Exception:
        return "unknown"


def _process_audio(app, socketio, sid, session: AudioSession, pcm: bytes):
    """
    Фоновый поток:
    1. Whisper → текст
    2. AI generate (stream с проверкой прерывания)
    3. Отправляем токены клиенту
    """
    with app.app_context():
        session.interrupted = False

        # ── 1. Transcribe ─────────────────────────────────────
        wav_data = pcm_to_wav(pcm)
        text = _transcribe(wav_data, session.lang)

        if not text or len(text.strip()) < 2:
            socketio.emit("rt_processing", {"status": "idle"}, to=sid)
            return

        log.info(f"RT transcribed: '{text[:50]}'")
        socketio.emit("rt_transcript", {"text": text, "final": True}, to=sid)

        if session.interrupted:
            return

        # ── 2. Get AI response (streaming) ────────────────────
        session.ai_speaking = True
        socketio.emit("rt_processing", {"status": "thinking"}, to=sid)

        reply_tokens = []
        for token in _ai_stream(session, text):
            if session.interrupted:
                break
            reply_tokens.append(token)
            socketio.emit("rt_ai_token", {"token": token}, to=sid)

        session.ai_speaking = False
        full_reply = "".join(reply_tokens).strip()

        if full_reply and not session.interrupted:
            socketio.emit("rt_ai_done", {"text": full_reply}, to=sid)
            log.info(f"RT AI replied: '{full_reply[:60]}'")
        else:
            socketio.emit("rt_ai_done", {"text": "", "interrupted": True}, to=sid)

        socketio.emit("rt_processing", {"status": "idle"}, to=sid)


def _transcribe(wav_data: bytes, lang: str) -> str:
    """Распознаёт речь через Whisper → Vosk → пустая строка."""
    # Try Whisper first
    try:
        import tempfile, whisper as _whisper
        model = _get_whisper_model()
        if model:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data)
                tmp = f.name
            import os as _os
            whisper_lang = {"ru":"ru","kk":"kk","en":"en","de":"de"}.get(lang)
            hints = {
                "kk":"Сәлем. Менің атым.",
                "ru":"Привет. Как дела?",
                "en":"Hello. How are you?",
                "de":"Hallo. Wie geht es dir?",
            }
            result = model.transcribe(
                tmp, language=whisper_lang, fp16=False,
                temperature=0.0, no_speech_threshold=0.6,
                initial_prompt=hints.get(lang,""),
            )
            _os.unlink(tmp)
            return (result.get("text") or "").strip()
    except Exception as e:
        log.debug(f"Whisper transcribe: {e}")

    # Fallback: Vosk
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
        paths = {
            "ru": os.getenv("VOSK_RU_MODEL_PATH","ml_models/vosk-ru"),
            "kk": os.getenv("VOSK_KZ_MODEL_PATH","ml_models/vosk-kk"),
            "en": os.getenv("VOSK_EN_MODEL_PATH","ml_models/vosk-en"),
            "de": os.getenv("VOSK_DE_MODEL_PATH","ml_models/vosk-de"),
        }
        path = paths.get(lang, paths["ru"])
        if os.path.exists(path):
            m = Model(path)
            rec = KaldiRecognizer(m, 16000)
            rec.SetWords(True)
            # Skip WAV header
            audio = wav_data[44:] if wav_data[:4] == b"RIFF" else wav_data
            rec.AcceptWaveform(audio)
            result = json.loads(rec.FinalResult())
            return result.get("text","").strip()
    except Exception as e:
        log.debug(f"Vosk transcribe: {e}")

    return ""


# Whisper model cache
_whisper_model_cache = None
def _get_whisper_model():
    global _whisper_model_cache
    if _whisper_model_cache is not None:
        return _whisper_model_cache
    try:
        import whisper
        size = os.getenv("WHISPER_MODEL","base")
        _whisper_model_cache = whisper.load_model(size)
        log.info(f"RT Whisper '{size}' loaded")
    except Exception as e:
        log.warning(f"RT Whisper unavailable: {e}")
        _whisper_model_cache = False
    return _whisper_model_cache if _whisper_model_cache else None


def _ai_stream(session: AudioSession, text: str):
    """Generator: yields tokens from AI. Checks session.interrupted."""
    from flask import current_app as app

    lang      = session.lang
    agent_id  = session.agent_id
    lang_map  = {
        "kk":"ТЕК ҚАЗАҚ ТІЛІНДЕ жауап бер.",
        "en":"Reply ONLY in English.",
        "de":"Antworte NUR auf Deutsch.",
        "ru":"Отвечай ТОЛЬКО на русском.",
    }

    # Get persona
    try:
        from app import AGENT_PERSONAS
        persona = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS.get("ari", {}))
        system  = lang_map.get(lang, lang_map["ru"]) + "\n\n" + persona.get("system","Ты дружелюбный AI.")
    except Exception:
        system = lang_map.get(lang, lang_map["ru"])

    msgs = [{"role":"system","content":system}, {"role":"user","content":text}]

    # Try OpenAI streaming
    if os.getenv("OPENAI_API_KEY") and not getattr(_ai_stream, '_openai_dead', False):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=1, timeout=15.0)
            stream = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
                messages=msgs, temperature=0.95, max_tokens=200, stream=True
            )
            for chunk in stream:
                if session.interrupted: return
                token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if token: yield token
            return
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                _ai_stream._openai_dead = True

    # Try Groq streaming
    if os.getenv("GROQ_API_KEY") and not getattr(_ai_stream, '_groq_dead', False):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY"), max_retries=1, timeout=12.0
            )
            stream = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),
                messages=msgs, temperature=0.95, max_tokens=200, stream=True
            )
            for chunk in stream:
                if session.interrupted: return
                token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if token: yield token
            return
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                _ai_stream._groq_dead = True

    # Try OpenRouter
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                default_headers={"HTTP-Referer":"https://vivlos.app"},
                max_retries=1, timeout=18.0
            )
            stream = client.chat.completions.create(
                model=os.getenv("OPENROUTER_MODEL","meta-llama/llama-3.3-70b-instruct:free"),
                messages=msgs, temperature=0.95, max_tokens=200, stream=True
            )
            for chunk in stream:
                if session.interrupted: return
                token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if token: yield token
            return
        except Exception as e:
            log.warning(f"RT OpenRouter: {str(e)[:60]}")

    # Fallback: Gemini non-streaming
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY",""))
        model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL","gemini-2.0-flash"),
            system_instruction=system
        )
        resp = model.generate_content(text)
        words = (resp.text or "").strip().split()
        import time
        for w in words:
            if session.interrupted: return
            yield w + " "
            time.sleep(0.025)
        return
    except Exception as e:
        log.warning(f"RT Gemini: {str(e)[:60]}")

    yield "Хм... попробуй ещё раз."