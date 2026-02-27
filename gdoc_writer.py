#!/usr/bin/env python3
"""
Voice to Doc — запись транскрипта, поинтов и задач в Google Document
Использование:
  python3 gdoc_writer.py --doc-id DOC_ID --transcript /tmp/vtd_transcript.txt \
    --keypoints /tmp/vtd_keypoints.txt --tasks /tmp/vtd_tasks.txt --title "КИБ"
"""

import argparse
import os
import sys
from datetime import datetime


def get_creds():
    """Получить Google credentials через OAuth2."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
    except ImportError:
        print("❌ Установите зависимости: pip3 install google-auth google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/documents"]
    token_path = os.path.expanduser("~/.claude/skills/voice-to-doc/token.pickle")
    creds_path = os.path.expanduser("~/.claude/skills/voice-to-doc/google_credentials.json")
    creds = None

    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"❌ Не найден файл {creds_path}")
                print("   Получите его на https://console.cloud.google.com/ → APIs & Services → Credentials")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return creds


def build_requests(title: str, transcript: str, keypoints: list[str], tasks: list[str]) -> list[dict]:
    """Собрать список запросов для Google Docs API (батч-запись)."""
    today = datetime.now().strftime("%d.%m.%Y %H:%M")
    separator = "═" * 50

    # Строим полный текст блока снизу вверх (insertText вставляет в index 1)
    sections = []

    # Полный транскрипт
    sections.append(f"\n\n📝 ПОЛНЫЙ ТРАНСКРИПТ\n{transcript}\n")

    # Задачи
    if tasks:
        task_lines = "\n".join(f"☐ {t}" for t in tasks)
        sections.append(f"\n\n✅ СПИСОК ЗАДАЧ\n{task_lines}\n")

    # Ключевые поинты
    if keypoints:
        kp_lines = "\n".join(f"• {kp}" for kp in keypoints)
        sections.append(f"\n\n🔑 КЛЮЧЕВЫЕ ПОИНТЫ\n{kp_lines}\n")

    # Заголовок блока
    sections.append(f"\n{separator}\n📅 {today} — {title}\n{separator}\n")

    # Google Docs API: insertText всегда добавляем в начало (index 1)
    requests = []
    for section in sections:
        requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": section
            }
        })

    return requests


def write_to_doc(doc_id: str, title: str, transcript: str, keypoints: list[str], tasks: list[str]):
    """Записать всё в Google Doc."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ Установите: pip3 install google-api-python-client")
        sys.exit(1)

    creds = get_creds()
    service = build("docs", "v1", credentials=creds)

    requests = build_requests(title, transcript, keypoints, tasks)

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()

    print(f"✅ Записано в Google Doc: https://docs.google.com/document/d/{doc_id}/edit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-id", required=True, help="ID Google Document")
    parser.add_argument("--title", default="Запись", help="Заголовок блока")
    parser.add_argument("--transcript", required=True, help="Файл с транскриптом")
    parser.add_argument("--keypoints", help="Файл с ключевыми поинтами (по одному на строку)")
    parser.add_argument("--tasks", help="Файл со списком задач (по одному на строку)")
    args = parser.parse_args()

    transcript = open(args.transcript, encoding="utf-8").read().strip()
    keypoints = open(args.keypoints, encoding="utf-8").read().strip().splitlines() if args.keypoints and os.path.exists(args.keypoints) else []
    tasks = open(args.tasks, encoding="utf-8").read().strip().splitlines() if args.tasks and os.path.exists(args.tasks) else []

    write_to_doc(args.doc_id, args.title, transcript, keypoints, tasks)
