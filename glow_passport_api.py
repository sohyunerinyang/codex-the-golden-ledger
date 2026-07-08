from __future__ import annotations

import json
import os
import sqlite3
import smtplib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DB_PATH = Path(__file__).with_name("glow_passport_leads.sqlite3")
HOST = "127.0.0.1"
PORT = int(os.getenv("GLOW_PASSPORT_API_PORT", "8001"))
NOTIFY_EMAIL = os.getenv("GLOW_PASSPORT_NOTIFY_EMAIL", "sohyunerinyang@gmail.com")
SMTP_HOST = os.getenv("GLOW_PASSPORT_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("GLOW_PASSPORT_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("GLOW_PASSPORT_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("GLOW_PASSPORT_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("GLOW_PASSPORT_SMTP_FROM", SMTP_USERNAME or NOTIFY_EMAIL)
SMTP_USE_TLS = os.getenv("GLOW_PASSPORT_SMTP_TLS", "1") != "0"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                consent INTEGER NOT NULL,
                result TEXT NOT NULL,
                message TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                source TEXT NOT NULL,
                notify_to TEXT NOT NULL,
                notification_status TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_lead(payload: dict[str, Any]) -> int:
    init_db()
    created_at = datetime.now(timezone.utc).isoformat()
    answers = payload.get("answers") if isinstance(payload.get("answers"), dict) else {}
    notification_status = "stored_for_email_followup"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO leads (
                created_at, name, email, consent, result, message,
                answers_json, source, notify_to, notification_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                str(payload.get("name", ""))[:120].strip(),
                str(payload.get("email", ""))[:254].strip(),
                int(bool(payload.get("consent", False))),
                str(payload.get("result", ""))[:60].strip(),
                str(payload.get("message", ""))[:1000].strip(),
                json.dumps(answers, ensure_ascii=False, sort_keys=True),
                str(payload.get("source", "glow-passport"))[:80].strip(),
                NOTIFY_EMAIL,
                notification_status,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_notification_status(lead_id: int, status: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE leads SET notification_status = ? WHERE id = ?",
            (status[:120], int(lead_id)),
        )
        conn.commit()


def send_notification_email(lead_id: int, payload: dict[str, Any]) -> str:
    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM and NOTIFY_EMAIL):
        return "email_not_configured"

    try:
        message = EmailMessage()
        message["Subject"] = f"[Glow Passport] New waitlist lead #{lead_id}"
        message["From"] = SMTP_FROM
        message["To"] = NOTIFY_EMAIL

        body = {
            "id": lead_id,
            "name": str(payload.get("name", "")).strip(),
            "email": str(payload.get("email", "")).strip(),
            "consent": bool(payload.get("consent", False)),
            "result": str(payload.get("result", "")).strip(),
            "message": str(payload.get("message", "")).strip(),
            "answers": payload.get("answers", {}),
            "source": str(payload.get("source", "glow-passport")).strip(),
            "submittedAtUTC": datetime.now(timezone.utc).isoformat(),
        }
        message.set_content(json.dumps(body, ensure_ascii=False, indent=2))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.ehlo()
            if SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
        return "email_sent"
    except Exception:
        return "email_failed"


class GlowPassportHandler(BaseHTTPRequestHandler):
    server_version = "GlowPassportAPI/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8000")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            init_db()
            self.send_json({"ok": True, "status": "ready"})
            return
        if path == "/api/product-scout":
            query = urllib.parse.parse_qs(parsed.query).get("q", ["K-beauty Olive Young TikTok viral skincare"])[0]
            self.send_json({"ok": True, "items": fetch_product_scout(query)})
            return
        else:
            self.send_json({"ok": False, "error": "not_found"}, status=404)
            return

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/leads":
            self.send_json({"ok": False, "error": "not_found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self.send_json({"ok": False, "error": "invalid_json"}, status=400)
            return

        email = str(payload.get("email", "")).strip()
        if "@" not in email or "." not in email:
            self.send_json({"ok": False, "error": "valid_email_required"}, status=422)
            return

        lead_id = insert_lead(payload)
        notification_status = send_notification_email(lead_id, payload)
        update_notification_status(lead_id, notification_status)
        self.send_json(
            {
                "ok": True,
                "id": lead_id,
                "notificationStatus": notification_status,
            },
            status=201,
        )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), GlowPassportHandler)
    print(f"Glow Passport API listening on http://{HOST}:{PORT}")
    server.serve_forever()


def fetch_product_scout(query: str) -> list[dict[str, str]]:
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    request = urllib.request.Request(url, headers={"User-Agent": "GlowPassport/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items: list[dict[str, str]] = []
        for item in root.findall(".//item")[:5]:
            source = item.findtext("source") or "Google"
            title = item.findtext("title") or "K-beauty product signal"
            link = item.findtext("link") or ""
            items.append({"source": source, "title": title, "link": link})
        return items
    except Exception:
        return []


if __name__ == "__main__":
    main()
