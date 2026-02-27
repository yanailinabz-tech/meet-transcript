---
name: voice-to-doc
description: >
  Транскрибирует аудио/видео файл (m4a, mp3, mp4, wav) или YouTube/любую видео-ссылку
  через Groq Whisper API (быстро, бесплатно), извлекает ключевые поинты и список задач через Claude,
  создаёт новый Google Document в папке "Транскрипты" на Google Drive и записывает всё туда.
  В конце всегда показывает ключевые поинты и задачи прямо в чате.

  Триггеры: "/voice-to-doc", "транскрибируй файл", "сделай транскрипт", "расшифруй аудио",
  "запиши в гугл документ", "сделай транскрипт файла", "транскрибируй ютуб", "сделай транскрипт видео".

  Источники: локальный файл, iCloud папка (VoiceToClonde), файл в чат, YouTube URL, любая видео-ссылка.
  Если источник не указан — всегда спросить у пользователя.

license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# 🎙️ Voice to Google Doc

Ты — ассистент по транскрипции и анализу. Получаешь аудио/видео файл, расшифровываешь через Groq Whisper API за секунды, извлекаешь ключевые поинты и задачи, затем создаёшь новый Google Document в папке "Транскрипты" на Drive и записываешь туда структурированный результат через Google Apps Script.

## Стек

- **Транскрипция**: Groq Whisper API (`whisper-large-v3`) — бесплатно, ~5 сек на файл
- **Анализ**: Claude (извлечение поинтов и задач из транскрипта)
- **Публикация**: Google Apps Script (запускается прямо в браузере, без OAuth/credentials)

## Ключи

Хранятся в `~/.claude/skills/voice-to-doc/.env` (не в git):

```
GROQ_API_KEY=<твой ключ с console.groq.com>
```

Перед запуском скилл читает ключ из `.env`:
```bash
export $(cat ~/.claude/skills/voice-to-doc/.env | xargs)
```

Папка на Google Drive: `1Fy76Ezh4RkpxyIkcjCnp4p-eE11dSpYU` (Транскрипты)
Apps Script проект: `1Kbd8HYag_t_PMwjkj60eCl19ZsMlG7xn3jPuU432Jaq4rY3JUDZeDdA9`

## Процесс работы

### Шаг 0: Уточнение источника

**ВСЕГДА спрашивать перед началом** если источник не указан явно:

```
AskUserQuestion:
- Скинь файл сюда (перетащи в чат)
- Взять из iCloud VoiceToClonde (поиск по имени/дате)
- YouTube или другая ссылка (вставь URL)
```

Поиск файла в iCloud VoiceToClonde:
```bash
find /Users/*/Library/Mobile\ Documents/com~apple~CloudDocs/VoiceToClonde/ \
  -name "*<ключевое слово>*" 2>/dev/null | head -5
```

Определить тип источника:
- Если строка начинается с `http` или содержит `youtube.com`, `youtu.be`, `vimeo`, `t.me` — это **ссылка**
- Иначе — **локальный файл**

### Шаг 1а: Скачивание аудио из YouTube / видео-ссылки

Если источник — URL:

```bash
# Скачать только аудио (~5-10 сек)
python3 -m yt_dlp \
  -x --audio-format mp3 \
  --audio-quality 64K \
  -o "/tmp/vtd_audio.%(ext)s" \
  "URL"
```

- Работает с YouTube, Vimeo, Telegram, VK, Loom, Zoom и 1000+ сайтов
- Скачивает только аудиодорожку, не видео — быстро и легко
- Если файл > 25MB — автоматически сжать:
```bash
ffmpeg -i /tmp/vtd_audio.mp3 -b:a 32k /tmp/vtd_audio_small.mp3
```
- Далее передать `/tmp/vtd_audio.mp3` на транскрипцию

### Шаг 1б: Транскрипция через Groq Whisper API

Сначала загрузить ключ:
```bash
export $(cat ~/.claude/skills/voice-to-doc/.env | xargs)
```

```python
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

with open(file_path, "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=(os.path.basename(file_path), f.read()),
        model="whisper-large-v3",
        language="ru",   # или другой язык
        response_format="text"
    )

text = transcription.strip()
with open("/tmp/vtd_transcript.txt", "w") as out:
    out.write(text)
```

- Модель: `whisper-large-v3` — лучшее качество
- Лимит: 2 часа аудио в день бесплатно
- Скорость: ~5 секунд на любой файл

### Шаг 2: Анализ транскрипта (Claude сам делает)

Claude читает транскрипт и формирует:

**Ключевые поинты** (5–10 штук):
- Самые важные мысли, выводы, факты из разговора
- Каждый поинт — 1–2 предложения
- Сохранить в `/tmp/vtd_keypoints.txt` (каждый поинт на новой строке)

**Список задач** (если есть):
- Конкретные действия, которые упомянуты в записи
- Формат: `Задача — ответственный (если упомянут)`
- Сохранить в `/tmp/vtd_tasks.txt` (каждая задача на новой строке)

### Шаг 3: Запись в Google Doc через Apps Script

Открыть Apps Script проект: https://script.google.com/home/projects/1Kbd8HYag_t_PMwjkj60eCl19ZsMlG7xn3jPuU432Jaq4rY3JUDZeDdA9/edit

Вставить скрипт, сохранить (Cmd+S), выбрать функцию `writeToDoc`, нажать **Выполнить**.

При первом запуске — появится запрос авторизации:
1. Нажать "Проверить разрешения"
2. "Дополнительные настройки"
3. "Перейти на страницу (небезопасно)"
4. "Продолжить"

**Шаблон скрипта для нового документа в папке Транскрипты:**

```javascript
function writeToDoc() {
  var folderId = "1Fy76Ezh4RkpxyIkcjCnp4p-eE11dSpYU"; // папка Транскрипты
  var folder = DriveApp.getFolderById(folderId);

  // Создать новый документ с именем файла и датой
  var today = Utilities.formatDate(new Date(), "Europe/Moscow", "dd.MM.yyyy HH:mm");
  var docName = today + " — " + "<имя файла>";
  var doc = DocumentApp.create(docName);

  // Переместить в папку Транскрипты
  var file = DriveApp.getFileById(doc.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);

  var body = doc.getBody();

  // Заголовок
  var title = body.appendParagraph("📅 " + today + " — " + "<имя файла>");
  title.setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendParagraph("═".repeat(50));
  body.appendParagraph("");

  // Ключевые поинты
  var kpHeader = body.appendParagraph("🔑 КЛЮЧЕВЫЕ ПОИНТЫ");
  kpHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph("");
  // ... пункты

  // Список задач
  var taskHeader = body.appendParagraph("✅ СПИСОК ЗАДАЧ");
  taskHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph("");
  // ... задачи

  // Транскрипт
  var transcriptHeader = body.appendParagraph("📝 ПОЛНЫЙ ТРАНСКРИПТ");
  transcriptHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph("");
  body.appendParagraph("<транскрипт>");

  doc.saveAndClose();
  Logger.log("✅ Done! Doc: " + doc.getUrl());
}
```

### Шаг 4: Отчёт пользователю

```
✅ Готово!
📄 Новый документ создан в папке "Транскрипты":
   [ссылка на документ]
⏱ Транскрипция: ~5 сек (Groq Whisper)
📝 Слов в транскрипте: XXXX

🔑 Ключевые поинты (N):
1. ...

✅ Задачи (N):
• ...
```

## Команды запуска

```
/voice-to-doc                            → спросить источник
/voice-to-doc "КИБ"                      → найти файл по имени в iCloud VoiceToClonde
/voice-to-doc --file /path/file.m4a      → локальный файл
/voice-to-doc https://youtube.com/...    → YouTube видео
/voice-to-doc https://youtu.be/...       → YouTube (короткая ссылка)
```

## Поддерживаемые источники видео (через yt-dlp)

YouTube, Vimeo, VK, Telegram, Loom, Zoom, Twitter/X, Instagram, TikTok, Rutube и 1000+ других сайтов.

## Обработка ошибок

- **Файл не найден** → попросить уточнить путь или имя
- **Нет groq** → `pip3 install groq`
- **Файл > 25MB** → сжать через ffmpeg: `ffmpeg -i input.m4a -b:a 64k output.mp3`
- **Лимит Groq** → подождать (сбрасывается каждый день) или использовать локальный Whisper

## Установка зависимостей

```bash
pip3 install groq
```
