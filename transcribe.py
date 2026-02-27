#!/usr/bin/env python3
"""
Voice to Doc — Whisper транскрипция
Использование: python3 transcribe.py --file audio.m4a --language ru --output /tmp/transcript.txt
"""

import argparse
import sys
import os

def transcribe(file_path: str, language: str = "ru", output: str = "/tmp/vtd_transcript.txt") -> str:
    try:
        import whisper
    except ImportError:
        print("❌ Whisper не установлен. Запустите: pip3 install openai-whisper")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        sys.exit(1)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"📁 Файл: {os.path.basename(file_path)} ({file_size_mb:.1f} MB)")
    print(f"🔄 Загружаю модель Whisper (medium)...")

    model = whisper.load_model("medium")
    print(f"🎙️ Транскрибирую... (язык: {language})")
    print("   Это может занять несколько минут на CPU...\n")

    result = model.transcribe(file_path, language=language, verbose=False)
    text = result["text"].strip()

    with open(output, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    print(f"\n✅ Транскрипция завершена!")
    print(f"   Слов: {word_count}")
    print(f"   Сохранено в: {output}")

    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper транскрипция аудио")
    parser.add_argument("--file", required=True, help="Путь к аудио/видео файлу")
    parser.add_argument("--language", default="ru", help="Язык (ru, en, ...)")
    parser.add_argument("--output", default="/tmp/vtd_transcript.txt", help="Путь для сохранения текста")
    args = parser.parse_args()

    transcribe(args.file, args.language, args.output)
