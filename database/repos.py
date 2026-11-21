# -*- coding: utf-8 -*-
"""
database/repos.py
Все запросы к БД — отдельно от бизнес-логики.
app.py импортирует функции отсюда, не пишет db.query напрямую.
"""
from datetime import datetime
from .setup import db
from .models import (
    User, CallLog, EmotionLog, UserMemory,
    AIConversation, AIThought, MoodPattern,
    Notification, CustomAgent, UserXP, Relationship,
)


# ══ Пользователи ══════════════════════════════════════════════
def get_user(user_id):
    return db.session.get(User, user_id)

def get_user_by_email(email):
    return User.query.filter_by(email=email.lower().strip()).first()

def create_user(name, email, password, age_group="adult"):
    u = User(name=name, email=email.lower().strip(), age_group=age_group)
    u.set_password(password)
    db.session.add(u); db.session.commit()
    return u


# ══ История разговоров ════════════════════════════════════════
def save_message(user_id, agent_id, role, content,
                 emotion="neutral", emotion_conf=0.0,
                 engine=None, lang="ru", session_id=""):
    """Сохраняет одно сообщение (user или ai) в ai_conversation."""
    msg = AIConversation(
        user_id=user_id, agent_id=agent_id, role=role,
        content=(content or "")[:2000],
        emotion=emotion, emotion_conf=emotion_conf,
        engine=engine, lang=lang, session_id=session_id,
    )
    db.session.add(msg)
    db.session.commit()
    return msg


def save_exchange(user_id, agent_id, user_text, ai_text,
                  emotion="neutral", emotion_conf=0.0,
                  engine=None, lang="ru", session_id=""):
    """Сохраняет пару: сообщение пользователя + ответ AI."""
    ts = datetime.utcnow()
    db.session.add(AIConversation(
        user_id=user_id, agent_id=agent_id, role="user",
        content=(user_text or "")[:2000],
        emotion=emotion, emotion_conf=emotion_conf,
        lang=lang, session_id=session_id, created_at=ts,
    ))
    db.session.add(AIConversation(
        user_id=user_id, agent_id=agent_id, role="ai",
        content=(ai_text or "")[:2000],
        emotion=emotion, engine=engine,
        lang=lang, session_id=session_id, created_at=ts,
    ))
    # AI "мысль" если заметил эмоцию
    if emotion not in ("neutral",) and emotion_conf > 0.5:
        emo_map = {
            "sad":"грусть","angry":"злость","fearful":"тревога",
            "happy":"радость","surprised":"удивление","disgusted":"недовольство"
        }
        db.session.add(AIThought(
            user_id=user_id, agent_id=agent_id, session_id=session_id,
            thought=f"Заметил: {emo_map.get(emotion, emotion)} ({int(emotion_conf*100)}%)",
            thought_type="emotion_noticed",
        ))
    db.session.commit()


def get_history(user_id, agent_id=None, limit=50, page=1):
    """История разговоров пользователя."""
    q = AIConversation.query.filter_by(user_id=user_id)
    if agent_id: q = q.filter_by(agent_id=agent_id)
    total = q.count()
    msgs = q.order_by(AIConversation.created_at.desc())\
             .offset((page-1)*limit).limit(limit).all()
    return total, list(reversed(msgs))


def search_history(user_id, query_text, agent_id=None, limit=20):
    """Поиск по истории разговоров."""
    q = AIConversation.query.filter_by(user_id=user_id)\
        .filter(AIConversation.content.ilike(f"%{query_text}%"))
    if agent_id: q = q.filter_by(agent_id=agent_id)
    return q.order_by(AIConversation.created_at.desc()).limit(limit).all()


def get_past_context(user_id, agent_id, limit=6):
    """Последние N сообщений из прошлых сессий для инжекта в промпт."""
    return AIConversation.query\
        .filter_by(user_id=user_id, agent_id=agent_id)\
        .order_by(AIConversation.created_at.desc())\
        .limit(limit).all()


# ══ AI Мысли ══════════════════════════════════════════════════
def save_thought(user_id, agent_id, thought, thought_type="general", session_id=""):
    db.session.add(AIThought(
        user_id=user_id, agent_id=agent_id,
        thought=thought, thought_type=thought_type, session_id=session_id,
    ))
    db.session.commit()

def get_thoughts(user_id, agent_id, limit=5):
    return AIThought.query\
        .filter_by(user_id=user_id, agent_id=agent_id)\
        .order_by(AIThought.created_at.desc()).limit(limit).all()


# ══ Память о пользователе ════════════════════════════════════
def save_memory_fact(user_id, content, category="general", importance=5):
    """Сохраняет факт без дублей."""
    short = content[:80]
    if UserMemory.query.filter_by(user_id=user_id, content=short).first():
        return None
    m = UserMemory(user_id=user_id, content=short,
                   category=category, importance=importance)
    db.session.add(m); db.session.commit()
    return m

def get_memories(user_id, min_importance=5, limit=12):
    return UserMemory.query.filter_by(user_id=user_id)\
        .filter(UserMemory.importance >= min_importance)\
        .order_by(UserMemory.importance.desc()).limit(limit).all()


# ══ Эмоции ════════════════════════════════════════════════════
def log_emotion(call_id, emotion, confidence):
    db.session.add(EmotionLog(call_id=call_id, emotion=emotion, confidence=confidence))
    db.session.commit()

def get_emotion_stats(user_id):
    """Распределение эмоций пользователя."""
    return db.session.query(
        AIConversation.emotion, db.func.count(AIConversation.id)
    ).filter_by(user_id=user_id, role="user")\
     .group_by(AIConversation.emotion).all()


# ══ Отношения ═════════════════════════════════════════════════
def get_or_create_relationship(user_id, agent_id):
    rel = Relationship.query.filter_by(user_id=user_id, agent_id=agent_id).first()
    if not rel:
        rel = Relationship(user_id=user_id, agent_id=agent_id)
        db.session.add(rel); db.session.commit()
    return rel

def update_relationship(user_id, agent_id, level_gain=1, trust_gain=0):
    rel = get_or_create_relationship(user_id, agent_id)
    rel.level = min(100, rel.level + level_gain)
    rel.trust = min(100, rel.trust + trust_gain)
    rel.msg_count = (rel.msg_count or 0) + 1
    rel.updated_at = datetime.utcnow()
    db.session.commit()
    return rel


# ══ XP ════════════════════════════════════════════════════════
def get_or_create_xp(user_id):
    xp = UserXP.query.filter_by(user_id=user_id).first()
    if not xp:
        xp = UserXP(user_id=user_id); db.session.add(xp); db.session.commit()
    return xp

def add_xp(user_id, amount):
    xp = get_or_create_xp(user_id)
    xp.total_xp = (xp.total_xp or 0) + amount
    xp.updated_at = datetime.utcnow()
    db.session.commit()
    return xp.total_xp


# ══ Статистика ════════════════════════════════════════════════
def get_conversation_stats(user_id):
    total = AIConversation.query.filter_by(user_id=user_id).count()
    by_agent = db.session.query(
        AIConversation.agent_id, db.func.count(AIConversation.id)
    ).filter_by(user_id=user_id).group_by(AIConversation.agent_id).all()
    emotions = get_emotion_stats(user_id)
    return {
        "total_messages": total,
        "by_agent": {a: c for a, c in by_agent},
        "emotion_distribution": {e: c for e, c in emotions if e},
    }