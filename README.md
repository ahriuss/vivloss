# Vivlos — AI Video Call Companions

AI-компаньоны с видеозвонками, эмоциями, памятью и стримингом ответов.  
Поддержка **RU / KK / EN / DE**.

## Возможности

- 12 персонажей со своим стилем речи (Ари, Бибо, Аппа, Макс, Драко, Лекс и др.)
- Видеозвонок + распознавание эмоций (face-api.js / DeepFace)
- Голосовой ввод (Web Speech / Whisper / Vosk)
- TTS ответов
- Память о пользователе, уровни отношений, XP
- Streaming ответов (OpenAI / Groq / Gemini / OpenRouter)
- Создание своих ботов

## Структура

```
vivlos/
├── app.py                 # Flask backend
├── ai/                    # Brain, personality, emotions, memory
├── database/              # SQLAlchemy models + repos
├── emotions/              # Emotion behavior rules
├── websocket/             # SocketIO chat + realtime audio
├── static/
│   ├── di.css / di.js / i18n.js
│   ├── face-api.min.js
│   ├── vad-processor.js
│   └── models/            # face-api weights
├── templates/index.html
├── instance/              # SQLite DB
├── requirements.txt
├── .env.example
└── README.md
```

## Быстрый старт

### 1. Python 3.10+

```bash
cd vivlos
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. API-ключи

Скопируй `.env.example` → `.env` и заполни **хотя бы один** ключ:

| Сервис     | Где взять                         | Бесплатно? |
|------------|-----------------------------------|------------|
| Gemini     | https://aistudio.google.com/apikey | да        |
| Groq       | https://console.groq.com          | да        |
| OpenRouter | https://openrouter.ai             | да (free models) |
| OpenAI     | https://platform.openai.com       | платно    |

Пример `.env`:

```env
GEMINI_API_KEY=AIza...
FLASK_SECRET=любая-случайная-строка
PORT=5002
```

### 3. Запуск

```bash
python app.py
```

Открой: **http://localhost:5002**

Тестовые аккаунты (создаются при первом запуске):

| Email            | Пароль    |
|------------------|-----------|
| alice@vivlos.kz  | alice123  |

### 4. Голосовые модели (у тебя уже скачаны)

Положи модели Vosk в папку `ml_models/` (или укажи пути в `.env`):

```
ml_models/
  vosk-ru/
  vosk-kk/
  vosk-en/
```

Whisper подтянется сам при первом использовании (`pip install openai-whisper` опционально).

Face-api модели уже лежат в `static/models/`.

## Загрузка на GitHub

```bash
# 1. Создай репозиторий на github.com (New repository)

# 2. В папке проекта:
git init
git add .
git commit -m "Initial commit: Vivlos AI video companions"

# 3. Привяжи remote (подставь свой URL):
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vivlos.git
git push -u origin main
```

**Важно:** `.env` и API-ключи **не** коммить — они в `.gitignore`.  
Крупные Vosk/Whisper модели тоже не заливай в git (папка `ml_models/` игнорируется).

## Опциональные зависимости

```bash
# Эмоции на сервере (DeepFace)
pip install deepface tf-keras opencv-python-headless

# Offline STT
pip install openai-whisper
# + модели Vosk с https://alphacephei.com/vosk/models
```

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: ai` | Запускай из корня: `python app.py` |
| Нет ответов AI | Проверь `.env` и ключи; в консоли будут ⚠ |
| Камера / микрофон | Только HTTPS или localhost; разреши доступ в браузере |
| SocketIO не работает | `pip install flask-socketio eventlet` |
| CSS / JS 404 | Файлы должны быть в `static/` |

## Лицензия

Для личного / учебного использования. Персонажи и UI — часть проекта Vivlos.
