# database package
from .setup import db, init_db
from .models import (
    User, CallLog, EmotionLog, UserMemory,
    AIConversation, AIThought, MoodPattern,
    Notification, CustomAgent, UserXP, Relationship,
    ChatThread, ChatMessage,
)
from .repos import (
    get_user, get_user_by_email, create_user,
    save_exchange, get_history, search_history,
    get_past_context, save_thought, get_thoughts,
    save_memory_fact, get_memories, log_emotion,
    get_or_create_relationship, update_relationship,
    get_or_create_xp, add_xp, get_conversation_stats,
)