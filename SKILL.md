---
name: voice-to-doc
description: >
  Транскрибирует аудио/видео файл (m4a, mp3, mp4, wav) или YouTube/любую видео-ссылку.
  Использует каскад облачных сервисов: Groq → SaluteSpeech → AssemblyAI → Deepgram → локальный Whisper.
  Извлекает ключевые поинты и список задач через Claude.
  Перед началом всегда спрашивает: куда выдать результат — в чат или в Google Doc.
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

- **Транскрипция**: каскад Groq → SaluteSpeech → AssemblyAI → Deepgram → локальный Whisper
- **Анализ**: Claude (извлечение поинтов и задач из транскрипта)
- **Публикация**: Google Apps Script (запускается прямо в браузере, без OAuth/credentials)

## Ключи

Хранятся в `~/.env` (глобальный файл, не в git):

```
GROQ_API_KEY=
SALUTE_SPEECH_API_KEY=
ASSEMBLYAI_API_KEY=
DEEPGRAM_API_KEY=
```

Перед запуском загрузить все ключи:
```bash
export $(grep -v '^#' ~/.env | xargs) 2>/dev/null
```

### Если у пользователя нет ключей

Проверить наличие каждого ключа и для отсутствующих — вывести инструкцию:

```
Для работы скилла нужен хотя бы один API ключ для транскрипции.

🟢 Groq (рекомендую — быстрый и бесплатный):
   → Зарегистрируйся на https://console.groq.com
   → После входа: API Keys → Create API Key
   → Добавь в ~/.env: GROQ_API_KEY=твой_ключ

🔵 SaluteSpeech (Сбер, 240 мин/мес бесплатно):
   → https://developers.sber.ru/portal/products/smartspeech
   → Создай проект → получи Client ID и Secret → закодируй в Base64
   → Добавь в ~/.env: SALUTE_SPEECH_API_KEY=base64_строка

🟡 AssemblyAI (бесплатный старт):
   → https://www.assemblyai.com
   → Sign Up → скопируй API Key с главной страницы
   → Добавь в ~/.env: ASSEMBLYAI_API_KEY=твой_ключ

🟠 Deepgram ($200 бесплатных кредитов):
   → https://console.deepgram.com
   → Sign Up → Create API Key
   → Добавь в ~/.env: DEEPGRAM_API_KEY=твой_ключ

Когда добавишь хотя бы один — напиши мне, запущу транскрипцию!
```

Папка на Google Drive: `1Fy76Ezh4RkpxyIkcjCnp4p-eE11dSpYU` (Транскрипты)
Apps Script проект: `1Kbd8HYag_t_PMwjkj60eCl19ZsMlG7xn3jPuU432Jaq4rY3JUDZeDdA9`

## Процесс работы

### Шаг 0: Уточнение источника и формата вывода

**ВСЕГДА спрашивать перед началом** два вопроса (можно одним сообщением):

**Вопрос 1 — источник** (если не указан явно):
```
AskUserQuestion:
- Скинь файл сюда (перетащи в чат)
- Взять из iCloud VoiceToClonde (поиск по имени/дате)
- YouTube или другая ссылка (вставь URL)
```

**Вопрос 2 — куда выдать результат** (спрашивать ВСЕГДА, даже если источник указан):
```
AskUserQuestion:
Куда выдать результат?
1. 💬 В чат — таймкоды, ключевые поинты и транскрипт прямо здесь
2. 📄 Google Doc — создать документ в папке "Транскрипты" на Drive
```

В зависимости от ответа:
- **В чат**: выдать таймкоды, ключевые поинты и полный транскрипт блоками прямо в сообщении. Google Doc не создавать.
- **Google Doc**: создать документ через Apps Script, в чат вывести только ключевые поинты + ссылку на документ.
- **Оба**: и в чат, и в Google Doc.

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

### Шаг 1б: Транскрипция — каскад облачных сервисов

Ключи берутся из `~/.env` (глобальный файл). Сначала загрузить все доступные ключи:
```bash
export $(grep -v '^#' ~/.env | xargs) 2>/dev/null
```

**Порядок попыток: Groq → SaluteSpeech → AssemblyAI → Deepgram → локальный Whisper**

После определения длины файла — сообщить пользователю:
```
⏳ Начинаю транскрипцию...
   Файл: [имя файла], [длительность]
   Сервис: Groq Whisper — ожидаемое время: ~10 сек
```

При переключении на следующий сервис — сообщить:
```
⚠️ Groq недоступен (лимит). Переключаюсь на SaluteSpeech — ожидаемое время: ~1-2 мин
```

Когда готово:
```
✅ Транскрипция готова за X сек через [сервис]. Анализирую...
```

Перед запуском извлечь аудио из видео (если нужно) и сжать до mp3 64k чтобы файл был легче:
```bash
ffmpeg -i input.mp4 -vn -ar 16000 -ac 1 -b:a 64k /tmp/vtd_audio.mp3 -y
```

---

#### Попытка 1: Groq Whisper API (быстро, ~5 сек)

```python
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
with open(file_path, "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=(os.path.basename(file_path), f.read()),
        model="whisper-large-v3",
        language="ru",
        response_format="text"
    )
text = transcription.strip()
```

Если Groq вернул ошибку лимита (rate limit / quota) → переходить к Попытке 2.

---

#### Попытка 2: SaluteSpeech (Сбер) — если есть SALUTE_SPEECH_API_KEY

```python
import requests, uuid, json, time
requests.packages.urllib3.disable_warnings()

auth_key = os.getenv("SALUTE_SPEECH_API_KEY")

def get_salute_token():
    resp = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={"Authorization": f"Basic {auth_key}", "RqUID": str(uuid.uuid4()),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"scope": "SALUTE_SPEECH_PERS"}, verify=False
    )
    return resp.json()["access_token"]

token = get_salute_token()

# Загрузить файл
with open(file_path, "rb") as f:
    resp = requests.post("https://smartspeech.sber.ru/rest/v1/data:upload",
        headers={"Authorization": f"Bearer {token}"}, data=f, verify=False)
audio_id = resp.json()["result"]["request_file_id"]

# Запустить распознавание
resp = requests.post("https://smartspeech.sber.ru/rest/v1/speech:async_recognize",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"options": {"language": "ru-RU", "audio_encoding": "MP3", "hypotheses_count": 1},
          "request_file_id": audio_id}, verify=False)
task_id = resp.json()["result"]["id"]

# Ждать результат (обычно 30-60 сек)
for i in range(60):
    time.sleep(10)
    if i % 6 == 0:
        token = get_salute_token()  # токен живёт 30 мин
    resp = requests.get(f"https://smartspeech.sber.ru/rest/v1/task:get?id={task_id}",
        headers={"Authorization": f"Bearer {token}"}, verify=False)
    status = resp.json().get("result", {}).get("status")
    if status == "DONE":
        file_id = resp.json()["result"]["response_file_id"]
        resp2 = requests.get(f"https://smartspeech.sber.ru/rest/v1/data:download?response_file_id={file_id}",
            headers={"Authorization": f"Bearer {token}"}, verify=False)
        chunks = resp2.json()
        text = " ".join(r.get("normalized_text", r.get("text",""))
                        for chunk in chunks for r in chunk.get("results", []))
        break
    elif status == "ERROR":
        raise Exception("SaluteSpeech error")
```

Если SaluteSpeech недоступен или вернул ошибку → переходить к Попытке 3.

---

#### Попытка 3: AssemblyAI — если есть ASSEMBLYAI_API_KEY

```python
import requests, time

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
headers = {"Authorization": API_KEY, "Content-Type": "application/json"}

# Загрузить файл
with open(file_path, "rb") as f:
    r = requests.post("https://api.assemblyai.com/v2/upload",
        headers={"Authorization": API_KEY}, data=f)
audio_url = r.json()["upload_url"]

# Запустить транскрипцию
r = requests.post("https://api.assemblyai.com/v2/transcript", headers=headers,
    json={"audio_url": audio_url, "language_code": "ru", "speech_models": ["universal-2"]})
tid = r.json()["id"]

# Ждать результат
for _ in range(60):
    time.sleep(10)
    r = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}", headers=headers)
    if r.json()["status"] == "completed":
        text = r.json()["text"]
        break
    elif r.json()["status"] == "error":
        raise Exception("AssemblyAI error")
```

---

#### Попытка 4: Deepgram — если есть DEEPGRAM_API_KEY

```python
import requests

API_KEY = os.getenv("DEEPGRAM_API_KEY")
with open(file_path, "rb") as f:
    resp = requests.post(
        "https://api.deepgram.com/v1/listen?model=nova-2&language=ru&punctuate=true",
        headers={"Authorization": f"Token {API_KEY}", "Content-Type": "audio/mp3"},
        data=f
    )
text = resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
```

- $200 бесплатных кредитов при регистрации (~2000 часов)
- Скорость: ~10-30 сек на файл
- Русский: поддерживается через модель `nova-2`

---

#### Попытка 5: Локальный Whisper — только если все облака недоступны

Предупредить пользователя: «Облачные сервисы недоступны. Запускаю локальный Whisper — это займёт 20-40 минут для длинных записей.»

```bash
python3 -m whisper "input.mp3" --language Russian --model small \
  --output_format txt --output_dir /tmp/vtd_whisper_out
```

Если через 10 минут файл результата ещё не появился — напомнить пользователю что процесс идёт и предложить подождать или прервать.

---

После успешной транскрипции любым методом — сохранить в `/tmp/vtd_transcript.txt`.

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

**Режим "в чат":**
Выдать в сообщении:
- Таймкоды (если запрашивались)
- Ключевые поинты
- Список задач (если есть)
- Полный транскрипт блоками с таймкодами

Google Doc не создавать.

**Режим "Google Doc":**
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

**Режим "оба":** сначала Google Doc, затем выдать всё в чат.

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
