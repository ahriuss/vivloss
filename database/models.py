# -*- coding: utf-8 -*-
"""
database/models.py
Все таблицы Vivlos — отдельно от app.py.
app.py подключает их через: from database.models import *
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .setup import db


# ══ Пользователи ══════════════════════════════════════════════
class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(200), unique=True, nullable=False)
    password_hash= db.Column(db.String(255), nullable=True)
    age_group    = db.Column(db.String(20), default="adult")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    calls        = db.relationship("CallLog", backref="user", lazy=True)

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p):
        if not self.password_hash: return True
        return check_password_hash(self.password_hash, p)


# ══ Звонки ════════════════════════════════════════════════════
class CallLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    agent_id   = db.Column(db.String(50), nullable=False)
    agent_name = db.Column(db.String(100))
    duration   = db.Column(db.Integer, default=0)
    messages   = db.Column(db.Text, default="[]")
    emotion    = db.Column(db.String(50))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Эмоции ════════════════════════════════════════════════════
class EmotionLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    call_id    = db.Column(db.Integer, db.ForeignKey("call_log.id"))
    emotion    = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    logged_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Память о пользователе ════════════════════════════════════
class UserMemory(db.Model):
    __tablename__ = "user_memory"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category   = db.Column(db.String(50))
    content    = db.Column(db.Text)
    importance = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used  = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Полная история разговоров с AI ════════════════════════════
class AIConversation(db.Model):
    """Каждое сообщение пользователя и ответ AI сохраняются здесь."""
    __tablename__ = "ai_conversation"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    agent_id     = db.Column(db.String(50), nullable=False)   # 'ari','max' и тд
    session_id   = db.Column(db.String(64))                    # UUID звонка
    role         = db.Column(db.String(10), nullable=False)    # 'user' | 'ai'
    content      = db.Column(db.Text, nullable=False)
    emotion      = db.Column(db.String(30), default="neutral")
    emotion_conf = db.Column(db.Float, default=0.0)
    engine       = db.Column(db.String(30))                    # 'gemini','groq'...
    lang         = db.Column(db.String(5), default="ru")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Мысли AI ══════════════════════════════════════════════════
class AIThought(db.Model):
    """Что AI заметил — эмоции, факты, настроение за сессию."""
    __tablename__ = "ai_thought"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    agent_id     = db.Column(db.String(50), nullable=False)
    session_id   = db.Column(db.String(64))
    thought      = db.Column(db.Text, nullable=False)
    thought_type = db.Column(db.String(30))  # 'emotion_noticed','fact_learned','mood'
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Настроение по дням ════════════════════════════════════════
class MoodPattern(db.Model):
    __tablename__ = "mood_pattern"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date         = db.Column(db.Date, default=datetime.utcnow)
    dominant_mood= db.Column(db.String(30))
    sad_count    = db.Column(db.Integer, default=0)
    happy_count  = db.Column(db.Integer, default=0)
    total_calls  = db.Column(db.Integer, default=0)


# ══ Чат-треды (новости/объявления) ════════════════════════════
class ChatThread(db.Model):
    __tablename__ = "chat_thread"
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(150), nullable=False)
    title_kk   = db.Column(db.String(150))
    avatar_icon= db.Column(db.String(50), default="ri-team-line")
    avatar_bg  = db.Column(db.String(20), default="#7c3aed")
    is_official= db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = "chat_message"
    id         = db.Column(db.Integer, primary_key=True)
    thread_id  = db.Column(db.Integer, db.ForeignKey("chat_thread.id"), nullable=False)
    sender     = db.Column(db.String(50), default="admin")
    text       = db.Column(db.Text)
    text_kk    = db.Column(db.Text)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Уведомления ═══════════════════════════════════════════════
class Notification(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    icon       = db.Column(db.String(50), default="ri-notification-3-line")
    title      = db.Column(db.String(200), nullable=False)
    title_kk   = db.Column(db.String(200))
    body       = db.Column(db.Text)
    body_kk    = db.Column(db.Text)
    kind       = db.Column(db.String(30), default="info")
    agent_id   = db.Column(db.String(50))
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Пользовательские AI-агенты ════════════════════════════════
class CustomAgent(db.Model):
    __tablename__ = "custom_agent"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    emoji         = db.Column(db.String(10), default="🤖")
    bg_color      = db.Column(db.String(20), default="#e8f4fd")
    description   = db.Column(db.Text, default="")
    system_prompt = db.Column(db.Text, default="")
    category      = db.Column(db.String(20), default="adults")
    voice_style   = db.Column(db.String(30), default="neutral")
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    # Personality sliders (optional, for custom agents)
    p_kindness    = db.Column(db.Integer, default=7)
    p_humor       = db.Column(db.Integer, default=5)
    p_energy      = db.Column(db.Integer, default=6)
    p_empathy     = db.Column(db.Integer, default=7)
    p_serious     = db.Column(db.Integer, default=5)
    p_curiosity   = db.Column(db.Integer, default=6)
    p_patience    = db.Column(db.Integer, default=6)
    p_topics      = db.Column(db.String(200), default="")
    p_style       = db.Column(db.String(200), default="")


# ══ XP / Прогресс ═════════════════════════════════════════════
class UserXP(db.Model):
    __tablename__  = "user_xp"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    total_xp       = db.Column(db.Integer, default=0)
    streak_days    = db.Column(db.Integer, default=0)
    last_call_date = db.Column(db.Date, nullable=True)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow)


# ══ Отношения пользователя с персонажем ═══════════════════════
class Relationship(db.Model):
    __tablename__ = "relationship"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    agent_id   = db.Column(db.String(64), nullable=False)
    level      = db.Column(db.Integer, default=0)   # 0-100
    trust      = db.Column(db.Integer, default=0)   # 0-100
    msg_count  = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)