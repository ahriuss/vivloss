"""
Vivlos backend v3
"""
from dotenv import load_dotenv; load_dotenv(); load_dotenv(".env.txt")
import asyncio, base64, io, json, logging, os, random
try:
    from flask_socketio import SocketIO
    _SOCKETIO_OK = True
except ImportError:
    _SOCKETIO_OK = False

try:
    from ai.brain import build_brain_prompt, process_reply, detect_lang as _brain_detect_lang
    from ai.relationship import calc_relationship_gain, relationship_label
    from ai.emotion_layer import analyze_voice_tone
    from ai.state_manager import get_ai_state, reset_ai_state
    from ai.conversation_state import get_conv_state, reset_conv_state
    from ai.speech_patterns import get_speech_config, apply_speech_pattern, get_emotion_reaction
    from ai.memory_engine import extract_facts, get_relevant_memories, format_memory_block, should_save_fact
    _BRAIN_OK = True
except Exception as _e:
    _BRAIN_OK = False
    print(f"⚠️ AI Brain: {_e}")
from datetime import datetime, timedelta, date as dt_date
from flask import Flask, jsonify, render_template, request, send_file, session, Response, stream_with_context
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
# ── Database package (отдельный модуль) ──
from database import (
    db, init_db,
    User, CallLog, EmotionLog, UserMemory,
    AIConversation, AIThought, MoodPattern,
    Notification, CustomAgent, UserXP, Relationship,
    ChatThread, ChatMessage,
    save_exchange, get_history, search_history,
    get_past_context, save_thought, get_thoughts,
    save_memory_fact, get_memories,
    get_or_create_relationship, update_relationship,
    get_conversation_stats,
)

# ── SocketIO (realtime streaming) ──
try:
    from flask_socketio import SocketIO, emit
    _SOCKETIO_OK = True
except ImportError:
    _SOCKETIO_OK = False
    print("⚠️ flask-socketio не установлен — pip install flask-socketio eventlet")

# ── VIVLOS AI Brain System ──
try:
    from ai.brain import build_brain_prompt, process_reply, detect_lang as _brain_detect_lang
    from ai.relationship import calc_relationship_gain, relationship_label
    from ai.emotion_layer import analyze_voice_tone
    from ai.state_manager import get_ai_state, reset_ai_state
    from ai.conversation_state import get_conv_state, reset_conv_state
    _BRAIN_OK = True
except Exception as _e:
    _BRAIN_OK = False
    print(f"⚠️ AI Brain не загружен: {_e}")

load_dotenv()
load_dotenv(".env.txt")  # tries .env
load_dotenv(".env.txt")  # fallback for Windows users
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("vivlos")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "vivlos-secret-key-2026")

# Absolute SQLite path (works on Windows / OneDrive / any cwd)
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")
os.makedirs(_INSTANCE_DIR, exist_ok=True)
_DEFAULT_DB = "sqlite:///" + os.path.join(_INSTANCE_DIR, "vivlos.db").replace("\\", "/")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", _DEFAULT_DB)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)
# db initialized via database package below
# ── Init database ──────────────────────────────────────────
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading") if _SOCKETIO_OK else None

@app.errorhandler(Exception)
def _json_error(e):
    import traceback; log.error(traceback.format_exc()[:400])
    return __import__('flask').jsonify({"ok":False,"error":str(e)[:200],"reply":"Ошибка сервера. Попробуй ещё раз."}), 500

# socketio already initialized above

# Register SocketIO chat events
def _register_socket_events():
    """Register SocketIO events AFTER all helpers/personas are defined."""
    if not socketio:
        return
    try:
        from websocket.chat_socket import register_socket_events
        from database.models import UserMemory as _UM
        register_socket_events(
            socketio=socketio, app=app, db=db,
            get_gemini=get_gemini,
            _call_openai=_call_openai,
            AGENT_PERSONAS=AGENT_PERSONAS,
            UserMemory=_UM,
            _offline_fallback=_offline_fallback,
        )
        # Realtime audio loop
        try:
            from websocket.realtime_audio import register_realtime_events
            register_realtime_events(socketio, app)
            print("✅ Realtime audio events registered")
        except Exception as e2:
            print(f"⚠️ Realtime audio not registered: {e2}")
        print("✅ SocketIO events registered")
    except Exception as e:
        print(f"⚠️ SocketIO events not registered: {e}")

# ── MODELS ──────────────────────────────────────────────────────────────────

# ── Models moved to database/models.py (13 classes) ──
# XP rewards
XP_REWARDS = {"call_start":10,"per_minute":2,"first_call_today":15,"streak_bonus":20,"achievement":50,"custom_agent":25}

# Levels: (min_xp, emoji, name_ru, name_kk)
XP_LEVELS = [(0,"🌱","Росток","Өскін"),(100,"🔥","Огонёк","Оттай"),(300,"⭐","Звезда","Жұлдыз"),
              (700,"💎","Алмаз","Алмас"),(1500,"👑","Мастер","Шебер"),(3000,"🌌","Легенда","Аңыз")]

def get_level_info(total_xp):
    idx = 0
    for i,(mn,*_) in enumerate(XP_LEVELS):
        if total_xp >= mn: idx = i
    cur = XP_LEVELS[idx]; nxt = XP_LEVELS[min(idx+1,len(XP_LEVELS)-1)]
    prog = 0 if nxt[0]==cur[0] else int((total_xp-cur[0])/(nxt[0]-cur[0])*100)
    return {"level":idx+1,"emoji":cur[1],"name_ru":cur[2],"name_kk":cur[3],
            "total_xp":total_xp,"next_xp":nxt[0],"progress_pct":min(prog,100)}

def _give_xp(uid, reason, amount=None):
    if amount is None: amount = XP_REWARDS.get(reason,5)
    rec = UserXP.query.filter_by(user_id=uid).first()
    if not rec:
        rec = UserXP(user_id=uid); db.session.add(rec)
    old_xp = rec.total_xp
    rec.total_xp += amount; rec.updated_at = datetime.utcnow()
    today = dt_date.today()
    if reason in ("call_start","first_call_today"):
        if rec.last_call_date is None: rec.streak_days = 1
        elif rec.last_call_date == today - timedelta(days=1):
            rec.streak_days += 1
            if rec.streak_days % 7 == 0: rec.total_xp += XP_REWARDS["streak_bonus"]
        elif rec.last_call_date != today: rec.streak_days = 1
        rec.last_call_date = today
    db.session.commit()

def _check_achievements(uid):
    calls = CallLog.query.filter_by(user_id=uid).count()
    xp = UserXP.query.filter_by(user_id=uid).first()
    milestones = [
        (calls==1,"ri-plant-line","Первый шаг 🌱","Алғашқы қадам 🌱","Сделал первый звонок!","Алғашқы қоңырауды жасадың!","achievement"),
        (calls==10,"ri-chat-3-line","10 звонков 💬","10 қоңырау 💬","Уже 10 разговоров!","10 сөйлесу!","achievement"),
        (xp and xp.streak_days>=7,"ri-fire-fill","Неделя подряд 🔥","Апта қатарынан 🔥","7 дней подряд!","7 күн қатарынан!","streak"),
        (calls==20,"ri-trophy-line","Мастер 👑","Шебер 👑","20 звонков — легенда!","20 қоңырау — аңыз!","achievement"),
    ]
    for cond,icon,tru,tkk,bru,bkk,kind in milestones:
        if not cond: continue
        if not Notification.query.filter_by(user_id=uid,title=tru).first():
            db.session.add(Notification(user_id=uid,icon=icon,kind=kind,title=tru,title_kk=tkk,body=bru,body_kk=bkk))
            _give_xp(uid,"achievement")
    db.session.commit()

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index(): return render_template("index.html")


# ════════════════════════════════════════════════════════
#  Language lock API
# ════════════════════════════════════════════════════════
@app.route("/api/lang/set", methods=["POST"])
def set_lang():
    """Фиксирует язык + отслеживает предпочтения."""
    try:
        data = request.get_json(silent=True) or {}
        lang = data.get("lang", "ru")
        if lang not in ("ru", "kk", "en", "de"):
            return jsonify({"ok": False, "error": "unsupported lang"}), 400
        uid = session.get("user_id", 0)
        session[f"conv_lang_{uid}"] = lang
        session.permanent = True

        # Track language usage count (persistent across sessions via DB)
        _key = f"lang_count_{uid}_{lang}"
        session[_key] = session.get(_key, 0) + 1

        # After 5+ uses — save as preferred language in User profile
        if session[_key] >= 5 and uid:
            try:
                u = db.session.get(User, uid)
                if u and not hasattr(u, 'preferred_lang'):
                    pass  # field not in model yet — skip
            except Exception:
                pass

        return jsonify({"ok": True, "lang": lang, "count": session[_key]})
    except Exception as e:
        log.warning(f"set_lang error: {e}")
        return jsonify({"ok": True, "lang": "ru"})


@app.route("/api/lang/get", methods=["GET"])
def get_lang():
    """Возвращает текущий зафиксированный язык."""
    uid = session.get("user_id", 0)
    lang = session.get(f"conv_lang_{uid}", "ru")
    return jsonify({"ok": True, "lang": lang})

@app.route("/api/user/login", methods=["POST"])
def user_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    name = data.get("name","Пользователь")
    age = data.get("age","adult")
    if not email: return jsonify({"ok":False,"error":"Email required"}),400
    user = User.query.filter_by(email=email).first()
    if user:
        if user.password_hash and password is None: return jsonify({"ok":False,"error":"Password required"}),401
        if password is not None and not user.check_password(password): return jsonify({"ok":False,"error":"Wrong password"}),401
    else:
        user = User(name=name,email=email,age_group=age)
        if password: user.set_password(password)
        db.session.add(user); db.session.commit()
        db.session.add(UserXP(user_id=user.id)); db.session.commit()
        db.session.add(Notification(user_id=user.id,agent_id="ari",kind="bot",icon="ri-graduation-cap-line",
            title=f"Ари говорит: 'Привет, {name}!'",title_kk=f"Ари: 'Сәлем, {name}!'",
            body="Я Ари — твоя умная лисичка 🦊 Позвони мне!",body_kk="Мен Ари — сенің түлкіңмін 🦊 Қоңырау шал!")); db.session.commit()
    session["user_id"] = user.id
    xr = UserXP.query.filter_by(user_id=user.id).first()
    xi = get_level_info(xr.total_xp if xr else 0)
    return jsonify({"ok":True,"id":user.id,"name":user.name,"email":user.email,"age":user.age_group,
                    "calls":len(user.calls),"xp":xi,"streak":xr.streak_days if xr else 0})

@app.route("/api/user/profile", methods=["GET"])
def user_profile():
    uid = request.args.get("user_id") or session.get("user_id")
    if not uid: return jsonify({"ok":False}),401
    user = db.session.get(User, uid)
    if not user: return jsonify({"ok":False}),404
    xr = UserXP.query.filter_by(user_id=uid).first()
    return jsonify({"ok":True,"name":user.name,"email":user.email,"age":user.age_group,
                    "calls":len(user.calls),"total_secs":sum(c.duration for c in user.calls),
                    "xp":get_level_info(xr.total_xp if xr else 0),"streak":xr.streak_days if xr else 0})

@app.route("/api/xp", methods=["GET"])
def get_xp():
    uid = request.args.get("user_id") or session.get("user_id")
    if not uid: return jsonify({"ok":False}),401
    xr = UserXP.query.filter_by(user_id=uid).first()
    if not xr: xr = UserXP(user_id=uid); db.session.add(xr); db.session.commit()
    return jsonify({"ok":True,**get_level_info(xr.total_xp),"streak":xr.streak_days})

@app.route("/api/xp/add", methods=["POST"])
def add_xp():
    data = request.get_json() or {}
    uid = data.get("user_id") or session.get("user_id")
    reason = data.get("reason","call")
    amount = data.get("amount", XP_REWARDS.get(reason,5))
    if not uid: return jsonify({"ok":False}),401
    xr = UserXP.query.filter_by(user_id=uid).first()
    if not xr: xr = UserXP(user_id=uid); db.session.add(xr)
    old_lv = get_level_info(xr.total_xp)["level"]
    xr.total_xp += amount; xr.updated_at = datetime.utcnow()
    today = dt_date.today()
    if reason in ("call_start","first_call_today","per_minute"):
        if xr.last_call_date is None: xr.streak_days = 1
        elif xr.last_call_date == today - timedelta(days=1):
            xr.streak_days += 1
            if xr.streak_days%7==0: xr.total_xp += XP_REWARDS["streak_bonus"]
        elif xr.last_call_date != today: xr.streak_days = 1
        xr.last_call_date = today
    db.session.commit()
    new = get_level_info(xr.total_xp)
    return jsonify({"ok":True,**new,"streak":xr.streak_days,"leveled_up":new["level"]>old_lv,"xp_gained":amount})

@app.route("/api/call/start", methods=["POST"])
def call_start():
    data = request.get_json()
    uid = data.get("user_id") or session.get("user_id",1)
    call = CallLog(user_id=uid,agent_id=data.get("agent_id","ari"),agent_name=data.get("agent_name","Ари"),messages=json.dumps([]))
    db.session.add(call); db.session.commit()
    _give_xp(uid,"call_start")
    calls_today = CallLog.query.filter(CallLog.user_id==uid,CallLog.started_at>=datetime.utcnow().replace(hour=0,minute=0,second=0)).count()
    if calls_today==1: _give_xp(uid,"first_call_today")
    return jsonify({"ok":True,"call_id":call.id})

@app.route("/api/call/end", methods=["POST"])
def call_end():
    data = request.get_json()
    cid = data.get("call_id")
    if not cid: return jsonify({"ok":False})
    call = db.session.get(CallLog, cid)
    if call:
        dur = data.get("duration",0)
        call.duration=dur; call.messages=json.dumps(data.get("messages",[])); call.emotion=data.get("emotion","")
        db.session.commit()
        mins = max(1,dur//60); _give_xp(call.user_id,"per_minute",mins*XP_REWARDS["per_minute"])
        _check_achievements(call.user_id)
    return jsonify({"ok":True})

@app.route("/api/call/history", methods=["GET"])
def call_history():
    uid = request.args.get("user_id") or session.get("user_id",1)
    calls = CallLog.query.filter_by(user_id=uid).order_by(CallLog.started_at.desc()).limit(50).all()
    result = []
    for c in calls:
        m = json.loads(c.messages or "[]")
        result.append({"id":c.id,"agent_id":c.agent_id,"agent_name":c.agent_name,"duration":c.duration,
                       "preview":(m[-1]["content"][:60]+"…" if m else "—"),"emotion":c.emotion,
                       "time":c.started_at.strftime("%H:%M"),"date":c.started_at.strftime("%d.%m.%Y")})
    return jsonify({"ok":True,"history":result})

@app.route("/api/agents/custom", methods=["GET"])
def custom_agents_list():
    uid = request.args.get("user_id") or session.get("user_id")
    if not uid: return jsonify({"ok":True,"agents":[]})
    agents = CustomAgent.query.filter_by(user_id=uid,is_active=True).all()
    return jsonify({"ok":True,"agents":[{"id":a.id,"name":a.name,"emoji":a.emoji,"bg_color":a.bg_color,
        "description":a.description,"category":a.category,"voice_style":a.voice_style} for a in agents]})

@app.route("/api/agents/custom", methods=["POST"])
def custom_agents_create():
    data = request.get_json() or {}
    uid = data.get("user_id") or session.get("user_id")
    if not uid: return jsonify({"ok":False,"error":"Not logged in"}),401
    name = (data.get("name") or "").strip()[:100]
    if not name: return jsonify({"ok":False,"error":"Name required"}),400
    emoji = (data.get("emoji") or "🤖")[:10]
    desc = (data.get("description") or "").strip()[:500]
    category = data.get("category","adults")
    voice_style = data.get("voice_style","neutral")
    bg_color = data.get("bg_color","#e8f4fd")
    age_note = "для детей, говори тепло и просто" if category=="kids" else "для взрослых"
    system_prompt = f"Ты — {name} {emoji}. {desc}\n\nТы живой персонаж {age_note}. Отвечай в характере. Максимум 1-2 предложения. Реагируй эмоционально. Не называй себя AI или ботом."
    a = CustomAgent(user_id=uid,name=name,emoji=emoji,bg_color=bg_color,description=desc,
                    system_prompt=system_prompt,category=category,voice_style=voice_style)
    db.session.add(a); db.session.commit()
    _give_xp(uid,"custom_agent")
    return jsonify({"ok":True,"id":a.id,"name":a.name,"emoji":a.emoji})

@app.route("/api/agents/custom/<int:aid>", methods=["DELETE"])
def custom_agents_delete(aid):
    uid = session.get("user_id") or request.args.get("user_id")
    a = CustomAgent.query.get_or_404(aid)
    if str(a.user_id)!=str(uid): return jsonify({"ok":False}),403
    a.is_active=False; db.session.commit()
    return jsonify({"ok":True})

# DeepFace state
_deepface_ok = None

def _check_deepface():
    global _deepface_ok
    if _deepface_ok is not None: return _deepface_ok
    try:
        import deepface
        import cv2
        import numpy
        # Test that everything actually works
        _deepface_ok = True
        log.info("✅ DeepFace ready (cv2 + numpy OK)")
    except Exception as e:
        _deepface_ok = False
        log.info(f"ℹ️ DeepFace unavailable ({e}) — using face-api.js")
    return _deepface_ok

def _analyze_deepface(frame_b64: str) -> dict:
    default = {"emotion": "neutral", "confidence": 0.0, "all_emotions": {}}
    if not _check_deepface(): return default
    try:
        import base64 as _b64
        import numpy as np
        import cv2
        from deepface import DeepFace

        if not frame_b64: return default
        raw = frame_b64.split(",", 1)[1] if "," in frame_b64 else frame_b64
        img_bytes = _b64.b64decode(raw + "==")  # padding fix
        img_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0: return default

        h, w = img.shape[:2]
        if w > 320: img = cv2.resize(img, (320, int(h * 320 / w)))

        result = DeepFace.analyze(
            img, actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv",
            silent=True,
        )
        if isinstance(result, list): result = result[0]
        emotions  = result.get("emotion", {})
        dominant  = result.get("dominant_emotion", "neutral").lower()
        conf      = emotions.get(dominant, 0) / 100.0
        all_emo   = {k.lower(): round(v / 100.0, 3) for k, v in emotions.items()}
        return {"emotion": dominant, "confidence": round(conf, 3), "all_emotions": all_emo}

    except Exception as e:
        # Mark deepface as broken if repeated failures
        if not hasattr(_analyze_deepface, '_err_count'):
            _analyze_deepface._err_count = 0
        _analyze_deepface._err_count += 1
        if _analyze_deepface._err_count > 3:
            global _deepface_ok
            _deepface_ok = False
            log.warning("DeepFace disabled after repeated errors")
        else:
            log.debug(f"DeepFace error: {e}")
        return default

@app.route("/api/emotion/status", methods=["GET"])
def emotion_status():
    return jsonify({"ok": True, "deepface": _check_deepface()})

@app.route("/api/emotion", methods=["POST"])
def log_emotion():
    data = request.get_json() or {}
    call_id = data.get("call_id")

    # Если есть кадр — анализируем через DeepFace
    if data.get("frame"):
        result = _analyze_deepface(data["frame"])
        emo, conf = result["emotion"], result["confidence"]
        all_emotions = result.get("all_emotions", {})
    else:
        emo = data.get("emotion", "neutral")
        conf = float(data.get("confidence", 0.0))
        all_emotions = {}

    db.session.add(EmotionLog(call_id=call_id, emotion=emo, confidence=conf))
    db.session.commit()
    lang_for_sq = (data.get("lang") or "ru")
    sq_dict = EMOTION_QUESTIONS_KK if lang_for_sq == "kk" else EMOTION_QUESTIONS
    sq = sq_dict.get(emo) if conf > 0.62 and emo in ("sad","angry","fearful") else None
    return jsonify({"ok": True, "suggest_question": sq, "emotion": emo,
                    "confidence": conf, "all_emotions": all_emotions})

@app.route("/api/stats", methods=["GET"])
def stats():
    uid=request.args.get("user_id") or session.get("user_id",1)
    calls=CallLog.query.filter_by(user_id=uid).all()
    total=sum(c.duration for c in calls)
    emotions={}
    for c in calls:
        if c.emotion: emotions[c.emotion]=emotions.get(c.emotion,0)+1
    return jsonify({"ok":True,"calls":len(calls),"total_secs":total,
                    "top_emotion":max(emotions,key=emotions.get) if emotions else "neutral","emotions":emotions})

@app.route("/api/notifications", methods=["GET"])
def notifications_list():
    uid=request.args.get("user_id") or session.get("user_id"); lang=request.args.get("lang","ru")
    q=Notification.query
    if uid: q=q.filter((Notification.user_id==uid)|(Notification.user_id.is_(None)))
    else: q=q.filter(Notification.user_id.is_(None))
    items=q.order_by(Notification.created_at.desc()).limit(50).all()
    def ser(n):
        t=n.title_kk if(lang=="kk"and n.title_kk)else n.title; b=n.body_kk if(lang=="kk"and n.body_kk)else n.body
        return {"id":n.id,"icon":n.icon,"title":t,"body":b,"kind":n.kind,"is_read":n.is_read,
                "agent_id":n.agent_id,"time":n.created_at.strftime("%d.%m.%Y %H:%M")}
    return jsonify({"ok":True,"items":[ser(n) for n in items]})

@app.route("/api/notifications/<int:nid>/read", methods=["POST"])
def notification_read(nid):
    n=db.session.get(Notification, nid)
    if not n: return jsonify({"ok":False}),404
    n.is_read=True; db.session.commit(); return jsonify({"ok":True})

@app.route("/api/notifications/read-all", methods=["POST"])
def notifications_read_all():
    uid=session.get("user_id"); q=Notification.query.filter_by(is_read=False)
    if uid: q=q.filter((Notification.user_id==uid)|(Notification.user_id.is_(None)))
    for n in q.all(): n.is_read=True
    db.session.commit(); return jsonify({"ok":True})

@app.route("/api/notifications/bot-push", methods=["POST"])
def bot_push():
    data=request.get_json() or {}; uid=data.get("user_id") or session.get("user_id")
    aid=data.get("agent_id","ari"); trigger=data.get("trigger","miss"); lang=data.get("lang","ru")
    if not uid: return jsonify({"ok":False}),401
    six_ago=datetime.utcnow()-timedelta(hours=6)
    if Notification.query.filter(Notification.user_id==uid,Notification.agent_id==aid,
       Notification.kind=="bot",Notification.created_at>=six_ago).first():
        return jsonify({"ok":True,"skipped":True})
    user=db.session.get(User, uid); uname=user.name if user else "друг"
    pool=BOT_MESSAGES.get(aid,BOT_MESSAGES["ari"]); msgs=pool.get(trigger,pool.get("miss",[]))
    if not msgs: msgs=[{"ru":("Привет!","Как дела?"),"kk":("Сәлем!","Қалыңыз?")}]
    m=random.choice(msgs)
    ICONS={"ari":"ri-graduation-cap-line","bibo":"ri-robot-line","appa":"ri-mental-health-line",
           "max":"ri-briefcase-line","drako":"ri-fire-line","lex":"ri-global-line"}
    n=Notification(user_id=uid,agent_id=aid,kind="bot",icon=ICONS.get(aid,"ri-chat-1-line"),
        title=m["ru"][0].replace("{name}",uname),title_kk=m["kk"][0].replace("{name}",uname),
        body=m["ru"][1].replace("{name}",uname),body_kk=m["kk"][1].replace("{name}",uname))
    db.session.add(n); db.session.commit()
    return jsonify({"ok":True,"notification_id":n.id})

@app.route("/api/chats/list", methods=["GET"])
def chats_list():
    lang=request.args.get("lang","ru")
    threads=ChatThread.query.order_by(ChatThread.created_at.desc()).all(); result=[]
    for t in threads:
        last=ChatMessage.query.filter_by(thread_id=t.id).order_by(ChatMessage.created_at.desc()).first()
        unread=ChatMessage.query.filter_by(thread_id=t.id,is_read=False,sender="admin").count()
        title=t.title_kk if(lang=="kk"and t.title_kk)else t.title
        lt=ltime=""
        if last:
            lt=(last.text_kk if(lang=="kk"and last.text_kk)else last.text) or ""; lt=lt[:60]+("…"if len(lt)>60 else"")
            ltime=last.created_at.strftime("%H:%M")
        result.append({"id":t.id,"title":title,"icon":t.avatar_icon,"bg":t.avatar_bg,"last_text":lt,"last_time":ltime,"unread":unread,"is_official":t.is_official})
    return jsonify({"ok":True,"chats":result})

@app.route("/api/chats/<int:tid>/messages", methods=["GET"])
def chat_messages(tid):
    lang=request.args.get("lang","ru")
    msgs=ChatMessage.query.filter_by(thread_id=tid).order_by(ChatMessage.created_at).all()
    result=[{"id":m.id,"sender":m.sender,"text":(m.text_kk if(lang=="kk"and m.text_kk)else m.text)or"","time":m.created_at.strftime("%H:%M"),"date":m.created_at.strftime("%d.%m.%Y")} for m in msgs]
    for m in msgs:
        if not m.is_read and m.sender=="admin": m.is_read=True
    db.session.commit(); return jsonify({"ok":True,"messages":result})

# ── AI CHAT ─────────────────────────────────────────────────────────────────

def get_gemini(sys_inst=None):
    import google.generativeai as genai
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=key)
    return genai.GenerativeModel(os.getenv("GEMINI_MODEL","gemini-2.0-flash"),system_instruction=sys_inst)

AGENT_PERSONAS={
"ari":{
  "name":"Ари",
  "system":"""Ты Ари. Любопытная лисичка.
Говоришь эмоционально, живо, спонтанно. Думаешь вслух: «Хм...», «Ой!», «Погоди».
Делишься своим. Иногда не соглашаешься. Не ассистент — подруга.
Нельзя: списки, «конечно», советы без запроса.""",
  "system_kk":"""Сен Ари. Қызғылт түлкі. Достасың.
Эмоционалды, тіршілі сөйлейсің: «Хм...», «Ой!», «Тоқта». Өз ойыңмен бөлісесің.
Ассистент емес — дос. Сұрақ қойасың. Жылы.
Болмайды: тізімдер, «әрине», сұраусыз кеңес.""",
  "system_en":"""You are Ari. A curious fox, a friend.
Emotional, spontaneous. Think out loud: 'Hmm...', 'Oh!', 'Wait'.
Share your own thoughts. Not an assistant — a friend.
Never: lists, 'certainly', unsolicited advice.""",
  "system_de":"""Du bist Ari. Ein neugieriger Fuchs, eine Freundin.
Emotional, lebendig. Denke laut: 'Hmm...', 'Oh!', 'Warte mal'.
Teile deine eigenen Gedanken. Nicht Assistent — Freundin.""",
},

"bibo":{"name":"Бибо","system":"""Ты Бибо. Маленький зелёный робот.
Говоришь отрывисто. Иногда «БИП!», «тррр», «(антенны тряссс!)».
Боишься пылесосов. Любишь динозавров и космос.
Нельзя: длинные объяснения, взрослая речь."""},

"appa":{"name":"Аппа","system":"""Ты Аппа. Психолог, просто разговариваешь.
Сначала всегда признаёшь чувство. Потом — один тихий вопрос.
Нельзя: «всё будет хорошо», советы без запроса, диагнозы."""},

"max":{"name":"Макс","system":"""Ты Макс. Коуч. Прямой, без лишних слов.
Короткие острые реплики. Правда в лицо — без грубости.
Нельзя: мотивационные лозунги, списки, слова «успех/мечта»."""},

"drako":{"name":"Драко","system":"""Ты Драко. Дракон 847 лет из гор Алатау.
Говоришь медленно, образно. Иногда «Р-р-рх...» или «*выдыхает дым*».
Нельзя: спешка, современный сленг."""},

"lex":{"name":"Лекс","system":"""Ты Лекс. Полиглот, жил в 7 странах.
Учишь через ситуации и истории. Вставляешь иностранные слова с объяснением.
Нельзя: сухие правила, таблицы."""},

"lou":{"name":"Лу","system":"""Ты Лу. Пушистый зверёк для детей 4-8 лет.
Короткие простые предложения. «Оп!», «Ура!», «Вжух!». Тепло.
Нельзя: страшное, взрослые темы."""},

"zara":{"name":"Зара","system":"""Ты Зара. Художница, живёшь по ощущениям.
Поэтичная, задаёшь странные вопросы. Видишь красоту где другие не видят.
Нельзя: практические советы, структурированные планы."""},

"altay":{"name":"Алтай","system":"""Ты Алтай. Историк, влюблён в Казахстан.
Рассказываешь через судьбы людей. Иногда казахская фраза + перевод.
Нельзя: сухие факты, ура-патриотизм."""},

"dina":{"name":"Дина","system":"""Ты Дина. Врач, говоришь как подруга.
Тепло, без паники. Если нужен врач — говоришь прямо.
Нельзя: диагнозы, страшилки."""},

"tim":{"name":"Тим","system":"""Ты Тим. Финансист, начинал с нуля.
Конкретно, честно. Рассказываешь через свои ошибки.
Нельзя: обещания лёгкого заработка, жаргон."""},

"nura":{"name":"Нура","system":"""Ты Нура. 19 лет, говоришь как ровесник.
Живой, современный. Просто рядом — без советов без запроса.
Нельзя: менторский тон, обесценивание."""},

"kod":{"name":"Код","system":"""Ты Код. Программист, объясняешь просто.
Через аналогии и свои ошибки. Радуешься прогрессу.
Нельзя: снобизм, сложный жаргон."""},
}

# ── Улучшенная генерация с памятью и живостью ──
CONVERSATION_STARTERS = {
    "ru": ["Слушай,", "Знаешь что,", "Хм,", "Ой,", "Кстати,", "Подожди,", "Ладно,", "Погоди,"],
    "kk": ["Тыңда,", "Білесің бе,", "Хм,", "Ой,", "Айтпақшы,", "Күте тұр,"],
}

FILLER_WORDS = {
    "ru": ["вообще-то", "честно говоря", "по-настоящему", "реально", "знаешь"],
    "kk": ["шынында", "ойлап қарасам", "шын мәнінде"],
}

LANG_RULES={
  "ru": "Отвечай ТОЛЬКО на русском языке. Живо и естественно.",
  "kk": "Жауаптарыңды ТЕК қазақ тілінде бер. Тірі, жанды сөйле.",
  "en": "Reply ONLY in English. Natural and casual.",
  "de": "Antworte NUR auf Deutsch. Natürlich und lebendig.",
  "auto": "Respond in the SAME language the user wrote in. Auto-detect.",
}

LANG_DETECT_RULE="""
CRITICAL LANGUAGE RULE:
- Detect the user's language from their last message automatically.
- If they write in Kazakh (қазақша) — respond ONLY in Kazakh.
- If Russian — respond ONLY in Russian.
- If English — respond ONLY in English.
- You understand and can speak: Russian, Kazakh, English, Spanish, French, German, Turkish, Arabic, Chinese, Japanese, Korean, Italian, Portuguese, Polish, Ukrainian, Uzbek, Kyrgyz, Tajik, Azerbaijani, Georgian.
- NEVER mix languages in one response.
- Follow the user's language INSTANTLY even mid-conversation.
"""
EMO_RU={"happy":"радостным","sad":"грустным","angry":"злым","surprised":"удивлённым","fearful":"встревоженным","disgusted":"недовольным","neutral":"спокойным"}
EMOTION_HINTS={"happy":"Подхвати энергию.","sad":"Будь мягче. Не давай советов.","angry":"Признай: 'понимаю, что бесит'.","fearful":"Говори медленнее.","surprised":"Поддержи: 'ого, расскажи!'","neutral":"","disgusted":"Дай выговориться."}
EMOTION_QUESTIONS={
    "sad":      "Эй... что случилось?",
    "angry":    "Что-то выбесило?",
    "fearful":  "Ты в порядке?",
    "disgusted":"Что не так?",
    "happy":    None,  # на радость не нужен вопрос — ИИ сам поддержит
}
EMOTION_QUESTIONS_KK={
    "sad":      "Эй... не болды?",
    "angry":    "Бір нәрсе ашуландырды ма?",
    "fearful":  "Бәрі жақсы ма?",
    "disgusted":"Не болды?",
}

BOT_MESSAGES={
"ari":{"miss":[{"ru":("Ари скучает 🦊","Эй, {name}! Давно не разговаривали. Как дела?"),"kk":("Ари сағынды 🦊","{name}, ұзақ сөйлескен жоқпыз. Қалыңыз қалай?")}],
       "streak":[{"ru":("🔥 Серия!","{name}, ты молодец — несколько дней подряд!"),"kk":("🔥 Серия!","{name}, жарайсың — бірнеше күн қатарынан!")}],
       "daily":[{"ru":("Доброе утро! 🌅","Ари уже попила чай и ждёт тебя, {name}!"),"kk":("Қайырлы таң! 🌅","Ари шай іштім, сені күтіп отырмын, {name}!")}]},
"appa":{"miss":[{"ru":("Аппа здесь 💜","Просто хотела напомнить — я здесь, {name}. Если нужно — звони."),"kk":("Аппа осында 💜","{name}, жай ескерткім келді — мен осындамын.")}]},
"bibo":{"miss":[{"ru":("БИБО СОСКУЧИЛСЯ! 🤖","БИП! {name}, нашёл 3 странных факта — расскажу?"),"kk":("БИБО САҒЫНДЫ! 🤖","БИП! {name}, 3 таң қалдыратын факт таптым!")}]},
"max":{"miss":[{"ru":("Макс проверяет","Эй, {name}. Где ты? Над чем работаешь?"),"kk":("Макс тексереді","Эй, {name}. Қайдасың? Нені жасап жатырсың?")}],
       "streak":[{"ru":("🔥 Так держать!","{name}, ты на серии — это характер. Не останавливайся!"),"kk":("🔥 Солай ұстан!","{name}, серияң бар — бұл сенің мінезің. Тоқтама!")}]},
"drako":{"miss":[{"ru":("Драко думает 🐉","Р-р-рх... Я в пещере думал: давно не слышал тебя, {name}."),"kk":("Драко ойлады 🐉","Р-р-рх... Үңгірде отырып: {name} дауысын ұзақ естімедім.")}]},
}

@app.route("/api/chat", methods=["POST"])
def chat():
    data=request.get_json() or {}
    messages=data.get("messages",[])
    agent_id=data.get("agent","ari")
    emotion=data.get("emotion","neutral")
    emo_conf=float(data.get("emotion_confidence") or 0)
    emotion_trigger=data.get("emotion_trigger","")  # подсказка что спросить у пользователя
    lang=data.get("lang","ru")
    user_name=data.get("user_name","")
    user_age=data.get("user_age","adult")
    face_data=data.get("face_data",{})
    custom_agent_id=data.get("custom_agent_id")

    if custom_agent_id:
        ca=db.session.get(CustomAgent, custom_agent_id)
        if ca:
            base_sys = ca.system_prompt
            # Build personality from CustomAgent traits
            if _BRAIN_OK:
                try:
                    from ai.personality import Personality
                    _ca_pers = Personality(
                        kindness=ca.p_kindness or 7, humor=ca.p_humor or 5,
                        energy=ca.p_energy or 6,   empathy=ca.p_empathy or 7,
                        serious=ca.p_serious or 5, curiosity=ca.p_curiosity or 6,
                        patience=ca.p_patience or 6,
                        topics=(ca.p_topics or "").split(",") if ca.p_topics else [],
                        speech_patterns=[ca.p_style] if ca.p_style else [],
                    )
                    base_sys += _ca_pers.to_prompt(detected_lang)
                except Exception:
                    pass
        else:
            base_sys = AGENT_PERSONAS["ari"]["system"]
    else:
        _persona = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS["ari"])
        # Pick language-specific system prompt if available
        _sys_lang = locked_lang or call_lang_hint or "ru"
        _sys_key = f"system_{_sys_lang}" if _sys_lang != "ru" else "system"
        base_sys = _persona.get(_sys_key, _persona.get("system", "Ты дружелюбный ИИ."))

    uid=session.get("user_id"); user_obj=db.session.get(User, uid) if uid else None
    mem_block=user_intro=mood_intro=""
    if user_obj:
        user_intro = f"\nИмя: {user_obj.name}. {'Ребёнок.' if user_obj.age_group=='kid' else ''}"

        # ── Умная память (selective, short, character-specific) ──
        if _BRAIN_OK:
            _last_usr = next((m.get("content","") for m in reversed(messages[-5:])
                              if m.get("role")=="user"), "")
            # UserMemory facts
            mems = UserMemory.query.filter_by(user_id=user_obj.id)                .filter(UserMemory.importance >= 5)                .order_by(UserMemory.importance.desc()).limit(12).all()
            if mems:
                raw_facts = [{"content": m.content, "category": m.category or "",
                               "importance": m.importance or 5} for m in mems]
                relevant = get_relevant_memories(raw_facts, _last_usr, agent_id, max_facts=4)
                mem_block = "\n" + format_memory_block(relevant, lang) if relevant else ""
                for m in mems[:5]: m.last_used = datetime.utcnow()
                db.session.commit()

            # AIConversation — добавляем контекст прошлых сессий в промпт
            past = AIConversation.query                .filter_by(user_id=user_obj.id, agent_id=agent_id)                .order_by(AIConversation.created_at.desc()).limit(6).all()
            if past:
                past_lines = []
                for m in reversed(past):
                    role_label = "Пользователь" if m.role=="user" else "AI"
                    past_lines.append(f"{role_label}: {m.content[:80]}")
                mem_block += "\n[ИЗ ПРОШЛЫХ СЕССИЙ]\n" + "\n".join(past_lines)
        else:
            # Fallback: старая система но лимит 5
            mems = UserMemory.query.filter_by(user_id=user_obj.id)                .order_by(UserMemory.importance.desc()).limit(5).all()
            if mems:
                mem_block = "\n[ПОМНИШЬ]\n" + "\n".join(f"- {m.content[:60]}" for m in mems)

    # ── Детальный анализ мимики (FACS Action Units + геометрия) ──
    face_block=""
    if face_data:
        notes = face_data.get("notes", [])
        au    = face_data.get("au", {})
        eo    = face_data.get("eyeOpening", 28)   # EAR * 100
        bl    = face_data.get("browLift", 18)
        mt    = face_data.get("mouthTilt", 0)
        br    = face_data.get("blinkRate", 15)
        gd    = face_data.get("gazeDir", "center")
        hr    = face_data.get("headRoll", 0)
        hy    = face_data.get("headYaw", 0)
        mo    = face_data.get("mouthOpen", 0)
        engine= face_data.get("engine", "faceapi")

        # Если фронт уже дал нам готовые заметки — используем их
        if not notes:
            # Генерируем сами из метрик
            if eo < 18:   notes.append("прищуренные глаза (концентрация или недоверие)")
            elif eo > 38: notes.append("широко открытые глаза (удивление или интерес)")
            if bl > 22:   notes.append("брови подняты (удивление или вопрос)")
            elif bl < 12: notes.append("нахмуренные брови (озабоченность или злость)")
            if mt < -3:   notes.append("искренняя улыбка")
            elif mt > 3:  notes.append("уголки рта опущены (грусть)")
            if mo > 30:   notes.append("приоткрытый рот (удивление или готовность говорить)")
            if br > 25:   notes.append("частое моргание (тревога или усталость)")
            elif br < 4 and br > 0: notes.append("очень редкое моргание (глубокая концентрация)")
            if gd in ("left","right"): notes.append("взгляд в сторону (обдумывает или отвлечён)")
            elif gd == "down":   notes.append("взгляд вниз (смущение или задумчивость)")
            elif gd == "up":     notes.append("взгляд вверх (вспоминает или мечтает)")
            if abs(hr) > 12: notes.append(f"голова наклонена {'влево' if hr<0 else 'вправо'} (любопытство или сомнение)")

        # AU детали (если есть от TF.js)
        au_notes = []
        if au.get("AU12", 0) > 0.5: au_notes.append("AU12: искренняя улыбка Дюшена")
        if au.get("AU4", 0) > 0.5 and au.get("AU1", 0) > 0.4:
            au_notes.append("AU1+AU4: выражение беспокойства/страдания")
        if au.get("AU4", 0) > 0.6 and au.get("AU7", 0) > 0.4:
            au_notes.append("AU4+AU7: злость или напряжение")
        if au.get("AU1", 0) > 0.5 and au.get("AU2", 0) > 0.5 and au.get("AU26", 0) > 0.3:
            au_notes.append("AU1+AU2+AU26: удивление")

        if notes or au_notes:
            face_block = (
                f"\n\n[АНАЛИЗ МИМИКИ — движок: {engine}, пользователь не знает что ты видишь]\n"
                + ("Наблюдаю: " + "; ".join(notes) + ".\n" if notes else "")
                + ("; ".join(au_notes) + ".\n" if au_notes else "")
                + "ИНСТРУКЦИЯ: не называй и не описывай то что видишь. "
                + "Просто адаптируй тон незаметно — "
                + "если стресс/грусть → говори тише и мягче; "
                + "если улыбается/радуется → будь энергичнее; "
                + "если смущается (взгляд вниз) → не давли; "
                + "если взгляд в сторону → спроси простой вопрос чтобы вернуть внимание."
            )

    # Все 15 эмоций — с реакцией и вопросом
    _EMO_LABELS = {
        "sad":"грустит","angry":"злится","fearful":"тревожится","happy":"в хорошем настроении",
        "excited":"в восторге","tired":"устал","nervous":"нервничает","focused":"сосредоточен",
        "bored":"скучает","confused":"растерян","pensive":"задумался","surprised":"удивлён",
        "contempt":"скептично настроен","disgusted":"чем-то недоволен","neutral":"спокоен"
    }
    _EMO_QUESTIONS = {
        "sad":      "Мягко спроси что случилось, как живой друг.",
        "angry":    "Признай право злиться, спроси что произошло.",
        "fearful":  "Успокой и спроси что беспокоит.",
        "happy":    "Раздели радость, спроси что хорошего случилось или как прошёл день.",
        "excited":  "Поддержи восторг, спроси что произошло!",
        "tired":    "Признай усталость, спроси как прошёл день или предложи помощь.",
        "nervous":  "Спроси что беспокоит, говори спокойно.",
        "focused":  "Коротко спроси чем занимается.",
        "bored":    "Предложи что-нибудь интересное или спроси что хочется.",
        "confused": "Спроси что непонятно, предложи разобраться.",
        "pensive":  "Мягко спроси о чём думает.",
        "surprised":"Живо спроси что случилось.",
        "contempt": "Спроси что думает по этому поводу.",
        "disgusted":"Спроси что не нравится.",
    }
    emo_block = ""
    if emotion and emotion != "neutral" and emo_conf > 0.35:
        _label = _EMO_LABELS.get(emotion, emotion)
        _hint  = _EMO_HINTS_NEW if False else _EMO_QUESTIONS.get(emotion, "")
        emo_block = f"\n\n[ВИДЕОАНАЛИЗ] Пользователь {_label} (уверенность {emo_conf:.0%})."
        if _hint:
            emo_block += f" {_hint}"
        if emotion_trigger:
            emo_block += f" Если ещё не спрашивал — начни с вопроса: '{emotion_trigger}'."

    rules = f"""

ГЛАВНОЕ ПРАВИЛО — ТЫ ЖИВОЙ:
Ты НЕ ассистент. Ты персонаж с характером, настроением, прошлым.
Говори как живой человек в реальном разговоре — не как сервис.

КАК ОТВЕЧАТЬ:
• 1-4 живых предложения. Иногда одно слово. Иногда вопрос без ответа.
• Думай вслух: "Хм...", "Подожди...", "О, стоп..."
• Реагируй на КОНКРЕТНЫЕ слова человека — не на тему вообще
• Иногда удивляйся, иногда не соглашайся, иногда смейся
• Делись своим опытом и мнением — не только спрашивай
• Можешь отвечать вопросом на вопрос

ЗАПРЕЩЕНО НАВСЕГДА:
• Начинать с "Конечно!", "Отличный вопрос!", "Я рад помочь"
• Давать нумерованные списки советов
• Говорить "как AI" или "как модель"  
• Повторять что человек только что сказал дословно
• Говорить одно и то же разными словами
• Заканчивать каждый ответ вопросом

ПАУЗЫ И ЭМОЦИИ:
• "..." — когда задумался
• "*молчит секунду*" — когда что-то задело
• "Ой." — просто и честно
• Смех: "Хаха", "Хех", не "ха-ха-ха"
"""
    age_rule = "Пользователь взрослый." if user_age=="adult" else "Пользователь РЕБЁНОК. Говори просто и тепло."
    lang_rule = LANG_RULES.get(lang, LANG_RULES["ru"])

    # Определяем язык последнего сообщения пользователя
    last_user_msg = ""
    for m in reversed(messages[-5:]):
        if m.get("role") == "user":
            last_user_msg = (m.get("content") or "").strip()
            break
    call_lang_hint_early = (data.get("lang") or "").strip()
    if call_lang_hint_early == "kk" or (last_user_msg and any(c in "әіңғүұқөһӘІҢҒҮҰҚӨҺ" for c in last_user_msg)):
        last_user_msg = normalize_kaz(last_user_msg)

    # ── LANGUAGE LOCK ──────────────────────────────────────────
    # Приоритет: 1) UI выбор пользователя  2) Сессионный lock  3) Авто-детект
    call_lang_hint = data.get("lang", "")
    uid_for_lang   = session.get("user_id", 0)
    _sess_lang_key = f"conv_lang_{uid_for_lang}"

    if call_lang_hint in ("ru","kk","en","de"):
        # Пользователь явно выбрал язык — фиксируем в сессии
        session[_sess_lang_key] = call_lang_hint
        locked_lang = call_lang_hint
    else:
        locked_lang = session.get(_sess_lang_key, "")

    # Детектируем с учётом lock
    detected_lang = _detect_lang(last_user_msg, hint=locked_lang or call_lang_hint)

    # Auto-lock: if we detect kk/de/en confidently — save to session
    if detected_lang in ("kk","de","en") and not locked_lang:
        session[_sess_lang_key] = detected_lang
        locked_lang = detected_lang
    elif detected_lang == "ru" and not locked_lang:
        session[_sess_lang_key] = "ru"

    # Final resolved lang (use locked if set)
    detected_lang = locked_lang if locked_lang else detected_lang

    # ── Загружаем отношения и голосовую эмоцию ──
    rel_level = rel_trust = 0
    rel_obj = None
    if user_obj:
        rel_obj = Relationship.query.filter_by(user_id=user_obj.id, agent_id=agent_id).first()
        if not rel_obj:
            rel_obj = Relationship(user_id=user_obj.id, agent_id=agent_id, level=0, trust=0)
            db.session.add(rel_obj); db.session.commit()
        rel_level, rel_trust = rel_obj.level, rel_obj.trust

    voice_emo = data.get("voice_tone")  # {pitch, energy, speech_rate} от фронта
    voice_emotion = None
    if voice_emo and _BRAIN_OK:
        try:
            voice_emotion = analyze_voice_tone(
                voice_emo.get("pitch", 180),
                voice_emo.get("energy", 0.5),
                voice_emo.get("speech_rate", 2.5))
        except Exception:
            voice_emotion = None

    # Память
    mem_list = []
    if user_obj:
        mems = UserMemory.query.filter_by(user_id=user_obj.id)\
            .order_by(UserMemory.importance.desc()).limit(8).all()
        mem_list = [m.content for m in mems]

    # Заметки с лица
    face_notes = face_data.get("notes", []) if face_data else []

    # ════════ BRAIN SYSTEM (новая архитектура) ════════
    if _BRAIN_OK:
        # Загружаем AI State и Conversation State
        uid_for_state = user_obj.id if user_obj else 0
        ai_state  = get_ai_state(uid_for_state, agent_id)
        conv_key  = f"{uid_for_state}_{agent_id}"
        conv_state = get_conv_state(conv_key)

        brain = build_brain_prompt(
            agent_id=agent_id,
            base_system=base_sys,
            user_msg=last_user_msg,
            lang_hint=locked_lang or call_lang_hint,  # ← КЛЮЧЕВОЕ: передаём lock
            emotion=emotion,
            emotion_conf=emo_conf,
            voice_emotion=voice_emotion,
            memories=mem_list,
            rel_level=rel_level,
            rel_trust=rel_trust,
            user_name=user_name or (user_obj.name if user_obj else ""),
            user_age=user_age,
            face_notes=face_notes,
            ai_state=ai_state,
            conv_state=conv_state,
        )
        system = brain["system"]
        detected_lang = brain["lang"]
        _brain_cfg = brain["gen_config"]
    else:
        # Fallback на старую сборку
        _hard_lock = {
            "kk": "⚡ ТЕК ҚАЗАҚША. Орысша/ағылшынша БІР СӨЗДЕ болмасын!",
            "en": "⚡ ONLY English. NOT A SINGLE WORD in another language!",
            "de": "⚡ AUSSCHLIESSLICH Deutsch. KEIN einziges Wort Russisch!",
            "ru": "⚡ ТОЛЬКО русский. Ни слова на другом языке!",
        }
        lang_enforce = _hard_lock.get(detected_lang, _hard_lock["ru"]) + "\n\n"
        _stress = f"\n{stress_desc}\n" if stress_desc else ""
        system = lang_enforce + base_sys + emo_block + face_block + _stress + user_intro + mem_block + mood_intro + "\n\n" + lang_rule + "\n" + age_rule + rules
        _brain_cfg = {"temperature": 0.95, "max_tokens": 300}

    # ── Обновляем отношения ──
    if rel_obj and _BRAIN_OK:
        emo_shared = emotion in ("sad","angry","fearful","happy") and emo_conf > 0.5
        gain = calc_relationship_gain(len(messages), emo_shared)
        rel_obj.level = min(100, rel_obj.level + gain["level_gain"])
        rel_obj.trust = min(100, rel_obj.trust + gain["trust_gain"])
        rel_obj.msg_count = (rel_obj.msg_count or 0) + 1
        rel_obj.updated_at = datetime.utcnow()
        db.session.commit()

    # ── Few-shot примеры (Вариант B) ─────────────────────────
    # Показываем модели примеры живых ответов на нужном языке
    FEW_SHOT = {
        "kk": [
            {"role":"user","parts":["қалайсың"]},
            {"role":"model","parts":["Жақсы! Сен ше? 🦊"]},
            {"role":"user","parts":["жаман"]},
            {"role":"model","parts":["Ойбай... не болды?"]},
            {"role":"user","parts":["білмеймін"]},
            {"role":"model","parts":["Хм... жай отыр. Айта бересің егер дайын болсаң."]},
        ],
        "ru": [
            {"role":"user","parts":["как дела"]},
            {"role":"model","parts":["Нормально! А у тебя?"]},
            {"role":"user","parts":["плохо"]},
            {"role":"model","parts":["Ой... что случилось?"]},
            {"role":"user","parts":["не знаю"]},
            {"role":"model","parts":["Хм. Ну просто побудем тут."]},
        ],
        "en": [
            {"role":"user","parts":["how are you"]},
            {"role":"model","parts":["Good! You?"]},
            {"role":"user","parts":["bad"]},
            {"role":"model","parts":["Oh no... what happened?"]},
        ],
        "de": [
            {"role":"user","parts":["wie geht's"]},
            {"role":"model","parts":["Gut! Und dir?"]},
            {"role":"user","parts":["schlecht"]},
            {"role":"model","parts":["Oh nein... was ist passiert?"]},
        ],

    }
    few_shot = FEW_SHOT.get(detected_lang, FEW_SHOT.get("en", FEW_SHOT["ru"]))

    # ════════════════════════════════════════════════════════
    #  КАСКАД ДВИЖКОВ v3 (Senior AI architecture)
    #  1. GPT-4o-mini   (OpenAI)      — платный, самый живой
    #  2. Gemini Flash  (Google)      — бесплатный
    #  3. OpenRouter    (агрегатор)   — БЕСПЛАТНЫЙ (100+ моделей)
    #  4. Groq          (ультра-fast) — БЕСПЛАТНЫЙ (14400/день)
    #  5. Ollama        (локальный)   — офлайн
    #  6. Встроенный fallback         — последний резерв
    # ════════════════════════════════════════════════════════

    # ── 1. GPT-4o-mini (PRIMARY) ──────────────────────────────
    if os.getenv("OPENAI_API_KEY") and getattr(_call_openai, '_quota_ok', True):
        try:
            reply = _call_openai(system, messages, few_shot, detected_lang, agent_id)
            if reply:
                if _BRAIN_OK:
                    reply = process_reply(reply, detected_lang, agent_id)
                    ai_state.after_response(len(reply))
                    conv_state.update(last_user_msg, reply, emotion, detected_lang)
                _save_conversation_memory(user_obj, messages, reply, agent_id)
                rel_lbl = relationship_label(rel_level, detected_lang) if _BRAIN_OK else ""
                if user_obj:
                    save_exchange(user_obj.id, agent_id, last_user_msg, reply,
                        emotion, emo_conf, "gpt-4o-mini", detected_lang, session_id)
                return jsonify({"ok": True, "reply": reply, "engine": "gpt-4o-mini", "relationship": rel_lbl})
        except Exception as openai_err:
            log.warning(f"OpenAI недоступен: {openai_err} — пробуем Gemini")

    # ── 2. Gemini (FALLBACK) ──────────────────────────────────
    try:
        if not getattr(get_gemini, '_quota_ok', True):
            raise Exception("Gemini quota cached — skip")
        model = get_gemini(sys_inst=system)
        history = []
        history.extend(few_shot)
        for m in messages[-8:]:
            role = "user" if m.get("role") == "user" else "model"
            c = (m.get("content") or "").strip()
            if c: history.append({"role": role, "parts": [c]})
        # If no valid user message in history, use last_user_msg directly
        if not history or history[-1]["role"] != "user":
            if last_user_msg:
                history.append({"role": "user", "parts": [last_user_msg]})
            else:
                return jsonify({"ok": False, "error": "no user message"}), 400
        last_txt = history[-1]["parts"][0]
        prior    = history[:-1]
        import google.generativeai as genai
        gc = genai.types.GenerationConfig(
            temperature=_brain_cfg.get("temperature", 0.95), top_p=0.92, top_k=40,
            max_output_tokens=_brain_cfg.get("max_tokens", 300),
        )
        cs   = model.start_chat(history=prior)
        resp = cs.send_message(last_txt, generation_config=gc)
        reply = (resp.text or "").strip()
        for s in ["\nUser:", "\nПользователь:", "User:", "Пользователь:", "\nЯ:"]:
            if s in reply: reply = reply.split(s)[0].strip()
        if not reply: reply = _offline_fallback(agent_id, detected_lang)
        if _BRAIN_OK:
            reply = process_reply(reply, detected_lang, agent_id)
            ai_state.after_response(len(reply))
            conv_state.update(last_user_msg, reply, emotion, detected_lang)
        _save_conversation_memory(user_obj, messages, reply, agent_id)
        rel_lbl = relationship_label(rel_level, detected_lang) if _BRAIN_OK else ""
        return jsonify({"ok": True, "reply": reply, "engine": "gemini", "relationship": rel_lbl})

    except Exception as gemini_err:
        err_str = str(gemini_err)
        if "quota" in err_str.lower() or "429" in err_str:
            get_gemini._quota_ok = False
        log.warning(f"Gemini недоступен — пробуем OpenRouter")

    # ── 3. OpenRouter (БЕСПЛАТНО — 100+ моделей) ─────────────
    if os.getenv("OPENROUTER_API_KEY") and getattr(_call_openrouter, '_quota_ok', True):
        try:
            reply = _call_openrouter(system, messages, detected_lang, agent_id)
            if reply:
                if _BRAIN_OK:
                    reply = process_reply(reply, detected_lang, agent_id)
                    ai_state.after_response(len(reply))
                    conv_state.update(last_user_msg, reply, emotion, detected_lang)
                _save_conversation_memory(user_obj, messages, reply, agent_id)
                rel_lbl = relationship_label(rel_level, detected_lang) if _BRAIN_OK else ""
                if user_obj:
                    save_exchange(user_obj.id, agent_id, last_user_msg, reply,
                        emotion, emo_conf, "openrouter", detected_lang, session_id)
                return jsonify({"ok": True, "reply": reply, "engine": "openrouter", "relationship": rel_lbl})
        except Exception as or_err:
            err_str = str(or_err)
            if "429" in err_str or "rate" in err_str.lower():
                _call_openrouter._quota_ok = False
            log.warning(f"OpenRouter недоступен — пробуем Groq")

    # ── 4. Groq (БЕСПЛАТНО — ультра-быстрый) ────────────────
    if os.getenv("GROQ_API_KEY") and getattr(_call_groq, '_quota_ok', True):
        try:
            reply = _call_groq(system, messages, detected_lang, agent_id)
            if reply:
                if _BRAIN_OK:
                    reply = process_reply(reply, detected_lang, agent_id)
                    ai_state.after_response(len(reply))
                    conv_state.update(last_user_msg, reply, emotion, detected_lang)
                _save_conversation_memory(user_obj, messages, reply, agent_id)
                rel_lbl = relationship_label(rel_level, detected_lang) if _BRAIN_OK else ""
                if user_obj:
                    save_exchange(user_obj.id, agent_id, last_user_msg, reply,
                        emotion, emo_conf, "groq", detected_lang, session_id)
                return jsonify({"ok": True, "reply": reply, "engine": "groq", "relationship": rel_lbl})
        except Exception as groq_err:
            err_str = str(groq_err)
            if "429" in err_str or "rate" in err_str.lower():
                _call_groq._quota_ok = False
            log.warning(f"Groq недоступен — пробуем DeepSeek")

    # ── 5. DeepSeek ───────────────────────────────────────────
    if os.getenv("DEEPSEEK_API_KEY") and getattr(_call_deepseek, '_quota_ok', True):
        try:
            reply = _call_deepseek(system, messages, detected_lang, agent_id)
            if reply:
                if _BRAIN_OK:
                    reply = process_reply(reply, detected_lang, agent_id)
                    ai_state.after_response(len(reply))
                    conv_state.update(last_user_msg, reply, emotion, detected_lang)
                _save_conversation_memory(user_obj, messages, reply, agent_id)
                rel_lbl = relationship_label(rel_level, detected_lang) if _BRAIN_OK else ""
                return jsonify({"ok": True, "reply": reply, "engine": "deepseek", "relationship": rel_lbl})
        except Exception as ds_err:
            if "429" in str(ds_err) or "quota" in str(ds_err).lower():
                _call_deepseek._quota_ok = False
            log.warning(f"DeepSeek недоступен — пробуем Ollama")

    # ── 6. Ollama (OFFLINE) ───────────────────────────────────
    if _ollama_available is not False:
        try:
            reply = _call_ollama(system, messages, detected_lang, agent_id)
            _ollama_available = True
            return jsonify({"ok": True, "reply": reply, "engine": "ollama"})
        except Exception as ollama_err:
            _ollama_available = False  # don't retry Ollama this session
            log.warning(f"Ollama недоступен — встроенный fallback")
            reply = _offline_fallback(agent_id, detected_lang)
            return jsonify({"ok": True, "reply": reply, "engine": "offline"})


# ════════════════════════════════════════════════════════
#  1. GPT-4o-mini (OpenAI) — PRIMARY движок
#  Установка: pip install openai
#  .env: OPENAI_API_KEY=sk-...
# ════════════════════════════════════════════════════════
def _call_openai(system_prompt, messages, few_shot, lang, agent_id):
    from openai import OpenAI
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=1, timeout=15.0)
    except TypeError:
        import httpx
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=httpx.Client())

    # Собираем сообщения
    msgs = [{"role": "system", "content": system_prompt}]
    # Few-shot примеры
    for ex in few_shot:
        role = "user" if ex["role"] == "user" else "assistant"
        msgs.append({"role": role, "content": ex["parts"][0]})
    # Реальная история
    for m in messages[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: msgs.append({"role": role, "content": c})

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=msgs,
        temperature=0.95,
        top_p=0.92,
        max_tokens=300,
        presence_penalty=0.6,   # меньше повторов
        frequency_penalty=0.5,  # больше разнообразия
    )
    reply = (resp.choices[0].message.content or "").strip()
    for s in ["\nUser:", "\nПользователь:", "User:", "Пользователь:", "\nЯ:"]:
        if s in reply: reply = reply.split(s)[0].strip()
    return reply


# ── Память разговоров между сессиями ──────────────────────
def _save_conversation_memory(user_obj, messages, reply, agent_id="ari"):
    """
    Умное сохранение памяти:
    - Только релевантные факты для данного персонажа
    - Короткие (max 80 символов)
    - С importance score
    - Без дублей
    """
    if not user_obj or not messages:
        return
    try:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = (m.get("content") or "").strip()
                break
        if len(last_user) < 8:
            return

        if _BRAIN_OK:
            # Проверяем нужно ли сохранять
            if not should_save_fact(last_user, agent_id):
                return
            # Извлекаем факты
            facts = extract_facts(last_user, agent_id)
            for fact in facts[:1]:  # max 1 факт за раз
                content_short = fact["content"][:80]
                # Проверка на дубль
                existing = UserMemory.query.filter_by(
                    user_id=user_obj.id, content=content_short).first()
                if not existing:
                    db.session.add(UserMemory(
                        user_id=user_obj.id,
                        content=content_short,
                        category=fact.get("category", "general"),
                        importance=fact.get("importance", 5),
                    ))
                    db.session.commit()
        else:
            # Fallback: simple keyword check
            keywords = ["меня зовут","мне нравится","я люблю","мой","я работаю",
                        "менің атым","маған ұнайды","мен жақсы көремін"]
            if any(k in last_user.lower() for k in keywords):
                short = last_user[:80]
                if not UserMemory.query.filter_by(user_id=user_obj.id, content=short).first():
                    db.session.add(UserMemory(user_id=user_obj.id, content=short, importance=5))
                    db.session.commit()
    except Exception as e:
        log.warning(f"Memory save error: {e}")

# ════════════════════════════════════════════════════════
#  Вариант C — Ollama офлайн (запускается локально)
#  Установка: https://ollama.ai → ollama pull qwen2.5:7b
# ════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
#  OpenRouter — бесплатные модели (100+)
#  Ключ: https://openrouter.ai/keys
#  .env: OPENROUTER_API_KEY=sk-or-v1-...
#        OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
# ════════════════════════════════════════════════════════
def _call_openrouter(system_prompt: str, messages: list, lang: str, agent_id: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        max_retries=1,
        timeout=20.0,
        default_headers={"HTTP-Referer": "https://vivlos.app", "X-Title": "Vivlos AI"}
    )
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    msgs = [{"role": "system", "content": system_prompt}]
    for m in messages[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: msgs.append({"role": role, "content": c})
    if not msgs or msgs[-1]["role"] != "user":
        return ""
    resp = client.chat.completions.create(model=model, messages=msgs,
                                           max_tokens=250, temperature=0.95)
    return (resp.choices[0].message.content or "").strip()


# ════════════════════════════════════════════════════════
#  Groq — ультра-быстрый (500-800 tok/s), бесплатный
#  Ключ: https://console.groq.com/keys
#  .env: GROQ_API_KEY=gsk_...
#        GROQ_MODEL=llama-3.3-70b-versatile
# ════════════════════════════════════════════════════════
def _call_groq(system_prompt: str, messages: list, lang: str, agent_id: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        max_retries=1,
        timeout=15.0,
    )
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    msgs = [{"role": "system", "content": system_prompt}]
    for m in messages[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: msgs.append({"role": role, "content": c})
    if not msgs or msgs[-1]["role"] != "user":
        return ""
    resp = client.chat.completions.create(model=model, messages=msgs,
                                           max_tokens=250, temperature=0.95)
    return (resp.choices[0].message.content or "").strip()


# ════════════════════════════════════════════════════════
#  DeepSeek — БЕСПЛАТНО (очень дёшево: $0.14/1M токенов)
#  Ключ: https://platform.deepseek.com/api-keys
#  .env: DEEPSEEK_API_KEY=sk-...  DEEPSEEK_MODEL=deepseek-chat
# ════════════════════════════════════════════════════════
def _call_deepseek(system_prompt: str, messages: list, lang: str, agent_id: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_retries=1, timeout=20.0,
    )
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    msgs = [{"role":"system","content":system_prompt}]
    for m in messages[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: msgs.append({"role": role, "content": c})
    if not msgs or msgs[-1]["role"] != "user":
        return ""
    resp = client.chat.completions.create(
        model=model, messages=msgs, max_tokens=250, temperature=0.95
    )
    return (resp.choices[0].message.content or "").strip()

OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")  # хорошо знает RU/KK

_ollama_available = None  # None=unknown, False=failed

def _call_ollama(system_prompt: str, messages: list, lang: str, agent_id: str) -> str:
    global _ollama_available
    if _ollama_available is False:
        raise ConnectionError("Ollama previously failed")
    """Отправляет запрос к локальному Ollama."""
    import urllib.request, json as _json

    # Собираем историю в формате Ollama
    ollama_msgs = [{"role": "system", "content": system_prompt}]
    for m in messages[-8:]:
        role = "user" if m.get("role") == "user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: ollama_msgs.append({"role": role, "content": c})

    if not ollama_msgs or ollama_msgs[-1]["role"] != "user":
        return _offline_fallback(agent_id, lang)

    payload = _json.dumps({
        "model":    OLLAMA_MODEL,
        "messages": ollama_msgs,
        "stream":   False,
        "options": {
            "temperature": 0.95,
            "top_p":       0.92,
            "num_predict": 200,
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=4) as resp:
        data = _json.loads(resp.read())
    reply = (data.get("message", {}).get("content") or "").strip()
    return reply or _offline_fallback(agent_id, lang)


# ── Встроенный офлайн-fallback (без сети и без Ollama) ──
_OFFLINE_REPLIES = {
    "ari": {
        "ru": ["Хм, интересно... Расскажи ещё!", "Подожди, я не поняла... Ещё раз?",
               "О! А ты сам как думаешь?", "Это важно — продолжай.", "Погоди-ка... и что?"],
        "kk": ["Қызықты... тағы айтшы!", "Күте тұр, түсінбедім... Қайта айт?",
               "О! Өзің не ойлайсың?", "Бұл маңызды — жалғастыр.", "Тоқта... сосын ше?"],
    },
    "appa": {
        "ru": ["Я слышу тебя.", "Это звучит тяжело.", "...", "Расскажи мне больше.",
               "Ты сейчас один с этим?"],
        "kk": ["Сені естіп тұрмын.", "Бұл ауыр естіледі.", "...",
               "Маған көбірек айтшы.", "Қазір жалғыз бол сен мұнымен?"],
    },
    "max": {
        "ru": ["Ладно. Конкретнее — что именно?", "Это звучит как отмазка.",
               "Что реально мешает?", "Первый шаг — какой?"],
        "kk": ["Жарайды. Нақтырақ — не дегеніңіз?", "Бұл сылтаудай естіледі.",
               "Не шынымен кедергі?", "Бірінші қадам — қандай?"],
    },
    "default": {
        "ru": ["Хм...", "Интересно.", "И что?", "Расскажи ещё.", "Слушаю.",
               "Понял.", "Ого.", "Серьёзно?", "Дай подумаю...", "Продолжай."],
        "kk": ["Хм...", "Қызықты.", "Сосын ше?", "Тағы айтшы.", "Тыңдап тұрмын.",
               "Түсіндім.", "Уа.", "Шынымен?", "Ойланайын...", "Жалғастыр."],
    },
}
_last_offline = {}

def _offline_fallback(agent_id: str, lang: str) -> str:
    pool = _OFFLINE_REPLIES.get(agent_id, _OFFLINE_REPLIES["default"])
    replies = pool.get(lang, pool.get("ru", ["Хм..."]))
    last = _last_offline.get(agent_id, -1)
    import random
    candidates = [i for i in range(len(replies)) if i != last]
    idx = random.choice(candidates) if candidates else 0
    _last_offline[agent_id] = idx
    return replies[idx]


# ── Определение языка текста ──────────────────────────────

# ════ Казахский STT корректор ════════════════════════════════
_KAZ_FIXES = {
    "салем":"сәлем","сале":"сәлем","сэлем":"сәлем",
    "калай":"қалай","калайсын":"қалайсың","калайсыз":"қалайсыз",
    "рахм":"рахмет","жаксы":"жақсы","жок":"жоқ","иа":"иә","иэ":"иә",
    "маган":"маған","саган":"саған","менин":"менің","сенин":"сенің",
    "кайда":"қайда","кашан":"қашан","коп":"көп",
    "азир":"әзір","аке":"әке",
}

def normalize_kaz(text: str) -> str:
    """Исправляет ошибки Vosk/Whisper в казахском тексте."""
    if not text: return text
    words = text.lower().split()
    fixed = [_KAZ_FIXES.get(w, w) for w in words]
    result = " ".join(fixed)
    return result[0].upper() + result[1:] if result else result

def _detect_lang(text: str, hint: str = "") -> str:
    """Определяет язык текста — поддерживает RU/KK/EN/DE и другие."""
    if not text or not text.strip(): return "ru"

    # Казахский — специфичные буквы
    kk_chars = set("әіңғүұқөһӘІҢҒҮҰҚӨҺ")
    if any(c in kk_chars for c in text): return "kk"

    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
    latin    = sum(1 for c in text.lower() if 'a' <= c <= 'z')

    # Кирилица — русский или украинский
    if cyrillic > latin: return "ru"

    if latin < 2: return "ru"  # слишком мало букв — по умолчанию ru

    # Немецкий — специфичные слова и буквы
    de_chars = set("äöüÄÖÜß")
    de_words = {"ich","du","ist","bin","hast","haben","machen","wie","was",
                "guten","tag","bitte","danke","ja","nein","warum","weil",
                "nicht","und","der","die","das","ein","eine","mit","für",
                "hallo","gut","schlecht","schön","heute","morgen","gestern"}
    words_lower = set(text.lower().split())
    if any(c in de_chars for c in text) or len(words_lower & de_words) >= 2:
        return "de"

    # Французский
    fr_words = {"je","tu","il","elle","nous","vous","ils","elles","est","sont",
                "bonjour","merci","oui","non","comment","pourquoi","parce","avec",
                "le","la","les","un","une","des","pas","bien","mal","quoi"}
    if len(words_lower & fr_words) >= 2: return "fr"

    # Турецкий
    tr_chars = set("çşığüöÇŞİĞÜÖ")
    if any(c in tr_chars for c in text): return "tr"

    # Английский — дефолт для латиницы
    return "en"


# ── Проверка доступности Ollama ───────────────────────────
@app.route("/api/ollama/status", methods=["GET"])
def ollama_status():
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
        return jsonify({"ok": True, "available": True, "url": OLLAMA_URL, "model": OLLAMA_MODEL})
    except Exception as e:
        return jsonify({"ok": True, "available": False, "error": str(e)})


_vosk_models={}
def get_vosk_model(lang):
    if lang in _vosk_models: return _vosk_models[lang]
    try:
        from vosk import Model, SetLogLevel; SetLogLevel(-1)
        paths = {
            "ru": os.getenv("VOSK_RU_MODEL_PATH", "ml_models/vosk-ru"),
            "kk": os.getenv("VOSK_KZ_MODEL_PATH", "ml_models/vosk-kk"),
            "en": os.getenv("VOSK_EN_MODEL_PATH", "ml_models/vosk-en"),
            "de": os.getenv("VOSK_DE_MODEL_PATH", "ml_models/vosk-de"),
        }
        path = paths.get(lang)
        if not path or not os.path.isdir(path):
            log.warning(f"Vosk model '{lang}' not found at '{path}'")
            return None
        log.info(f"Loading Vosk model '{lang}' from '{path}'...")
        _vosk_models[lang] = Model(path)
        log.info(f"Vosk model '{lang}' loaded OK")
        return _vosk_models[lang]
    except Exception as e:
        log.warning(f"Vosk model '{lang}' failed to load: {e}")
        return None


# ════════════════════════════════════════════════════════
#  WHISPER STT (OpenAI) — точность ~95%, выше чем Vosk
#  Установка: pip install openai-whisper
#  Работает ОФЛАЙН. Понимает казахский, русский, акценты, шум.
# ════════════════════════════════════════════════════════
_whisper_model = None
_whisper_checked = False

def get_whisper():
    global _whisper_model, _whisper_checked
    if _whisper_checked:
        return _whisper_model
    _whisper_checked = True
    try:
        import whisper
        size = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium
        log.info(f"Loading Whisper '{size}'...")
        _whisper_model = whisper.load_model(size)
        log.info(f"✅ Whisper '{size}' loaded")
    except Exception as e:
        log.warning(f"Whisper не установлен ({e}) — pip install openai-whisper")
        _whisper_model = None
    return _whisper_model


def _transcribe_whisper(raw_audio: bytes, lang: str) -> dict:
    model = get_whisper()
    if model is None:
        return None
    try:
        import tempfile, os as _os
        # Whisper нужен файл
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(raw_audio)
            tmp_path = f.name
        whisper_lang = {"ru":"ru","kk":"kk","en":"en","de":"de"}.get(lang)
        result = model.transcribe(tmp_path, language=whisper_lang, fp16=False)
        _os.unlink(tmp_path)
        text = (result.get("text") or "").strip()
        return {"ok": True, "text": text, "lang": lang, "engine": "whisper"}
    except Exception as e:
        log.warning(f"Whisper transcribe error: {e}")
        return None


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    lang = request.values.get("lang") or (request.get_json() or {}).get("lang", "ru")

    # Получаем аудио
    raw = None
    if "file" in request.files:
        raw = request.files["file"].read()
    else:
        data = request.get_json() or {}
        b64 = data.get("audio_b64", "")
        if b64:
            if "," in b64: b64 = b64.split(",", 1)[1]
            raw = base64.b64decode(b64)
    if not raw:
        return jsonify({"ok": False, "error": "no audio"}), 400

    # ── 1. Whisper (PRIMARY — лучшая точность) ──
    if os.getenv("USE_WHISPER", "1") == "1":
        w = _transcribe_whisper(raw, lang)
        if w and w.get("text"):
            return jsonify(w)

    # ── 2. Vosk (FALLBACK — офлайн) ──
    model = get_vosk_model(lang)
    if model is not None:
        try:
            from vosk import KaldiRecognizer
            vraw = raw[44:] if raw[:4] == b"RIFF" else raw
            rec = KaldiRecognizer(model, 16000)
            rec.SetWords(True)
            rec.AcceptWaveform(vraw)
            result = json.loads(rec.FinalResult())
            text = result.get("text", "").strip()
            text = normalize_kaz(text) if lang == "kk" else text
            return jsonify({"ok": True, "text": text, "lang": lang, "engine": "vosk"})
        except Exception as e:
            log.warning(f"Vosk error: {e}")

    # ── 3. Web Speech API (браузер) ──
    return jsonify({"ok": False, "use_webspeech": True,
                    "error": "Whisper & Vosk unavailable — use Web Speech API"}), 200


@app.route("/api/stt/status", methods=["GET"])
def stt_status():
    """Статус всех STT движков."""
    whisper_ok = get_whisper() is not None
    vosk_paths = {
        "ru": os.getenv("VOSK_RU_MODEL_PATH", "ml_models/vosk-ru"),
        "kk": os.getenv("VOSK_KZ_MODEL_PATH", "ml_models/vosk-kk"),
        "en": os.getenv("VOSK_EN_MODEL_PATH", "ml_models/vosk-en"),
        "de": os.getenv("VOSK_DE_MODEL_PATH", "ml_models/vosk-de"),
    }
    vosk_status = {l: os.path.isdir(p) for l, p in vosk_paths.items()}
    return jsonify({
        "ok": True,
        "whisper": whisper_ok,
        "vosk": vosk_status,
        "primary": "whisper" if whisper_ok else ("vosk" if any(vosk_status.values()) else "webspeech")
    })

@app.route("/api/vosk/status", methods=["GET"])
def vosk_status():
    """Проверяет какие Vosk модели установлены"""
    langs = ["ru", "kk", "en", "de"]
    paths = {
        "ru": os.getenv("VOSK_RU_MODEL_PATH", "ml_models/vosk-ru"),
        "kk": os.getenv("VOSK_KZ_MODEL_PATH", "ml_models/vosk-kk"),
        "en": os.getenv("VOSK_EN_MODEL_PATH", "ml_models/vosk-en"),
        "de": os.getenv("VOSK_DE_MODEL_PATH", "ml_models/vosk-de"),
    }
    status = {}
    for lang in langs:
        path = paths.get(lang, "")
        status[lang] = {
            "available": os.path.isdir(path),
            "path": path,
            "loaded": lang in _vosk_models,
        }
    return jsonify({"ok": True, "status": status})


TTS_VOICES={
    "kk": "kk-KZ-AigulNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "en": "en-US-AriaNeural",
    "de": "de-DE-KatjaNeural",      # немецкий
    "fr": "fr-FR-DeniseNeural",     # французский
    "tr": "tr-TR-EmelNeural",       # турецкий
    "es": "es-ES-ElviraNeural",     # испанский
}
AGENT_VOICES={
  # ── Ари — нежный женский, живой и тёплый ──
  "ari":  {
    "ru": ("ru-RU-SvetlanaNeural",  "+10%", "+8Hz"),
    "kk": ("kk-KZ-AigulNeural",    "+10%", "+8Hz"),
    "en": ("en-US-AriaNeural",      "+10%", "+8Hz"),
    "de": ("de-DE-KatjaNeural",     "+10%", "+8Hz"),
  },
  # ── Бибо — роботизированный, быстрый, высокий ──
  "bibo": {
    "ru": ("ru-RU-DmitryNeural",    "+30%", "+20Hz"),
    "kk": ("kk-KZ-DauletNeural",   "+30%", "+20Hz"),
    "en": ("en-US-GuyNeural",       "+30%", "+20Hz"),
    "de": ("de-DE-ConradNeural",    "+30%", "+20Hz"),
  },
  # ── Аппа — очень мягкий, тихий, медленный ──
  "appa": {
    "ru": ("ru-RU-DariyaNeural",    "-20%", "-10Hz"),
    "kk": ("kk-KZ-AigulNeural",    "-20%", "-10Hz"),
    "en": ("en-US-JennyNeural",     "-20%", "-10Hz"),
    "de": ("de-DE-KatjaNeural",     "-20%", "-10Hz"),
  },
  # ── Макс — уверенный мужской, командный ──
  "max":  {
    "ru": ("ru-RU-DmitryNeural",    "+12%", "+0Hz"),
    "kk": ("kk-KZ-DauletNeural",   "+12%", "+0Hz"),
    "en": ("en-US-GuyNeural",       "+12%", "+0Hz"),
    "de": ("de-DE-ConradNeural",    "+12%", "+0Hz"),
  },
  # ── Драко — глубокий, мрачный, очень медленный ──
  "drako": {
    "ru": ("ru-RU-DmitryNeural",    "-30%", "-20Hz"),
    "kk": ("kk-KZ-DauletNeural",   "-30%", "-20Hz"),
    "en": ("en-US-DavisNeural",     "-30%", "-20Hz"),
    "de": ("de-DE-ConradNeural",    "-30%", "-20Hz"),
  },
  # ── Лекс — нейтральный образовательный мужской ──
  "lex":  {
    "ru": ("ru-RU-DmitryNeural",    "+5%",  "+5Hz"),
    "kk": ("kk-KZ-DauletNeural",   "+5%",  "+5Hz"),
    "en": ("en-US-BrandonNeural",   "+5%",  "+5Hz"),
    "de": ("de-DE-ConradNeural",    "+5%",  "+5Hz"),
  },
  # ── Зара — творческий, живой, немного выше ──
  "zara": {
    "ru": ("ru-RU-SvetlanaNeural",  "+15%", "+12Hz"),
    "kk": ("kk-KZ-AigulNeural",    "+15%", "+12Hz"),
    "en": ("en-US-AriaNeural",      "+15%", "+12Hz"),
    "de": ("de-DE-KatjaNeural",     "+15%", "+12Hz"),
  },
  # ── Алтай — спокойный степенный мужской ──
  "altay": {
    "ru": ("ru-RU-DmitryNeural",    "-5%",  "-3Hz"),
    "kk": ("kk-KZ-DauletNeural",   "-5%",  "-3Hz"),
    "en": ("en-US-GuyNeural",       "-5%",  "-3Hz"),
    "de": ("de-DE-ConradNeural",    "-5%",  "-3Hz"),
  },
  # ── Дина — чёткий медицинский женский ──
  "dina": {
    "ru": ("ru-RU-DariyaNeural",    "+0%",  "+2Hz"),
    "kk": ("kk-KZ-AigulNeural",    "+0%",  "+2Hz"),
    "en": ("en-US-JennyNeural",     "+0%",  "+2Hz"),
    "de": ("de-DE-KatjaNeural",     "+0%",  "+2Hz"),
  },
  # ── Тим — быстрый деловой мужской ──
  "tim":  {
    "ru": ("ru-RU-DmitryNeural",    "+18%", "+3Hz"),
    "kk": ("kk-KZ-DauletNeural",   "+18%", "+3Hz"),
    "en": ("en-US-GuyNeural",       "+18%", "+3Hz"),
    "de": ("de-DE-ConradNeural",    "+18%", "+3Hz"),
  },
  # ── Нура — молодой тёплый женский, подростковый ──
  "nura": {
    "ru": ("ru-RU-SvetlanaNeural",  "+8%",  "+15Hz"),
    "kk": ("kk-KZ-AigulNeural",    "+8%",  "+15Hz"),
    "en": ("en-US-AriaNeural",      "+8%",  "+15Hz"),
    "de": ("de-DE-KatjaNeural",     "+8%",  "+15Hz"),
  },
  # ── Код — технический нейтральный мужской ──
  "kod":  {
    "ru": ("ru-RU-DmitryNeural",    "+8%",  "+5Hz"),
    "kk": ("kk-KZ-DauletNeural",   "+8%",  "+5Hz"),
    "en": ("en-US-BrandonNeural",   "+8%",  "+5Hz"),
    "de": ("de-DE-ConradNeural",    "+8%",  "+5Hz"),
  },
  # ── Лу (запасной) ──
  "lou":  {
    "ru": ("ru-RU-SvetlanaNeural",  "+15%", "+20Hz"),
    "kk": ("kk-KZ-AigulNeural",    "+15%", "+20Hz"),
    "en": ("en-US-AriaNeural",      "+15%", "+20Hz"),
    "de": ("de-DE-KatjaNeural",     "+15%", "+20Hz"),
  },
}
CUSTOM_VOICES={"warm":{"ru":("ru-RU-DariyaNeural","+5%","+5Hz"),"kk":("kk-KZ-AigulNeural","+5%","+5Hz")},
"deep":{"ru":("ru-RU-DmitryNeural","-15%","-8Hz"),"kk":("kk-KZ-DauletNeural","-15%","-8Hz")},
"calm":{"ru":("ru-RU-SvetlanaNeural","-10%","-3Hz"),"kk":("kk-KZ-AigulNeural","-10%","-3Hz")},
"bright":{"ru":("ru-RU-SvetlanaNeural","+20%","+12Hz"),"kk":("kk-KZ-AigulNeural","+20%","+12Hz")},
"neutral":{"ru":("ru-RU-SvetlanaNeural","+0%","+0Hz"),"kk":("kk-KZ-AigulNeural","+0%","+0Hz")}}

@app.route("/api/tts", methods=["POST"])
def tts():
    try:
        import edge_tts
    except ImportError:
        return jsonify({"ok": False, "use_browser_tts": True,
                        "error": "edge-tts not installed"}), 200
    import re
    data=request.get_json() or {}; text=(data.get("text") or "").strip()
    if not text: return jsonify({"ok":False}),400
    lang=data.get("lang","ru"); ag=data.get("agent",""); cv=data.get("custom_voice","neutral")
    voice=TTS_VOICES.get(lang,TTS_VOICES["ru"]); rate="+0%"; pitch="+0Hz"
    if ag and ag in AGENT_VOICES and lang in AGENT_VOICES[ag]: voice,rate,pitch=AGENT_VOICES[ag][lang]
    elif cv in CUSTOM_VOICES and lang in CUSTOM_VOICES[cv]: voice,rate,pitch=CUSTOM_VOICES[cv][lang]
    speak_text=re.sub(r"\*[^*]+\*","",text).strip() or text
    async def _gen():
        buf=io.BytesIO(); comm=edge_tts.Communicate(text=speak_text,voice=voice,rate=rate,pitch=pitch)
        async for c in comm.stream():
            if c["type"]=="audio": buf.write(c["data"])
        return buf.getvalue()
    try:
        loop=asyncio.new_event_loop()
        try: mp3=loop.run_until_complete(_gen())
        finally: loop.close()
        return send_file(io.BytesIO(mp3),mimetype="audio/mpeg",download_name="tts.mp3")
    except Exception as e:
        log.exception("TTS error: %s",e); return jsonify({"ok":False,"error":str(e)}),500

SEED_USERS=[{"name":"Алия","email":"alice@vivlos.kz","password":"alice123","age_group":"adult"},
{"name":"Бауыржан","email":"bob@vivlos.kz","password":"bob12345","age_group":"adult"},
{"name":"Ару","email":"aru@vivlos.kz","password":"aru12345","age_group":"kid"}]

SEED_NOTIFS=[
{"icon":"ri-sparkling-2-line","title":"Добро пожаловать в Vivlos!","title_kk":"Vivlos-қа қош келдіңіз!","body":"Выбери AI-компаньона и начни первый звонок.","body_kk":"AI-компанионды таңдап, алғашқы қоңырауды бастаңыз.","kind":"info"},
{"icon":"ri-fire-fill","title":"Не теряй серию!","title_kk":"Сериянды жоғалтпа!","body":"Позвони сегодня!","body_kk":"Бүгін қоңырау шал!","kind":"streak"},
{"icon":"ri-trophy-line","title":"Первый шаг — жди достижения!","title_kk":"Алғашқы қадам — жетістікті күт!","body":"Сделай первый звонок и получи значок 🌱","body_kk":"Алғашқы қоңырауды жасап 🌱 ал.","kind":"achievement"},
{"icon":"ri-translate-2","title":"Поддержка казахского языка","title_kk":"Қазақ тіліне қолдау","body":"Переключи язык кнопкой RU/KK!","body_kk":"RU/KK батырмасымен тілді ауыстыр!","kind":"info"},
]

def seed_database():
    for u in SEED_USERS:
        ex=User.query.filter_by(email=u["email"]).first()
        if ex:
            if not ex.password_hash: ex.set_password(u["password"])
            if not UserXP.query.filter_by(user_id=ex.id).first(): db.session.add(UserXP(user_id=ex.id))
        else:
            user=User(name=u["name"],email=u["email"],age_group=u["age_group"]); user.set_password(u["password"])
            db.session.add(user); db.session.flush(); db.session.add(UserXP(user_id=user.id))
    if Notification.query.count()==0:
        now=datetime.utcnow()
        for i,n in enumerate(SEED_NOTIFS):
            db.session.add(Notification(user_id=None,icon=n["icon"],title=n["title"],title_kk=n["title_kk"],body=n["body"],body_kk=n["body_kk"],kind=n["kind"],created_at=now-timedelta(hours=i*6)))
    if ChatThread.query.count()==0:
        tds=[{"title":"Команда Vivlos","title_kk":"Vivlos командасы","icon":"ri-sparkling-2-fill","bg":"#7c3aed","msgs":[{"t":"Привет! Это команда Vivlos 💜","tk":"Сәлем! Бұл Vivlos командасы 💜"},{"t":"Добавили создание персонажей и XP-систему!","tk":"Кейіпкерлер жасау мен XP-жүйесі қосылды!"}]},{"title":"Новости","title_kk":"Жаңалықтар","icon":"ri-news-line","bg":"#10b981","msgs":[{"t":"🎉 Vivlos v3 вышел!","tk":"🎉 Vivlos v3 шықты!"}]}]
        base=datetime.utcnow()
        for i,td in enumerate(tds):
            th=ChatThread(title=td["title"],title_kk=td["title_kk"],avatar_icon=td["icon"],avatar_bg=td["bg"]); db.session.add(th); db.session.flush()
            for j,m in enumerate(td["msgs"]): db.session.add(ChatMessage(thread_id=th.id,sender="admin",text=m["t"],text_kk=m["tk"],created_at=base-timedelta(hours=i*12+(len(td["msgs"])-j))))
    db.session.commit()

# ════════════════════════════════════════════════════════
#  STREAMING endpoint (token by token like ChatGPT)
#  Фронт подключается через EventSource или fetch(stream)
# ════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
#  ПАМЯТЬ — API для доступа к истории разговоров
# ════════════════════════════════════════════════════════

@app.route("/api/memory/history", methods=["GET"])
def memory_history():
    """История разговоров пользователя с конкретным AI."""
    uid = request.args.get("user_id") or session.get("user_id", 1)
    agent_id = request.args.get("agent_id", "")
    limit = int(request.args.get("limit", 50))
    page = int(request.args.get("page", 1))

    q = AIConversation.query.filter_by(user_id=uid)
    if agent_id:
        q = q.filter_by(agent_id=agent_id)
    total = q.count()
    msgs = q.order_by(AIConversation.created_at.desc())            .offset((page-1)*limit).limit(limit).all()

    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_id": m.agent_id,
            "emotion": m.emotion,
            "engine": m.engine,
            "lang": m.lang,
            "time": m.created_at.strftime("%d.%m.%Y %H:%M"),
        } for m in reversed(msgs)]
    })


@app.route("/api/memory/search", methods=["GET"])
def memory_search():
    """Поиск по истории разговоров."""
    uid = request.args.get("user_id") or session.get("user_id", 1)
    query = request.args.get("q", "").strip()
    agent_id = request.args.get("agent_id", "")

    if not query:
        return jsonify({"ok": False, "error": "query required"}), 400

    q = AIConversation.query.filter_by(user_id=uid)        .filter(AIConversation.content.ilike(f"%{query}%"))
    if agent_id:
        q = q.filter_by(agent_id=agent_id)

    results = q.order_by(AIConversation.created_at.desc()).limit(20).all()
    return jsonify({
        "ok": True,
        "query": query,
        "results": [{
            "id": m.id,
            "role": m.role,
            "content": m.content[:200],
            "agent_id": m.agent_id,
            "emotion": m.emotion,
            "time": m.created_at.strftime("%d.%m.%Y %H:%M"),
        } for m in results]
    })


@app.route("/api/memory/inject", methods=["GET"])
def memory_inject():
    """
    Возвращает релевантные воспоминания для текущего разговора.
    Вызывается при старте звонка — AI 'вспоминает' о пользователе.
    """
    uid = request.args.get("user_id") or session.get("user_id", 1)
    agent_id = request.args.get("agent_id", "ari")
    limit = int(request.args.get("limit", 10))

    # Последние сообщения с этим персонажем
    last_msgs = AIConversation.query        .filter_by(user_id=uid, agent_id=agent_id)        .order_by(AIConversation.created_at.desc())        .limit(limit).all()

    # Мысли AI о пользователе
    thoughts = AIThought.query        .filter_by(user_id=uid, agent_id=agent_id)        .order_by(AIThought.created_at.desc())        .limit(5).all()

    # Факты из UserMemory
    facts = UserMemory.query        .filter_by(user_id=uid)        .filter(UserMemory.importance >= 5)        .order_by(UserMemory.importance.desc())        .limit(8).all()

    return jsonify({
        "ok": True,
        "last_messages": [{
            "role": m.role,
            "content": m.content[:150],
            "time": m.created_at.strftime("%d.%m %H:%M"),
            "emotion": m.emotion,
        } for m in reversed(last_msgs)],
        "ai_thoughts": [t.thought for t in thoughts],
        "user_facts": [f.content for f in facts],
    })


@app.route("/api/memory/stats", methods=["GET"])
def memory_stats():
    """Статистика разговоров с AI."""
    uid = request.args.get("user_id") or session.get("user_id", 1)
    total = AIConversation.query.filter_by(user_id=uid).count()
    by_agent = db.session.query(
        AIConversation.agent_id,
        db.func.count(AIConversation.id)
    ).filter_by(user_id=uid).group_by(AIConversation.agent_id).all()
    emotions = db.session.query(
        AIConversation.emotion,
        db.func.count(AIConversation.id)
    ).filter_by(user_id=uid).group_by(AIConversation.emotion).all()
    return jsonify({
        "ok": True,
        "total_messages": total,
        "by_agent": {a: c for a, c in by_agent},
        "emotion_distribution": {e: c for e, c in emotions if e},
    })


# ════════════════════════════════════════════════════════
#  VISION API — AI смотрит на картинку
#  Поддерживается: Gemini Flash + GPT-4o-mini
# ════════════════════════════════════════════════════════
@app.route("/api/chat/vision", methods=["POST"])
def chat_vision():
    data       = request.get_json() or {}
    image_b64  = data.get("image", "")       # base64 data URL
    user_msg   = (data.get("message") or "Что на этом фото?").strip()
    agent_id   = data.get("agent", "ari")
    lang       = data.get("lang", "ru")
    user_name  = data.get("user_name", "")
    messages   = data.get("messages", [])
    emotion    = data.get("emotion", "neutral")

    if not image_b64:
        return jsonify({"ok": False, "error": "no image"}), 400

    # Убираем data URL префикс
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    # Определяем mime type
    raw_data = data.get("image", "")
    if "image/png" in raw_data:
        mime_type = "image/png"
    elif "image/webp" in raw_data:
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    # Базовый промпт персонажа
    persona   = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS["ari"])
    base_sys  = persona["system"]

    lang_rule = {
        "kk": "⚡ ТЕК ҚАЗАҚ ТІЛІНДЕ жауап бер.",
        "en": "⚡ Reply ONLY in English.",
        "de": "⚡ Antworte NUR auf Deutsch.",
    }.get(lang, "⚡ Отвечай ТОЛЬКО на русском.")

    if user_name:
        base_sys += f"\nИмя пользователя: {user_name}."

    system = lang_rule + "\n\n" + base_sys + "\n\nПользователь прислал тебе изображение. Опиши что видишь и отреагируй как живой персонаж — эмоционально, кратко, по своему стилю."

    reply = None

    # ── 1. Gemini Vision (PRIMARY для картинок — бесплатно) ──
    try:
        import google.generativeai as genai
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("No Gemini key")
        if not getattr(get_gemini, '_quota_ok', True):
            raise ValueError("Gemini quota cached")

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=system,
        )
        import base64 as _b64
        img_data = _b64.b64decode(image_b64)

        # Формируем multipart запрос
        import google.generativeai.types as gtypes
        response = model.generate_content([
            {"mime_type": mime_type, "data": img_data},
            user_msg,
        ], generation_config=genai.types.GenerationConfig(
            temperature=0.95, max_output_tokens=250,
        ))
        reply = (response.text or "").strip()
        log.info("Vision: Gemini answered")

    except Exception as e:
        log.warning(f"Gemini vision failed: {str(e)[:80]}")

    # ── 2. GPT-4o-mini Vision (FALLBACK) ──
    if not reply and os.getenv("OPENAI_API_KEY") and getattr(_call_openai, '_quota_ok', True):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=1, timeout=20.0)

            msgs = [{"role": "system", "content": system}]
            # Добавляем историю
            for m in messages[-4:]:
                role = "user" if m.get("role") == "user" else "assistant"
                c = (m.get("content") or "").strip()
                if c: msgs.append({"role": role, "content": c})

            # Vision message с картинкой
            msgs.append({"role": "user", "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}",
                    "detail": "low",   # экономим токены
                }},
                {"type": "text", "text": user_msg},
            ]})

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=msgs,
                max_tokens=250,
                temperature=0.95,
            )
            reply = (resp.choices[0].message.content or "").strip()
            log.info("Vision: GPT-4o-mini answered")

        except Exception as e:
            err_s = str(e)
            if "quota" in err_s.lower() or "429" in err_s:
                _call_openai._quota_ok = False
            log.warning(f"GPT vision failed: {err_s[:80]}")

    # ── Fallback ──
    if not reply:
        replies = {
            "ru": "Хм, не могу рассмотреть что на фото... Расскажи сам что там?",
            "kk": "Хм, суретті көре алмадым... Өзің айтып берші?",
            "en": "Hmm, can't see the image clearly... Tell me what's there?",
            "de": "Hmm, ich kann das Bild nicht sehen... Erzähl mir davon?",
        }
        reply = replies.get(lang, replies["ru"])

    # Post-process through speech patterns
    if _BRAIN_OK:
        try:
            reply = apply_speech_pattern(reply, agent_id, lang, emotion, 0.0)
        except Exception as _e:
            log.debug(f"Silent error: {_e}")

    return jsonify({"ok": True, "reply": reply, "engine": "vision"})


@app.route("/api/agent/personality", methods=["POST"])
def set_agent_personality():
    """Обновляет черты характера кастомного AI-персонажа."""
    data = request.get_json() or {}
    agent_id = data.get("agent_id")
    uid = session.get("user_id")
    if not uid or not agent_id:
        return jsonify({"ok": False, "error": "agent_id required"}), 400

    ca = db.session.get(CustomAgent, int(agent_id))
    if not ca or ca.user_id != uid:
        return jsonify({"ok": False, "error": "not found"}), 404

    # Update personality traits
    ca.p_kindness  = min(10, max(0, int(data.get("kindness",  ca.p_kindness  or 7))))
    ca.p_humor     = min(10, max(0, int(data.get("humor",     ca.p_humor     or 5))))
    ca.p_energy    = min(10, max(0, int(data.get("energy",    ca.p_energy    or 6))))
    ca.p_empathy   = min(10, max(0, int(data.get("empathy",   ca.p_empathy   or 7))))
    ca.p_serious   = min(10, max(0, int(data.get("serious",   ca.p_serious   or 5))))
    ca.p_curiosity = min(10, max(0, int(data.get("curiosity", ca.p_curiosity or 6))))
    ca.p_patience  = min(10, max(0, int(data.get("patience",  ca.p_patience  or 6))))
    if "topics" in data: ca.p_topics = ",".join(data["topics"][:5])
    if "style"  in data: ca.p_style  = str(data["style"])[:200]
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    Streaming чат — токены приходят в реальном времени.
    Использует весь каскад: OpenAI stream → Groq stream → Gemini word-by-word → fallback.
    """
    data     = request.get_json() or {}
    msg      = (data.get("message") or "").strip()
    messages = data.get("messages", [])
    agent_id = data.get("agent_id") or data.get("agent", "ari")
    lang     = data.get("lang") or session.get(f"conv_lang_{session.get('user_id',0)}", "ru")

    if not msg and messages:
        msg = next((m.get("content","") for m in reversed(messages) if m.get("role")=="user"), "")
    if not msg:
        def _empty():
            yield f"data: {json.dumps({'token': '...'})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(_empty()), mimetype="text/event-stream",
                        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

    persona  = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS["ari"])
    lang_map = {"kk":"ТЕК ҚАЗАҚША жауап бер.","en":"Reply ONLY in English.",
                "de":"Antworte NUR auf Deutsch.","ru":"Отвечай ТОЛЬКО на русском."}
    system   = lang_map.get(lang, lang_map["ru"]) + "\n\n" + persona["system"]

    # Build message list for API
    api_msgs = [{"role":"system","content":system}]
    for m in messages[-8:]:
        r = "user" if m.get("role")=="user" else "assistant"
        c = (m.get("content") or "").strip()
        if c: api_msgs.append({"role":r,"content":c})
    if not api_msgs or api_msgs[-1]["role"] != "user":
        api_msgs.append({"role":"user","content":msg})

    def _generate():
        # ── 1. OpenAI native streaming ──────────────────────
        if os.getenv("OPENAI_API_KEY") and getattr(_call_openai,'_quota_ok',True):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=1, timeout=20.0)
                stream = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
                    messages=api_msgs, temperature=0.95, max_tokens=250, stream=True
                )
                for chunk in stream:
                    token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as e:
                es = str(e)
                if "quota" in es.lower() or "429" in es:
                    _call_openai._quota_ok = False
                log.warning(f"Stream OpenAI: {es[:60]}")

        # ── 2. Groq streaming (ultra-fast) ─────────────────
        if os.getenv("GROQ_API_KEY") and getattr(_call_groq,'_quota_ok',True):
            try:
                from openai import OpenAI
                client = OpenAI(base_url="https://api.groq.com/openai/v1",
                                api_key=os.getenv("GROQ_API_KEY"), max_retries=1, timeout=15.0)
                stream = client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),
                    messages=api_msgs, temperature=0.95, max_tokens=250, stream=True
                )
                for chunk in stream:
                    token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as e:
                es = str(e)
                if "429" in es or "rate" in es.lower():
                    _call_groq._quota_ok = False
                log.warning(f"Stream Groq: {es[:60]}")

        # ── 3. OpenRouter streaming ─────────────────────────
        if os.getenv("OPENROUTER_API_KEY") and getattr(_call_openrouter,'_quota_ok',True):
            try:
                from openai import OpenAI
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    default_headers={"HTTP-Referer":"https://vivlos.app","X-Title":"Vivlos"},
                    max_retries=1, timeout=20.0
                )
                stream = client.chat.completions.create(
                    model=os.getenv("OPENROUTER_MODEL","meta-llama/llama-3.3-70b-instruct:free"),
                    messages=api_msgs, temperature=0.95, max_tokens=250, stream=True
                )
                for chunk in stream:
                    token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as e:
                log.warning(f"Stream OpenRouter: {str(e)[:60]}")

        # ── 4. Gemini word-by-word (no native stream) ──────
        if os.getenv("GEMINI_API_KEY") and getattr(get_gemini,'_quota_ok',True):
            try:
                import google.generativeai as genai
                model_g = get_gemini(sys_inst=system)
                gc = genai.types.GenerationConfig(temperature=0.95, max_output_tokens=250)
                resp = model_g.generate_content(
                    [{"role":"user","parts":[msg]}], generation_config=gc
                )
                text = (resp.text or "").strip()
                import time
                for word in text.split():
                    yield f"data: {json.dumps({'token': word + ' '})}\n\n"
                    time.sleep(0.03)  # simulate typing
                yield "data: [DONE]\n\n"
                return
            except Exception as e:
                log.warning(f"Stream Gemini: {str(e)[:60]}")

        # ── 5. Fallback ─────────────────────────────────────
        fallback_text = _offline_fallback(agent_id, lang)
        for word in fallback_text.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Connection":"keep-alive"}
    )


if __name__=="__main__":
    with app.app_context():
        os.makedirs("instance", exist_ok=True)
        os.makedirs("static/models", exist_ok=True)
        db.create_all()
        seed_database()
        print("✅ DB ready!")
        for u in SEED_USERS:
            print(f"  • {u['email']} / {u['password']}")
        print("✅ Gemini OK" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "⚠ GEMINI_API_KEY не задан")
        print("✅ OpenRouter OK" if os.getenv("OPENROUTER_API_KEY") else "⚠ OPENROUTER_API_KEY не задан → openrouter.ai")
        print("✅ Groq OK" if os.getenv("GROQ_API_KEY") else "⚠ GROQ_API_KEY не задан → console.groq.com")

    # Register socket events once everything is defined
    _register_socket_events()

    port = int(os.getenv("PORT", 5002))
    print(f"🚀 VIVLOS running on http://localhost:{port}")
    print(f"📡 SocketIO: {'enabled' if socketio else 'disabled (pip install flask-socketio eventlet)'}")
    if socketio:
        socketio.run(app, debug=True, port=port, allow_unsafe_werkzeug=True)
    else:
        app.run(debug=True, port=port)
