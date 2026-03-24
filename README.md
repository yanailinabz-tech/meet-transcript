# 🎙️ voice-to-doc — Claude skill для транскрипции

Claude skill для транскрипции аудио и видео записей в текст с автоматическим анализом и сохранением в Google Doc.

## Что умеет

- Транскрибирует аудио и видео файлы (mp4, mp3, m4a, wav) и YouTube/любые видео-ссылки
- Автоматически переключается между облачными сервисами если один недоступен
- Извлекает ключевые поинты и список задач из записи
- Сохраняет результат в чат или создаёт Google Doc в папке "Транскрипты"
- Сообщает о прогрессе и времени ожидания в процессе работы

## Каскад сервисов транскрипции

Скилл пробует сервисы по порядку — если один не работает или исчерпан лимит, автоматически переходит к следующему:

| # | Сервис | Скорость | Бесплатно | Русский |
|---|--------|----------|-----------|---------|
| 1 | **Groq Whisper** | ~10 сек | 2 часа/день | ✅ |
| 2 | **SaluteSpeech** (Сбер) | ~1-2 мин | 240 мин/мес | ✅ |
| 3 | **AssemblyAI** | ~1-2 мин | $50 кредитов | ✅ |
| 4 | **Deepgram** | ~30 сек | $200 кредитов | ✅ |
| 5 | **Локальный Whisper** | 20-40 мин | безлимитно | ✅ |

## Установка

### 1. Установи скилл

Скопируй папку `voice-to-doc` в директорию скиллов Claude:

```bash
git clone https://github.com/yanailinabz-tech/meet-transcript.git
cp -r meet-transcript ~/.claude/skills/voice-to-doc
```

### 2. Получи API ключи (нужен хотя бы один)

**Groq** — рекомендуется, самый быстрый:
- Зарегистрируйся на [console.groq.com](https://console.groq.com)
- API Keys → Create API Key

**SaluteSpeech** (Сбер):
- Зарегистрируйся на [developers.sber.ru](https://developers.sber.ru/portal/products/smartspeech)
- Создай проект → получи Client ID и Secret → закодируй в Base64: `echo -n "id:secret" | base64`

**AssemblyAI**:
- Зарегистрируйся на [assemblyai.com](https://www.assemblyai.com)
- API Key на главной странице после входа

**Deepgram**:
- Зарегистрируйся на [console.deepgram.com](https://console.deepgram.com)
- Create API Key

### 3. Добавь ключи в `~/.env`

```bash
GROQ_API_KEY=твой_ключ
SALUTE_SPEECH_API_KEY=base64_строка
ASSEMBLYAI_API_KEY=твой_ключ
DEEPGRAM_API_KEY=твой_ключ
```

> ⚠️ Файл `~/.env` никогда не попадает в git — он только локально на твоём компе.

### 4. Установи зависимости

```bash
pip3 install groq requests
# Для YouTube ссылок:
pip3 install yt-dlp
# Для локального Whisper (запасной вариант):
pip3 install openai-whisper
```

ffmpeg должен быть установлен:
```bash
brew install ffmpeg
```

## Использование

Просто напиши Claude:

```
сделай транскрипт /путь/к/файлу.mp4
транскрибируй https://youtube.com/watch?v=...
расшифруй аудио из iCloud (VoiceToClonde)
/voice-to-doc
```

Claude спросит куда выдать результат (в чат или Google Doc) и запустит транскрипцию.

## Что выдаёт

**В чат:**
- Таймкоды по ключевым моментам
- Ключевые поинты (5–10 штук)
- Список задач (если упоминались)
- Полный транскрипт

**В Google Doc:**
- Создаёт новый документ в папке "Транскрипты" на Google Drive
- Структурированное оглавление: поинты → задачи → транскрипт
- Ссылка на документ в чат

## Структура репозитория

```
voice-to-doc/
├── SKILL.md          — инструкция для Claude (основной файл скилла)
├── .env.example      — пример файла с ключами
└── .gitignore        — исключает .env из git
```

## Источники аудио

- Локальный файл (mp4, mp3, m4a, wav)
- iCloud папка VoiceToClonde
- YouTube, Vimeo, Telegram, VK, Loom, Zoom, TikTok и 1000+ сайтов через yt-dlp
- Файл, перетащенный прямо в чат Claude

## Лицензия

MIT
