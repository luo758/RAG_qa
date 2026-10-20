from __future__ import annotations

import base64
import hashlib
import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from html import escape

from sqlalchemy.orm import Session

from .config import settings
from .models import Captcha

CAPTCHA_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def _svg_captcha(code: str) -> str:
    width, height = 180, 64
    colors = ["#0f766e", "#ea580c", "#2563eb", "#7c3aed", "#be123c"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="12" fill="#f8fafc"/>',
    ]
    for _ in range(7):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{random.choice(colors)}" stroke-opacity="0.28" stroke-width="1.4"/>'
        )
    for index, char in enumerate(code):
        x = 25 + index * 36
        y = 43 + random.randint(-5, 5)
        rotation = random.randint(-16, 16)
        parts.append(
            f'<text x="{x}" y="{y}" transform="rotate({rotation} {x} {y})" '
            f'fill="{random.choice(colors)}" font-family="Verdana,Arial" '
            f'font-size="30" font-weight="700">{escape(char)}</text>'
        )
    for _ in range(26):
        parts.append(
            f'<circle cx="{random.randint(0, width)}" cy="{random.randint(0, height)}" '
            f'r="{random.choice([1, 1, 2])}" fill="{random.choice(colors)}" opacity="0.35"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def create_captcha(db: Session) -> tuple[Captcha, str]:
    code = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(4))
    captcha = Captcha(
        id=str(uuid.uuid4()),
        code_hash=_hash_code(code),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
        + timedelta(seconds=settings.captcha_expire_seconds),
    )
    db.add(captcha)
    db.commit()
    db.refresh(captcha)
    return captcha, code


def captcha_image_data(code: str) -> str:
    payload = base64.b64encode(_svg_captcha(code).encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"


def verify_captcha(db: Session, captcha_id: str, code: str) -> bool:
    captcha = db.get(Captcha, captcha_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not captcha or captcha.used or captcha.expires_at < now:
        return False
    if not secrets.compare_digest(captcha.code_hash, _hash_code(code)):
        return False
    captcha.used = True
    db.commit()
    return True
