# -*- coding: utf-8 -*-
"""
RCOIN·BOT — игровой бот (aiogram 3.x) + веб-приложение (aiohttp) в одном файле.

Запуск:  pip install -U aiogram aiohttp  &&  BOT_TOKEN=... python rcoin_bot.py
Render:  Start Command `python rubinbot.py`, переменные окружения см. README в ответе.
Токен НЕ хранится в коде — только в переменной окружения BOT_TOKEN.
"""
import asyncio
import atexit
import base64
import hashlib
import hmac
import json
import logging
import math
import os
import random
import re
import sqlite3
import re as _db_re
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # локальный запуск на SQLite не требует psycopg2
    psycopg2 = None
    RealDictCursor = None
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape as esc
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import io
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, BufferedInputFile, CallbackQuery, ErrorEvent, FSInputFile,
                           InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle,
                           InputTextMessageContent, LabeledPrice, LinkPreviewOptions, Message, PreCheckoutQuery, WebAppInfo)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rcoin")
_BTN_FIELDS = getattr(InlineKeyboardButton, "model_fields", {})
HAS_BUTTON_STYLE = "style" in _BTN_FIELDS
HAS_BUTTON_ICON = "icon_custom_emoji_id" in _BTN_FIELDS

# ============================ КОНФИГ ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9176453419:AAHNmMOTd17-lKxERnixROhSOcRi91wIGto").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "5257618084") or 0)
ADMIN_IDS = {OWNER_ID} | {int(v) for v in re.findall(r"\d+", os.getenv("ADMIN_IDS", "5257618084"))}
ADMIN_IDS.discard(0)
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@playhomemines").strip()
REQUIRED_CHAT = os.getenv("REQUIRED_CHAT", "@gamehomemines").strip()
ANNOUNCE_CHAT = os.getenv("ANNOUNCE_CHAT", REQUIRED_CHAT).strip()
REQUIRE_SUB = os.getenv("REQUIRE_SUB", "1") == "1"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_FILE = os.getenv("DB_FILE", "data.db")  # SQLite fallback for local development only
PORT = int(os.getenv("PORT", "8080"))
PREMIUM_EMOJI = os.getenv("PREMIUM_EMOJI", "1") == "1"   # <tg-emoji> в тексте
PREMIUM_ICONS = os.getenv("PREMIUM_ICONS", "1") == "1"   # иконки на кнопках
_pub = (os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
WEBAPP_URL = _pub if _pub.startswith("https://") else ""
TREASURY_START = int(os.getenv("TREASURY_START", "2000000000"))
TRANSFER_COMMISSION = int(os.getenv("TRANSFER_COMMISSION", "15"))
# Лимиты экономики: баланс упирается в потолок, излишек уходит в «Архив».
MAX_BALANCE = int(os.getenv("MAX_BALANCE", "5000000000"))
MAX_BET = int(os.getenv("MAX_BET", "1000000000"))
MAX_TRANSFER = int(os.getenv("MAX_TRANSFER", "1000000000"))
REF_PERCENT = 2
BONUS_AMOUNT = 2500
MINT_COST = 10_000
IMAGE_PATH = "image.png"
# For Render persistent disk, set NFT_DIR=/var/data/nft_images.
NFT_DIR = Path(os.getenv("NFT_DIR", "/var/data/nft_images" if os.getenv("RENDER") else "nft_images"))
BALANCE_BANNER = Path(os.getenv("BALANCE_BANNER", "balance_banner.png"))
NFT_ART_VERSION = 6
UI_TICKER_KEY = "ui:ticker"
UI_TICKER_DEFAULT = ("RUBIN · NEW BLACK COLLECTION · АПГРЕЙДЕР 2.0 · "
                     "ЧЁРНЫЙ ПРЕМИУМ · АРЕНА С БОНУСОМ · ")
UI_THEME_KEY = "ui:theme"
UI_THEME_DEFAULT = "obsidian"

dp = Dispatcher(storage=MemoryStorage())
bot: Bot = None  # type: ignore
BOT_USERNAME = "bot"

# ============================ ЭМОДЗИ ============================
EMOJI_IDS = {
    "games": "5841551282321497604", "dice": "5312533460324199794", "roulette": "6228608791529656524",
    "fortune": "5434093331292377553", "mines": "5370692462882857093", "crash": "5283080528818360566",
    "basket": "5384327463629233871", "darts": "5310278924616356636", "blackjack": "5285420684699260907",
    "sun": "5391270767889497941", "hunt": "5370553185683394181", "spin": "5915833712368424979",
    "football": "5413474404485061402", "pyramid": "5224257782013769471", "miner": "5370692462882857093",
    "hi_lo": "5926783847453692661", "ttt": "5222158908805632010", "door": "5259067694396474462",
    "profile": "5202216593966244027", "balance": "5197491391206281629", "bank": "5881948563591666817",
    "diamond": "5438496463044752972", "star": "5438496463044752972", "lock": "5305621469134857194",
    "nft": "5262517101578443800", "referral": "5942877472163892475", "check": "5810189259327413739",
    "treasury": "5798678875823153004", "win": "5305747221996177787", "lose": "5305474786400690766",
    "settings": "5258096772776991776", "admin": "6129805886383723340", "donate": "5438496463044752972",
    "ad": "5213391561999526028", "market": "5278702045883292456", "question": "5436113877181941026",
    "item_1": "5332717942599618048", "item_2": "5404752966584394198", "item_3": "5280924618444514633",
    "item_4": "5368488358681000659", "item_5": "5398024200235529935", "item_6": "5449449325434266744",
    "item_7": "5201924046563852634", "item_8": "5199959030306456092", "item_9": "5316599316884766402",
    "snowflake": "5449449325434266744",
}
FALLBACK = {
    "games": "🎮", "dice": "🎲", "roulette": "🎰", "fortune": "🎡", "mines": "💣", "crash": "🚀",
    "basket": "🏀", "darts": "🎯", "blackjack": "🃏", "sun": "☀️", "hunt": "🏹", "spin": "🎰",
    "football": "⚽", "pyramid": "🔺", "miner": "⛏", "hi_lo": "🎴", "ttt": "❌", "door": "🚪",
    "profile": "👤", "balance": "💰", "bank": "🏦", "diamond": "💎", "star": "⭐", "lock": "🔒",
    "nft": "🖼", "referral": "👥", "check": "✅", "treasury": "🏛", "win": "🏆", "lose": "💔",
    "settings": "⚙️", "admin": "👑", "donate": "🎁", "ad": "📢", "market": "🛒", "question": "❔",
    "item_1": "❄️", "item_2": "🍬", "item_3": "🧦", "item_4": "🧤", "item_5": "🍪", "item_6": "⭐",
    "item_7": "🔔", "item_8": "🧊", "item_9": "☕", "snowflake": "❄️",
}
SOUVENIRS = {"item_1": "Снежный шар", "item_2": "Леденец-трость", "item_3": "Носок с подарками",
             "item_4": "Варежка Деда Мороза", "item_5": "Пряник-драчун", "item_6": "Ёлочная звезда",
             "item_7": "Колокольчик саней", "item_8": "Сосулька-сабля", "item_9": "Кружка какао"}


def E(key: str) -> str:
    fb = FALLBACK.get(key, "▫️")
    if PREMIUM_EMOJI and key in EMOJI_IDS:
        return f'<tg-emoji emoji-id="{EMOJI_IDS[key]}">{fb}</tg-emoji>'
    return fb


def _auto_style(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(w in t for w in ("отмена", "назад", "покинуть", "снять", "удалить", "выйти", "стоп", "закрыть")):
        return "danger"
    if any(w in t for w in ("донат", "premium", "stars", "пополнить", "подписка", "купить", "магазин")):
        return "primary"
    if any(w in t for w in ("играть", "вступить", "войти", "бонус", "ежедневный", "забрать",
                            "начать", "сыграть", "крутить", "открыть", "готово", "подтвердить")):
        return "success"
    return None


def btn(text: str, data: str = None, icon: str = None, url: str = None, web: str = None,
        style: str = None) -> InlineKeyboardButton:
    kw: Dict[str, Any] = {"text": text}
    if data:
        kw["callback_data"] = data
    if url:
        kw["url"] = url
    if web:
        kw["web_app"] = WebAppInfo(url=web)
    if icon and PREMIUM_ICONS and HAS_BUTTON_ICON:
        custom_id = EMOJI_IDS.get(icon)
        if not custom_id:
            custom_id = globals().get("BADGES", {}).get(icon, {}).get("id")
        if custom_id:
            kw["icon_custom_emoji_id"] = str(custom_id)
    st = style or _auto_style(text)
    if st and HAS_BUTTON_STYLE:
        kw["style"] = st
    return InlineKeyboardButton(**kw)


def qbtn(data: str) -> InlineKeyboardButton:
    """Кнопка-вопрос (мины, башня, бонус 5x5)."""
    if PREMIUM_ICONS:
        return btn("\u2800", data, icon="question")
    return btn("\u2800", data)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows if r])


def box(*lines) -> str:
    return "<blockquote>" + "\n".join(str(l) for l in lines) + "</blockquote>"


# ---------- защита от DOCUMENT_INVALID (битые/запрещённые кастомные эмодзи) ----------
TGE_RE = re.compile(r'<tg-emoji emoji-id="\d+">(.*?)</tg-emoji>', re.S)
_fb_hits = [0]


def _strip_method(method):
    """Копия запроса без кастомных и обычных эмодзи (или None, если нечего убирать)."""
    upd = {}
    for f in ("text", "caption"):
        v = getattr(method, f, None)
        if isinstance(v, str) and v:
            nv = _strip_emoji_text(v)
            if nv != v:
                upd[f] = nv
    rm = getattr(method, "reply_markup", None)
    if isinstance(rm, InlineKeyboardMarkup):
        rows, changed = [], False
        for row in rm.inline_keyboard:
            nr = []
            for b in row:
                d = b.model_dump(exclude_none=True)
                if "icon_custom_emoji_id" in d:
                    d.pop("icon_custom_emoji_id")
                    changed = True
                if "style" in d:
                    d.pop("style")
                    changed = True
                clean = _strip_emoji_text(d.get("text") or "")
                if clean == "…" or not clean.strip():
                    clean = "\u2800"
                if clean != d.get("text"):
                    changed = True
                d["text"] = clean[:64]
                nr.append(InlineKeyboardButton(**d))
            rows.append(nr)
        if changed:
            upd["reply_markup"] = InlineKeyboardMarkup(inline_keyboard=rows)
    return method.model_copy(update=upd) if upd else None


class EmojiFallback(BaseRequestMiddleware):
    """Если Telegram отклонил запрос из-за кастомных эмодзи — повторяем его с обычными эмодзи."""

    async def __call__(self, make_request, bot, method):
        try:
            return await make_request(bot, method)
        except TelegramBadRequest as e:
            s_ = str(e).lower()
            if any(k in s_ for k in ("document_invalid", "emoji", "icon", "button", "style")):
                plain = _strip_method(method)
                if plain is not None:
                    res = await make_request(bot, plain)
                    _fb_hits[0] += 1
                    log.warning("Кастомные эмодзи отклонены Telegram (%s) — отправлено без них [%s]", e, _fb_hits[0])
                    return res
            raise


async def validate_emoji_ids():
    """Оставляем только те ID эмодзи, которые реально существуют."""
    global EMOJI_IDS
    badges = globals().get("BADGES") or {}
    ids = sorted(set(EMOJI_IDS.values()) | {str(b.get("id")) for b in badges.values() if b.get("id")})
    valid = set()
    try:
        for i in range(0, len(ids), 200):
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=ids[i:i + 200])
            valid |= {st.custom_emoji_id for st in stickers}
    except Exception as e:
        log.warning("Не удалось проверить ID эмодзи (%s) — оставляю все, откат сработает автоматически", e)
        return
    bad = [k for k, v in EMOJI_IDS.items() if v not in valid]
    if bad:
        log.warning("Недействительные ID эмодзи, заменены обычными: %s", ", ".join(bad))
    EMOJI_IDS = {k: v for k, v in EMOJI_IDS.items() if v in valid}
    for key, b in badges.items():
        if b.get("id") and str(b["id"]) not in valid:
            log.warning("Недействительный ID галочки %s — включаю обычный символ", key)
            b["id"] = ""
    log.info("Рабочих премиум-эмодзи: %s из %s", len(EMOJI_IDS), len(EMOJI_IDS) + len(bad))


# ---------- единая замена обычных эмодзи на кастомные ----------
# Ключ — обычный эмодзи, значение — ключ EMOJI_IDS / BADGES.
EMOJI_ALIASES = {
    "🎮": "games", "🎲": "dice", "🎰": "spin", "🎡": "fortune", "💣": "mines",
    "🚀": "crash", "🏀": "basket", "🎯": "darts", "🃏": "blackjack", "☀": "sun",
    "🏹": "hunt", "⚽": "football", "🔺": "pyramid", "⛏": "miner", "🎴": "hi_lo",
    "❌": "ttt", "🚪": "door", "👤": "profile", "💰": "balance", "💸": "balance",
    "🏦": "bank", "💎": "diamond", "⭐": "star", "🔒": "lock", "🖼": "nft",
    "👥": "referral", "✅": "check", "🏛": "treasury", "🏆": "win", "💔": "lose",
    "⚙": "settings", "👑": "admin", "🎁": "donate", "📢": "ad", "🛒": "market",
    "❔": "question", "❄": "snowflake", "❄️": "snowflake", "🍬": "item_2", "🧦": "item_3", "🧤": "item_4",
    "🍪": "item_5", "🔔": "item_7", "🧊": "item_8", "☕": "item_9",
    "☑": "black", "✔": "blue", "💠": "rubin", "🛡": "moder", "🎧": "support",
    "🧪": "tester", "🎄": "ny", "👨": "dev",
}
EMOJI_SEQUENCES = {
    "👨‍💻": "dev", "☑️": "black", "✔️": "blue", "❄️": "item_1", "☀️": "sun",
    "⚙️": "settings", "🎄": "ny",
}
EMOJI_RANGES = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D\u20E3]"
)
EMOJI_SEQ_RE = re.compile("|".join(re.escape(s) for s in sorted(EMOJI_SEQUENCES, key=len, reverse=True)))
EMOJI_ANY_RE = re.compile("(?:" + EMOJI_SEQ_RE.pattern + ")|(?:" + EMOJI_RANGES.pattern + ")")


def _emoji_id(key: Optional[str]) -> str:
    if not key:
        return ""
    eid = EMOJI_IDS.get(key)
    if not eid:
        b = globals().get("BADGES") or {}
        eid = (b.get(key) or {}).get("id")
    return str(eid) if eid else ""


def _emoji_key(token: str) -> Optional[str]:
    key = EMOJI_SEQUENCES.get(token) or EMOJI_ALIASES.get(token)
    if not key and token.endswith("\ufe0f"):
        key = EMOJI_ALIASES.get(token[:-1])
    return key


def _replace_emoji_chunk(text: str) -> str:
    def repl(m):
        token = m.group(0)
        if token in ("\ufe0f", "\u200d", "\u20e3"):
            return ""
        key = _emoji_key(token)
        eid = _emoji_id(key)
        if eid and PREMIUM_EMOJI:
            return f'<tg-emoji emoji-id="{eid}">{token}</tg-emoji>'
        return ""
    return EMOJI_ANY_RE.sub(repl, text)


def _tidy_text(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", line).strip() if line.strip() else ""
        lines.append(line)
    return "\n".join(lines)


HTML_TAG_RE = re.compile(r"<tg-emoji\b[^>]*>.*?</tg-emoji>|<[^>]+>", re.S)


def premiumize_text(text: str) -> str:
    """Заменяет обычные эмодзи на <tg-emoji>, не трогая HTML-разметку."""
    if not text or not isinstance(text, str):
        return text
    out, last = [], 0
    for m in HTML_TAG_RE.finditer(text):
        out.append(_replace_emoji_chunk(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(_replace_emoji_chunk(text[last:]))
    s = _tidy_text("".join(out))
    if not re.sub(r"<[^>]+>", "", s).strip():
        return "…"
    return s


def premiumize_button(b: InlineKeyboardButton) -> InlineKeyboardButton:
    d = b.model_dump(exclude_none=True)
    text = str(d.get("text") or "")
    icon = d.get("icon_custom_emoji_id")
    m = TGE_RE.search(text)
    if m and not icon:
        im = re.search(r'emoji-id="(\d+)"', m.group(0))
        if im:
            icon = im.group(1)
    text = TGE_RE.sub("", text)
    stripped = text.strip()
    m2 = EMOJI_SEQ_RE.match(stripped) or EMOJI_ANY_RE.match(stripped)
    if m2 and not icon:
        key = _emoji_key(m2.group(0))
        if key:
            icon = _emoji_id(key)
    text = re.sub(r"[ \t]{2,}", " ", EMOJI_ANY_RE.sub("", text)).strip()
    if not text:
        text = "\u2800"
    d["text"] = text[:64]
    if icon and PREMIUM_ICONS and HAS_BUTTON_ICON:
        d["icon_custom_emoji_id"] = str(icon)
    else:
        d.pop("icon_custom_emoji_id", None)
    return InlineKeyboardButton(**d)


def premiumize_markup(markup):
    if not isinstance(markup, InlineKeyboardMarkup):
        return markup
    rows = [[premiumize_button(b) for b in row] for row in markup.inline_keyboard]
    return InlineKeyboardMarkup(inline_keyboard=rows)


class PremiumOut(BaseRequestMiddleware):
    """Приводит исходящие сообщения к премиум-эмодзи и чистит обычные."""

    async def __call__(self, make_request, bot, method):
        if not hasattr(method, "parse_mode"):
            return await make_request(bot, method)
        upd = {}
        for f in ("text", "caption"):
            v = getattr(method, f, None)
            if isinstance(v, str) and v:
                nv = premiumize_text(v)
                if nv != v:
                    upd[f] = nv
        rm = getattr(method, "reply_markup", None)
        if isinstance(rm, InlineKeyboardMarkup):
            nrm = premiumize_markup(rm)
            if nrm is not None:
                upd["reply_markup"] = nrm
        if upd:
            method = method.model_copy(update=upd)
        return await make_request(bot, method)


def _strip_emoji_text(text: str) -> str:
    s = TGE_RE.sub("", text or "")
    s = EMOJI_ANY_RE.sub("", s)
    s = _tidy_text(s)
    return s or "…"


# ============================ УТИЛИТЫ ============================
MSK = timezone(timedelta(hours=3))


def now() -> int:
    return int(time.time())


def today() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d")


def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", "'")
    except Exception:
        return str(n)


def dur(sec) -> str:
    sec = int(max(0, sec))
    h, r = divmod(sec, 3600)
    mn, s = divmod(r, 60)
    out = []
    if h:
        out.append(f"{h} ч")
    if mn:
        out.append(f"{mn} мин")
    if s or not out:
        out.append(f"{s} сек")
    return " ".join(out)


def gen_code(n=8, alphabet=string.ascii_uppercase + string.digits) -> str:
    return "".join(random.choices(alphabet, k=n))


def parse_amount(text, balance: int = 0) -> int:
    t = str(text).strip().lower().replace(",", ".").replace(" ", "")
    if t in ("все", "всё", "вб", "all", "max"):
        return int(balance)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(к{1,3}|k{1,3})?", t)
    if not m:
        return 0
    mult = {0: 1, 1: 1000, 2: 10 ** 6, 3: 10 ** 9}[len(m.group(2) or "")]
    return int(float(m.group(1)) * mult)


def _norm(t: Optional[str]) -> str:
    t = (t or "").strip().lower()
    if t.startswith("/"):
        t = t[1:]
    return re.sub(r"^(\S+?)@\w+", r"\1", t)


def first_word(t: Optional[str]) -> str:
    s = _norm(t).split()
    return s[0] if s else ""


def P(*names):
    """Фильтр текстовой команды: точное слово или слово + аргументы (с / или без)."""
    names = tuple(n.lower() for n in names)

    def f(t):
        if not t:
            return False
        s = _norm(t)
        return any(s == n or s.startswith(n + " ") for n in names)
    return F.text.func(f)


def mention(uid: int, name: str) -> str:
    return f'<a href="tg://user?id={uid}">{esc(str(name))}</a>'


def deeplink(arg: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={arg}"


# ============================ БАЗА ДАННЫХ ============================
# На Render задайте DATABASE_URL от Neon/Supabase/другого PostgreSQL.
# SQLite оставлен только для локального запуска и тестов.
AUTO_ID_TABLES = {"check_activations", "ads", "bet_history", "referrals", "transfer_history",
                  "promo_codes", "promo_uses", "nft_items", "gifts", "sessions", "trade_logs"}

class _CompatCursor:
    def __init__(self, cursor):
        self._c = cursor
        self._lastrowid = None
    @property
    def rowcount(self): return self._c.rowcount
    @property
    def lastrowid(self): return self._lastrowid
    def fetchall(self): return self._c.fetchall()
    def fetchone(self): return self._c.fetchone()
    def execute(self, sql, args=()):
        raw = sql.strip().rstrip(";")
        if raw.upper().startswith("CREATE TABLE"):
            raw = raw.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
        # Compatibility for the one SQLite schema-inspection statement.
        m = _db_re.match(r"PRAGMA\s+table_info\((\w+)\)", raw, _db_re.I)
        if m:
            self._c.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s ORDER BY ordinal_position", (m.group(1),))
            return self
        if _db_re.match(r"PRAGMA\s+journal_mode", raw, _db_re.I):
            self._c.execute("SELECT 'wal' AS journal_mode")
            return self
        if _db_re.match(r"INSERT\s+OR\s+IGNORE\s+INTO", raw, _db_re.I):
            raw = _db_re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", raw, count=1, flags=_db_re.I)
            if " ON CONFLICT " not in raw.upper():
                raw += " ON CONFLICT DO NOTHING"
        # Return generated ids where the original code expects SQLite lastrowid.
        im = _db_re.match(r"INSERT\s+INTO\s+(\w+)", raw, _db_re.I)
        if im and im.group(1).lower() in AUTO_ID_TABLES and " RETURNING " not in raw.upper():
            raw += " RETURNING id"
        raw = raw.replace("?", "%s")
        self._c.execute(raw, args or ())
        if " RETURNING id" in raw.upper():
            row = self._c.fetchone()
            if row:
                self._lastrowid = row.get("id") if isinstance(row, dict) else row[0]
        return self
    def close(self): self._c.close()

class _CompatConnection:
    def __init__(self, raw): self._raw = raw
    def execute(self, sql, args=()):
        cur = _CompatCursor(self._raw.cursor(cursor_factory=RealDictCursor))
        return cur.execute(sql, args)
    def cursor(self): return _CompatCursor(self._raw.cursor(cursor_factory=RealDictCursor))
    def commit(self): self._raw.commit()
    def close(self): self._raw.close()
    def __enter__(self): return self
    def __exit__(self, typ, val, tb):
        if typ: self._raw.rollback()
        else: self._raw.commit()
        self.close()

def db_connect(path=None, timeout=30):
    if DATABASE_URL:
        if psycopg2 is None:
            raise RuntimeError("DATABASE_URL задан, но psycopg2 не установлен: pip install psycopg2-binary")
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return _CompatConnection(psycopg2.connect(url, connect_timeout=timeout, sslmode="require"))
    return sqlite3.connect(str(path or DB_FILE), timeout=timeout)

def q(sql: str, args=(), one: bool = False):
    c = db_connect(timeout=30)
    if not DATABASE_URL:
        c.row_factory = sqlite3.Row
    try:
        rows = c.execute(sql, args).fetchall()
    finally:
        c.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]

def x(sql: str, args=()) -> Tuple[int, int]:
    c = db_connect(timeout=30)
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.rowcount, cur.lastrowid
    finally:
        c.close()


USER_COLS = {
    "username": "TEXT DEFAULT ''", "display_name": "TEXT DEFAULT ''", "first_name": "TEXT DEFAULT ''",
    "last_name": "TEXT DEFAULT ''", "balance_coin": "INTEGER DEFAULT 0", "balance_point": "INTEGER DEFAULT 0",
    "stars_balance": "INTEGER DEFAULT 0", "bank_balance": "INTEGER DEFAULT 0",
    "salary_pending": "INTEGER DEFAULT 0",
    "bank_limit": "INTEGER DEFAULT 500000000", "bonus_last_time": "INTEGER DEFAULT 0",
    "banned_until": "INTEGER DEFAULT 0", "muted_until": "INTEGER DEFAULT 0", "ban_reason": "TEXT DEFAULT ''",
    "mute_reason": "TEXT DEFAULT ''", "total_wins": "INTEGER DEFAULT 0", "total_losses": "INTEGER DEFAULT 0",
    "total_games": "INTEGER DEFAULT 0", "total_games_day": "INTEGER DEFAULT 0", "last_game_day": "INTEGER DEFAULT 0",
    "referral_code": "TEXT DEFAULT ''", "referred_by": "INTEGER DEFAULT 0", "referral_earnings": "INTEGER DEFAULT 0",
    "referral_percent": "INTEGER DEFAULT 2", "referral_withdrawn": "INTEGER DEFAULT 0",
    "created_at": "INTEGER DEFAULT 0", "is_anonymous": "INTEGER DEFAULT 0", "last_spin_time": "INTEGER DEFAULT 0",
    "about_text": "TEXT DEFAULT ''", "rank_title": "TEXT DEFAULT 'Новичок'", "custom_username": "TEXT DEFAULT ''",
    "profile_emoji": "TEXT DEFAULT ''", "profile_emoji_fb": "TEXT DEFAULT '✨'",
    "balance_nft_id": "INTEGER DEFAULT 0", "profile_nft_id": "INTEGER DEFAULT 0",
    "is_scammer": "INTEGER DEFAULT 0", "is_admin_rank": "INTEGER DEFAULT 0", "is_donater": "INTEGER DEFAULT 0",
    "is_official": "INTEGER DEFAULT 0", "treasury_access": "INTEGER DEFAULT 0", "titles": "TEXT DEFAULT '[]'",
    "antiludo_until": "INTEGER DEFAULT 0", "shield_until": "INTEGER DEFAULT 0", "inventory": "TEXT DEFAULT '[]'",
    "ev_day": "TEXT DEFAULT ''", "ev_stash_used": "INTEGER DEFAULT 0", "ev_boss_day": "TEXT DEFAULT ''",
    "ev_wheel_last": "INTEGER DEFAULT 0", "ev_points": "INTEGER DEFAULT 0",
    "db5_streak": "INTEGER DEFAULT 0", "db5_last_day": "TEXT DEFAULT ''",
    "archive_coin": "INTEGER DEFAULT 0", "mine_pending": "INTEGER DEFAULT 0", "mine_last": "INTEGER DEFAULT 0",
}
SCHEMA = [
    "CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY)",
    "CREATE TABLE IF NOT EXISTS checks(check_id TEXT PRIMARY KEY, owner_id INTEGER, amount INTEGER, activations INTEGER DEFAULT 0, max_activations INTEGER, description TEXT DEFAULT '', password TEXT DEFAULT '', created_at INTEGER, is_active INTEGER DEFAULT 1)",
    "CREATE TABLE IF NOT EXISTS check_activations(id INTEGER PRIMARY KEY AUTOINCREMENT, check_id TEXT, user_id INTEGER, activated_at INTEGER, UNIQUE(check_id,user_id))",
    "CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, channel_link TEXT, price_per_sub INTEGER, target_subs INTEGER, paid_points INTEGER, created_at INTEGER, status TEXT DEFAULT 'active', current_subs INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS subscriptions(user_id INTEGER, ad_id INTEGER, claimed INTEGER DEFAULT 0, claimed_at INTEGER DEFAULT 0, PRIMARY KEY(user_id,ad_id))",
    "CREATE TABLE IF NOT EXISTS bet_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, game_type TEXT, bet_amount INTEGER, win_amount INTEGER, is_win INTEGER, bet_data TEXT, created_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS referrals(id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER, created_at INTEGER, reward_given INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS transfer_history(id INTEGER PRIMARY KEY AUTOINCREMENT, from_user_id INTEGER, to_user_id INTEGER, amount INTEGER, created_at INTEGER, comment TEXT DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS promo_codes(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, reward INTEGER, uses INTEGER DEFAULT 0, max_uses INTEGER, created_by INTEGER, created_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS promo_uses(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, promo_id INTEGER, used_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS nft_items(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, name TEXT, level INTEGER DEFAULT 1, rarity TEXT DEFAULT 'common', price INTEGER, created_at INTEGER, for_sale INTEGER DEFAULT 0, sale_price INTEGER DEFAULT 0, description TEXT DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS gifts(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, rarity TEXT DEFAULT 'common', owner_id INTEGER DEFAULT 0, used INTEGER DEFAULT 0, used_by INTEGER DEFAULT 0, created_at INTEGER, expires_at INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS treasury(id INTEGER PRIMARY KEY, balance_coin INTEGER DEFAULT 0, balance_point INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS treasury_settings(id INTEGER PRIMARY KEY CHECK (id = 1), auto_fri INTEGER DEFAULT 1, auto_sat INTEGER DEFAULT 1, fri_amount INTEGER DEFAULT 1000000, sat_amount INTEGER DEFAULT 500000, auto_slots INTEGER DEFAULT 50, chat_ids TEXT DEFAULT '', updated_at INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS event_progress(id INTEGER PRIMARY KEY CHECK (id = 1), boss_hp INTEGER DEFAULT 0, boss_max INTEGER DEFAULT 0, day TEXT DEFAULT '', season INTEGER DEFAULT 1)",
    "CREATE TABLE IF NOT EXISTS miner_data(user_id INTEGER PRIMARY KEY, mine_level INTEGER DEFAULT 0, business_level INTEGER DEFAULT 0, villa_level INTEGER DEFAULT 0, last_collect INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, game TEXT, bet INTEGER, state TEXT, status TEXT DEFAULT 'active', created_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS quests(user_id INTEGER, day TEXT, key TEXT, value INTEGER DEFAULT 0, PRIMARY KEY(user_id,day,key))",
    "CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS boss_hits(day TEXT, user_id INTEGER, dmg INTEGER DEFAULT 0, PRIMARY KEY(day,user_id))",
    "CREATE TABLE IF NOT EXISTS daily5(user_id INTEGER, day TEXT, streak INTEGER, grid TEXT, opened TEXT, pot INTEGER DEFAULT 0, status TEXT DEFAULT 'open', PRIMARY KEY(user_id,day))",
    "CREATE TABLE IF NOT EXISTS snowman_daily(user_id INTEGER, day TEXT, snowballs INTEGER DEFAULT 0, snowmen INTEGER DEFAULT 0, last_collect INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, PRIMARY KEY(user_id,day))",
    "CREATE TABLE IF NOT EXISTS snowman_rewards(day TEXT, user_id INTEGER, place INTEGER, amount INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0, PRIMARY KEY(day,place))",
]
EXTRA_COLS = {
    "nft_archive": {"price": "INTEGER DEFAULT 0"},
    "nft_items": {"photo": "TEXT DEFAULT '🎨'", "model": "TEXT DEFAULT 'Стандартный'",
                  "background": "TEXT DEFAULT 'Обычный'", "base_name": "TEXT DEFAULT ''"},
    "gifts": {"expires_at": "INTEGER DEFAULT 0"},
    "treasury_settings": {"daily_enabled": "INTEGER DEFAULT 1", "daily_amount": "INTEGER DEFAULT 100000",
                          "daily_hour": "INTEGER DEFAULT 12"},
}


def ensure_cols(table: str, cols: Dict[str, str]):
    have = {r["name"] for r in q(f"PRAGMA table_info({table})")}
    if not have:
        return
    for name, decl in cols.items():
        if name not in have:
            try:
                x(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            except Exception as e:
                log.warning("ALTER %s.%s: %s", table, name, e)


def init_db():
    if DATABASE_URL:
        # PostgreSQL schema: replace SQLite AUTOINCREMENT with BIGSERIAL.
        for statement in SCHEMA:
            pg_statement = statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
            x(pg_statement)
    else:
        db_path = Path(DB_FILE).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(db_path), timeout=30)
        try:
            c.execute("PRAGMA journal_mode=WAL")
        finally:
            c.close()
        for statement in SCHEMA:
            x(statement)
    ensure_cols("users", USER_COLS)
    for t, cols in EXTRA_COLS.items():
        ensure_cols(t, cols)
    x("INSERT OR IGNORE INTO treasury(id,balance_coin,balance_point,updated_at) VALUES(1,?,0,?)", (TREASURY_START, now()))
    x("INSERT OR IGNORE INTO treasury_settings(id) VALUES(1)")
    x("INSERT OR IGNORE INTO event_progress(id,boss_hp,boss_max,day,season) VALUES(1,0,0,'',1)")
    log.info("База данных готова: %s", "PostgreSQL" if DATABASE_URL else DB_FILE)
    init_tables()
    seed_nft_archive()


def kv_get(key: str) -> Optional[str]:
    r = q("SELECT value FROM kv WHERE key=?", (key,), one=True)
    return r["value"] if r else None


def kv_set(key: str, value: str):
    x("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def ui_ticker() -> str:
    return (kv_get(UI_TICKER_KEY) or UI_TICKER_DEFAULT).strip()[:300]


def ui_theme() -> str:
    return (kv_get(UI_THEME_KEY) or UI_THEME_DEFAULT).strip()[:24]


def get_user(uid: int) -> Dict[str, Any]:
    r = q("SELECT * FROM users WHERE user_id=?", (uid,), one=True)
    if not r:
        x("INSERT OR IGNORE INTO users(user_id,created_at,referral_code) VALUES(?,?,?)", (uid, now(), gen_code()))
        r = q("SELECT * FROM users WHERE user_id=?", (uid,), one=True)
    for k in USER_COLS:
        if r.get(k) is None:
            r[k] = "" if "TEXT" in USER_COLS[k] else 0
    if not r["referral_code"]:
        code = gen_code()
        x("UPDATE users SET referral_code=? WHERE user_id=?", (code, uid))
        r["referral_code"] = code
    return r


def user_exists(uid: int) -> bool:
    return q("SELECT 1 FROM users WHERE user_id=?", (uid,), one=True) is not None


def update_user(uid: int, **kw):
    if not kw:
        return
    bad = [k for k in kw if k not in USER_COLS]
    if bad:
        raise ValueError(f"unknown user columns: {bad}")
    x(f"UPDATE users SET {', '.join(k + '=?' for k in kw)} WHERE user_id=?", (*kw.values(), uid))


def ensure_user(tu) -> None:
    uid = tu.id
    uname_ = (getattr(tu, "username", "") or "").lower()
    fn = getattr(tu, "first_name", "") or ""
    ln = getattr(tu, "last_name", "") or ""
    if not user_exists(uid):
        x("INSERT OR IGNORE INTO users(user_id,username,display_name,first_name,last_name,created_at,referral_code) VALUES(?,?,?,?,?,?,?)",
          (uid, uname_, fn or uname_ or str(uid), fn, ln, now(), gen_code()))
    else:
        x("UPDATE users SET username=?, first_name=?, last_name=? WHERE user_id=?", (uname_, fn, ln, uid))
        x("UPDATE users SET display_name=? WHERE user_id=? AND (display_name IS NULL OR display_name='')",
          (fn or uname_ or str(uid), uid))


def find_user(token: str) -> Optional[Dict[str, Any]]:
    token = (token or "").strip().lstrip("@")
    if not token:
        return None
    if token.isdigit():
        return get_user(int(token)) if user_exists(int(token)) else None
    t = token.lower()
    r = q("SELECT user_id FROM users WHERE lower(username)=? OR lower(custom_username)=? LIMIT 1", (t, t), one=True)
    return get_user(r["user_id"]) if r else None


def uname(u: Dict[str, Any], anon: bool = True) -> str:
    if anon and u.get("is_anonymous"):
        return "Аноним"
    n = u.get("display_name") or u.get("first_name") or u.get("username") or str(u["user_id"])
    return esc(str(n))[:40]


def is_admin(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return True
    r = q("SELECT is_admin_rank FROM users WHERE user_id=?", (uid,), one=True)
    return bool(r and r["is_admin_rank"])


def add_coin(uid: int, n: int) -> int:
    """Начисляет RCOIN с потолком MAX_BALANCE; излишек уходит в Архив. Возвращает сумму излишка.

    shortcut: чтение и запись не в одной транзакции — при одновременных начислениях одного игрока
    возможна гонка в пределах одного процесса; для бота это допустимо."""
    n = int(n)
    if n <= 0:
        if n < 0:
            x("UPDATE users SET balance_coin=balance_coin+? WHERE user_id=?", (n, uid))
        return 0
    r = q("SELECT balance_coin FROM users WHERE user_id=?", (uid,), one=True)
    cur = int(r["balance_coin"] or 0) if r else 0
    add = min(n, max(0, MAX_BALANCE - cur))
    over = n - add
    if add:
        x("UPDATE users SET balance_coin=balance_coin+? WHERE user_id=?", (add, uid))
    if over:
        x("UPDATE users SET archive_coin=archive_coin+? WHERE user_id=?", (over, uid))
    return over


def normalize_balances() -> int:
    """Переносит всё, что выше лимита, в Архив. Нужно после старых админ-выдач."""
    moved = 0
    for r in q("SELECT user_id, balance_coin FROM users WHERE balance_coin>?", (MAX_BALANCE,)):
        over = int(r["balance_coin"] or 0) - MAX_BALANCE
        if over <= 0:
            continue
        if x("UPDATE users SET balance_coin=?, archive_coin=archive_coin+? WHERE user_id=?",
             (MAX_BALANCE, over, r["user_id"]))[0] == 1:
            moved += over
    if moved:
        log.info("Лимит баланса: в Архив перенесено %s RCOIN", fmt(moved))
    return moved


def spend(uid: int, n: int, col: str = "balance_coin") -> bool:
    n = int(n)
    if n <= 0 or col not in ("balance_coin", "balance_point", "stars_balance"):
        return False
    return x(f"UPDATE users SET {col}={col}-? WHERE user_id=? AND {col}>=?", (n, uid, n))[0] == 1


def treasury_get() -> int:
    r = q("SELECT balance_coin FROM treasury WHERE id=1", one=True)
    return int(r["balance_coin"]) if r else 0


def treasury_add(n: int):
    x("UPDATE treasury SET balance_coin=balance_coin+?, updated_at=? WHERE id=1", (int(n), now()))


def treasury_take(n: int) -> bool:
    n = int(n)
    return n > 0 and x("UPDATE treasury SET balance_coin=balance_coin-?, updated_at=? WHERE id=1 AND balance_coin>=?", (n, now(), n))[0] == 1


def tset_get() -> Dict[str, Any]:
    r = q("SELECT * FROM treasury_settings WHERE id=1", one=True)
    if not r:
        x("INSERT OR IGNORE INTO treasury_settings(id) VALUES(1)")
        r = q("SELECT * FROM treasury_settings WHERE id=1", one=True)
    return r or {"auto_fri": 1, "auto_sat": 1, "fri_amount": 1_000_000,
                 "sat_amount": 500_000, "auto_slots": 50, "chat_ids": "",
                 "daily_enabled": 1, "daily_amount": 100_000, "daily_hour": 12}


def tset_update(**kw):
    allowed = {"auto_fri", "auto_sat", "fri_amount", "sat_amount", "auto_slots", "chat_ids",
               "daily_enabled", "daily_amount", "daily_hour"}
    data = {k: v for k, v in kw.items() if k in allowed}
    if not data:
        return
    x(f"UPDATE treasury_settings SET {', '.join(k + '=?' for k in data)}, updated_at=? WHERE id=1",
      (*data.values(), now()))


def tset_chats() -> List[str]:
    raw = str(tset_get().get("chat_ids") or "")
    return [c for c in re.split(r"[,\s]+", raw) if c]


def chat_ref(ref: str):
    try:
        return int(ref)
    except (TypeError, ValueError):
        return ref


# ---------- сессии многошаговых игр ----------
def sess_new(uid: int, game: str, bet: int, state: dict, status: str = "active") -> int:
    return x("INSERT INTO sessions(user_id,game,bet,state,status,created_at) VALUES(?,?,?,?,?,?)",
             (uid, game, int(bet), json.dumps(state), status, now()))[1]


def sess_get(sid: int) -> Optional[Dict[str, Any]]:
    r = q("SELECT * FROM sessions WHERE id=?", (sid,), one=True)
    if r:
        r["state"] = json.loads(r["state"] or "{}")
    return r


def sess_save(sid: int, state: dict):
    x("UPDATE sessions SET state=? WHERE id=?", (json.dumps(state), sid))


def sess_close(sid: int, status: str = "done") -> bool:
    return x("UPDATE sessions SET status=? WHERE id=? AND status='active'", (status, sid))[0] == 1


# ---------- квесты / титулы / учёт игр ----------
def quest_inc(uid: int, key: str, n: int = 1):
    x("INSERT INTO quests(user_id,day,key,value) VALUES(?,?,?,?) ON CONFLICT(user_id,day,key) DO UPDATE SET value=value+excluded.value",
      (uid, today(), key, n))


def quest_get(uid: int, key: str) -> int:
    r = q("SELECT value FROM quests WHERE user_id=? AND day=? AND key=?", (uid, today(), key), one=True)
    return int(r["value"]) if r else 0


TITLES = [(100000, "👑 ИМПЕРАТОР"), (50000, "🏰 ГРАНД"), (25000, "🔥 МАСТЕР"), (10000, "⭐ ЛЕГЕНДА"),
          (5000, "🎯 СНАЙПЕР"), (2500, "⚔️ БОЕЦ"), (1000, "🎮 ИГРОК")]


def refresh_title(uid: int, total: int):
    names = [t for n, t in TITLES if total >= n]
    if not names:
        return
    u = get_user(uid)
    upd = {"titles": json.dumps(list(reversed(names)), ensure_ascii=False)}
    if not (u["is_scammer"] or u["is_admin_rank"] or u["is_donater"] or u["is_official"]):
        upd["rank_title"] = names[0]
    update_user(uid, **upd)


def settle(uid: int, game: str, bet: int, payout: int, detail: str = "") -> int:
    """Начисляет выплату, пишет статистику/историю/квесты/реф-бонус. Ставка уже списана. Возвращает баланс."""
    bet, payout = int(bet), int(payout)
    if payout > bet > 0:
        payout = int(payout * win_mult(uid))
    if payout > 0:
        add_coin(uid, payout)
    win = payout > bet
    loss = payout < bet
    d = int(time.time()) // 86400
    x("UPDATE users SET total_games=total_games+1, total_wins=total_wins+?, total_losses=total_losses+?, "
      "total_games_day=CASE WHEN last_game_day=? THEN total_games_day+1 ELSE 1 END, last_game_day=? WHERE user_id=?",
      (1 if win else 0, 1 if loss else 0, d, d, uid))
    x("INSERT INTO bet_history(user_id,game_type,bet_amount,win_amount,is_win,bet_data,created_at) VALUES(?,?,?,?,?,?,?)",
      (uid, game, bet, payout, 1 if win else 0, detail[:200], now()))
    quest_inc(uid, "games")
    if win:
        quest_inc(uid, "wins")
    u = get_user(uid)
    refresh_title(uid, u["total_games"])
    if u["referred_by"] and bet > 0:
        cut = bet * REF_PERCENT // 100
        if cut > 0:
            x("UPDATE users SET referral_earnings=referral_earnings+? WHERE user_id=?", (cut, u["referred_by"]))
            x("UPDATE referrals SET total_earned=total_earned+? WHERE referred_id=?", (cut, uid))
    return u["balance_coin"]


# ---------- ответы ----------
async def ans(cb: CallbackQuery, text: str = None, alert: bool = False):
    try:
        if text:
            text = re.sub(r"\s{2,}", " ", EMOJI_ANY_RE.sub("", str(text))).strip()
            text = text[:190]
        await cb.answer(text, show_alert=alert)
    except Exception:
        pass


async def safe_edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup = None):
    try:
        await cb.message.edit_text(text[:4090], reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower():
            return
        try:
            await cb.message.answer(text[:4090], reply_markup=markup)
        except Exception as e2:
            log.warning("safe_edit: %s", e2)


# ---------- FSM «ввод пользователя» ----------
class Flow(StatesGroup):
    input = State()


FLOWS: Dict[str, Any] = {}


def flow(kind: str):
    def deco(fn):
        FLOWS[kind] = fn
        return fn
    return deco


async def step(m: Message, state: FSMContext, kind: str, prompt: str, **data):
    await state.update_data(kind=kind, **data)
    await m.reply(prompt + "\n\n<i>Отмена — напиши «отмена»</i>")


async def ask(target, state: FSMContext, kind: str, prompt: str, **data):
    await state.set_state(Flow.input)
    await state.set_data({"kind": kind, **data})
    msg = target.message if isinstance(target, CallbackQuery) else target
    await msg.answer(prompt + "\n\n<i>Отмена — напиши «отмена»</i>") if isinstance(target, CallbackQuery) \
        else await msg.reply(prompt + "\n\n<i>Отмена — напиши «отмена»</i>")
    if isinstance(target, CallbackQuery):
        await ans(target)


@dp.message(Flow.input, F.text, ~F.text.startswith("/"))
async def flow_input(message: Message, state: FSMContext):
    d = await state.get_data()
    txt = message.text.strip()
    if txt.lower() in ("отмена", "cancel", "назад"):
        await state.clear()
        await message.reply("❌ Отменено.")
        return
    fn = FLOWS.get(d.get("kind"))
    if not fn:
        await state.clear()
        return
    await fn(message, state, d, txt)


# ============================ MIDDLEWARE ============================
PROTECTED = {
    "куб", "кубик", "рулетка", "рул", "фортуна", "кф", "солнце", "игры", "профиль", "баскет", "мины", "дартс",
    "дс", "очко", "банк", "барабан", "краш", "пирамида", "майнер", "хило", "маркет", "кн", "башня", "арена",
    "охота", "спин", "футбол", "склад", "ивенты", "санте", "обмен", "чек", "дать", "нк", "перевод", "антилудо",
    "ежедневный", "бонус", "казна", "рекл", "донат", "помочь", "инвентарь", "antiludo",
    "игра", "сыграть", "зимняя", "зимние", "эмодзи", "смайл", "лабиринт", "лаб", "нг",
}
_sub_cache: Dict[int, float] = {}


async def missing_subs(uid: int) -> List[str]:
    if time.time() - _sub_cache.get(uid, 0) < 120:
        return []
    miss = []
    for chat in (REQUIRED_CHANNEL, REQUIRED_CHAT):
        if not chat:
            continue
        try:
            mem = await bot.get_chat_member(chat_id=chat, user_id=uid)
            if mem.status not in ("member", "administrator", "creator"):
                miss.append(chat)
        except Exception as e:  # бот не админ в канале и т.п. — не блокируем людей
            log.debug("sub check %s: %s", chat, e)
    if not miss:
        _sub_cache[uid] = time.time()
    return miss


def sub_kb(miss: List[str]) -> InlineKeyboardMarkup:
    rows = [[btn(f"Подписаться: {c}", url=f"https://t.me/{c.lstrip('@')}")] for c in miss]
    rows.append([btn("✅ Проверить подписку", "check_sub")])
    return kb(*rows)


class Guard(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tu = event.from_user
        if tu is None or tu.is_bot:
            return
        ensure_user(tu)
        is_cb = isinstance(event, CallbackQuery)
        if is_cb:
            st = data.get("state")
            if st is not None and event.data != "noop":
                try:
                    if await st.get_state():
                        await st.clear()
                except Exception:
                    pass
        if is_admin(tu.id):
            return await handler(event, data)
        u = get_user(tu.id)
        t = now()
        word = "" if is_cb else first_word(event.text)
        cmdlike = (not is_cb) and (word in PROTECTED or (event.text or "").startswith("/"))
        for col, label in (("banned_until", "забанены"), ("muted_until", "замучены")):
            if u[col] > t:
                until = "навсегда" if u[col] >= 9_999_999_999 else "до " + datetime.fromtimestamp(u[col], MSK).strftime("%d.%m.%Y %H:%M")
                reason = u["ban_reason"] if col == "banned_until" else u["mute_reason"]
                txt = f"🔒 Вы {label} {until}.\nПричина: {esc(reason or '—')}"
                if is_cb:
                    await ans(event, txt, True)
                elif event.chat.type == "private" or cmdlike:
                    await event.reply(txt)
                return
        if REQUIRE_SUB:
            need = (is_cb and event.data not in ("check_sub", "noop")) or (not is_cb and word in PROTECTED)
            if need:
                miss = await missing_subs(tu.id)
                if miss:
                    txt = f"{E('lock')} <b>Для использования бота нужна подписка:</b>\n" + "\n".join(f"❌ {c}" for c in miss)
                    if is_cb:
                        await ans(event, "Сначала подпишись на канал и чат", True)
                        await event.message.answer(txt, reply_markup=sub_kb(miss))
                    else:
                        await event.reply(txt, reply_markup=sub_kb(miss))
                    return
        return await handler(event, data)


dp.message.outer_middleware(Guard())
dp.callback_query.outer_middleware(Guard())


@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery):
    _sub_cache.pop(cb.from_user.id, None)
    miss = await missing_subs(cb.from_user.id)
    if miss:
        await ans(cb, "Подписка не найдена", True)
        return
    await ans(cb, "Подписка подтверждена!")
    await cb.message.answer(f"{E('check')} <b>Подписка подтверждена!</b> Напиши /start или <code>меню</code>.")


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await ans(cb)


# ============================ ИГРЫ: общие функции ============================
_cd: Dict[int, float] = {}


def left_time(ts: int) -> str:
    return dur(ts - now())


async def gate(m: Message, cd: float = 1.5) -> Optional[Dict[str, Any]]:
    u = get_user(m.from_user.id)
    if u["antiludo_until"] > now():
        await m.reply(f"{E('lock')} 🚫 На тебя наложено <b>антилудо</b>. Игры через {left_time(u['antiludo_until'])}.")
        return None
    t = time.monotonic()
    if t - _cd.get(u["user_id"], 0) < cd:
        await m.reply("⏳ Не так быстро!")
        return None
    _cd[u["user_id"]] = t
    return u


async def take_bet(m: Message, u: Dict[str, Any], raw: str, count: int = 1) -> int:
    bet = parse_amount(raw, u["balance_coin"])
    if bet <= 0:
        await m.reply(f"{E('lock')} Неверная ставка. Примеры: <code>100</code>, <code>5к</code>, <code>2кк</code>, <code>все</code>")
        return 0
    if bet * count > MAX_BET:
        await m.reply(f"{E('lock')} Максимальная ставка — <b>{fmt(MAX_BET)}</b> RCOIN.")
        return 0
    if not spend(u["user_id"], bet * count):
        bal = get_user(u["user_id"])["balance_coin"]
        await m.reply(f"{E('lock')} <b>Недостаточно RCOIN!</b>\n💰 Баланс: {fmt(bal)}\n🎯 Нужно: {fmt(bet * count)}")
        return 0
    return bet


def result_text(u, ekey: str, title: str, bet: int, pay: int, lines=(), bal: int = 0) -> str:
    if pay > bet:
        head = f"{E(ekey)} <b>{title} — ПОБЕДА!</b>"
        res = f"✅ Выигрыш: <b>+{fmt(pay - bet)}</b> RCOIN (выплата {fmt(pay)})"
    elif pay == bet:
        head = f"{E(ekey)} <b>{title} — ВОЗВРАТ</b>"
        res = "🤝 Ставка возвращена"
    else:
        head = f"{E(ekey)} <b>{title} — ПРОИГРЫШ</b>"
        res = f"❌ Проигрыш: <b>-{fmt(bet - pay)}</b> RCOIN" + (f" (возврат {fmt(pay)})" if pay else "")
    return box(head, f"👤 {uname(u)}", *lines, f"💸 Ставка: {fmt(bet)}", res, f"📊 Баланс: {fmt(bal)} RCOIN")


async def play_dice(m: Message, emoji: str, delay: float = 3.6) -> int:
    d = await m.reply_dice(emoji=emoji)
    await asyncio.sleep(delay)
    return d.dice.value


def usage(text: str) -> str:
    return f"{E('lock')} <b>Неправильный формат!</b>\n\n{text}"


# ============================ КУБИК ============================
@dp.message(P("куб", "кубик"))
async def g_dice(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    ok = {"1", "2", "3", "4", "5", "6", "чет", "нечет", "мал", "бол"}
    ch = list(dict.fromkeys(p[2:])) if len(p) >= 3 else []
    if not ch or len(ch) > 6 or any(c not in ok for c in ch):
        await m.reply(usage("• <code>куб 100 3</code> — число (x5.5)\n• <code>куб 100 чет</code> / <code>нечет</code> / <code>мал</code> / <code>бол</code> — x1.9\n• несколько: <code>куб 100 1 2 чет</code>"))
        return
    bet = await take_bet(m, u, p[1], len(ch))
    if not bet:
        return
    roll = await play_dice(m, "🎲")
    pay = 0
    for c in ch:
        if c.isdigit() and int(c) == roll:
            pay += int(bet * 5.5)
        elif (c == "чет" and roll % 2 == 0) or (c == "нечет" and roll % 2 == 1) or \
                (c == "мал" and roll <= 3) or (c == "бол" and roll >= 4):
            pay += int(bet * 1.9)
    total = bet * len(ch)
    bal = settle(u["user_id"], "dice", total, pay, f"{ch} roll={roll}")
    await m.reply(result_text(u, "dice", "Кубик", total, pay, [f"🎲 Выпало: <b>{roll}</b>", f"🎯 Выбор: {', '.join(ch)}"], bal))


# ============================ РУЛЕТКА ============================
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


@dp.message(P("рулетка", "рул"))
async def g_roulette(m: Message):
    u = await gate(m, 3)
    if not u:
        return
    p = m.text.lower().split()
    valid = {"к", "ч", "з", "чет", "нечет", "б", "м"}
    if len(p) < 3 or not (p[2] in valid or (p[2].isdigit() and 0 <= int(p[2]) <= 36)):
        await m.reply(usage("• <code>рулетка 100к к</code> — красное (x2)\n• <code>ч</code> чёрное, <code>чет</code>, <code>нечет</code> — x2\n• <code>б</code> 1-18, <code>м</code> 19-36 — x2\n• <code>з</code> зеро или число 0-36 — x36"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    msg = await m.reply("🎰 Рулетка крутится...")
    await asyncio.sleep(2.5)
    n = random.randint(0, 36)
    c = p[2]
    mult = 0
    if (c == "к" and n in RED) or (c == "ч" and n != 0 and n not in RED) or (c == "чет" and n != 0 and n % 2 == 0) \
            or (c == "нечет" and n % 2 == 1) or (c == "б" and 1 <= n <= 18) or (c == "м" and 19 <= n <= 36):
        mult = 2
    elif (c == "з" and n == 0) or (c.isdigit() and int(c) == n):
        mult = 36
    pay = bet * mult
    bal = settle(u["user_id"], "roulette", bet, pay, f"{c} -> {n}")
    col = "🟢" if n == 0 else ("🔴" if n in RED else "⚫")
    await msg.edit_text(result_text(u, "roulette", "Рулетка", bet, pay, [f"🎯 Ставка на: <b>{c}</b>", f"🎰 Выпало: <b>{n}</b> {col}"], bal))


# ============================ ФОРТУНА ============================
@dp.message(P("фортуна", "кф"))
async def g_fortune(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>фортуна 100</code> или <code>кф все</code>\nМножители: x0 (36%), x0.5 (22%), x1 (20%), x2 (16%), x5 (6%)"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    mult = random.choices([0, 0.5, 1, 2, 5], weights=[36, 22, 20, 16, 6])[0]
    pay = int(bet * mult)
    bal = settle(u["user_id"], "fortune", bet, pay, f"x{mult}")
    await m.reply(result_text(u, "fortune", "Колесо фортуны", bet, pay, [f"📈 Множитель: <b>x{mult}</b>"], bal))


# ============================ БАСКЕТ / ДАРТС / ФУТБОЛ ============================
@dp.message(P("баскет"))
async def g_basket(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 3 or p[2] not in ("п", "м", "чп", "з"):
        await m.reply(usage("• <code>баскет 100 м</code> — мимо (x2.2)\n• <code>п</code> — попадание, <code>чп</code> — чистое, <code>з</code> — застрял (x4.5)"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    roll = await play_dice(m, "🏀", 4.2)
    code = {1: "м", 2: "м", 3: "з", 4: "п", 5: "чп"}.get(roll, "м")
    mult = {"м": 2.2, "з": 4.5, "п": 4.5, "чп": 4.5}[code]
    pay = int(bet * mult) if p[2] == code else 0
    bal = settle(u["user_id"], "basket", bet, pay, f"{p[2]} -> {code}")
    names = {"м": "Мимо ❌", "з": "Застрял 💫", "п": "Попадание 🎯", "чп": "Чистое попадание 🏆"}
    await m.reply(result_text(u, "basket", "Баскет", bet, pay, [f"🏀 Результат: <b>{names[code]}</b>"], bal))


@dp.message(P("дартс", "дс"))
async def g_darts(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 3 or p[2] not in ("к", "б", "ц", "м"):
        await m.reply(usage("• <code>дартс 100 к</code> — красное (x2.7)\n• <code>б</code> — белое (x2.7)\n• <code>ц</code> — центр (x5.5)\n• <code>м</code> — мимо (x5.5)"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    roll = await play_dice(m, "🎯", 3.4)
    code = {1: "м", 2: "к", 3: "б", 4: "к", 5: "б", 6: "ц"}[roll]
    mult = 5.5 if code in ("м", "ц") else 2.7
    pay = int(bet * mult) if p[2] == code else 0
    bal = settle(u["user_id"], "darts", bet, pay, f"{p[2]} -> {code}")
    names = {"м": "Мимо ❌", "к": "Красное 🔴", "б": "Белое ⚪", "ц": "Центр 🎯"}
    await m.reply(result_text(u, "darts", "Дартс", bet, pay, [f"🎯 Результат: <b>{names[code]}</b>"], bal))


@dp.message(P("футбол"))
async def g_football(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 3 or p[2] not in ("г", "м"):
        await m.reply(usage("• <code>футбол 100 г</code> — гол (x1.5)\n• <code>футбол 100 м</code> — мимо (x2.2)"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    roll = await play_dice(m, "⚽", 4.2)
    code = "г" if roll >= 3 else "м"
    mult = 1.5 if p[2] == "г" else 2.2
    pay = int(bet * mult) if p[2] == code else 0
    bal = settle(u["user_id"], "football", bet, pay, f"{p[2]} -> {code}")
    await m.reply(result_text(u, "football", "Футбол", bet, pay, [f"⚽ Результат: <b>{'ГОЛ!' if code == 'г' else 'Мимо ❌'}</b>"], bal))


# ============================ СПИН (слот-машина) ============================
@dp.message(P("спин"))
async def g_spin(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>спин 100</code>\n777 — x20, три одинаковых — x5, два одинаковых — x0.7"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    roll = await play_dice(m, "🎰", 2.8)
    v = roll - 1
    a, b, c = v % 4, (v // 4) % 4, v // 16
    sym = ["BAR", "🍇", "🍋", "7️⃣"]
    if a == b == c:
        mult = 20 if a == 3 else 5
        txt = "🎉 ТРИ ОДИНАКОВЫХ!"
    elif a == b or b == c or a == c:
        mult, txt = 0.7, "😊 Два одинаковых"
    else:
        mult, txt = 0, "💀 Ничего не совпало"
    pay = int(bet * mult)
    bal = settle(u["user_id"], "spin", bet, pay, f"{a}{b}{c}")
    await m.reply(result_text(u, "spin", "Спин", bet, pay, [f"🎰 {sym[a]} | {sym[b]} | {sym[c]}", txt], bal))


# ============================ КРАШ ============================
def crash_point() -> float:
    r = random.random()
    return max(1.0, min(1000.0, math.floor(95 / (1 - r)) / 100))


@dp.message(P("краш"))
async def g_crash(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("• <code>краш 100 2.5</code> — ставка 100, забрать на x2.5\n• <code>краш 100</code> — цель x2\nЦель от 1.01 до 100"))
        return
    target = 2.0
    if len(p) >= 3:
        try:
            target = float(p[2].replace(",", "."))
        except ValueError:
            await m.reply(usage("Множитель — число, например 2.5"))
            return
    if not 1.01 <= target <= 100:
        await m.reply(usage("Цель от 1.01 до 100"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    cp = crash_point()
    pay = int(bet * target) if cp >= target else 0
    bal = settle(u["user_id"], "crash", bet, pay, f"t={target} cp={cp}")
    line = f"🚀 Ракета долетела до <b>x{cp:.2f}</b>" if pay else f"💥 Ракета крашнулась на <b>x{cp:.2f}</b>"
    await m.reply(result_text(u, "crash", "Краш", bet, pay, [f"🎯 Твоя цель: x{target:.2f}", line], bal))


# ============================ ОХОТА ============================
@dp.message(P("охота"))
async def g_hunt(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>охота 100</code> — зверь убежит или станет добычей (до x100)"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    r = random.random() * 100
    if r < 0.5:
        mult, animal = 100, "🐻 Медведь"
    elif r < 1.5:
        mult, animal = random.choice([10, 12, 15]), "🐺 Волк"
    elif r < 4:
        mult, animal = random.choice([5, 6, 8]), "🦊 Лиса"
    elif r < 8:
        mult, animal = random.choice([3, 4]), "🐰 Заяц"
    else:
        mult, animal = 0, "💨 Зверь убежал"
    pay = bet * mult
    bal = settle(u["user_id"], "hunt", bet, pay, animal)
    await m.reply(result_text(u, "hunt", "Охота", bet, pay, [f"🐾 {animal}" + (f" (x{mult})" if mult else "")], bal))


# ============================ СОЛНЦЕ ============================
SUN_CELLS = [0, 0, 0, 0, 0, 0.5, 1, 2, 5]


@dp.message(P("солнце"))
async def g_sun(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>солнце 100</code> — выбери одну из 9 клеток. Множители: x0, x0.5, x1, x2, x5"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    cells = SUN_CELLS[:]
    random.shuffle(cells)
    sid = sess_new(u["user_id"], "sun", bet, {"cells": cells})
    rows = [[btn("☀️", f"sun:{sid}:{r * 3 + c}", "sun") for c in range(3)] for r in range(3)]
    await m.reply(f"{E('sun')} <b>СОЛНЦЕ</b>\n👤 {uname(u)}\n💸 Ставка: {fmt(bet)}\nВыбери клетку:", reply_markup=kb(*rows))


@dp.callback_query(F.data.startswith("sun:"))
async def cb_sun(cb: CallbackQuery):
    _, sid, i = cb.data.split(":")
    s = sess_get(int(sid))
    if not s or s["user_id"] != cb.from_user.id:
        return await ans(cb, "Это не твоя игра", True)
    if not sess_close(s["id"]):
        return await ans(cb, "Игра уже завершена", True)
    cells = s["state"]["cells"]
    mult = cells[int(i)]
    pay = int(s["bet"] * mult)
    u = get_user(cb.from_user.id)
    bal = settle(u["user_id"], "sun", s["bet"], pay, f"x{mult}")
    grid = "\n".join(" ".join(f"x{cells[r * 3 + c]}" for c in range(3)) for r in range(3))
    await safe_edit(cb, result_text(u, "sun", "Солнце", s["bet"], pay, [f"☀️ Тебе выпало: <b>x{mult}</b>", f"<code>{grid}</code>"], bal))
    await ans(cb)


# ============================ МИНЫ ============================
def mines_mult(m: int, k: int) -> float:
    if k <= 0:
        return 1.0
    pr = 1.0
    for i in range(k):
        pr *= (25 - i) / (25 - m - i)
    return max(1.0, math.floor(0.97 * pr * 100) / 100)


def mines_start(uid: int, bet: int, m: int) -> int:
    mines = random.sample(range(25), m)
    return sess_new(uid, "mines", bet, {"m": m, "mines": mines, "open": []})


def mines_finish(s: dict, status: str) -> dict:
    """Закрывает игру. Возвращает {'payout','balance'}."""
    st = s["state"]
    mult = mines_mult(st["m"], len(st["open"])) if status == "won" else 0
    pay = int(s["bet"] * mult)
    bal = settle(s["user_id"], "mines", s["bet"], pay, f"m={st['m']} open={len(st['open'])}")
    return {"payout": pay, "balance": bal, "mult": mult}


def mines_open(sid: int, uid: int, i: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "mines":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    st = s["state"]
    if not 0 <= i < 25 or i in st["open"]:
        return {"err": "Клетка уже открыта"}
    if i in st["mines"]:
        if not sess_close(sid, "lost"):
            return {"err": "Игра уже завершена"}
        f = mines_finish(s, "lost")
        return {"status": "lost", "state": st, "bet": s["bet"], **f}
    st["open"].append(i)
    sess_save(sid, st)
    if len(st["open"]) >= 25 - st["m"]:
        if not sess_close(sid, "won"):
            return {"err": "Игра уже завершена"}
        f = mines_finish(s, "won")
        return {"status": "won", "state": st, "bet": s["bet"], **f}
    return {"status": "safe", "state": st, "bet": s["bet"], "mult": mines_mult(st["m"], len(st["open"]))}


def mines_cash(sid: int, uid: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "mines":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    if not s["state"]["open"]:
        return {"err": "Сначала открой хотя бы одну клетку"}
    if not sess_close(sid, "won"):
        return {"err": "Игра уже завершена"}
    f = mines_finish(s, "won")
    return {"status": "won", "state": s["state"], "bet": s["bet"], **f}


def mines_kb(sid: int, st: dict, over: bool = False) -> InlineKeyboardMarkup:
    opened, mines = set(st["open"]), set(st["mines"])
    safe_icon = "snowflake" if st.get("ev") else "diamond"
    rows = []
    for r in range(5):
        row = []
        for c in range(5):
            i = r * 5 + c
            if over:
                icon = "mines" if i in mines else (safe_icon if i in opened else "question")
                row.append(btn("\u2800", "noop", icon=icon))
            elif i in opened:
                row.append(btn("\u2800", "noop", icon=safe_icon))
            else:
                row.append(qbtn(f"mn:o:{sid}:{i}"))
        rows.append(row)
    if not over:
        if opened:
            rows.append([btn(f"Забрать выигрыш ×{mines_mult(st['m'], len(opened)):.2f}", f"mn:c:{sid}", icon="win", style="primary")])
        else:
            rows.append([btn("Отменить игру", f"mn:x:{sid}", icon="door", style="danger")])
    return kb(*rows)


def mines_text(u, bet: int, st: dict, extra: str = "") -> str:
    k = len(st["open"])
    mult = mines_mult(st["m"], k)
    return (f"{E('mines')} <b>МИНЫ</b>\n👤 {uname(u)}\n💸 Ставка: {fmt(bet)} RCOIN\n💣 Мин: {st['m']}\n"
            f"💎 Открыто: {k}\n📈 Множитель: <b>x{mult:.2f}</b>\n💰 Сейчас можно забрать: <b>{fmt(int(bet * mult))}</b>\n" + extra)


@dp.message(P("мины"))
async def g_mines(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("• <code>мины 100 3</code> — ставка 100, 3 мины (1-10)\n• <code>мины все</code> — по умолчанию 3 мины"))
        return
    cnt = 3
    if len(p) >= 3:
        if not p[2].isdigit() or not 1 <= int(p[2]) <= 10:
            await m.reply(usage("Количество мин: от 1 до 10"))
            return
        cnt = int(p[2])
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    sid = mines_start(u["user_id"], bet, cnt)
    s = sess_get(sid)
    await m.reply(mines_text(u, bet, s["state"], "\n<i>Выбери клетку</i>"), reply_markup=mines_kb(sid, s["state"]))


@dp.callback_query(F.data.startswith("mn:"))
async def cb_mines(cb: CallbackQuery):
    _, act, sid, *rest = cb.data.split(":")
    sid = int(sid)
    uid = cb.from_user.id
    u = get_user(uid)
    if act == "x":
        s = sess_get(sid)
        if not s or s["user_id"] != uid:
            return await ans(cb, "Это не твоя игра", True)
        if s["state"]["open"]:
            return await ans(cb, "Уже начатую игру отменить нельзя — забери выигрыш", True)
        if not sess_close(sid, "cancel"):
            return await ans(cb, "Игра уже завершена", True)
        add_coin(uid, s["bet"])
        await safe_edit(cb, f"↩️ Игра отменена, ставка {fmt(s['bet'])} RCOIN возвращена.")
        return await ans(cb)
    r = mines_open(sid, uid, int(rest[0])) if act == "o" else mines_cash(sid, uid)
    if "err" in r:
        return await ans(cb, r["err"], True)
    st, bet = r["state"], r["bet"]
    if r["status"] == "safe":
        await safe_edit(cb, mines_text(u, bet, st, "\n<i>Выбери следующую клетку или забери выигрыш</i>"), mines_kb(sid, st))
        return await ans(cb)
    if r["status"] == "lost":
        txt = box(f"{E('mines')} <b>МИНЫ — ВЗРЫВ! 💥</b>", f"👤 {uname(u)}", f"💸 Ставка: {fmt(bet)} RCOIN",
                  f"❌ Проигрыш: -{fmt(bet)}", f"📊 Баланс: {fmt(r['balance'])} RCOIN")
    else:
        txt = box(f"{E('win')} <b>МИНЫ — ВЫИГРЫШ!</b>", f"👤 {uname(u)}", f"💸 Ставка: {fmt(bet)} RCOIN",
                  f"📈 Множитель: x{r['mult']:.2f}", f"✅ Получено: <b>+{fmt(r['payout'])}</b> RCOIN",
                  f"📊 Баланс: {fmt(r['balance'])} RCOIN")
    await safe_edit(cb, txt, mines_kb(sid, st, over=True))
    await ans(cb, "💥 Мина!" if r["status"] == "lost" else "💰 Выигрыш зачислен", r["status"] == "lost")


# ============================ БАШНЯ / ПИРАМИДА ============================
def climb_mult(cols: int, b: int, k: int) -> float:
    if k <= 0:
        return 1.0
    return max(1.0, round(0.95 * (cols / (cols - b)) ** k, 2))


def climb_start(uid: int, bet: int, kind: str, b: int = 1) -> int:
    if kind == "tower":
        cols, levels = 5, 9
    elif kind == "gems":
        cols, levels = 3, 7
    else:
        cols, levels = 4, 8
    bombs = [random.sample(range(cols), b) for _ in range(levels)]
    return sess_new(uid, "climb", bet, {"kind": kind, "cols": cols, "levels": levels, "b": b, "bombs": bombs, "picks": []})


def climb_finish(s: dict, won: bool) -> dict:
    st = s["state"]
    mult = climb_mult(st["cols"], st["b"], len(st["picks"])) if won else 0
    pay = int(s["bet"] * mult)
    bal = settle(s["user_id"], st["kind"], s["bet"], pay, f"lvl={len(st['picks'])}")
    return {"payout": pay, "balance": bal, "mult": mult}


def climb_pick(sid: int, uid: int, col: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "climb":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    st = s["state"]
    lvl = len(st["picks"])
    if not 0 <= col < st["cols"]:
        return {"err": "Некорректная клетка"}
    if col in st["bombs"][lvl]:
        if not sess_close(sid, "lost"):
            return {"err": "Игра уже завершена"}
        st["picks"].append(col)
        s["state"] = st
        return {"status": "lost", "state": st, "bet": s["bet"], **climb_finish({**s, "state": {**st, "picks": st["picks"][:-1]}}, False)}
    st["picks"].append(col)
    sess_save(sid, st)
    if len(st["picks"]) >= st["levels"]:
        if not sess_close(sid, "won"):
            return {"err": "Игра уже завершена"}
        return {"status": "won", "state": st, "bet": s["bet"], **climb_finish(s | {"state": st}, True)}
    return {"status": "safe", "state": st, "bet": s["bet"]}


def climb_cash(sid: int, uid: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "climb":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    if not s["state"]["picks"]:
        return {"err": "Сначала пройди хотя бы один уровень"}
    if not sess_close(sid, "won"):
        return {"err": "Игра уже завершена"}
    return {"status": "won", "state": s["state"], "bet": s["bet"], **climb_finish(s, True)}


def climb_kb(sid: int, st: dict, over: bool = False) -> InlineKeyboardMarkup:
    picks, cols, levels = st["picks"], st["cols"], st["levels"]
    safe_icon = "snowflake" if st.get("ev") else "diamond"
    lvl = len(picks)
    rows = []
    if st["kind"] == "tower":
        # текущий ряд сверху, пройденные ниже (новые растут вверх, как в оригинале)
        if not over and lvl < levels:
            rows.append([qbtn(f"cl:p:{sid}:{c}") for c in range(cols)])
        for r in range(len(picks) - 1, -1, -1):
            row = []
            for c in range(cols):
                bomb = c in st["bombs"][r]
                if c == picks[r]:
                    icon = "crash" if bomb else safe_icon
                elif over and bomb:
                    icon = "mines"
                else:
                    icon = "question"
                row.append(btn("\u2800", "noop", icon=icon))
            rows.append(row)
    elif not over:
        ds = [btn(str(c + 1), f"cl:p:{sid}:{c}", "door", style="success") for c in range(cols)]
        rows = [ds[:2], ds[2:]]
    if not over:
        if lvl:
            rows.append([btn(f"Забрать выигрыш ×{climb_mult(cols, st['b'], lvl):.2f}", f"cl:c:{sid}", "win", style="primary")])
        else:
            rows.append([btn("Отменить игру", f"cl:x:{sid}", "door", style="danger")])
    return kb(*rows)


def climb_text(u, bet: int, st: dict, extra: str = "") -> str:
    lvl, levels, cols, b = len(st["picks"]), st["levels"], st["cols"], st["b"]
    tower = st["kind"] == "tower"
    name = "БАШНЯ" if tower else "ПИРАМИДА"
    nxt = [f"{k} • <b>x{climb_mult(cols, b, k):.2f}</b>" for k in range(lvl + 1, min(lvl + 5, levels) + 1)]
    lines = [f"{E('games' if tower else 'pyramid')} <b>{name} · {'начни игру!' if lvl == 0 else 'игра идёт'}</b>",
             f"👤 {uname(u)}", "┈┈┈┈┈┈┈┈┈┈┈┈", f"💣 Мин: {b}", f"💸 Ставка: {fmt(bet)} RCOIN"]
    if lvl:
        m = climb_mult(cols, b, lvl)
        lines += [f"💼 Пройдено: {lvl} из {levels}", f"💰 Выигрыш: x{m:.2f} / {fmt(int(bet * m))} RCOIN"]
    lines += ["", "⬆️ <b>Следующий уровень:</b>", "   ".join(nxt) or "—"]
    return "\n".join(lines) + extra


async def climb_cmd(m: Message, kind: str):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        ex = {"tower": "<code>башня 500</code> / <code>башня 500 2</code> (2 бомбы в ряду, 1-3)",
              "ladder": "<code>лесница 500</code> — 4 кнопки в ряду",
              "gems": "<code>алмазы 500</code> — 3 кнопки в ряду"}.get(kind, "<code>пирамида 500</code> — 4 двери, 1 ловушка")
        await m.reply(usage(ex))
        return
    b = 1
    if kind == "tower" and len(p) >= 3:
        if not p[2].isdigit() or not 1 <= int(p[2]) <= 3:
            await m.reply(usage("Бомб в ряду: 1-3"))
            return
        b = int(p[2])
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    sid = climb_start(u["user_id"], bet, kind, b)
    st = sess_get(sid)["state"]
    await m.reply(climb_text(u, bet, st, "\n<i>Выбери клетку</i>"), reply_markup=climb_kb(sid, st))


@dp.message(P("башня", "башн"))
async def g_tower(m: Message):
    await climb_cmd(m, "tower")


@dp.message(P("лесница", "лестница"))
async def g_ladder(m: Message):
    await climb_cmd(m, "ladder")


@dp.message(P("алмазы", "алмаз"))
async def g_gems(m: Message):
    await climb_cmd(m, "gems")


@dp.message(P("пирамида"))
async def g_pyramid(m: Message):
    await climb_cmd(m, "pyramid")


@dp.callback_query(F.data.startswith("cl:"))
async def cb_climb(cb: CallbackQuery):
    _, act, sid, *rest = cb.data.split(":")
    sid = int(sid)
    uid = cb.from_user.id
    u = get_user(uid)
    if act == "x":
        s = sess_get(sid)
        if not s or s["user_id"] != uid:
            return await ans(cb, "Это не твоя игра", True)
        if s["state"]["picks"]:
            return await ans(cb, "Начатую игру отменить нельзя", True)
        if not sess_close(sid, "cancel"):
            return await ans(cb, "Игра уже завершена", True)
        add_coin(uid, s["bet"])
        await safe_edit(cb, f"↩️ Игра отменена, ставка {fmt(s['bet'])} RCOIN возвращена.")
        return await ans(cb)
    r = climb_pick(sid, uid, int(rest[0])) if act == "p" else climb_cash(sid, uid)
    if "err" in r:
        return await ans(cb, r["err"], True)
    st, bet = r["state"], r["bet"]
    if r["status"] == "safe":
        await safe_edit(cb, climb_text(u, bet, st, "\n<i>Выбирай дальше или забери выигрыш</i>"), climb_kb(sid, st))
        return await ans(cb)
    name = "БАШНЯ" if st["kind"] == "tower" else "ПИРАМИДА"
    if r["status"] == "lost":
        txt = box(f"💥 <b>{name} — ПРОИГРЫШ</b>", f"👤 {uname(u)}", f"📊 Дошёл до уровня {len(st['picks']) - 1}",
                  f"❌ -{fmt(bet)} RCOIN", f"📊 Баланс: {fmt(r['balance'])}")
    else:
        txt = box(f"{E('win')} <b>{name} — ВЫИГРЫШ!</b>", f"👤 {uname(u)}", f"📈 Множитель: x{r['mult']:.2f}",
                  f"✅ Получено: <b>+{fmt(r['payout'])}</b> RCOIN", f"📊 Баланс: {fmt(r['balance'])}")
    await safe_edit(cb, txt, climb_kb(sid, st, over=True))
    await ans(cb, "💥 Ловушка!" if r["status"] == "lost" else "💰 Выигрыш зачислен", r["status"] == "lost")


# ============================ ОЧКО (БЛЭКДЖЕК) ============================
def bj_deck() -> List[str]:
    d = [f"{r}{s}" for s in "♠♥♦♣" for r in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]]
    random.shuffle(d)
    return d


def bj_val(hand: List[str]) -> int:
    v, aces = 0, 0
    for c in hand:
        r = c[:-1]
        if r == "A":
            aces += 1
            v += 11
        elif r in ("J", "Q", "K"):
            v += 10
        else:
            v += int(r)
    while v > 21 and aces:
        v -= 10
        aces -= 1
    return v


def bj_text(u, bet, st, final: str = "") -> str:
    d = " ".join(st["d"]) + f" = {bj_val(st['d'])}" if final else f"{st['d'][0]} ❔"
    return (f"{E('blackjack')} <b>ОЧКО</b>\n👤 {uname(u)}\n🎴 Твои: {' '.join(st['p'])} = <b>{bj_val(st['p'])}</b>\n"
            f"🎴 Дилер: {d}\n💸 Ставка: {fmt(bet)}\n{final}")


@dp.message(P("очко"))
async def g_bj(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>очко 100</code> — набери 21 или больше дилера. Блэкджек x2.5"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    deck = bj_deck()
    st = {"deck": deck, "p": [deck.pop(), deck.pop()], "d": [deck.pop(), deck.pop()]}
    if bj_val(st["p"]) == 21:
        pay = bet if bj_val(st["d"]) == 21 else int(bet * 2.5)
        bal = settle(u["user_id"], "blackjack", bet, pay, "blackjack")
        await m.reply(result_text(u, "blackjack", "Очко — БЛЭКДЖЕК", bet, pay, [f"🎴 {' '.join(st['p'])}", f"🎴 Дилер: {' '.join(st['d'])}"], bal))
        return
    sid = sess_new(u["user_id"], "bj", bet, st)
    await m.reply(bj_text(u, bet, st), reply_markup=kb([btn("➕ Ещё", f"bj:h:{sid}", "blackjack"), btn("✋ Стоп", f"bj:s:{sid}", "blackjack")]))


@dp.callback_query(F.data.startswith("bj:"))
async def cb_bj(cb: CallbackQuery):
    _, act, sid = cb.data.split(":")
    s = sess_get(int(sid))
    if not s or s["user_id"] != cb.from_user.id:
        return await ans(cb, "Это не твоя игра", True)
    if s["status"] != "active":
        return await ans(cb, "Игра уже завершена", True)
    u, st, bet = get_user(cb.from_user.id), s["state"], s["bet"]
    if act == "h":
        st["p"].append(st["deck"].pop())
        pv = bj_val(st["p"])
        if pv > 21:
            if not sess_close(s["id"], "lost"):
                return await ans(cb)
            bal = settle(u["user_id"], "blackjack", bet, 0, "bust")
            await safe_edit(cb, result_text(u, "blackjack", "Очко — ПЕРЕБОР", bet, 0, [f"🎴 {' '.join(st['p'])} = {pv}"], bal))
            return await ans(cb)
        if pv < 21:
            sess_save(s["id"], st)
            await safe_edit(cb, bj_text(u, bet, st), kb([btn("➕ Ещё", f"bj:h:{s['id']}", "blackjack"), btn("✋ Стоп", f"bj:s:{s['id']}", "blackjack")]))
            return await ans(cb)
    if not sess_close(s["id"], "done"):
        return await ans(cb)
    while bj_val(st["d"]) < 17:
        st["d"].append(st["deck"].pop())
    pv, dv = bj_val(st["p"]), bj_val(st["d"])
    pay = bet * 2 if (dv > 21 or pv > dv) else (bet if pv == dv else 0)
    bal = settle(u["user_id"], "blackjack", bet, pay, f"{pv}:{dv}")
    await safe_edit(cb, result_text(u, "blackjack", "Очко", bet, pay, [f"🎴 Ты: {' '.join(st['p'])} = {pv}", f"🎴 Дилер: {' '.join(st['d'])} = {dv}"], bal))
    await ans(cb)


# ============================ ХИ-ЛО ============================
CARD_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}


def cname(v: int) -> str:
    return CARD_NAMES.get(v, str(v))


def hl_probs(st: dict) -> Tuple[float, float]:
    n = len(st["deck"]) or 1
    return sum(1 for c in st["deck"] if c > st["cur"]) / n, sum(1 for c in st["deck"] if c < st["cur"]) / n


def hl_kb(sid: int, st: dict) -> InlineKeyboardMarkup:
    ph, pl = hl_probs(st)
    row = []
    if ph > 0:
        row.append(btn(f"⬆️ Выше ({ph * 100:.0f}%)", f"hl:h:{sid}", "hi_lo"))
    if pl > 0:
        row.append(btn(f"⬇️ Ниже ({pl * 100:.0f}%)", f"hl:l:{sid}", "hi_lo"))
    rows = [row]
    if st["round"] > 0:
        rows.append([btn(f"💰 Забрать ×{st['mult']:.2f}", f"hl:c:{sid}")])
    return kb(*rows)


def hl_text(u, bet, st) -> str:
    return (f"{E('hi_lo')} <b>ХИ-ЛО</b>\n👤 {uname(u)}\n💸 Ставка: {fmt(bet)}\n🎴 Карта: <b>{cname(st['cur'])}</b>\n"
            f"📈 Множитель: x{st['mult']:.2f} ({fmt(int(bet * st['mult']))})\n🔄 Раунд: {st['round']}/8\n<i>Ничья — проигрыш. Следующая карта выше или ниже?</i>")


@dp.message(P("хило"))
async def g_hilo(m: Message):
    u = await gate(m)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>хило 100</code> — угадывай выше/ниже, множитель растёт по шансам"))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    deck = [v for v in range(2, 15) for _ in range(4)]
    random.shuffle(deck)
    st = {"deck": deck, "cur": deck.pop(), "mult": 1.0, "round": 0}
    sid = sess_new(u["user_id"], "hilo", bet, st)
    await m.reply(hl_text(u, bet, st), reply_markup=hl_kb(sid, st))


@dp.callback_query(F.data.startswith("hl:"))
async def cb_hilo(cb: CallbackQuery):
    _, act, sid = cb.data.split(":")
    s = sess_get(int(sid))
    if not s or s["user_id"] != cb.from_user.id:
        return await ans(cb, "Это не твоя игра", True)
    if s["status"] != "active":
        return await ans(cb, "Игра уже завершена", True)
    u, st, bet = get_user(cb.from_user.id), s["state"], s["bet"]

    async def finish(pay: int, title: str, lines):
        if not sess_close(s["id"]):
            return
        bal = settle(u["user_id"], "hilo", bet, pay, f"r={st['round']}")
        await safe_edit(cb, result_text(u, "hi_lo", title, bet, pay, lines, bal))

    if act == "c":
        if st["round"] == 0:
            return await ans(cb, "Сначала угадай хотя бы раз", True)
        await finish(int(bet * st["mult"]), "Хи-Ло", [f"📈 Множитель: x{st['mult']:.2f}"])
        return await ans(cb, "💰 Выигрыш зачислен")
    ph, pl = hl_probs(st)
    pr = ph if act == "h" else pl
    if pr <= 0:
        return await ans(cb, "Так выбрать нельзя", True)
    old = st["cur"]
    nxt = st["deck"].pop()
    ok = nxt > old if act == "h" else nxt < old
    if not ok:
        await finish(0, "Хи-Ло", [f"🎴 Было {cname(old)} → стало <b>{cname(nxt)}</b>"])
        return await ans(cb, "❌ Не угадал")
    st["mult"] = round(st["mult"] * max(1.02, 0.95 / pr), 2)
    st["cur"], st["round"] = nxt, st["round"] + 1
    if st["round"] >= 8:
        await finish(int(bet * st["mult"]), "Хи-Ло — МАКСИМУМ", [f"📈 Множитель: x{st['mult']:.2f}"])
        return await ans(cb, "🏆 Максимум!")
    sess_save(s["id"], st)
    await safe_edit(cb, hl_text(u, bet, st), hl_kb(s["id"], st))
    await ans(cb, "✅ Угадал!")


# ============================ КРЕСТИКИ-НОЛИКИ ============================
TT_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def tt_kb(sid: int, board: str, over: bool = False) -> InlineKeyboardMarkup:
    sym = {"-": "question", "X": "ttt", "O": "star"}
    rows = [[btn("\u2800",
                 "noop" if over or board[r * 3 + c] != "-" else f"tt:m:{sid}:{r * 3 + c}",
                 icon=sym[board[r * 3 + c]]) for c in range(3)] for r in range(3)]
    if not over:
        rows.append([btn("Сдаться", f"tt:q:{sid}", icon="door", style="danger")])
    return kb(*rows)


def tt_text(st: dict, bet: int, extra: str = "") -> str:
    turn = st["names"][str(st["turn"])]
    return (f"{E('ttt')} <b>КРЕСТИКИ-НОЛИКИ</b>\n❌ {esc(st['names'][str(st['p1'])])}  vs  ⭕ {esc(st['names'][str(st['p2'])])}\n"
            f"💸 Ставка: {fmt(bet)} (банк {fmt(bet * 2)})\n" + (extra or f"Ходит: <b>{esc(turn)}</b>"))


@dp.message(P("кн", "крестики"))
async def g_ttt(m: Message):
    u = get_user(m.from_user.id)
    p = m.text.split()
    if len(p) < 2 or not m.reply_to_message or not m.reply_to_message.from_user:
        await m.reply(usage("Ответь на сообщение соперника: <code>кн 1000</code>"))
        return
    opp = m.reply_to_message.from_user
    if opp.is_bot or opp.id == u["user_id"]:
        await m.reply(f"{E('lock')} Выбери другого соперника.")
        return
    ensure_user(opp)
    bet = parse_amount(p[1], u["balance_coin"])
    if bet <= 0 or u["balance_coin"] < bet:
        await m.reply(f"{E('lock')} Недостаточно RCOIN для такой ставки.")
        return
    o = get_user(opp.id)
    st = {"p1": u["user_id"], "p2": opp.id, "board": "-" * 9, "turn": u["user_id"],
          "names": {str(u["user_id"]): re.sub(r"<[^>]+>", "", uname(u, False)), str(opp.id): re.sub(r"<[^>]+>", "", uname(o, False))}}
    sid = sess_new(u["user_id"], "ttt", bet, st, "pending")
    await m.reply(f"{E('ttt')} {mention(opp.id, st['names'][str(opp.id)])}, тебя вызывает <b>{esc(st['names'][str(u['user_id'])])}</b> "
                  f"в крестики-нолики на <b>{fmt(bet)}</b> RCOIN!",
                  reply_markup=kb([btn("✅ Принять", f"tt:a:{sid}"), btn("❌ Отклонить", f"tt:d:{sid}")]))


@dp.callback_query(F.data.startswith("tt:"))
async def cb_ttt(cb: CallbackQuery):
    _, act, sid, *rest = cb.data.split(":")
    s = sess_get(int(sid))
    uid = cb.from_user.id
    if not s:
        return await ans(cb, "Игра не найдена", True)
    st, bet = s["state"], s["bet"]
    if act in ("a", "d"):
        if s["status"] != "pending":
            return await ans(cb, "Вызов уже неактуален", True)
        if act == "d":
            if uid not in (st["p1"], st["p2"]):
                return await ans(cb, "Это не твой вызов", True)
            x("UPDATE sessions SET status='cancel' WHERE id=? AND status='pending'", (s["id"],))
            await safe_edit(cb, "❌ Вызов отклонён.")
            return await ans(cb)
        if uid != st["p2"]:
            return await ans(cb, "Принять может только вызванный игрок", True)
        if x("UPDATE sessions SET status='active' WHERE id=? AND status='pending'", (s["id"],))[0] != 1:
            return await ans(cb)
        if not spend(st["p1"], bet):
            x("UPDATE sessions SET status='cancel' WHERE id=?", (s["id"],))
            await safe_edit(cb, "❌ У вызвавшего не хватает RCOIN.")
            return await ans(cb)
        if not spend(st["p2"], bet):
            add_coin(st["p1"], bet)
            x("UPDATE sessions SET status='cancel' WHERE id=?", (s["id"],))
            await safe_edit(cb, "❌ У тебя не хватает RCOIN.")
            return await ans(cb)
        await safe_edit(cb, tt_text(st, bet), tt_kb(s["id"], st["board"]))
        return await ans(cb, "Игра началась!")
    if s["status"] != "active":
        return await ans(cb, "Игра завершена", True)
    if uid not in (st["p1"], st["p2"]):
        return await ans(cb, "Ты не участвуешь в игре", True)

    async def end(winner: Optional[int], extra: str):
        if not sess_close(s["id"]):
            return
        pool = bet * 2
        if winner:
            rake = pool * 5 // 100
            treasury_add(rake)
            loser = st["p2"] if winner == st["p1"] else st["p1"]
            settle(winner, "ttt", bet, pool - rake, "win")
            settle(loser, "ttt", bet, 0, "lose")
        else:
            settle(st["p1"], "ttt", bet, bet, "draw")
            settle(st["p2"], "ttt", bet, bet, "draw")
        await safe_edit(cb, tt_text(st, bet, extra), tt_kb(s["id"], st["board"], True))

    if act == "q":
        other = st["p2"] if uid == st["p1"] else st["p1"]
        await end(other, f"🏳️ {esc(st['names'][str(uid)])} сдался. Победитель: <b>{esc(st['names'][str(other)])}</b>")
        return await ans(cb)
    if uid != st["turn"]:
        return await ans(cb, "Сейчас не твой ход", True)
    i = int(rest[0])
    if st["board"][i] != "-":
        return await ans(cb, "Клетка занята", True)
    mark = "X" if uid == st["p1"] else "O"
    b = list(st["board"])
    b[i] = mark
    st["board"] = "".join(b)
    if any(st["board"][a] == st["board"][c] == st["board"][d] == mark for a, c, d in TT_LINES):
        await end(uid, f"🏆 Победил <b>{esc(st['names'][str(uid)])}</b>! Приз {fmt(bet * 2 * 95 // 100)} RCOIN")
        return await ans(cb, "Победа!")
    if "-" not in st["board"]:
        await end(None, "🤝 Ничья — ставки возвращены")
        return await ans(cb)
    st["turn"] = st["p2"] if uid == st["p1"] else st["p1"]
    sess_save(s["id"], st)
    await safe_edit(cb, tt_text(st, bet), tt_kb(s["id"], st["board"]))
    await ans(cb)


# ============================ АРЕНА В ЧАТЕ ============================
ARENAS: Dict[int, dict] = {}
_arena_seq = [0]
ARENA_MARKS = ["🟥", "🟦", "🟩", "🟨", "🟪", "🟧"]
ARENA_RING = 20


def arena_name(u: Dict[str, Any]) -> str:
    n = u.get("display_name") or u.get("username") or str(u["user_id"])
    return re.sub(r"<[^>]+>", "", str(n))[:24]


def arena_pick(bets: Dict[int, int]) -> int:
    ids = list(bets)
    return random.choices(ids, weights=[bets[i] for i in ids])[0]


def arena_text(a: dict, extra: str = "") -> str:
    pl = a["players"]
    n = len(pl)
    bank = a["bet"] * n
    lines = [f"{E('games')} <b>АРЕНА</b> · ставка <b>{fmt(a['bet'])}</b> RCOIN",
             f"{E('balance')} Банк: <b>{fmt(bank)}</b> RCOIN · игроков <b>{n}/{len(ARENA_MARKS)}</b>"]
    if pl:
        lines.append("")
        for i, (uid, name) in enumerate(pl.items()):
            lines.append(f"{ARENA_MARKS[i]} <b>{esc(name)}</b> · {fmt(a['bet'])} · {100 / n:.0f}%")
    else:
        lines.append("<i>Пока никого нет.</i>")
    lines.append("")
    return "\n".join(lines) + extra


def arena_kb(aid: int, a: dict) -> InlineKeyboardMarkup:
    rows = [[btn(f"Вступить · {fmt(a['bet'])}", f"ar:j:{aid}", icon="games")]]
    if len(a["players"]) == 1:
        rows.append([btn("Отменить арену", f"ar:x:{aid}", icon="door")])
    return kb(*rows)


@dp.message(P("арена"))
async def g_arena(m: Message):
    u = await gate(m, 3)
    if not u:
        return
    p = m.text.lower().split()
    if len(p) < 2:
        await m.reply(usage("<code>арена 500</code> — открыть арену со ставкой 500.\nКогда зайдёт 2-й игрок, через 15 секунд шарик выберет победителя. Комиссия 10%."))
        return
    bet = await take_bet(m, u, p[1])
    if not bet:
        return
    _arena_seq[0] += 1
    aid = _arena_seq[0]
    a = {"bet": bet, "players": {u["user_id"]: arena_name(u)}, "started": False, "chat": m.chat.id, "msg": None}
    ARENAS[aid] = a
    a["msg"] = await m.reply(arena_text(a, "⏳ Ждём соперника..."), reply_markup=arena_kb(aid, a))


@dp.callback_query(F.data.startswith("ar:"))
async def cb_arena(cb: CallbackQuery):
    _, act, aid = cb.data.split(":")
    a = ARENAS.get(int(aid))
    uid = cb.from_user.id
    if not a or a["started"]:
        return await ans(cb, "Арена уже недоступна", True)
    if act == "x":
        if list(a["players"])[0] != uid or len(a["players"]) != 1:
            return await ans(cb, "Отменить может только создатель", True)
        ARENAS.pop(int(aid), None)
        add_coin(uid, a["bet"])
        await safe_edit(cb, "↩️ Арена отменена, ставка возвращена.")
        return await ans(cb)
    if uid in a["players"]:
        return await ans(cb, "Ты уже в арене", True)
    if len(a["players"]) >= len(ARENA_MARKS):
        return await ans(cb, "Арена заполнена", True)
    if not spend(uid, a["bet"]):
        return await ans(cb, "Недостаточно RCOIN", True)
    a["players"][uid] = arena_name(get_user(uid))
    a["msg"] = cb.message
    await ans(cb, "Ты в арене!")
    if len(a["players"]) == 2:
        asyncio.create_task(arena_run(int(aid)))
    else:
        await safe_edit(cb, arena_text(a, "⏳ Идёт отсчёт..."), arena_kb(int(aid), a))


async def _arena_edit(a: dict, text: str, markup=None):
    try:
        await a["msg"].edit_text(text, reply_markup=markup)
    except Exception as e:
        log.debug("arena edit: %s", e)


async def arena_run(aid: int):
    a = ARENAS.get(aid)
    if not a:
        return
    try:
        for s in (15, 10, 5):
            await _arena_edit(a, arena_text(a, f"⏱ Старт через <b>{s}</b> сек..."), arena_kb(aid, a))
            await asyncio.sleep(5)
        a["started"] = True
        pl = a["players"]
        bets = {uid: a["bet"] for uid in pl}
        winner = arena_pick(bets)
        ids = list(pl)
        n, per = len(ids), ARENA_RING // len(ids)
        ring = []
        for i, uid in enumerate(ids):
            ring += [ARENA_MARKS[i]] * (per + (1 if i < ARENA_RING - per * n else 0))
        wi = ids.index(winner)
        wcells = [i for i, c in enumerate(ring) if c == ARENA_MARKS[wi]]
        target = random.choice(wcells)
        start = random.randrange(ARENA_RING)
        total = ARENA_RING * 2 + (target - start) % ARENA_RING
        for k in range(1, 8):
            pos = (start + int(total * (1 - (1 - k / 7) ** 2.2))) % ARENA_RING if k < 7 else target
            line = "".join("●" if i == pos else c for i, c in enumerate(ring))
            await _arena_edit(a, f"{E('games')} <b>АРЕНА</b> — шарик катится...\n\n{line}")
            await asyncio.sleep(0.9 + k * 0.15)
        pool = a["bet"] * n
        rake = pool // 10
        treasury_add(rake)
        prize = pool - rake
        for uid in ids:
            settle(uid, "arena", a["bet"], prize if uid == winner else 0, "arena")
        line = "".join("●" if i == target else c for i, c in enumerate(ring))
        await _arena_edit(a, box(f"{E('win')} <b>АРЕНА — РЕЗУЛЬТАТ</b>", line,
                                 f"Победитель: <b>{esc(pl[winner])}</b> {ARENA_MARKS[wi]}",
                                 f"Выигрыш: <b>+{fmt(prize - a['bet'])}</b> RCOIN (банк {fmt(pool)}, комиссия {fmt(rake)})"))
    except Exception:
        log.exception("arena")
        for uid in list(a["players"]):
            add_coin(uid, a["bet"])
    finally:
        ARENAS.pop(aid, None)


# ============================ МАЙНЕР ============================
MINER = {"mine": ("Шахта", 15_000_000, 15_000, "mine_level"),
         "business": ("Бизнес-дом", 30_000_000, 30_000, "business_level"),
         "villa": ("Вилла", 100_000_000, 100_000, "villa_level")}


def miner_row(uid: int) -> Dict[str, Any]:
    x("INSERT OR IGNORE INTO miner_data(user_id) VALUES(?)", (uid,))
    return q("SELECT * FROM miner_data WHERE user_id=?", (uid,), one=True)


def miner_income(r: dict) -> int:
    return sum(r[v[3]] * v[2] for v in MINER.values())


async def v_miner(uid: int, private: bool):
    r = miner_row(uid)
    inc = miner_income(r)
    hrs = min(24, (now() - r["last_collect"]) / 3600) if r["last_collect"] else (24 if inc else 0)
    lines = [f"{E('miner')} <b>МАЙНЕР</b>\n"]
    for key, (nm, cost, per, col) in MINER.items():
        lines.append(f"• {nm}: {r[col]}/3 ур. — {fmt(r[col] * per)}/час (след. уровень {fmt(cost)})")
    lines.append(f"\n{E('balance')} Доход: <b>{fmt(inc)}</b>/час\n📦 Накоплено: <b>{fmt(int(inc * hrs))}</b> (максимум за 24 ч)\n💰 Всего заработано: {fmt(r['total_earned'])}")
    rows = [[btn(f"Купить {v[0]}", f"mi:b:{k}", "miner")] for k, v in MINER.items()]
    rows.append([btn("Собрать доход", "mi:c", "balance")])
    rows.append([btn("Назад", "menu:games", "door")])
    return "\n".join(lines), kb(*rows)


@dp.callback_query(F.data.startswith("mi:"))
async def cb_miner(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split(":")
    r = miner_row(uid)
    if parts[1] == "b":
        nm, cost, per, col = MINER[parts[2]]
        if r[col] >= 3:
            return await ans(cb, "Максимальный уровень 3", True)
        if not spend(uid, cost):
            return await ans(cb, f"Нужно {fmt(cost)} RCOIN", True)
        if r["last_collect"] == 0:
            x("UPDATE miner_data SET last_collect=? WHERE user_id=?", (now(), uid))
        x(f"UPDATE miner_data SET {col}={col}+1 WHERE user_id=?", (uid,))
        await ans(cb, f"{nm} улучшена!")
    elif parts[1] == "c":
        inc = miner_income(r)
        if not inc:
            return await ans(cb, "Сначала купи постройку", True)
        hrs = min(24, (now() - r["last_collect"]) / 3600)
        pay = int(inc * hrs)
        if hrs < 1 or pay <= 0:
            return await ans(cb, "Сбор доступен раз в час", True)
        if x("UPDATE miner_data SET last_collect=?, total_earned=total_earned+? WHERE user_id=? AND last_collect=?",
             (now(), pay, uid, r["last_collect"]))[0] != 1:
            return await ans(cb)
        add_coin(uid, pay)
        await ans(cb, f"Собрано {fmt(pay)} RCOIN!", True)
    t, k = await v_miner(uid, True)
    await safe_edit(cb, t, k)


# ============================ ВИДЫ (меню) ============================
VIEWS: Dict[str, Any] = {}


def view(name: str):
    def deco(fn):
        VIEWS[name] = fn
        return fn
    return deco


def bonus_state(u) -> Tuple[bool, int]:
    nxt = u["bonus_last_time"] + 3600
    return (now() >= nxt, max(0, nxt - now()))


def main_kb(uid: int, private: bool) -> InlineKeyboardMarkup:
    u = get_user(uid)
    avail, _ = bonus_state(u)
    rows = []
    if avail:
        rows.append([btn(f"Получить бонус {fmt(BONUS_AMOUNT)}", "bonus:get", "donate")])
    rows += [
        [btn("Игры", "menu:games", "games"), btn("Профиль", "menu:profile", "profile")],
        [btn("Ивенты", "menu:events", "star"), btn("Склад", "menu:stash", "diamond")],
        [btn("Маркет", "menu:market", "market"), btn("Банк", "menu:bank", "bank")],
        ([btn("Ежедневный 5×5", "menu:db5", "question"), btn("Заработать", "menu:earn", "balance")]
         if daily5_available(uid) else [btn("Заработать", "menu:earn", "balance")]),
    ]
    if private and WEBAPP_URL:
        rows.append([btn("🌐 Веб-апп: арена и игры", web=WEBAPP_URL)])
    rows.append([btn("Топ", "menu:top", "star"), btn("Помощь", "menu:help", "question")])
    return kb(*rows)


@view("main")
async def v_main(uid: int, private: bool):
    u = get_user(uid)
    avail, left = bonus_state(u)
    t = (f"{E('games')} <b>RCOIN·BOT</b> — удача на твоей стороне!\n\n"
         f"{E('profile')} {uname(u, False)}\n{E('balance')} <b>{fmt(u['balance_coin'])}</b> RCOIN\n"
         f"{E('diamond')} <b>{fmt(u['balance_point'])}</b> RBP\n{E('bank')} Банк: {fmt(u['bank_balance'])} RCOIN\n\n"
         + ("🎁 <b>Бонус доступен!</b>" if avail else f"⏳ Бонус через {dur(left)}") +
         "\n\nКоманды: <code>игры</code> · <code>помощь</code> · <code>склад</code> · <code>маркет</code>")
    return t, main_kb(uid, private)


@view("games")
async def v_games(uid: int, private: bool):
    return games_page(0)


@view("profile")
async def v_profile(uid: int, private: bool):
    u = get_user(uid)
    st = q("SELECT COUNT(*) n, SUM(is_win) w FROM bet_history WHERE user_id=?", (uid,), one=True)
    n, w = st["n"] or 0, st["w"] or 0
    refs = q("SELECT COUNT(*) n FROM referrals WHERE referrer_id=?", (uid,), one=True)["n"]
    titles = " ".join(json.loads(u["titles"] or "[]")) or "—"
    uname_line = f"@{esc(u['custom_username'])}" if u["custom_username"] else "<i>не куплен</i>"
    _, pcap = nft_photo(uid, "profile")
    pe = ""
    if u.get("profile_emoji"):
        fb = esc(u.get("profile_emoji_fb") or "✨")[:8]
        pe = f'<tg-emoji emoji-id="{u["profile_emoji"]}">{fb}</tg-emoji> '
    t = (f"{pe}{E('profile')} <b>ПРОФИЛЬ</b>\n"
         f"<blockquote>👤 {uname(u, False)}\n"
         f"🏷 {uname_line}\n"
         f"🆔 <code>{uid}</code>\n"
         f"🎖 {rank_line(uid)}\n"
         f"💎 {esc(titles)}\n"
         f"📝 {esc(u['about_text'] or 'не указано')}</blockquote>\n"
         f"<blockquote>{E('balance')} <b>{fmt(u['balance_coin'])}</b> RCOIN · {E('diamond')} {fmt(u['balance_point'])} RBP\n"
         f"{E('bank')} Банк: {fmt(u['bank_balance'])} · ⭐ {fmt(u['stars_balance'])}\n"
         f"{E('games')} Игр: {n} · побед: {w} · {round(w / max(n, 1) * 100, 1)}%\n"
         f"{E('referral')} Рефералов: {refs}</blockquote>\n"
         f"🖼 {esc(pcap) if pcap else 'Фото профиля не выбрано'}\n"
         f"<i>сменить ник Имя · о себе Текст · +юзер @ник</i>")
    return t, kb([btn("Склад", "menu:stash", "diamond"), btn("Рефералы", "menu:refs", "referral")],
                 [btn("Оформление", "prof:decor", "star"), btn("Фото профиля", "prof:photo", "profile")],
                 [btn("История", "menu:history", "games"), btn("Настройки", "menu:settings", "settings")],
                 [btn("Назад", "menu:main", "door")])


@dp.callback_query(F.data == "prof:decor")
async def cb_prof_decor(cb: CallbackQuery):
    uid = cb.from_user.id
    prem = is_premium(uid) or uid == OWNER_ID
    t = (f"{E('settings')} <b>ОФОРМЛЕНИЕ ПРОФИЛЯ</b>\n\n"
         f"Поставь премиум-эмодзи рядом с рангом, выбери галочки и заполни «О себе».\n"
         f"Статус: <b>{'Premium активен' if prem else 'нужен Premium'}</b>")
    first = [btn("Эмодзи профиля", "prof:emoji", "star")] if prem else [btn("Купить Premium", "badges:menu", "diamond")]
    await safe_edit(cb, t, kb(first, [btn("Галочки", "badges:menu", "check"), btn("Назад", "menu:profile", "door")]))
    await ans(cb)


@dp.callback_query(F.data == "prof:photo")
async def cb_prof_photo(cb: CallbackQuery):
    await send_profile_photo(cb.message, cb.from_user.id)
    await ans(cb)


@dp.callback_query(F.data == "prof:emoji")
async def cb_prof_emoji(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    if not (is_premium(uid) or uid == OWNER_ID):
        return await ans(cb, "Эмодзи профиля доступно с Premium", True)
    await ask(cb, state, "prof_emoji",
              "Отправь сообщение с премиум-эмодзи — он встанет рядом с рангом.\n"
              "Убрать: <code>-</code>")


@flow("prof_emoji")
async def f_prof_emoji(m: Message, state: FSMContext, d, txt):
    uid = m.from_user.id
    if not (is_premium(uid) or uid == OWNER_ID):
        await state.clear()
        return await m.reply("Эмодзи профиля доступно только с Premium.")
    if (txt or "").strip().lower() in ("-", "сброс", "убрать", "нет"):
        update_user(uid, profile_emoji="", profile_emoji_fb="")
        await state.clear()
        return await m.reply("Эмодзи убрано из профиля.")
    ents = [e for e in (m.entities or []) if str(getattr(e, "type", "")) == "custom_emoji" and getattr(e, "custom_emoji_id", None)]
    if not ents:
        return await m.reply("Это не премиум-эмодзи. Вставь кастомный эмодзи Telegram и отправь сообщение.")
    e = ents[0]
    eid = str(e.custom_emoji_id)
    fb = ((m.text or "").strip() or "✨")[:8]
    update_user(uid, profile_emoji=eid, profile_emoji_fb=fb)
    await state.clear()
    await m.reply(f'<tg-emoji emoji-id="{eid}">{esc(fb)}</tg-emoji> <b>Эмодзи установлено в профиль!</b>')


@dp.message(P("эмодзи", "смайл", "профильэмодзи"))
async def cmd_profile_emoji(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not (is_premium(uid) or uid == OWNER_ID):
        return await message.reply("Эмодзи профиля доступно с Premium. Купить: <code>галочки</code>.")
    await ask(message, state, "prof_emoji",
              "Отправь сообщение с премиум-эмодзи — он встанет рядом с рангом.\n"
              "Убрать: <code>-</code>")


@view("settings")
async def v_settings(uid: int, private: bool):
    u = get_user(uid)
    t = (f"{E('settings')} <b>Настройки</b>\n\n🔒 Анонимность: <b>{'включена' if u['is_anonymous'] else 'выключена'}</b>\n"
         f"Скрывает имя в играх. Включение стоит 15 000 RCOIN.")
    return t, kb([btn("Выключить анонимность" if u["is_anonymous"] else "Включить анонимность (15 000)", "set:anon", "settings")],
                 [btn("Назад", "menu:profile", "door")])


@view("history")
async def v_history(uid: int, private: bool):
    rows = q("SELECT game_type,bet_amount,win_amount,is_win,created_at FROM bet_history WHERE user_id=? ORDER BY id DESC LIMIT 12", (uid,))
    if not rows:
        return "📭 История игр пуста.", kb([btn("Назад", "menu:profile", "door")])
    lines = ["📜 <b>Последние игры</b>\n"]
    for r in rows:
        mark = "✅" if r["is_win"] else ("🤝" if r["win_amount"] == r["bet_amount"] else "❌")
        lines.append(f"{mark} {esc(r['game_type'])} · ставка {fmt(r['bet_amount'])} → {fmt(r['win_amount'])} · "
                     f"{datetime.fromtimestamp(r['created_at'], MSK).strftime('%d.%m %H:%M')}")
    return "\n".join(lines), kb([btn("Назад", "menu:profile", "door")])


@view("help")
async def v_help(uid: int, private: bool):
    t = (f"{E('question')} <b>ПОМОЩЬ</b>\n\n<b>Основное:</b> <code>б</code> баланс · <code>бонус</code> (раз в час) · <code>профиль</code> · "
         "<code>топ</code> · <code>история</code> · <code>статистика</code> · <code>рефералы</code> · <code>настройки</code>\n\n"
         "<b>Игры:</b> <code>куб</code> <code>рулетка</code> <code>фортуна</code> <code>баскет</code> <code>дартс</code> <code>футбол</code> <code>спин</code> "
         "<code>солнце</code> <code>краш</code> <code>охота</code> <code>очко</code> <code>мины</code> <code>башня</code> <code>пирамида</code> <code>хило</code> "
         "<code>арена</code> <code>кн</code> (ответом) <code>майнер</code> — список и формат: <code>игры</code>\n\n"
         "<b>Деньги:</b> <code>дать 100к @ник</code> · <code>нк 1000 ID</code> · <code>перевод 5 @ник</code> (RBP) · <code>банк</code> · <code>обмен</code> · "
         "<code>чек</code> · <code>промо КОД</code> · <code>казна</code> · <code>донат</code> · <code>барабан</code>\n\n"
         "<b>NFT и склад:</b> <code>маркет</code> · <code>склад</code> · <code>подарок КОД</code> · <code>передать нфт ID @ник</code> · "
         "<code>передать подарок КОД @ник</code>\n\n"
         "<b>Ивенты:</b> <code>ивенты</code> · <code>игра снежки 10000</code> · <code>лабиринт 10000</code> · <code>помочь санте 100к</code> · <code>ежедневный</code> (бонус 5×5)\n\n"
         "<b>Профиль:</b> <code>эмодзи</code> (Premium) · <code>галочки</code> · <code>о себе Текст</code> · <code>сменить ник Имя</code>\n\n"
         "<b>Прочее:</b> <code>/antiludo</code> (ответом, 100 000 RCOIN — блок игр на 5 мин) · <code>+юзер @ник</code> · "
         "<code>сменить ник Имя</code> · <code>о себе Текст</code>\n\n"
         "Суммы: 1к = 1 000 · 1кк = 1 000 000 · 1ккк = 1 000 000 000 · <code>все</code> = весь баланс\n"
         f"Статус бота: ответы идут реплаем на твоё сообщение.")
    return t, kb([btn("Назад", "menu:main", "door")])


def reg_view(name: str, *words: str):
    @dp.message(P(*words))
    async def _h(message: Message, state: FSMContext):
        await state.clear()
        try:
            t, k = await VIEWS[name](message.from_user.id, message.chat.type == "private")
            await message.reply(t, reply_markup=k)
        except Exception as e:
            log.warning("view %s failed: %s", name, e)
            if name == "games":
                t2, k2 = games_page(0, plain=True)
                await message.answer(t2, reply_markup=k2)
            else:
                raise


async def _open_games(message: Message, state: FSMContext):
    await state.clear()
    try:
        t, k = await VIEWS["games"](message.from_user.id, message.chat.type == "private")
        await message.reply(t, reply_markup=k)
    except Exception as e:
        log.warning("games command failed: %s", e)
        t2, k2 = games_page(0, plain=True)
        await message.answer(t2, reply_markup=k2)


@dp.message(Command("games", "игры", "game"))
async def cmd_games_command(message: Message, state: FSMContext):
    await _open_games(message, state)


@dp.message(F.text.regexp(r"(?i)^@\w+\s+(?:игры|games)$"))
async def cmd_games_mention(message: Message, state: FSMContext):
    await _open_games(message, state)


reg_view("main", "меню", "menu", "старт")
reg_view("games", "игры", "games")
reg_view("profile", "профиль", "profile")
reg_view("help", "помощь", "help")
reg_view("history", "история")


@dp.callback_query(F.data.startswith("menu:"))
async def cb_menu(cb: CallbackQuery):
    name = cb.data.split(":")[1]
    fn = VIEWS.get(name)
    if not fn:
        return await ans(cb, "Раздел недоступен", True)
    t, k = await fn(cb.from_user.id, cb.message.chat.type == "private")
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data == "set:anon")
async def cb_anon(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    if u["is_anonymous"]:
        update_user(u["user_id"], is_anonymous=0)
    else:
        if not spend(u["user_id"], 15000):
            return await ans(cb, "Нужно 15 000 RCOIN", True)
        update_user(u["user_id"], is_anonymous=1)
    t, k = await v_settings(u["user_id"], True)
    await safe_edit(cb, t, k)
    await ans(cb, "Готово")


# ============================ /start, баланс, бонус ============================
def try_referral(uid: int, code: str):
    u = get_user(uid)
    if u["referred_by"] or u["total_games"] > 0 or not code:
        return
    r = q("SELECT user_id FROM users WHERE referral_code=?", (code.upper(),), one=True)
    if not r or r["user_id"] == uid:
        return
    update_user(uid, referred_by=r["user_id"])
    x("INSERT INTO referrals(referrer_id,referred_id,created_at) VALUES(?,?,?)", (r["user_id"], uid, now()))
    add_coin(r["user_id"], 25_000)
    x("UPDATE users SET referral_earnings=referral_earnings+25000 WHERE user_id=?", (r["user_id"],))


@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    args = (command.args or "").strip()
    uid = message.from_user.id
    if args.startswith("promo_"):
        return await do_promo(message, args[6:])
    if args.startswith("check_"):
        return await do_check(message, args[6:], state)
    if args.startswith("room_"):
        code = re.sub(r"\D", "", args)[:6]
        if len(code) == 6:
            return await message.reply(box("🔐 <b>ТЕБЯ ПОЗВАЛИ В КОМНАТУ</b>",
                                           f"Код: <code>{code}</code>",
                                           f"Войти: <code>комната войти {code}</code>"))
    if args:
        try_referral(uid, args.replace("ref_", ""))
    t, k = await v_main(uid, message.chat.type == "private")
    if Path(IMAGE_PATH).exists() and message.chat.type == "private":
        try:
            await message.reply_photo(FSInputFile(IMAGE_PATH), caption=f"{E('games')} <b>Добро пожаловать в RCOIN·BOT!</b>")
        except Exception as e:
            log.debug("start photo: %s", e)
    await message.reply(t, reply_markup=k)


@dp.message(P("б", "бал", "баланс"))
async def cmd_balance(message: Message):
    await send_balance(message, message.from_user.id)


@dp.callback_query(F.data == "bonus:get")
async def cb_bonus(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    ok = x("UPDATE users SET balance_coin=balance_coin+?, bonus_last_time=? WHERE user_id=? AND bonus_last_time<=?",
           (BONUS_AMOUNT, now(), u["user_id"], now() - 3600))[0]
    if not ok:
        return await ans(cb, "Бонус пока недоступен", True)
    await ans(cb, f"🎁 +{fmt(BONUS_AMOUNT)} RCOIN!", True)
    t, k = await v_main(u["user_id"], cb.message.chat.type == "private")
    await safe_edit(cb, t, k)


@dp.message(F.web_app_data)
async def webapp_action(message: Message):
    """Actions from the Mini App: keep the actual rewards and menus inside bot handlers."""
    action = (message.web_app_data.data or "").strip().lower()
    uid = message.from_user.id
    if action == "bonus":
        u = get_user(uid)
        ok, left = bonus_state(u)
        if not ok:
            return await message.answer(f"⏳ Бонус будет доступен через {dur(left)}.")
        update_user(uid, bonus_last_time=now())
        amount = BONUS_AMOUNT * bonus_mult(uid)
        add_coin(uid, amount)
        return await send_balance(message, uid)
    if action == "daily":
        t, k = await VIEWS["db5"](uid, True)
        return await message.answer(t, reply_markup=k)
    if action == "earn":
        t, k = await VIEWS["earn"](uid, True)
        return await message.answer(t, reply_markup=k)


@dp.message(P("бонус"))
async def cmd_bonus(message: Message, state: FSMContext):
    if len(message.text.split()) > 1 and message.text.lower().split()[1] in ("5х5", "5x5", "5×5"):
        return await cmd_db5(message)
    u = get_user(message.from_user.id)
    ok = x("UPDATE users SET balance_coin=balance_coin+?, bonus_last_time=? WHERE user_id=? AND bonus_last_time<=?",
           (BONUS_AMOUNT, now(), u["user_id"], now() - 3600))[0]
    if not ok:
        return await message.reply(f"⏳ Бонус недоступен. Следующий через {dur(u['bonus_last_time'] + 3600 - now())}.")
    await message.reply(f"{E('donate')} <b>Бонус получен: +{fmt(BONUS_AMOUNT)} RCOIN!</b>\nСледующий через 1 час.")


@dp.message(P("барабан"))
async def cmd_drum(message: Message):
    u = get_user(message.from_user.id)
    if now() - u["last_spin_time"] < 86400:
        return await message.reply(f"{E('spin')} Барабан доступен через {dur(u['last_spin_time'] + 86400 - now())}")
    if x("UPDATE users SET last_spin_time=? WHERE user_id=? AND last_spin_time=?", (now(), u["user_id"], u["last_spin_time"]))[0] != 1:
        return
    win = random.randint(1000, 500000)
    add_coin(u["user_id"], win)
    await message.reply(box(f"{E('spin')} <b>БАРАБАН!</b>", f"🎉 Ты выиграл <b>{fmt(win)}</b> RCOIN", "Следующий спин через 24 часа"))


@dp.message(P("поинт"))
async def cmd_point(message: Message):
    u = get_user(message.from_user.id)
    await message.reply(f"{E('diamond')} Твой баланс RBP: <b>{fmt(u['balance_point'])}</b>\n1 RBP = 50 000 RCOIN · обмен: <code>обмен</code>")


@dp.message(P("статистика"))
async def cmd_stats(message: Message):
    u = get_user(message.from_user.id)
    st = q("SELECT COUNT(*) n, SUM(is_win) w, SUM(win_amount) s FROM bet_history WHERE user_id=?", (u["user_id"],), one=True)
    if not st["n"]:
        return await message.reply("📊 Ты ещё не сыграл ни одной игры.")
    await message.reply(f"📊 <b>Статистика</b>\n🎯 Игр: {st['n']}\n✅ Побед: {st['w'] or 0}\n💰 Выплат всего: {fmt(st['s'] or 0)} RCOIN\n"
                        f"📈 Процент побед: {round((st['w'] or 0) / st['n'] * 100, 1)}%")


# ============================ ИГРЫ: меню описаний ============================
GAMES = [
    ("dice", "Кубик", "Число 1-6 (x5.5) или чёт/нечёт/мал/бол (x1.9).\n<code>куб 100 3</code> · <code>куб 100 чет мал</code>"),
    ("roulette", "Рулетка", "Красное/чёрное, чёт/нечёт, 1-18/19-36 (x2), число/зеро (x36).\n<code>рулетка 100к к</code> · <code>рулетка 100 7</code>"),
    ("fortune", "Фортуна", "Колесо множителей x0…x5.\n<code>фортуна 100</code> · <code>кф все</code>"),
    ("basket", "Баскет", "Угадай исход броска.\n<code>баскет 100 м</code> (мимо) · <code>п</code> · <code>чп</code> · <code>з</code>"),
    ("mines", "Мины", "Поле 5×5, открывай клетки и забирай выигрыш.\n<code>мины 100 3</code> (1-10 мин)"),
    ("darts", "Дартс", "Красное/белое x2.7, центр/мимо x5.5.\n<code>дартс 100 к</code>"),
    ("blackjack", "Очко", "21 против дилера, блэкджек x2.5.\n<code>очко 100</code>"),
    ("crash", "Краш", "Выбери множитель — долетит ли ракета?\n<code>краш 100 2.5</code>"),
    ("sun", "Солнце", "Выбери 1 из 9 клеток (x0…x5).\n<code>солнце 100</code>"),
    ("hunt", "Охота", "Добыча до x100.\n<code>охота 100</code>"),
    ("spin", "Спин", "Слот-машина: 777 x20.\n<code>спин 100</code>"),
    ("football", "Футбол", "Гол x1.5, мимо x2.2.\n<code>футбол 100 г</code>"),
    ("pyramid", "Пирамида", "4 двери, одна — ловушка, 8 уровней.\n<code>пирамида 100</code>"),
    ("games", "Башня", "9 уровней по 5 клеток, 1-3 бомбы в ряду.\n<code>башня 500</code> · <code>башня 500 2</code>"),
    ("hi_lo", "Хи-Ло", "Выше или ниже? Множитель по шансам.\n<code>хило 100</code>"),
    ("ttt", "Крестики-нолики", "Дуэль на коины, ответом на сообщение соперника.\n<code>кн 1000</code>"),
    ("games", "Арена", "Открой арену — при 2+ игроках через 15 сек шарик выбирает победителя.\n<code>арена 500</code> (в вебке — ставки разного размера)"),
    ("miner", "Майнер", "Пассивный доход каждый час.\n<code>майнер</code>"),
]


def _game_button(text: str, data: str, icon: str = None, plain: bool = False) -> InlineKeyboardButton:
    kw = {"text": text, "callback_data": data}
    has_icon = False
    if not plain and PREMIUM_ICONS and HAS_BUTTON_ICON and icon:
        cid = EMOJI_IDS.get(icon)
        if cid:
            kw["icon_custom_emoji_id"] = str(cid)
            has_icon = True
    if not has_icon:
        kw["text"] = f"{FALLBACK.get(icon, '▫️')} {text}"
    return InlineKeyboardButton(**kw)


EVENT_GAME_BUTTONS = [
    ("Новогодние игры", "ev:games!", "star"),
    ("Снежки", "evg:snow", "item_1"),
    ("Лёд", "evg:ice", "item_2"),
    ("Медведь", "evg:bear", "item_3"),
    ("Сани", "evg:santa", "item_4"),
    ("Подарки", "evg:gift", "item_5"),
    ("Пряники", "evg:mint", "item_6"),
    ("Нг мины", "evg:mines", "mines"),
    ("Нг башня", "evg:tower", "games"),
    ("Ледяной лабиринт", "lab:new", "item_8"),
]


def games_page(page: int = 0, plain: bool = False):
    """Старая большая панель: все игры сразу, ивентовые — на втором экране."""
    page = 1 if int(page or 0) else 0
    rows = []
    if page == 0:
        row = []
        for i, (icon, name, _) in enumerate(GAMES):
            row.append(_game_button(name, f"gm:i:{i}", icon, plain))
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([
            _game_button("Новогодние игры", "ev:games!", "star", plain),
            _game_button("Дальше ▶️", "gm:p:1", "door", plain),
        ])
        text = (f"{E('games')} <b>ВСЕ ИГРЫ</b>\n"
                f"Полный список — <b>{len(GAMES)}</b> игр. Выбери игру кнопкой ниже.\n"
                f"{E('star')} Новогодние игры — кнопка внизу или «Дальше».")
    else:
        for j in range(0, len(EVENT_GAME_BUTTONS), 2):
            rows.append([_game_button(text, data, icon, plain)
                         for text, data, icon in EVENT_GAME_BUTTONS[j:j + 2]])
        rows.append([_game_button("◀️ Все игры", "gm:p:0", "door", plain)])
        text = (f"{E('star')} <b>НОВОГОДНИЕ ИГРЫ</b>\n"
                "Зимние режимы и мини-игры. Выбери игру кнопкой ниже.")
    rows.append([_game_button("Назад", "menu:main", "door", plain)])
    if plain:
        text = re.sub(r"<[^>]+>", "", text)
    return text, kb(*rows)


@dp.callback_query(F.data.startswith("gm:"))
async def cb_games(cb: CallbackQuery):
    _, act, v = cb.data.split(":")
    if act == "p":
        t, k = games_page(int(v))
    else:
        key, name, text = GAMES[int(v)]
        if name == "Майнер":
            t, k = await v_miner(cb.from_user.id, True)
        else:
            t, k = f"{E(key)} <b>{name}</b>\n\n{text}", kb([btn("К играм", "gm:p:0", "games")])
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.message(P("майнер"))
async def cmd_miner(message: Message):
    t, k = await v_miner(message.from_user.id, True)
    await message.reply(t, reply_markup=k)


# ============================ ТОП ============================
@view("top")
async def v_top(uid: int, private: bool):
    return (f"{E('star')} <b>ТОП ИГРОКОВ</b>\nВыбери категорию:",
            kb([btn("По RCOIN", "top:coin", "balance"), btn("По RBP", "top:rbp", "diamond")],
               [btn("По играм", "top:games", "games"), btn("За день", "top:day", "games")],
               [btn("Неделя (конкурс)", "top:week", "star")], [btn("Назад", "menu:main", "door")]))


reg_view("top", "топ", "top")


@dp.callback_query(F.data.startswith("top:"))
async def cb_top(cb: CallbackQuery):
    kind = cb.data.split(":")[1]
    d = int(time.time()) // 86400
    if kind == "coin":
        rows = q("SELECT display_name n, balance_coin v FROM users ORDER BY balance_coin DESC LIMIT 10"); title, unit = "ПО RCOIN", "RCOIN"
    elif kind == "rbp":
        rows = q("SELECT display_name n, balance_point v FROM users ORDER BY balance_point DESC LIMIT 10"); title, unit = "ПО RBP", "RBP"
    elif kind == "games":
        rows = q("SELECT display_name n, total_games v FROM users ORDER BY total_games DESC LIMIT 10"); title, unit = "ПО ИГРАМ", "игр"
    elif kind == "day":
        rows = q("SELECT display_name n, total_games_day v FROM users WHERE last_game_day=? ORDER BY total_games_day DESC LIMIT 10", (d,)); title, unit = "ЗА СЕГОДНЯ", "игр"
    else:
        rows = q("SELECT u.display_name n, COUNT(*) v FROM bet_history b JOIN users u ON u.user_id=b.user_id WHERE b.created_at>? "
                 "GROUP BY b.user_id ORDER BY v DESC LIMIT 10", (now() - 7 * 86400,)); title, unit = "ЕЖЕНЕДЕЛЬНЫЙ КОНКУРС", "игр"
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{E('star')} <b>ТОП {title}</b>\n"]
    for i, r in enumerate(rows):
        lines.append(f"{medals[i] if i < 3 else str(i + 1) + '.'} {esc(r['n'] or 'Игрок')} — {fmt(r['v'])} {unit}")
    if not rows:
        lines.append("Пока пусто")
    await safe_edit(cb, "\n".join(lines), kb([btn("К топу", "menu:top", "star")]))
    await ans(cb)


# ============================ БАНК ============================
@view("bank")
async def v_bank(uid: int, private: bool):
    u = get_user(uid)
    t = (f"{E('bank')} <b>БАНК</b>\n\n{E('balance')} Баланс: {fmt(u['balance_coin'])}\n🏦 В банке: {fmt(u['bank_balance'])}\n"
         f"📈 Лимит: {fmt(u['bank_limit'])}\n\n<i>Деньги в банке защищены от проигрышей.</i>\n"
         f"Команды: <code>банк положить 1кк</code> · <code>банк снять 500к</code>")
    return t, kb([btn("Положить", "bk:d", "bank"), btn("Снять", "bk:w", "bank")],
                 [btn("Повысить лимит", "bk:up", "bank")], [btn("Назад", "menu:main", "door")])


def bank_move(uid: int, amount: int, deposit: bool) -> str:
    if amount < 100:
        return "Минимальная сумма — 100 RCOIN"
    u = get_user(uid)
    if deposit:
        if u["bank_balance"] + amount > u["bank_limit"]:
            return f"Превышен лимит банка. Можно положить ещё {fmt(u['bank_limit'] - u['bank_balance'])}"
        if x("UPDATE users SET balance_coin=balance_coin-?, bank_balance=bank_balance+? WHERE user_id=? AND balance_coin>=?", (amount, amount, uid, amount))[0] != 1:
            return "Недостаточно RCOIN на балансе"
        return f"✅ Положено в банк: {fmt(amount)} RCOIN"
    if x("UPDATE users SET balance_coin=balance_coin+?, bank_balance=bank_balance-? WHERE user_id=? AND bank_balance>=?", (amount, amount, uid, amount))[0] != 1:
        return "Недостаточно средств в банке"
    return f"✅ Снято с банка: {fmt(amount)} RCOIN"


reg_view("bank", "банк-меню")


@dp.message(P("банк"))
async def cmd_bank(message: Message, state: FSMContext):
    p = message.text.lower().split()
    u = get_user(message.from_user.id)
    if len(p) >= 3 and p[1] in ("положить", "снять"):
        dep = p[1] == "положить"
        amt = parse_amount(p[2], u["balance_coin"] if dep else u["bank_balance"])
        return await message.reply(bank_move(u["user_id"], amt, dep))
    t, k = await v_bank(u["user_id"], True)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data.startswith("bk:"))
async def cb_bank(cb: CallbackQuery, state: FSMContext):
    act = cb.data.split(":")[1]
    if act in ("d", "w"):
        return await ask(cb, state, "bank_d" if act == "d" else "bank_w", "Введи сумму (1к, 1кк, все):")
    u = get_user(cb.from_user.id)
    if u["bank_limit"] >= 10_000_000_000:
        return await ans(cb, "Максимальный лимит достигнут", True)
    cost = max(u["bank_limit"] // 10, 100000)
    if not spend(u["user_id"], cost):
        return await ans(cb, f"Нужно {fmt(cost)} RCOIN", True)
    update_user(u["user_id"], bank_limit=u["bank_limit"] + 500_000_000)
    await ans(cb, "Лимит повышен на 500 000 000", True)
    t, k = await v_bank(u["user_id"], True)
    await safe_edit(cb, t, k)


@flow("bank_d")
async def f_bank_d(m: Message, state: FSMContext, d, txt):
    u = get_user(m.from_user.id)
    await m.reply(bank_move(u["user_id"], parse_amount(txt, u["balance_coin"]), True))
    await state.clear()


@flow("bank_w")
async def f_bank_w(m: Message, state: FSMContext, d, txt):
    u = get_user(m.from_user.id)
    await m.reply(bank_move(u["user_id"], parse_amount(txt, u["bank_balance"]), False))
    await state.clear()


# ============================ ОБМЕН RCOIN <-> RBP ============================
@dp.message(P("обмен"))
async def cmd_exchange(message: Message):
    u = get_user(message.from_user.id)
    await message.reply(f"{E('diamond')} <b>ОБМЕН ВАЛЮТ</b>\n\n{E('balance')} RCOIN: {fmt(u['balance_coin'])}\n{E('diamond')} RBP: {fmt(u['balance_point'])}\n\n"
                        "📊 Покупка: 100 000 RCOIN = 1 RBP\n📊 Продажа: 1 RBP = 50 000 RCOIN",
                        reply_markup=kb([btn("RCOIN → RBP", "ex:buy", "diamond")], [btn("RBP → RCOIN", "ex:sell", "diamond")]))


@dp.callback_query(F.data.startswith("ex:"))
async def cb_exchange(cb: CallbackQuery, state: FSMContext):
    buy = cb.data.endswith("buy")
    await ask(cb, state, "ex_buy" if buy else "ex_sell",
              "Сколько RBP купить? (по 100 000 RCOIN)" if buy else "Сколько RBP продать? (по 50 000 RCOIN)")


@flow("ex_buy")
async def f_ex_buy(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or int(txt) < 1:
        return await m.reply("Введи целое число RBP.")
    n = int(txt)
    if not spend(m.from_user.id, n * 100000):
        return await m.reply(f"Нужно {fmt(n * 100000)} RCOIN")
    x("UPDATE users SET balance_point=balance_point+? WHERE user_id=?", (n, m.from_user.id))
    await state.clear()
    await m.reply(f"{E('diamond')} Куплено <b>{n}</b> RBP за {fmt(n * 100000)} RCOIN")


@flow("ex_sell")
async def f_ex_sell(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or int(txt) < 1:
        return await m.reply("Введи целое число RBP.")
    n = int(txt)
    if not spend(m.from_user.id, n, "balance_point"):
        return await m.reply("Недостаточно RBP")
    add_coin(m.from_user.id, n * 50000)
    await state.clear()
    await m.reply(f"{E('diamond')} Продано <b>{n}</b> RBP, получено {fmt(n * 50000)} RCOIN")


# ============================ ПЕРЕВОДЫ ============================
def resolve_target(message: Message, token: Optional[str]) -> Optional[Dict[str, Any]]:
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_bot and not token:
        ensure_user(message.reply_to_message.from_user)
        return get_user(message.reply_to_message.from_user.id)
    return find_user(token) if token else None


@dp.message(P("дать", "нк"))
async def cmd_give(message: Message):
    u = get_user(message.from_user.id)
    p = message.text.split(maxsplit=3)
    if len(p) < 2:
        return await message.reply(usage(f"• <code>дать 100к @ник</code>\n• <code>нк 1000 123456789</code>\n• <code>дать 500</code> — ответом на сообщение\nКомиссия {TRANSFER_COMMISSION}% платит отправитель."))
    amount = parse_amount(p[1], u["balance_coin"])
    if amount < 1:
        return await message.reply(f"{E('lock')} Неверная сумма.")
    if amount > MAX_TRANSFER:
        return await message.reply(f"{E('lock')} Максимальный перевод — <b>{fmt(MAX_TRANSFER)}</b> RCOIN.")
    reply_mode = bool(message.reply_to_message)
    target = resolve_target(message, None if (len(p) >= 3 and not reply_mode) else None) if reply_mode else find_user(p[2]) if len(p) >= 3 else None
    comment = (p[2] if reply_mode and len(p) >= 3 else (p[3] if len(p) >= 4 else ""))
    if not target:
        return await message.reply(f"{E('lock')} Получатель не найден. Он должен хотя бы раз запустить бота.")
    if target["user_id"] == u["user_id"]:
        return await message.reply(f"{E('lock')} Нельзя перевести самому себе.")
    commission = amount * TRANSFER_COMMISSION // 100
    if not spend(u["user_id"], amount + commission):
        return await message.reply(f"{E('lock')} <b>Недостаточно RCOIN!</b>\nНужно: {fmt(amount + commission)} (сумма {fmt(amount)} + комиссия {fmt(commission)})")
    add_coin(target["user_id"], amount)
    treasury_add(commission)
    x("INSERT INTO transfer_history(from_user_id,to_user_id,amount,created_at,comment) VALUES(?,?,?,?,?)", (u["user_id"], target["user_id"], amount, now(), comment[:100]))
    t = box(f"{E('balance')} <b>Перевод RCOIN</b>", f"👤 От: {uname(u, False)}", f"👤 Кому: {uname(target, False)}",
            f"💵 Сумма: {fmt(amount)}", f"💸 Комиссия ({TRANSFER_COMMISSION}%): {fmt(commission)}" + (f"\n📝 {esc(comment)}" if comment else ""))
    await message.reply(t)
    try:
        await bot.send_message(target["user_id"], box(f"{E('balance')} <b>Тебе пришёл перевод!</b>", f"От: {uname(u, False)}", f"+{fmt(amount)} RCOIN"))
    except Exception:
        pass


@dp.message(P("перевод"))
async def cmd_give_rbp(message: Message):
    u = get_user(message.from_user.id)
    p = message.text.split()
    if len(p) < 2 or not p[1].isdigit():
        return await message.reply(usage("<code>перевод 10 @ник</code> — перевести RBP (или ответом: <code>перевод 10</code>)"))
    n = int(p[1])
    target = resolve_target(message, p[2] if len(p) >= 3 else None)
    if not target or target["user_id"] == u["user_id"]:
        return await message.reply(f"{E('lock')} Получатель не найден.")
    if n > MAX_TRANSFER:
        return await message.reply(f"{E('lock')} Максимальный перевод — <b>{fmt(MAX_TRANSFER)}</b>.")
    if n < 1 or not spend(u["user_id"], n, "balance_point"):
        return await message.reply(f"{E('lock')} Недостаточно RBP.")
    x("UPDATE users SET balance_point=balance_point+? WHERE user_id=?", (n, target["user_id"]))
    await message.reply(box(f"{E('diamond')} <b>Перевод RBP</b>", f"{uname(u, False)} → {uname(target, False)}", f"💎 {fmt(n)} RBP"))


# ============================ КАЗНА ============================
@dp.message(P("казна"))
async def cmd_treasury(message: Message):
    t, k = await v_treasury(message.from_user.id, True)
    await message.reply(t, reply_markup=k)


@view("treasury")
async def v_treasury(uid: int, private: bool):
    u = get_user(uid)
    st = tset_get()
    chats = tset_chats()
    t = (f"{E('treasury')} <b>КАЗНА</b>\n\n"
         f"💰 RCOIN: <b>{fmt(treasury_get())}</b>\n\n"
         f"⚙️ Авточеки: пятница {'вкл' if int(st.get('auto_fri') or 0) else 'выкл'} · "
         f"суббота {'вкл' if int(st.get('auto_sat') or 0) else 'выкл'}\n"
         f"💵 Суммы: {fmt(st.get('fri_amount') or 0)} / {fmt(st.get('sat_amount') or 0)}\n"
         f"🎟 Активаций: {fmt(st.get('auto_slots') or 0)}\n"
         f"📣 Чаты: {len(chats) if chats else 'не настроены'}\n\n"
         "Авточеки и ивенты финансируются из казны.")
    rows = []
    if u["treasury_access"] or is_admin(uid):
        rows.append([btn("Пополнить", "tr:d", "treasury"), btn("Снять", "tr:w", "treasury")])
        rows.append([btn("Авточеки", "tr:auto", "settings"), btn("Чаты", "tr:chats", "ad")])
        rows.append([btn("Ивент-чек", "tr:event", "check")])
    rows.append([btn("Назад", "menu:main", "door")])
    return t, kb(*rows)


def treasury_auto_view():
    st = tset_get()
    t = (f"⚙️ <b>АВТОЧЕКИ ИЗ КАЗНЫ</b>\n\n"
         f"Пятница: <b>{'вкл' if int(st.get('auto_fri') or 0) else 'выкл'}</b> · "
         f"сумма <b>{fmt(st.get('fri_amount') or 0)}</b>\n"
         f"Суббота: <b>{'вкл' if int(st.get('auto_sat') or 0) else 'выкл'}</b> · "
         f"сумма <b>{fmt(st.get('sat_amount') or 0)}</b>\n"
         f"Каждый день: <b>{'вкл' if int(st.get('daily_enabled') or 0) else 'выкл'}</b> · "
         f"сумма <b>{fmt(st.get('daily_amount') or 0)}</b> · в <b>{int(st.get('daily_hour') or 12)}:00</b>\n"
         f"Активаций в чеке: <b>{fmt(st.get('auto_slots') or 0)}</b>\n\n"
         "Если указаны чаты — бот публикует чек-ссылку в них. Если нет — начисляет всем игрокам.")
    rows = [
        [btn("Пятница вкл/выкл", "tr:t:fri", "settings"), btn("Суббота вкл/выкл", "tr:t:sat", "settings")],
        [btn("Сумма пятницы", "tr:a:fri", "balance"), btn("Сумма субботы", "tr:a:sat", "balance")],
        [btn("Ежедневно вкл/выкл", "tr:t:daily", "settings"), btn("Сумма дня", "tr:a:daily", "balance")],
        [btn("Активаций", "tr:slots", "check")],
        [btn("Назад", "tr:home", "door")],
    ]
    return t, kb(*rows)


def treasury_event_view():
    st = tset_get()
    t = (f"🎁 <b>ИВЕНТ-ЧЕК ИЗ КАЗНЫ</b>\n\n"
         f"В казне: <b>{fmt(treasury_get())}</b>\n"
         f"Пятничный чек: <b>{fmt(st.get('fri_amount') or 0)}</b> × {fmt(st.get('auto_slots') or 0)}\n"
         f"Субботний чек: <b>{fmt(st.get('sat_amount') or 0)}</b> × {fmt(st.get('auto_slots') or 0)}\n\n"
         "Запуск выдаст чек сразу.")
    rows = [
        [btn("Пятничный чек", "tr:run:fri", "check")],
        [btn("Субботний чек", "tr:run:sat", "check")],
        [btn("Назад", "tr:home", "door")],
    ]
    return t, kb(*rows)


@dp.callback_query(F.data.startswith("tr:"))
async def cb_treasury(cb: CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    if not (u["treasury_access"] or is_admin(u["user_id"])):
        return await ans(cb, "Нет доступа", True)
    parts = cb.data.split(":")
    act = parts[1]
    if act in ("d", "w"):
        return await ask(cb, state, "tr_d" if act == "d" else "tr_w", "Введи сумму RCOIN (1к, 1кк):")
    if act == "home":
        t, k = await v_treasury(u["user_id"], True)
        await safe_edit(cb, t, k)
        return await ans(cb)
    if act == "auto":
        t, k = treasury_auto_view()
        await safe_edit(cb, t, k)
        return await ans(cb)
    if act == "chats":
        return await ask(cb, state, "tr_chats", "Отправь ID чатов/каналов через запятую или @username. «-» — очистить:")
    if act == "event":
        t, k = treasury_event_view()
        await safe_edit(cb, t, k)
        return await ans(cb)
    if act == "t" and len(parts) > 2 and parts[2] in ("fri", "sat", "daily"):
        st = tset_get()
        col = "auto_daily" if parts[2] == "daily" else "auto_" + parts[2]
        val = 0 if int(st.get(col) or 0) else 1
        tset_update(**{col: val})
        t, k = treasury_auto_view()
        await safe_edit(cb, t, k)
        return await ans(cb, "Авточек обновлён", True)
    if act == "a" and len(parts) > 2 and parts[2] in ("fri", "sat", "daily"):
        if parts[2] == "daily":
            return await ask(cb, state, "tr_ad", "Введи сумму ежедневного чека:")
        return await ask(cb, state, "tr_af" if parts[2] == "fri" else "tr_as", "Введи сумму RCOIN:")
    if act == "slots":
        return await ask(cb, state, "tr_slots", "Сколько активаций в одном чеке?")
    if act == "run" and len(parts) > 2 and parts[2] in ("fri", "sat"):
        ok = await distribute_check(parts[2])
        return await ans(cb, "✅ Чек запущен" if ok else "❌ Не хватило казны, чатов или игроков", True)
    return await ans(cb, "Неизвестное действие", True)


@flow("tr_d")
async def f_tr_d(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt, get_user(m.from_user.id)["balance_coin"])
    if n <= 0 or not spend(m.from_user.id, n):
        return await m.reply("Недостаточно RCOIN или неверная сумма.")
    treasury_add(n)
    await state.clear()
    await m.reply(f"✅ В казну внесено {fmt(n)}. В казне: {fmt(treasury_get())}")


@flow("tr_w")
async def f_tr_w(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0 or not treasury_take(n):
        return await m.reply("В казне недостаточно средств или неверная сумма.")
    add_coin(m.from_user.id, n)
    await state.clear()
    await m.reply(f"✅ Снято из казны {fmt(n)}. В казне: {fmt(treasury_get())}")


@flow("tr_af")
async def f_tr_af(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0:
        return await m.reply("Введи положительную сумму.")
    tset_update(fri_amount=n)
    await state.clear()
    await m.reply(f"✅ Сумма пятничного чека: {fmt(n)}")


@flow("tr_as")
async def f_tr_as(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0:
        return await m.reply("Введи положительную сумму.")
    tset_update(sat_amount=n)
    await state.clear()
    await m.reply(f"✅ Сумма субботнего чека: {fmt(n)}")


@flow("tr_ad")
async def f_tr_ad(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0:
        return await m.reply("Введи положительную сумму.")
    tset_update(daily_amount=n)
    await state.clear()
    await m.reply(f"✅ Ежедневный чек: {fmt(n)}")


@flow("tr_slots")
async def f_tr_slots(m: Message, state: FSMContext, d, txt):
    if not txt.strip().isdigit() or not 1 <= int(txt) <= 100_000:
        return await m.reply("Введи число активаций от 1 до 100000.")
    tset_update(auto_slots=int(txt))
    await state.clear()
    await m.reply(f"✅ Активаций в чеке: {fmt(int(txt))}")


@flow("tr_chats")
async def f_tr_chats(m: Message, state: FSMContext, d, txt):
    raw = "" if txt.strip() in ("", "-") else " ".join(txt.split())[:500]
    tset_update(chat_ids=raw)
    await state.clear()
    await m.reply("✅ Чаты сохранены." if raw else "✅ Список чатов очищен.")


# ============================ ЧЕКИ ============================
@dp.message(P("чек"))
async def cmd_check_book(message: Message):
    t, k = await v_checks(message.from_user.id, True)
    await message.reply(t, reply_markup=k)


GIGACHAT_AUTH = os.getenv("GIGACHAT_AUTH", "").strip()
GIGACHAT_ID = os.getenv("GIGACHAT_CLIENT_ID", "").strip()
GIGACHAT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "").strip()


def giga_auth() -> str:
    """Ключ из базы (задан командой в боте) или из переменных окружения."""
    saved = (kv_get("gigachat:auth") or "").strip()
    if saved:
        return saved
    if GIGACHAT_AUTH:
        return GIGACHAT_AUTH
    if GIGACHAT_ID and GIGACHAT_SECRET:
        return base64.b64encode(f"{GIGACHAT_ID}:{GIGACHAT_SECRET}".encode()).decode()
    return ""


async def ai_answer(prompt: str, system: str = "") -> Optional[str]:
    """Ответ внешней модели (GigaChat). Без ключа возвращает None."""
    auth = giga_auth()
    if not auth or not prompt.strip():
        return None
    import aiohttp
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                              headers={"Authorization": "Basic " + auth,
                                       "RqUID": gen_code(16, "0123456789abcdef"),
                                       "Content-Type": "application/x-www-form-urlencoded"},
                              data={"scope": "GIGACHAT_API_PERS"}) as r:
                token = (await r.json()).get("access_token")
            if not token:
                return None
            msgs = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt[:4000]}]
            async with s.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                              headers={"Authorization": "Bearer " + token},
                              json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}) as r:
                data = await r.json()
                return (data["choices"][0]["message"]["content"] or "").strip()[:3500]
    except Exception:
        log.exception("ai_answer")
        return None


@dp.message(P("поддержка", "саппорт", "support"))
async def cmd_support(message: Message):
    await message.reply(
        "🆘 <b>ПОДДЕРЖКА RUBIN</b>\n\n"
        "Пиши сюда по любым вопросам: баланс, NFT, вывод, ошибки.\n"
        "Отвечаем в порядке очереди.",
        reply_markup=kb([btn("Написать в поддержку", url="https://t.me/RubinHelpSBbot", icon="support")]))


@dp.message(P("диаг", "диагностика"))
async def cmd_diag(message: Message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    cols = {r["name"] for r in q("PRAGMA table_info(users)")}
    art = len(list(NFT_ART_DIR.glob("*.jpg")))
    fan = (Path(__file__).with_name("mining_art") / "fan.jpg").is_file()
    try:
        st = api_mining_state({"user_id": uid}, {})
        mine = f"ok · серверов {sum(1 for x in st['servers'] if x['owned'])}, доход {fmt(st['rate'])}/сутки"
    except Exception as e:
        mine = f"ОШИБКА: {e}"
    lines = [f"🩺 <b>ДИАГНОСТИКА</b>",
             f"БД: {'✅' if {'archive_coin','mine_pending','mine_last'} <= cols else '❌ нет колонок'}",
             f"NFT-архив: {archive_count()} лотов",
             f"Майнинг: {mine}",
             f"Арт NFT: {art} шт · код-арт: ✅",
             f"Кулер: {'✅ файл' if fan else '✅ рисуется кодом'}",
             f"AI-ключ: {'✅ сохранён' if giga_auth() else '❌ не задан (команда «ключ ID SECRET») — на NFT не влияет'}"]
    await message.reply("\n".join(lines))


@dp.message(P("ключ", "апиключ", "gigakey"))
async def cmd_set_giga_key(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    vals = [p.strip().strip('"').strip("'") for p in parts[1:]]
    if vals and vals[0].lower() in ("сброс", "reset", "удалить", "clear"):
        kv_set("gigachat:auth", "")
        return await message.reply("🗑 Ключ GigaChat удалён.")
    if not vals:
        return await message.reply(
            "🔑 <b>Ключ GigaChat</b>\n"
            "Вариант 1: <code>ключ CLIENT_ID SECRET</code>\n"
            "Вариант 2: <code>ключ AUTH_BASE64</code> (готовая строка Authorization)\n"
            "Вариант 3: переменные <code>GIGACHAT_CLIENT_ID</code> и <code>GIGACHAT_CLIENT_SECRET</code> на хостинге.\n\n"
            "Без ключа бот работает: NFT рисуются кодом, AI-ассистент просто отключён.")
    if len(vals) == 1:
        token = vals[0]
        if ":" in token and not token.endswith("="):
            token = base64.b64encode(token.encode()).decode()
    else:
        token = base64.b64encode(f"{vals[0]}:{vals[1]}".encode()).decode()
    if len(token) < 12:
        return await message.reply("❌ Ключ слишком короткий. Пришли CLIENT_ID и SECRET.")
    kv_set("gigachat:auth", token)
    try:
        await message.delete()
    except Exception:
        pass
    ok = await ai_answer("Ответь одним словом: работает", system="Тест соединения.")
    await message.reply("✅ Ключ сохранён." + (" Соединение с GigaChat работает." if ok else
                                               " Но проверка не прошла — проверь ID/SECRET и доступ к API."))


@dp.message(P("ассистент", "ии", "ai"))
async def cmd_assistant(message: Message):
    if not is_admin(message.from_user.id):
        return
    prompt = message.text.split(maxsplit=1)
    if len(prompt) < 2:
        return await message.reply("🤖 <b>AI-ассистент</b>\nНапиши задачу: <code>ассистент добавь игру на реакцию</code>",
                                   reply_markup=kb([btn("Статус ключа", "ai:status")]))
    if not giga_auth():
        return await message.reply("🔑 Нужен ключ GigaChat: задай переменную окружения <code>GIGACHAT_AUTH</code> "
                                   "(base64 client_id:client_secret). После этого ассистент заработает без правок кода.")
    await message.reply("⏳ Думаю…")
    ans = await ai_answer(prompt[1], system="Ты помощник разработчика Telegram-бота на aiogram. Отвечай кратко и по делу, код — блоками.")
    await message.reply((ans or "Не удалось получить ответ.")[:4000])


@dp.callback_query(F.data == "adm:ai")
async def cb_adm_ai(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет доступа", True)
    status = "✅ ключ задан" if giga_auth() else "❌ ключ не задан"
    await safe_edit(cb, box("🤖 <b>НЕЙРОСЕТЬ</b>",
                            f"Статус: {status}",
                            "Команда: <code>ассистент добавь игру на реакцию</code>",
                            "В инлайне: <code>@бот .ai вопрос</code>",
                            "Ключ на хостинге: <code>GIGACHAT_AUTH</code>"),
                    kb([btn("Спросить сейчас", "adm:ai:ask", "question")],
                       [btn("Назад", "adm:menu", "door")]))
    return await ans(cb)


@dp.callback_query(F.data == "adm:ai:ask")
async def cb_adm_ai_ask(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет доступа", True)
    if not giga_auth():
        return await ans(cb, "Сначала задай GIGACHAT_AUTH", True)
    await ask(cb, state, "ai_task", "Что сделать? Опиши задачу или промпт:")


@flow("ai_task")
async def f_ai_task(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return
    if not giga_auth():
        return await m.reply("Ключ не задан.")
    await m.reply("⏳ Думаю…")
    answer = await ai_answer(txt, system="Ты помощник разработчика Telegram-бота на aiogram. Отвечай кратко, код — блоками.")
    await state.clear()
    await m.reply((answer or "Не удалось получить ответ.")[:4000])


@dp.callback_query(F.data == "ai:status")
async def cb_ai_status(cb: CallbackQuery):
    await ans(cb, "Ключ задан" if giga_auth() else "Ключ не задан", True)


@dp.inline_query()
async def inline_checks(query: InlineQuery):
    raw = (query.query or "").strip()
    low = raw.lower()
    uid = query.from_user.id
    u = get_user(uid)
    results = []
    if low.startswith(("чек", "check")):
        parts = raw.split(maxsplit=3)
        amount = parse_amount(parts[1], u["balance_coin"]) if len(parts) > 1 else 0
        act = 1
        rest = parts[2:]
        if rest and rest[0].strip().isdigit():
            act = max(1, min(int(rest[0].strip()), 100000))
            rest = rest[1:]
        note = (" ".join(rest).strip() if rest else "")[:180]
        tok = gen_code(6)
        kv_set("inl:" + tok, note + "\x1f" + str(act))
        if amount > 0:
            results.append(InlineQueryResultArticle(
                id=f"check:{amount}",
                title=f"Чек на {fmt(amount)} RCOIN" + (f" · {act} акт." if act > 1 else "") + (" · с текстом" if note else ""),
                description=(note or f"Создать чек на {fmt(amount)} RCOIN") + f" · {act} активаций · баланс {fmt(u['balance_coin'])}",
                input_message_content=InputTextMessageContent(
                    message_text=f"{E('check')} <b>Чек на {fmt(amount)} RCOIN</b>\n"
                                 + (f"{esc(note)}\n" if note else "")
                                 + "Нажми кнопку, чтобы создать чек.",
                    parse_mode=ParseMode.HTML),
                reply_markup=kb([btn(f"Создать чек · {fmt(amount)}", f"ck:inl:{amount}:{act}:{tok}",
                                     icon="check", style="success")]),
            ))
        else:
            results.append(InlineQueryResultArticle(
                id="check-hint",
                title="Чек: укажи сумму",
                description="Например: чек 1000",
                input_message_content=InputTextMessageContent(
                    message_text="Напиши в инлайн-режиме: <code>чек 1000</code>",
                    parse_mode=ParseMode.HTML),
            ))
    elif low.startswith((".ai ", ".r ", "аи ")):
        prompt = raw.split(maxsplit=1)[1].strip() if len(raw.split(maxsplit=1)) > 1 else ""
        answer = await ai_answer(prompt) if prompt else None
        text = answer or ("🔑 AI не настроен: отправь админу команду «ключ CLIENT_ID SECRET»." if not giga_auth() else "Не удалось ответить.")
        results.append(InlineQueryResultArticle(
            id="ai",
            title="AI: " + (prompt[:40] or "вопрос"),
            description=text[:120],
            input_message_content=InputTextMessageContent(
                message_text=f"🤖 <b>AI</b>\n<i>{esc(prompt[:200])}</i>\n\n{esc(text[:3000])}",
                parse_mode=ParseMode.HTML)))
    else:
        rows = q("SELECT user_id,display_name,username,balance_coin FROM users ORDER BY balance_coin DESC LIMIT 10")
        lines = [f"{E('win')} <b>ТОП RCOIN</b>"]
        for i, r in enumerate(rows, 1):
            name = r.get("display_name") or r.get("username") or str(r.get("user_id") or "")
            lines.append(f"{i}. {esc(str(name))} — <b>{fmt(r['balance_coin'])}</b> RCOIN")
        text = "\n".join(lines) if rows else "Пока нет игроков."
        results.append(InlineQueryResultArticle(
            id="top",
            title="Топ RCOIN",
            description="Топ-10 игроков по балансу",
            input_message_content=InputTextMessageContent(message_text=text, parse_mode=ParseMode.HTML),
        ))
    await query.answer(results[:20], cache_time=0, is_personal=True)


@view("checks")
async def v_checks(uid: int, private: bool):
    u = get_user(uid)
    return (f"{E('check')} <b>Чековая книжка</b>\n\n{E('balance')} Баланс: {fmt(u['balance_coin'])}\nСумма чека списывается сразу: сумма × активации.",
            kb([btn("Создать чек", "ck:new", "check")], [btn("Мои чеки", "ck:my", "check")], [btn("Назад", "menu:main", "door")]))


@dp.callback_query(F.data.startswith("ck:"))
async def cb_checks(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    uid = cb.from_user.id
    act = parts[1]
    if act == "inl":
        try:
            amount = int(parts[2])
            act = max(1, min(int(parts[3]), 100000)) if len(parts) > 3 else 1
            raw_note = kv_get("inl:" + parts[4]) if len(parts) > 4 and parts[4] else ""
            note, _, act_saved = (raw_note or "").partition("\x1f")
            if act_saved.isdigit():
                act = max(1, min(int(act_saved), 100000))
        except (IndexError, ValueError):
            return await ans(cb, "Неверная сумма", True)
        if amount <= 0:
            return await ans(cb, "Неверная сумма", True)
        if not spend(uid, amount):
            return await ans(cb, "Недостаточно RCOIN", True)
        cid = gen_code()
        x("INSERT INTO checks(check_id,owner_id,amount,max_activations,description,created_at) VALUES(?,?,?,?,?,?)",
          (cid, uid, amount, act, (note or "Инлайн-чек")[:200], now()))
        text = box(f"{E('check')} <b>Чек создан!</b>", f"💰 {fmt(amount)} RCOIN",
                   ("Сообщение: " + esc(note)) if note else "Отправь ссылку тому, кому хочешь передать чек.")
        markup = kb([btn(f"Забрать {fmt(amount)}", url=deeplink("check_" + cid), icon="check")])
        if getattr(cb, "inline_message_id", None):
            try:
                await bot.edit_message_text(text, inline_message_id=cb.inline_message_id,
                                            reply_markup=markup, parse_mode=ParseMode.HTML)
            except Exception as e:
                log.warning("inline edit: %s", e)
                await bot.send_message(uid, text, reply_markup=markup)
        else:
            await safe_edit(cb, text, markup)
        return await ans(cb, "Чек создан", True)
    if act == "new":
        return await ask(cb, state, "ck_amount", "Сумма RCOIN <b>на одну активацию</b>:")
    if act == "my":
        rows = q("SELECT * FROM checks WHERE owner_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 10", (uid,))
        if not rows:
            await safe_edit(cb, "📭 У тебя нет активных чеков.", kb([btn("Назад", "ck:home", "door")]))
            return await ans(cb)
        lines, rws = [f"{E('check')} <b>Мои чеки</b>\n"], []
        for r in rows:
            lines.append(f"🆔 <code>{r['check_id']}</code> · {fmt(r['amount'])} × {r['activations']}/{r['max_activations']} · пароль: {'есть' if r['password'] else 'нет'}\n📝 {esc(r['description'] or '—')}")
            rws.append([btn(f"🔗 {r['check_id']}", f"ck:l:{r['check_id']}"), btn("🔑", f"ck:p:{r['check_id']}"),
                        btn("📝", f"ck:d:{r['check_id']}"), btn("🗑", f"ck:x:{r['check_id']}")])
        rws.append([btn("Назад", "ck:home", "door")])
        await safe_edit(cb, "\n".join(lines), kb(*rws))
        return await ans(cb)
    if act == "home":
        t, k = await v_checks(uid, True)
        await safe_edit(cb, t, k)
        return await ans(cb)
    ck = q("SELECT * FROM checks WHERE check_id=?", (parts[2],), one=True)
    if not ck or ck["owner_id"] != uid:
        return await ans(cb, "Чек не найден", True)
    if act == "l":
        await cb.message.answer(f"🔗 Ссылка на чек:\n<code>{deeplink('check_' + ck['check_id'])}</code>")
        return await ans(cb)
    if act == "p":
        return await ask(cb, state, "ck_pass", "Введи пароль для чека (или «-» чтобы убрать):", cid=ck["check_id"])
    if act == "d":
        return await ask(cb, state, "ck_desc", "Введи описание чека:", cid=ck["check_id"])
    if act == "x":
        rest = (ck["max_activations"] - ck["activations"]) * ck["amount"]
        if x("UPDATE checks SET is_active=0 WHERE check_id=? AND is_active=1", (ck["check_id"],))[0] == 1:
            add_coin(uid, rest)
            await ans(cb, f"Чек удалён, возвращено {fmt(rest)} RCOIN", True)
        await cb_checks(cb.model_copy(update={"data": "ck:my"}), state)


@flow("ck_amount")
async def f_ck_amount(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0:
        return await m.reply("Введи положительную сумму.")
    await step(m, state, "ck_acts", "Количество активаций:", amount=n)


@flow("ck_acts")
async def f_ck_acts(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or not 1 <= int(txt) <= 100000:
        return await m.reply("Введи число активаций (1-100000).")
    acts, amt = int(txt), d["amount"]
    if not spend(m.from_user.id, amt * acts):
        await state.clear()
        return await m.reply(f"{E('lock')} Нужно {fmt(amt * acts)} RCOIN.")
    cid = gen_code()
    x("INSERT INTO checks(check_id,owner_id,amount,max_activations,created_at) VALUES(?,?,?,?,?)", (cid, m.from_user.id, amt, acts, now()))
    await state.clear()
    await m.reply(box(f"{E('check')} <b>Чек создан!</b>", f"🆔 <code>{cid}</code>", f"💰 {fmt(amt)} × {acts} = {fmt(amt * acts)} RCOIN",
                      f"🔗 <code>{deeplink('check_' + cid)}</code>"))


@flow("ck_desc")
async def f_ck_desc(m: Message, state: FSMContext, d, txt):
    x("UPDATE checks SET description=? WHERE check_id=? AND owner_id=?", (txt[:200], d["cid"], m.from_user.id))
    await state.clear()
    await m.reply("✅ Описание сохранено.")


@flow("ck_pass")
async def f_ck_pass(m: Message, state: FSMContext, d, txt):
    x("UPDATE checks SET password=? WHERE check_id=? AND owner_id=?", ("" if txt == "-" else txt[:50], d["cid"], m.from_user.id))
    await state.clear()
    await m.reply("✅ Пароль сохранён.")


async def do_check(message: Message, cid: str, state: FSMContext):
    uid = message.from_user.id
    ck = q("SELECT * FROM checks WHERE check_id=? AND is_active=1", (cid,), one=True)
    if not ck:
        return await message.reply(f"{E('lock')} Чек не найден или уже неактивен.")
    if ck["owner_id"] == uid:
        return await message.reply(f"{E('lock')} Нельзя активировать свой чек.")
    if q("SELECT 1 FROM check_activations WHERE check_id=? AND user_id=?", (cid, uid), one=True):
        return await message.reply(f"{E('lock')} Ты уже активировал этот чек.")
    if ck["password"]:
        await state.set_state(Flow.input)
        await state.set_data({"kind": "ck_enter", "cid": cid})
        return await message.reply(f"{E('lock')} Чек защищён паролем.\n📝 {esc(ck['description'] or '')}\n\nВведи пароль:")
    await claim_check(message, cid)


async def claim_check(message: Message, cid: str):
    uid = message.from_user.id
    try:
        x("INSERT INTO check_activations(check_id,user_id,activated_at) VALUES(?,?,?)", (cid, uid, now()))
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return await message.reply(f"{E('lock')} Ты уже активировал этот чек.")
    ok = x("UPDATE checks SET activations=activations+1 WHERE check_id=? AND is_active=1 AND activations<max_activations", (cid,))[0]
    if not ok:
        x("DELETE FROM check_activations WHERE check_id=? AND user_id=?", (cid, uid))
        return await message.reply(f"{E('lock')} Чек уже использован.")
    ck = q("SELECT * FROM checks WHERE check_id=?", (cid,), one=True)
    if ck["activations"] >= ck["max_activations"]:
        x("UPDATE checks SET is_active=0 WHERE check_id=?", (cid,))
    add_coin(uid, ck["amount"])
    await message.reply(box(f"{E('check')} <b>ЧЕК АКТИВИРОВАН!</b>", f"💰 Получено: <b>+{fmt(ck['amount'])}</b> RCOIN"))
    if ck["owner_id"]:
        try:
            await bot.send_message(ck["owner_id"], f"{E('check')} Чек <code>{cid}</code> активирован ({ck['activations']}/{ck['max_activations']}) — {uname(get_user(uid), False)}")
        except Exception:
            pass


@flow("ck_enter")
async def f_ck_enter(m: Message, state: FSMContext, d, txt):
    ck = q("SELECT password FROM checks WHERE check_id=? AND is_active=1", (d["cid"],), one=True)
    if not ck:
        await state.clear()
        return await m.reply("Чек уже неактивен.")
    if txt != ck["password"]:
        return await m.reply("❌ Неверный пароль. Попробуй ещё раз или «отмена».")
    await state.clear()
    await claim_check(m, d["cid"])


# ============================ ПРОМОКОДЫ ============================
async def do_promo(message: Message, code: str):
    uid = message.from_user.id
    pr = q("SELECT * FROM promo_codes WHERE code=?", (code.strip().upper(),), one=True)
    if not pr:
        return await message.reply(f"{E('lock')} <b>Промокод не найден!</b>")
    if pr["max_uses"] and pr["max_uses"] > 0 and pr["uses"] >= pr["max_uses"]:
        return await message.reply(f"{E('lock')} Промокод исчерпан.")
    if q("SELECT 1 FROM promo_uses WHERE user_id=? AND promo_id=?", (uid, pr["id"]), one=True):
        return await message.reply(f"{E('lock')} Ты уже использовал этот промокод.")
    if x("UPDATE promo_codes SET uses=uses+1 WHERE id=? AND (max_uses=0 OR uses<max_uses)", (pr["id"],))[0] != 1:
        return await message.reply(f"{E('lock')} Промокод исчерпан.")
    x("INSERT INTO promo_uses(user_id,promo_id,used_at) VALUES(?,?,?)", (uid, pr["id"], now()))
    add_coin(uid, pr["reward"])
    await message.reply(box(f"{E('donate')} <b>Промокод активирован!</b>", f"💰 +{fmt(pr['reward'])} RCOIN"))


@dp.message(P("промо"))
async def cmd_promo(message: Message):
    p = message.text.split()
    if len(p) >= 2:
        return await do_promo(message, p[1])
    await message.reply("Активация: <code>промо КОД</code>")


@dp.message(P("создатьпромо"))
async def cmd_promo_create(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Только для администраторов.")
    p = message.text.split()
    if len(p) < 3 or parse_amount(p[2]) <= 0:
        return await message.reply("Формат: <code>создатьпромо КОД СУММА [лимит]</code> (лимит 0 = безлимит)")
    lim = int(p[3]) if len(p) > 3 and p[3].isdigit() else 0
    try:
        x("INSERT INTO promo_codes(code,reward,max_uses,created_by,created_at) VALUES(?,?,?,?,?)", (p[1].upper(), parse_amount(p[2]), lim, message.from_user.id, now()))
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return await message.reply("Такой код уже есть.")
    await message.reply(f"✅ Промокод <code>{esc(p[1].upper())}</code>: {fmt(parse_amount(p[2]))} RCOIN, лимит {lim or '∞'}\n🔗 <code>{deeplink('promo_' + p[1].upper())}</code>")


# ============================ РЕФЕРАЛЫ ============================
@view("refs")
async def v_refs(uid: int, private: bool):
    u = get_user(uid)
    n = q("SELECT COUNT(*) n FROM referrals WHERE referrer_id=?", (uid,), one=True)["n"]
    avail = u["referral_earnings"] - u["referral_withdrawn"]
    t = (f"{E('referral')} <b>Реферальная система</b>\n\n👥 Приглашено: {n}\n💰 Заработано: {fmt(u['referral_earnings'])}\n"
         f"💸 Выведено: {fmt(u['referral_withdrawn'])}\n📊 Доступно: <b>{fmt(avail)}</b>\n\n"
         f"За каждого друга +25 000 RCOIN и {REF_PERCENT}% от его ставок.\n🔗 Твоя ссылка:\n<code>{deeplink(u['referral_code'])}</code>")
    return t, kb([btn("Вывести всё", "ref:out", "balance")], [btn("Назад", "menu:profile", "door")])


reg_view("refs", "рефералы", "реф")


@dp.callback_query(F.data == "ref:out")
async def cb_ref_out(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    avail = u["referral_earnings"] - u["referral_withdrawn"]
    if avail <= 0:
        return await ans(cb, "Нечего выводить", True)
    if x("UPDATE users SET referral_withdrawn=referral_withdrawn+?, balance_coin=balance_coin+? WHERE user_id=? AND referral_earnings-referral_withdrawn>=?",
         (avail, avail, u["user_id"], avail))[0] != 1:
        return await ans(cb)
    await ans(cb, f"+{fmt(avail)} RCOIN", True)
    t, k = await v_refs(u["user_id"], True)
    await safe_edit(cb, t, k)


@dp.message(P("вывести"))
async def cmd_ref_out(message: Message):
    u = get_user(message.from_user.id)
    avail = u["referral_earnings"] - u["referral_withdrawn"]
    if avail <= 0:
        return await message.reply("Нечего выводить.")
    if x("UPDATE users SET referral_withdrawn=referral_withdrawn+?, balance_coin=balance_coin+? WHERE user_id=? AND referral_earnings-referral_withdrawn>=?",
         (avail, avail, u["user_id"], avail))[0] == 1:
        await message.reply(f"{E('check')} Выведено {fmt(avail)} RCOIN.")


# ============================ ПРОФИЛЬ: ник, о себе, юзернейм ============================
@dp.message(P("сменить"))
async def cmd_rename(message: Message):
    p = message.text.split(maxsplit=2)
    if len(p) < 3 or p[1].lower() != "ник":
        return await message.reply("Формат: <code>сменить ник НовоеИмя</code> (150 000 RCOIN)")
    name = p[2].strip()
    if not 2 <= len(name) <= 30:
        return await message.reply("Имя от 2 до 30 символов.")
    if not spend(message.from_user.id, 150000):
        return await message.reply(f"{E('lock')} Нужно 150 000 RCOIN.")
    update_user(message.from_user.id, display_name=name)
    await message.reply(f"{E('check')} Имя изменено на <b>{esc(name)}</b>")


@dp.message(P("о"))
async def cmd_about_me(message: Message):
    p = message.text.split(maxsplit=2)
    if len(p) < 2:
        return
    sub = p[1].lower()
    if sub == "боте":
        return await cmd_about(message)
    if sub != "себе":
        return
    if len(p) == 2:
        u = get_user(message.from_user.id)
        return await message.reply(f"📝 <b>О себе:</b> {esc(u['about_text'] or 'не указано')}\n\nИзменить: <code>о себе Новый текст</code>")
    if len(p[2]) > 300:
        return await message.reply("До 300 символов.")
    update_user(message.from_user.id, about_text=p[2].strip())
    await message.reply(f"{E('check')} Описание обновлено!")


async def cmd_about(message: Message):
    await message.reply(f"{E('games')} <b>О RCOIN·BOT</b>\n\nИгровой бот: 18 игр, NFT-маркет и коллекционные подарки, склад, зимний ивент, "
                        "ежедневный бонус 5×5, банк, чеки, промокоды, рефералы, авто-чеки из казны, веб-апп с ареной.\n\n"
                        f"📢 {esc(REQUIRED_CHANNEL)} · 💬 {esc(REQUIRED_CHAT)}")


@dp.message(P("+юзер"))
async def cmd_buy_username(message: Message):
    p = message.text.split()
    if len(p) < 2:
        return await message.reply("Формат: <code>+юзер @ник</code> (100 000 000 RCOIN)")
    name = p[1].lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", name):
        return await message.reply("Ник: 3-20 символов, латиница, цифры и _")
    if q("SELECT 1 FROM users WHERE lower(custom_username)=?", (name.lower(),), one=True):
        return await message.reply("Этот юзернейм уже занят.")
    if not spend(message.from_user.id, 100_000_000):
        return await message.reply(f"{E('lock')} Нужно 100 000 000 RCOIN.")
    treasury_add(100_000_000)
    update_user(message.from_user.id, custom_username=name)
    await message.reply(box(f"{E('nft')} <b>ЮЗЕРНЕЙМ КУПЛЕН!</b>", f"🔹 @{esc(name)}"))


# ============================ ДОНАТ (Telegram Stars) ============================
DONATE_RATE = 10_000_000       # 1 ⭐ = 10 000 000 RCOIN
DONATE_MIN_STARS = 10          # минимум 10 ⭐ = 100 000 000 RCOIN


@dp.message(P("донат"))
async def cmd_donate(message: Message):
    u = get_user(message.from_user.id)
    await message.reply(
        f"{E('donate')} <b>ПОПОЛНЕНИЕ RCOIN</b>\n\n"
        f"{E('balance')} Баланс: <b>{fmt(u['balance_coin'])}</b> RCOIN\n"
        f"{E('treasury')} Архив: {fmt(u.get('archive_coin') or 0)}\n\n"
        f"⭐ <b>10 звёзд</b> → 100 000 000 RCOIN\n"
        f"⭐ <b>100 звёзд</b> → 1 000 000 000 RCOIN\n"
        f"Минимальная покупка — {DONATE_MIN_STARS} ⭐. Курс: 1 ⭐ = {fmt(DONATE_RATE)} RCOIN.",
        reply_markup=kb([btn("10 ⭐ → 100кк", "don:buy:10", "star")],
                        [btn("100 ⭐ → 1ккк", "don:buy:100", "star")],
                        [btn("Своя сумма", "don:stars", "donate")],
                        [btn("RUBIN Premium · 100 ⭐", "don:premium", "diamond")]))


@dp.callback_query(F.data.startswith("don:buy:"))
async def cb_don_preset(cb: CallbackQuery):
    await _donate_invoice(cb.from_user.id, int(cb.data.split(":")[2]))
    await ans(cb)


@dp.callback_query(F.data == "don:premium")
async def cb_don_premium(cb: CallbackQuery):
    uid = cb.from_user.id
    if is_premium(uid):
        return await ans(cb, "Premium уже активен", True)
    await stars_invoice(uid, 100, "RUBIN Premium на 30 дней",
                        "Галочка «Лудоман», +50% к выигрышу и TGP-эмодзи", f"premium:{uid}")
    await ans(cb, "Счёт выставлен")


@dp.callback_query(F.data == "don:stars")
async def cb_don(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "stars", f"Сколько звёзд ⭐ потратить? Минимум {DONATE_MIN_STARS}.")


async def stars_invoice(uid: int, stars: int, title: str, description: str, payload: str) -> bool:
    """Счёт Telegram Stars с произвольным payload (донат, премиум, сервер)."""
    try:
        await bot.send_invoice(chat_id=uid, title=title, description=description[:255],
                               payload=payload, provider_token="", currency="XTR",
                               prices=[LabeledPrice(label=title[:32], amount=int(stars))])
        return True
    except Exception as e:
        log.warning("invoice %s: %s", payload, e)
        try:
            await bot.send_message(uid, "Не удалось создать счёт. Открой диалог с ботом и попробуй снова.")
        except Exception:
            pass
        return False


async def _donate_invoice(uid: int, stars: int) -> bool:
    stars = int(stars)
    coins = stars * DONATE_RATE
    if stars < DONATE_MIN_STARS:
        try:
            await bot.send_message(uid, f"Минимальная покупка — {DONATE_MIN_STARS} ⭐.")
        except Exception:
            pass
        return False
    try:
        await bot.send_invoice(chat_id=uid, title="Пополнение RCOIN",
                               description=f"{fmt(coins)} RCOIN за {stars} ⭐",
                               payload=f"donate:{coins}", provider_token="", currency="XTR",
                               prices=[LabeledPrice(label=f"{fmt(coins)} RCOIN", amount=stars)])
        return True
    except Exception as e:
        log.warning("invoice: %s", e)
        try:
            await bot.send_message(uid, "Не удалось создать счёт. Открой диалог с ботом и попробуй снова.")
        except Exception:
            pass
        return False


@flow("stars")
async def f_stars(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or not DONATE_MIN_STARS <= int(txt) <= 100000:
        return await m.reply(f"Введи целое число звёзд, не меньше {DONATE_MIN_STARS}.")
    if await _donate_invoice(m.from_user.id, int(txt)):
        await state.clear()


@dp.pre_checkout_query()
async def on_pre_checkout(q_: PreCheckoutQuery):
    await q_.answer(ok=True)


@dp.message(F.successful_payment)
async def on_paid(message: Message):
    sp = message.successful_payment
    if kv_get("pay:" + sp.telegram_payment_charge_id):
        return
    kv_set("pay:" + sp.telegram_payment_charge_id, "1")
    uid = message.from_user.id
    payload = sp.invoice_payload or ""
    if payload.startswith("premium:"):
        set_premium(uid, 30 * 86400)
        give_badge(uid, "blue")
        u = get_user(uid)
        if not u.get("profile_emoji"):
            update_user(uid, profile_emoji="5801043446257833221", profile_emoji_fb="💎")
        await message.reply(box("💎 <b>RUBIN PREMIUM АКТИВЕН</b>",
                                "30 дней премиума и голубая галочка",
                                "Ранг: <b>Лудоман</b> · +50% к выигрышу",
                                "TGP-эмодзи добавлено в профиль"))
        return
    if payload.startswith("server:"):
        try:
            tier = int(payload.split(":")[1])
        except (ValueError, IndexError):
            tier = -1
        sv = SERVER_BY_TIER.get(tier)
        if sv:
            grant_server(uid, tier)
            await message.reply(box("🖥 <b>СЕРВЕР КУПЛЕН</b>", f"«{sv[1]}» на 30 дней",
                                    f"Доход: {fmt(sv[3])} RCOIN/сутки", "Забери добычу в разделе «Майнинг»"))
        return
    coins = sp.total_amount * DONATE_RATE
    over = add_coin(uid, coins)
    note = f"\n🏛 Сверх лимита в Архив: {fmt(over)}" if over else ""
    await message.reply(box(f"{E('star')} <b>ПОПОЛНЕНИЕ УСПЕШНО!</b>",
                            f"💰 +{fmt(coins - over)} RCOIN{note}", "Спасибо! 🎉"))


# ============================ ЗАРАБОТОК / РЕКЛАМА ============================
@view("earn")
async def v_earn(uid: int, private: bool):
    ads = q("SELECT * FROM ads WHERE status='active' AND current_subs<target_subs")
    rows = []
    lines = [f"{E('balance')} <b>ЗАРАБОТАЙ RCOIN</b>\n", "• Ежедневный бонус 5×5 • Ивенты (склад, босс, колесо) • Квесты • Бонус раз в час • Барабан раз в сутки\n"]
    if ads:
        lines.append("📢 <b>Подпишись на каналы:</b>")
    for a in ads:
        done = q("SELECT claimed FROM subscriptions WHERE user_id=? AND ad_id=?", (uid, a["id"]), one=True)
        rows.append([btn(f"{'✅' if done and done['claimed'] else '📢'} {a['channel_link']} +{fmt(a['price_per_sub'])}", f"ad:s:{a['id']}")])
    rows.append([btn("Ежедневный 5×5", "menu:db5", "question"), btn("Ивенты", "menu:events", "star")])
    if is_admin(uid):
        rows.append([btn("➕ Создать рекламу (админ)", "ad:new", "ad")])
    rows.append([btn("Назад", "menu:main", "door")])
    return "\n".join(lines), kb(*rows)


reg_view("earn", "рекл", "заработать")


@dp.callback_query(F.data.startswith("ad:"))
async def cb_ads(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    uid = cb.from_user.id
    if parts[1] == "new":
        if not is_admin(uid):
            return await ans(cb, "Только для админов", True)
        return await ask(cb, state, "ad_ch", "Канал для рекламы (@channel). Бот должен быть админом канала, чтобы проверять подписку:")
    ad = q("SELECT * FROM ads WHERE id=? AND status='active'", (int(parts[2]),), one=True)
    if not ad:
        return await ans(cb, "Задание неактуально", True)
    if q("SELECT 1 FROM subscriptions WHERE user_id=? AND ad_id=? AND claimed=1", (uid, ad["id"]), one=True):
        return await ans(cb, "Награда уже получена", True)
    try:
        mem = await bot.get_chat_member(chat_id=ad["channel_link"], user_id=uid)
        ok = mem.status in ("member", "administrator", "creator")
    except Exception:
        return await ans(cb, "Не могу проверить подписку (бот не админ канала)", True)
    if not ok:
        return await ans(cb, f"Сначала подпишись на {ad['channel_link']}", True)
    try:
        x("INSERT INTO subscriptions(user_id,ad_id,claimed,claimed_at) VALUES(?,?,1,?)", (uid, ad["id"], now()))
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return await ans(cb, "Награда уже получена", True)
    add_coin(uid, ad["price_per_sub"])
    x("UPDATE ads SET current_subs=current_subs+1 WHERE id=?", (ad["id"],))
    x("UPDATE ads SET status='completed' WHERE id=? AND current_subs>=target_subs", (ad["id"],))
    await ans(cb, f"+{fmt(ad['price_per_sub'])} RCOIN!", True)
    t, k = await v_earn(uid, True)
    await safe_edit(cb, t, k)


@flow("ad_ch")
async def f_ad_ch(m: Message, state: FSMContext, d, txt):
    if not txt.startswith("@"):
        return await m.reply("Введи @username канала.")
    await step(m, state, "ad_price", "Награда за подписку (RCOIN):", channel=txt)


@flow("ad_price")
async def f_ad_price(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt)
    if n <= 0:
        return await m.reply("Введи сумму.")
    await step(m, state, "ad_subs", "Сколько подписчиков нужно:", channel=d["channel"], price=n)


@flow("ad_subs")
async def f_ad_subs(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or int(txt) < 1:
        return await m.reply("Введи число.")
    subs = int(txt)
    total = subs * d["price"]
    if not spend(m.from_user.id, total):
        await state.clear()
        return await m.reply(f"Нужно {fmt(total)} RCOIN.")
    aid = x("INSERT INTO ads(owner_id,channel_link,price_per_sub,target_subs,paid_points,created_at) VALUES(?,?,?,?,?,?)",
            (m.from_user.id, d["channel"], d["price"], subs, total, now()))[1]
    await state.clear()
    await m.reply(f"{E('check')} Реклама #{aid} создана: {esc(d['channel'])}, {fmt(d['price'])} × {subs} = {fmt(total)} RCOIN.")


# ============================ ЕЖЕДНЕВНЫЙ БОНУС 5×5 ============================
DB5 = {1: (3, 150_000), 2: (4, 250_000), 3: (5, 400_000), 4: (6, 600_000), 5: (7, 900_000), 6: (8, 1_300_000)}


def db5_cfg(streak: int) -> Tuple[int, int]:
    return DB5.get(streak, (9, 2_000_000))


async def db5_verified(uid: int) -> bool:
    need = "@" + BOT_USERNAME.lower()
    if need in (get_user(uid)["about_text"] or "").lower():
        return True
    try:
        chat = await bot.get_chat(uid)
        return need in (getattr(chat, "bio", None) or "").lower()
    except Exception as e:
        log.debug("bio check: %s", e)
        return False


def db5_kb(row: dict) -> InlineKeyboardMarkup:
    grid, opened = json.loads(row["grid"]), json.loads(row["opened"])
    rows = []
    for r in range(5):
        line = []
        for c in range(5):
            i = r * 5 + c
            if i in opened:
                line.append(btn(f"{fmt(grid[i] // 1000)}к" if grid[i] else "▫️", "noop"))
            else:
                line.append(qbtn(f"db5:o:{i}"))
        rows.append(line)
    if opened and row["status"] == "open":
        rows.append([btn(f"💰 Забрать {fmt(row['pot'])}", "db5:c", "win")])
    return kb(*rows)


def db5_text(row: dict, streak_cfg: Tuple[int, int], extra: str = "") -> str:
    k, mx = streak_cfg
    opened = json.loads(row["opened"])
    return (f"{E('question')} <b>ЕЖЕДНЕВНЫЙ БОНУС 5×5</b>\n\n🔥 Серия: <b>{row['streak']}</b> дн.\n🗂 Можно открыть ячеек: <b>{k}</b> (открыто {len(opened)})\n"
            f"💰 Максимальный приз ячейки: {fmt(mx)}\n🎁 Накоплено: <b>{fmt(row['pot'])}</b>\n{extra}\n<i>Чем длиннее серия — тем больше ячеек и призов!</i>")


@view("db5")
async def v_db5(uid: int, private: bool):
    if not await db5_verified(uid):
        return (f"{E('question')} <b>Ежедневный бонус 5×5</b>\n\nЧтобы играть, добавь <code>@{esc(BOT_USERNAME)}</code> в описание профиля Telegram («О себе») "
                f"или командой <code>о себе @{esc(BOT_USERNAME)} Привет</code> и нажми «Проверить».",
                kb([btn("✅ Проверить", "db5:chk")], [btn("Назад", "menu:main", "door")]))
    d = today()
    row = q("SELECT * FROM daily5 WHERE user_id=? AND day=?", (uid, d), one=True)
    if not row:
        u = get_user(uid)
        yday = (datetime.now(MSK) - timedelta(days=1)).strftime("%Y-%m-%d")
        streak = u["db5_streak"] + 1 if u["db5_last_day"] == yday else 1
        k, mx = db5_cfg(streak)
        p = min(0.45 + 0.07 * streak, 0.9)
        grid = [max(5000, int(mx * random.random() ** 2) // 1000 * 1000) if random.random() < p else 0 for _ in range(25)]
        x("INSERT OR IGNORE INTO daily5(user_id,day,streak,grid,opened,pot,status) VALUES(?,?,?,?,?,0,'open')", (uid, d, streak, json.dumps(grid), "[]"))
        update_user(uid, db5_streak=streak, db5_last_day=d)
        row = q("SELECT * FROM daily5 WHERE user_id=? AND day=?", (uid, d), one=True)
    if row["status"] == "paid":
        return (f"{E('question')} <b>Бонус на сегодня получен!</b>\n🔥 Серия: {row['streak']} дн. Приходи завтра — ячеек будет больше!",
                kb([btn("Назад", "menu:main", "door")]))
    return db5_text(row, db5_cfg(row["streak"])), db5_kb(row)


@dp.message(P("ежедневный", "дб5", "бонус5"))
async def cmd_db5(message: Message):
    t, k = await v_db5(message.from_user.id, True)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data.startswith("db5:"))
async def cb_db5(cb: CallbackQuery):
    uid = cb.from_user.id
    act = cb.data.split(":")[1]
    if act == "chk":
        if not await db5_verified(uid):
            return await ans(cb, "Юзернейм бота не найден в описании. Добавь и повтори.", True)
        await ans(cb, "Проверено!")
        t, k = await v_db5(uid, True)
        return await safe_edit(cb, t, k)
    row = q("SELECT * FROM daily5 WHERE user_id=? AND day=?", (uid, today()), one=True)
    if not row or row["status"] != "open":
        return await ans(cb, "Поле недоступно. Открой бонус заново.", True)
    cfg = db5_cfg(row["streak"])
    grid, opened = json.loads(row["grid"]), json.loads(row["opened"])
    pot = row["pot"]
    if act == "o":
        i = int(cb.data.split(":")[2])
        if i in opened or len(opened) >= cfg[0]:
            return await ans(cb, "Нельзя", True)
        opened.append(i)
        pot += grid[i]
        x("UPDATE daily5 SET opened=?, pot=? WHERE user_id=? AND day=? AND status='open'", (json.dumps(opened), pot, uid, today()))
        note = f"+{fmt(grid[i])}" if grid[i] else "пусто"
        if len(opened) < cfg[0]:
            row = q("SELECT * FROM daily5 WHERE user_id=? AND day=?", (uid, today()), one=True)
            await safe_edit(cb, db5_text(row, cfg, f"🔹 Ячейка: <b>{note}</b>"), db5_kb(row))
            return await ans(cb, note)
        await ans(cb, note)
    if x("UPDATE daily5 SET status='paid' WHERE user_id=? AND day=? AND status='open'", (uid, today()))[0] != 1:
        return
    pot = q("SELECT pot FROM daily5 WHERE user_id=? AND day=?", (uid, today()), one=True)["pot"]
    add_coin(uid, pot)
    row = q("SELECT * FROM daily5 WHERE user_id=? AND day=?", (uid, today()), one=True)
    await safe_edit(cb, box(f"{E('win')} <b>Бонус 5×5 получен!</b>", f"💰 +{fmt(pot)} RCOIN", f"🔥 Серия: {row['streak']} дн. Завтра — {db5_cfg(row['streak'] + 1)[0]} ячеек!"),
                    db5_kb(row))


# ============================ NFT / ПОДАРКИ / СКЛАД ============================
# Базовая модель NFT редкости не имеет. Две редкости открываются только после улучшения.
RARITIES = ["common", "rare", "epic"]
UPGRADE_RARITIES = ["rare", "epic"]
RARITY_EMOJI = {"common": "⚪", "rare": "🟣", "epic": "🟠", "uncommon": "🔵", "legendary": "🟠"}
RARITY_NAME = {"common": "Без редкости", "rare": "Редкий", "epic": "Эпический",
               "uncommon": "Редкий", "legendary": "Эпический"}
RARITY_BASE = {"common": 50_000, "rare": 250_000, "epic": 600_000,
               "uncommon": 250_000, "legendary": 600_000}
ROLLIX_PRICE = 250_000_000
ROLLIX_TOTAL = 500
OWNER_NFT_ID = 1
INFINITE_PRICE = -1
NFT_POOL = {
    "common": [("Снеговик-неудачник", "⛄"), ("Носок с дыркой", "🧦"), ("Мандаринка на удачу", "🍊"),
               ("Пельмень-талисман", "🥟"), ("Тапок Деда Мороза", "🥿"), ("Космический кот", "🐱"),
               ("Пузырчатая плёнка", "🫧"), ("Капибара в снегу", "🦫")],
    "rare": [("Оливье в вакууме", "🥗"), ("Селёдка под шубой (NFT)", "🐟"), ("Олень Рудольф в отпуске", "🦌"),
             ("Кот в гирлянде", "😼"), ("Бенгальский огонёк", "🎇"), ("Пиксельный дракон", "🐉"),
             ("Золотой мандарин", "🍊"), ("Снегурочка-хакер", "👩‍💻"), ("Шампанское 00:00", "🍾"),
             ("Хрустальная ёлка", "🎄"), ("Пингвин-диджей", "🐧"), ("Радужный единорог", "🦄")],
    "epic": [("Санта-майнер", "🎅"), ("Кибер-снеговик 2077", "🤖"), ("Мамонт под ёлкой", "🦣"),
             ("Звёздный олень", "✨"), ("Робот-бариста", "☕"), ("Дух Нового года", "🎆"),
             ("Золотой Дед Мороз", "👑"), ("Часы курантов", "🕛"), ("Ёлка-мультивселенная", "🌌"),
             ("Северное сияние Prime", "🌠"), ("GTA 6 Vice City", "🌴")],
}
MODELS = [("Стандартный", 1.0, 30), ("Зимний", 1.2, 25), ("Снежный", 1.4, 18), ("Золотой", 2.0, 12),
          ("Неоновый", 2.5, 8), ("Призрачный", 3.5, 5), ("Космический", 5.0, 2)]
BGS = [("Чёрный бархат", 1.0, 30), ("Обсидиан", 1.2, 25), ("Дым", 1.5, 18),
       ("Нуар", 2.0, 14), ("Оникс", 3.0, 8), ("Полночь", 4.0, 5)]
BG_ALIASES = {"Обычный": "Чёрный бархат", "Морозный": "Обсидиан", "Праздничный": "Дым",
              "Звёздный": "Нуар", "Северное сияние": "Оникс", "Галактика": "Полночь"}


def bg_label(name: str) -> str:
    return BG_ALIASES.get(str(name or ""), str(name or "Чёрный бархат"))


def bg_mult(name: str) -> float:
    key = bg_label(name)
    return next((m for nm, m, _ in BGS if nm == key), 1.0)
PHOTOS = ["🎄", "🎁", "⛄", "❄️", "🎅", "🤶", "🦌", "🎀", "✨", "🌲", "🔔", "🍊", "🥂", "🧸", "🐧", "🐲", "🦄", "🤖", "🌌", "👑"]


def nft_pool(rarity: str) -> list:
    """Старые редкости из БД сводим к трём актуальным."""
    key = str(rarity or "common")
    if key not in NFT_POOL:
        key = "epic" if key in ("legendary", "epic") else "rare" if key == "uncommon" else "common"
    return NFT_POOL[key]


# Кейсы: тематические наборы. Внутри — базовая модель без редкости;
# арт и одна из двух редкостей открываются только после улучшения.
CASES = [
    {"key": "ny", "name": "Новогодний", "price": 150_000, "icon": "🎄", "tag": "СЕЗОН",
     "accent": "#8b5cf6",
     "names": ["Снеговик-неудачник", "Мандаринка на удачу", "Олень Рудольф в отпуске",
               "Кот в гирлянде", "Хрустальная ёлка", "Дух Нового года"]},
    {"key": "gta", "name": "GTA 6 Vice", "price": 500_000, "icon": "🌴", "tag": "ЭКСКЛЮЗИВ",
     "accent": "#ff4fa3",
     "names": ["GTA 6 Vice City", "Капибара в Vice City", "Пальма на закате",
               "Неоновый олень", "Угнанный снеговик"]},
    {"key": "capy", "name": "Капибара", "price": 250_000, "icon": "🐹", "tag": "ХИТ",
     "accent": "#b98b5e",
     "names": ["Капибара в снегу", "Капибара-майнер", "Капибара в гирлянде",
               "Капибара-сантехник", "Капибара-космонавт"]},
    {"key": "penguin", "name": "Пингвин", "price": 200_000, "icon": "🐧", "tag": "МЕМ",
     "accent": "#4a9bff",
     "names": ["Пингвин-диджей", "Пингвин с ножом", "Пингвин-хакер",
               "Пингвин на льдине", "Пингвин-миллиардер"]},
    {"key": "space", "name": "Космос", "price": 400_000, "icon": "🌌", "tag": "RARE",
     "accent": "#a855f7",
     "names": ["Космический кот", "Звёздный олень", "Ёлка-мультивселенная",
               "Северное сияние Prime", "Планета Рубин"]},
    {"key": "gold", "name": "Золотой", "price": 1_000_000, "icon": "👑", "tag": "VIP",
     "accent": "#ffd76a",
     "names": ["Золотой мандарин", "Золотой Дед Мороз", "Часы курантов",
               "Золотая капибара", "Золотой пингвин"]},
    {"key": "cyber", "name": "Кибер 2077", "price": 750_000, "icon": "🤖", "tag": "NEON",
     "accent": "#22d3ee",
     "names": ["Кибер-снеговик 2077", "Робот-бариста", "Снегурочка-хакер",
               "Пиксельный дракон", "Неоновый мамонт"]},
    {"key": "cozy", "name": "Уютный", "price": 120_000, "icon": "☕", "tag": "ДОМ",
     "accent": "#f59e0b",
     "names": ["Оливье в вакууме", "Пельмень-талисман", "Носок с дыркой",
               "Тапок Деда Мороза", "Пузырчатая плёнка"]},
    {"key": "meme", "name": "Мемный", "price": 90_000, "icon": "😼", "tag": "FUN",
     "accent": "#34d399",
     "names": ["Селёдка под шубой (NFT)", "Мамонт под ёлкой", "Радужный единорог",
               "Бенгальский огонёк", "Кот в гирлянде"]},
    {"key": "premium", "name": "Премиум", "price": 2_000_000, "icon": "💠", "tag": "TOP",
     "accent": "#e879f9",
     "names": ["Рубин #1", "GTA 6 Vice City", "Дух Нового года",
               "Северное сияние Prime", "Капибара-миллиардер"]},
]
CASE_BY_KEY = {c["key"]: c for c in CASES}


def case_open(uid: int, key: str) -> dict:
    c = CASE_BY_KEY.get(str(key or ""))
    if not c:
        return {"ok": False, "err": "Такого кейса нет"}
    if not spend(uid, c["price"]):
        return {"ok": False, "err": f"Нужно {fmt(c['price'])} RCOIN"}
    name = random.choice(c["names"])
    model = random.choices(MODELS, weights=[w for _, _, w in MODELS])[0][0]
    bg = random.choices(BGS, weights=[w for _, _, w in BGS])[0][0]
    nid = make_nft(uid, name, "common", "blank", f"Из кейса «{c['name']}». Арт откроется после улучшения.",
                   c["price"] * 2, model=model, background=bg)
    make_nft_image(nid)
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    return {"ok": True, "id": nid, "name": name, "model": model, "case": c["name"],
            "url": f"/nft/{nid}?v=1", "balance": get_user(uid)["balance_coin"],
            "item": nft_public(n)}


def nft_public(n: dict, ver: int = 0) -> dict:
    level = int(n.get("level") or 1)
    return {"id": n["id"], "name": n["name"], "level": level,
            "model": n.get("model") or "Стандартный",
            "background": bg_label(n.get("background")),
            "rarity": RARITY_NAME.get(n.get("rarity") or "common", "Без редкости") if level > 1 else "Без редкости",
            "rarity_key": n.get("rarity") if level > 1 else "common",
            "value": nft_value(n),
            "upgrade_cost": nft_upgrade_cost(n),
            "url": f"/nft/{n['id']}?v={ver or level}",
            "in_balance": False, "in_profile": False}


def _sync_nft_sequence():
    if not DATABASE_URL:
        return
    try:
        x("SELECT setval(pg_get_serial_sequence('nft_items','id'), (SELECT MAX(id) FROM nft_items))")
    except Exception:
        log.debug("nft sequence sync failed", exc_info=True)


def make_nft(owner: int, name: str, rarity: str, photo: str = None, desc: str = "", price: int = None,
             model: str = None, background: str = None, nft_id: Optional[int] = None) -> int:
    if photo is None:
        photo = next((e for n, e in nft_pool(rarity) if n == name), random.choice(PHOTOS))
    price = price or RARITY_BASE.get(rarity, 50_000)
    model = model or random.choices(MODELS, weights=[w for _, _, w in MODELS])[0][0]
    background = background or random.choices(BGS, weights=[w for _, _, w in BGS])[0][0]
    if nft_id and int(nft_id) > 0:
        nft_id = int(nft_id)
        exists = q("SELECT 1 FROM nft_items WHERE id=?", (nft_id,), one=True)
        if exists:
            x("UPDATE nft_items SET owner_id=?, name=?, base_name=?, level=1, rarity=?, price=?, "
              "description=?, photo=?, model=?, background=? WHERE id=?",
              (owner, name, name, rarity, price, desc, photo, model, background, nft_id))
        else:
            x("INSERT INTO nft_items(id,owner_id,name,base_name,level,rarity,price,created_at,description,photo,model,background) "
              "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
              (nft_id, owner, name, name, 1, rarity, price, now(), desc, photo, model, background))
            _sync_nft_sequence()
        for key in ("nftpng", "nftsvg", "nftimg"):
            kv_set(f"{key}:{nft_id}", "")
        return nft_id
    return x("INSERT INTO nft_items(owner_id,name,base_name,level,rarity,price,created_at,description,photo,model,background) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
             (owner, name, name, 1, rarity, price, now(), desc, photo, model, background))[1]


OWNER_NFT_ASSET = Path(__file__).with_name("owner_nft_1.png")


def ensure_owner_nft():
    """Выдаёт владельцу NFT #1 с его фото и ценой ∞. Идемпотентно."""
    if not OWNER_ID or not OWNER_NFT_ASSET.exists():
        return
    try:
        raw = OWNER_NFT_ASSET.read_bytes()
        get_user(OWNER_ID)
        make_nft(OWNER_ID, "Рубин #1", "epic", OWNER_NFT_ASSET.name,
                 "Алмаз владельца Rubin bot. Единственный экземпляр.", INFINITE_PRICE,
                 model="Призрачный", background="Чёрный бархат", nft_id=OWNER_NFT_ID)
        NFT_DIR.mkdir(parents=True, exist_ok=True)
        dst = NFT_DIR / "owner_nft_1.png"
        dst.write_bytes(raw)
        kv_set(f"nftpng:{OWNER_NFT_ID}", base64.b64encode(raw).decode("ascii"))
        kv_set(f"nftimg:{OWNER_NFT_ID}", dst.name)
        kv_set(f"nftsvg:{OWNER_NFT_ID}", "")
        u = get_user(OWNER_ID)
        if not int(u.get("balance_nft_id") or 0):
            update_user(OWNER_ID, balance_nft_id=OWNER_NFT_ID)
        if not int(u.get("profile_nft_id") or 0):
            update_user(OWNER_ID, profile_nft_id=OWNER_NFT_ID)
        log.info("NFT владельца #%s готов", OWNER_NFT_ID)
    except Exception:
        log.exception("ensure_owner_nft")


def make_gift(owner: int, rarity: str, name: str = "Коллекционный бокс") -> Tuple[int, str]:
    for _ in range(5):
        code = "GIFT-" + gen_code(10, "ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        try:
            return x("INSERT INTO gifts(code,name,rarity,owner_id,created_at) VALUES(?,?,?,?,?)", (code, name, rarity, owner, now()))[1], code
        except (sqlite3.IntegrityError, psycopg2.IntegrityError):
            continue
    raise RuntimeError("gift code collision")


def gift_open(uid: int, gid: int) -> Optional[int]:
    g = q("SELECT * FROM gifts WHERE id=?", (gid,), one=True)
    if not g or g["used"] or g["owner_id"] not in (0, uid):
        return None
    if x("UPDATE gifts SET used=1, used_by=? WHERE id=? AND used=0 AND owner_id IN (0,?)", (uid, gid, uid))[0] != 1:
        return None
    name, emoji = random.choice(nft_pool(g["rarity"]))
    # Сразу красивый AI-арт, без пустой заглушки.
    return make_nft(uid, name, g["rarity"], "✨", "Открыто из коллекционного бокса")


def rollix_stock() -> int:
    raw = kv_get("rollix:stock")
    if raw is None:
        kv_set("rollix:stock", str(ROLLIX_TOTAL))
        return ROLLIX_TOTAL
    try:
        return max(0, int(raw))
    except Exception:
        return 0


def nft_is_infinite(n: dict) -> bool:
    try:
        return int(n.get("price") or 0) < 0
    except (TypeError, ValueError):
        return False


def nft_price_text(n: dict) -> str:
    return "∞" if nft_is_infinite(n) else fmt(n.get("price") or 0)


def nft_value(n: dict) -> int:
    if nft_is_infinite(n):
        return 0
    mm = next((m for nm, m, _ in MODELS if nm == n["model"]), 1.0)
    bm = bg_mult(n["background"])
    return int(RARITY_BASE.get(n["rarity"], 50_000) * mm * bm * (1 + 0.1 * (n["level"] - 1)))


NFT_EMOJI_KEYS = ["item_1", "item_2", "item_3", "item_4", "item_5", "item_6", "item_7",
                  "item_8", "item_9", "diamond", "star", "nft", "win", "treasury", "rubin", "blue", "ny"]


def nft_emoji_key(nft_id: int) -> str:
    return NFT_EMOJI_KEYS[int(nft_id) % len(NFT_EMOJI_KEYS)]


def nft_emoji_id(nft_id: int) -> str:
    return _emoji_id(nft_emoji_key(nft_id))


def nft_emoji(nft_id: int) -> str:
    key = nft_emoji_key(nft_id)
    b = (globals().get("BADGES") or {}).get(key)
    fb = b["fallback"] if b else FALLBACK.get(key, "🎨")
    eid = _emoji_id(key)
    if PREMIUM_EMOJI and eid:
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return fb


def nft_card(n: dict) -> str:
    sale = f"\n🛒 На продаже за <b>{fmt(n['sale_price'])}</b>" if n["for_sale"] else ""
    u = get_user(n["owner_id"])
    pins = []
    if int(u.get("balance_nft_id") or 0) == n["id"]:
        pins.append("в балансе")
    if int(u.get("profile_nft_id") or 0) == n["id"]:
        pins.append("в профиле")
    pin = ("\n📌 " + " · ".join(pins)) if pins else ""
    rarity = (f"✨ Редкость: {RARITY_NAME.get(n['rarity'], '—')}\n" if int(n["level"]) > 1
              else "✨ Редкость: появится после улучшения\n")
    return (f"{nft_emoji(n['id'])} <b>{esc(n['name'])}</b> <code>#{n['id']}</code>\n"
            + rarity
            + f"📊 Уровень: {n['level']}\n🎭 Модель: {esc(n['model'])}\n"
            f"🖼 Фон: {esc(bg_label(n['background']))}\n💰 Стоимость: <b>{nft_price_text(n)}</b>{'' if nft_is_infinite(n) else ' RCOIN'}{sale}\n📝 {esc(n['description'] or '—')}{pin}")


def nft_upgrade_cost(n: dict) -> int:
    if nft_is_infinite(n):
        return 0
    if "роликс" in str(n.get("name", "")).lower():
        return ROLLIX_PRICE
    return max(20_000, int(RARITY_BASE.get(n["rarity"], 50_000) * 0.25 * n["level"]))


def nft_upgrade(uid: int, nid: int) -> Tuple[bool, str, Optional[dict]]:
    """Улучшение NFT: открывает арт и одну из двух редкостей (редкий/эпический)."""
    n = q("SELECT * FROM nft_items WHERE id=? AND owner_id=?", (int(nid), uid), one=True)
    if not n:
        return False, "NFT не найден", None
    if nft_is_infinite(n):
        return False, "NFT владельца улучшать не нужно", None
    if n["for_sale"]:
        return False, "Сначала сними NFT с продажи", None
    cost = nft_upgrade_cost(n)
    if not spend(uid, cost):
        return False, f"Нужно {fmt(cost)} RCOIN", None
    level = int(n["level"]) + 1
    if int(n["level"]) <= 1 or n["rarity"] not in UPGRADE_RARITIES:
        rarity = random.choice(UPGRADE_RARITIES)
    else:
        rarity = n["rarity"]
    if "роликс" in str(n["name"]).lower():
        model, bg = "Космический", "Галактика"
    else:
        model = random.choices(MODELS, weights=[w for _, _, w in MODELS])[0][0]
        bg = random.choices(BGS, weights=[w for _, _, w in BGS])[0][0]
    n2 = {**n, "model": model, "background": bg, "level": level, "rarity": rarity, "photo": "✨"}
    val = nft_value(n2)
    x("UPDATE nft_items SET model=?, background=?, level=?, rarity=?, price=?, photo=? WHERE id=? AND owner_id=?",
      (model, bg, level, rarity, val, "✨", n["id"], uid))
    make_nft_image(n["id"])
    return True, f"NFT улучшен: {RARITY_NAME[rarity]}", q("SELECT * FROM nft_items WHERE id=?", (n["id"],), one=True)


def inv_get(uid: int) -> List[dict]:
    try:
        v = json.loads(get_user(uid)["inventory"] or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def inv_add(uid: int, key: str, n: int = 1):
    inv = inv_get(uid)
    for it in inv:
        if it.get("key") == key:
            it["qty"] = int(it.get("qty", 1)) + n
            break
    else:
        inv.append({"key": key, "qty": n})
    update_user(uid, inventory=json.dumps(inv))


@view("stash")
async def v_stash(uid: int, private: bool):
    inv = inv_get(uid)
    boxes = q("SELECT COUNT(*) n FROM gifts WHERE owner_id=? AND used=0", (uid,), one=True)["n"]
    nfts = q("SELECT COUNT(*) n FROM nft_items WHERE owner_id=?", (uid,), one=True)["n"]
    lines = [f"{E('diamond')} <b>ТВОЙ СКЛАД</b>\n", f"🎁 Коллекционных боксов: <b>{boxes}</b>\n🖼 NFT: <b>{nfts}</b>\n", "❄️ <b>Сувениры зимнего ивента:</b>"]
    if inv:
        for it in inv:
            lines.append(f"{E(it['key'])} {SOUVENIRS.get(it['key'], 'Сувенир')} — ×{it.get('qty', 1)}")
    else:
        lines.append("<i>Пока пусто — открывай «Зимний склад» в ивентах!</i>")
    return "\n".join(lines), kb([btn(f"Боксы ({boxes})", "inv:boxes", "donate"), btn(f"NFT ({nfts})", "inv:nfts:0", "nft")],
                                [btn("Маркет", "menu:market", "market"), btn("Ивенты", "menu:events", "star")],
                                [btn("Назад", "menu:main", "door")])


reg_view("stash", "склад", "инвентарь", "инвент", "мойсклад")


@dp.message(P("мой"))
async def cmd_my_sklad(message: Message):
    if len(message.text.split()) > 1 and message.text.lower().split()[1] == "склад":
        t, k = await v_stash(message.from_user.id, True)
        await message.reply(t, reply_markup=k)


@dp.callback_query(F.data.startswith("inv:"))
async def cb_inv(cb: CallbackQuery):
    parts = cb.data.split(":")
    uid = cb.from_user.id
    act = parts[1]
    if act == "boxes":
        gs = q("SELECT * FROM gifts WHERE owner_id=? AND used=0 ORDER BY id DESC LIMIT 20", (uid,))
        if not gs:
            await safe_edit(cb, "📭 Боксов нет. Купи их в маркете!", kb([btn("Маркет", "menu:market", "market")], [btn("Назад", "menu:stash", "door")]))
            return await ans(cb)
        rows = [[btn(f"{RARITY_EMOJI[g['rarity']]} {RARITY_NAME[g['rarity']]} бокс · {g['code']}", f"inv:g:{g['id']}")] for g in gs]
        rows.append([btn("Назад", "menu:stash", "door")])
        await safe_edit(cb, f"🎁 <b>Твои боксы</b> ({len(gs)})\nВнутри — случайный NFT той же редкости.", kb(*rows))
        return await ans(cb)
    if act == "g":
        g = q("SELECT * FROM gifts WHERE id=? AND owner_id=? AND used=0", (int(parts[2]), uid), one=True)
        if not g:
            return await ans(cb, "Бокс не найден", True)
        await safe_edit(cb, f"🎁 {RARITY_EMOJI[g['rarity']]} <b>{RARITY_NAME[g['rarity']]} бокс</b>\nКод: <code>{g['code']}</code>\n\n"
                            f"Передать другу: <code>передать подарок {g['code']} @ник</code>",
                        kb([btn("🎉 Открыть", f"inv:o:{g['id']}")], [btn("Назад", "inv:boxes")]))
        return await ans(cb)
    if act == "o":
        nid = gift_open(uid, int(parts[2]))
        if not nid:
            return await ans(cb, "Не удалось открыть бокс", True)
        n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
        await safe_edit(cb, box("🎉 <b>БОКС ОТКРЫТ!</b>", nft_card(n), "<i>NFT неулучшенный — улучши его в складе!</i>"),
                        kb([btn("Открыть карточку", f"nft:v:{nid}", "nft")], [btn("К боксам", "inv:boxes")]))
        return await ans(cb, "🎉")
    if act == "nfts":
        page = int(parts[2])
        total = q("SELECT COUNT(*) n FROM nft_items WHERE owner_id=?", (uid,), one=True)["n"]
        ns = q("SELECT * FROM nft_items WHERE owner_id=? ORDER BY CASE WHEN price < 0 THEN 0 ELSE 1 END, price DESC LIMIT 8 OFFSET ?", (uid, page * 8))
        if not ns and page == 0:
            await safe_edit(cb, "📭 У тебя нет NFT. Купи бокс в маркете и открой его!", kb([btn("Маркет", "menu:market", "market")], [btn("Назад", "menu:stash", "door")]))
            return await ans(cb)
        rows = [[btn(f"{n['photo']} {n['name']} · {nft_price_text(n)}" + (" 🛒" if n["for_sale"] else ""), f"nft:v:{n['id']}")] for n in ns]
        nav = []
        if page > 0:
            nav.append(btn("◀️", f"inv:nfts:{page - 1}"))
        if (page + 1) * 8 < total:
            nav.append(btn("▶️", f"inv:nfts:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([btn("Назад", "menu:stash", "door")])
        await safe_edit(cb, f"{E('nft')} <b>Твои NFT</b> ({total})", kb(*rows))
        return await ans(cb)


@dp.callback_query(F.data.startswith("nft:"))
async def cb_nft(cb: CallbackQuery, state: FSMContext):
    _, act, nid = cb.data.split(":")
    uid = cb.from_user.id
    n = q("SELECT * FROM nft_items WHERE id=?", (int(nid),), one=True)
    if not n or n["owner_id"] != uid:
        return await ans(cb, "NFT не найден или не твой", True)
    if act == "v":
        rows = []
        u = get_user(uid)
        in_bal = int(u.get("balance_nft_id") or 0) == int(nid)
        in_prof = int(u.get("profile_nft_id") or 0) == int(nid)
        rows.append([btn("Убрать из баланса" if in_bal else "В баланс", f"nft:bal:{nid}", "balance",
                          style="danger" if in_bal else "primary"),
                     btn("Убрать из профиля" if in_prof else "В профиль", f"nft:prof:{nid}", "profile",
                         style="danger" if in_prof else "success")])
        if not nft_is_infinite(n):
            if n["for_sale"]:
                rows.append([btn("Снять с продажи", f"nft:us:{nid}")])
            else:
                rows.append([btn(f"⚡ Улучшить ({fmt(nft_upgrade_cost(n))})", f"nft:up:{nid}")])
                rows.append([btn("✏️ Название (50к)", f"nft:rn:{nid}"), btn("🖼 Фото (50к)", f"nft:ph:{nid}")])
                rows.append([btn("📤 Передать", f"nft:tr:{nid}"), btn("🛒 Продать", f"nft:sl:{nid}")])
        rows.append([btn("Назад", "inv:nfts:0", "door")])
        await safe_edit(cb, nft_card(n), kb(*rows))
        return await ans(cb)
    if act in ("bal", "prof"):
        col = "balance_nft_id" if act == "bal" else "profile_nft_id"
        current = int(get_user(uid).get(col) or 0)
        new_value = 0 if current == int(nid) else int(nid)
        update_user(uid, **{col: new_value})
        await ans(cb, "Откреплено" if new_value == 0 else "Фото закреплено", True)
        return await cb_nft(cb.model_copy(update={"data": f"nft:v:{nid}"}), state)
    if nft_is_infinite(n) and act not in ("v", "bal", "prof"):
        return await ans(cb, "Это NFT владельца — изменить нельзя", True)
    if n["for_sale"] and act != "us":
        return await ans(cb, "Сначала сними NFT с продажи", True)
    if act == "up":
        ok, msg, n2 = nft_upgrade(uid, int(nid))
        if not ok:
            return await ans(cb, msg, True)
        await safe_edit(cb, box("⚡ <b>NFT УЛУЧШЕН!</b>", nft_card(n2)), kb([btn("Ещё раз", f"nft:v:{nid}")], [btn("К списку", "inv:nfts:0")]))
        return await ans(cb, "⚡ " + msg)
    if act == "us":
        x("UPDATE nft_items SET for_sale=0, sale_price=0 WHERE id=? AND owner_id=?", (n["id"], uid))
        n = q("SELECT * FROM nft_items WHERE id=?", (n["id"],), one=True)
        return await cb_nft(cb.model_copy(update={"data": f"nft:v:{nid}"}), state)
    prompts = {"rn": ("nft_rn", "Новое название NFT (до 30 символов). Стоимость 50 000 RCOIN:"),
               "ph": ("nft_ph", "Отправь один эмодзи для фото NFT. Стоимость 50 000 RCOIN:"),
               "tr": ("nft_tr", "Кому передать? Введи @юзернейм или ID игрока:"),
               "sl": ("nft_sl", f"За сколько RCOIN продать? (оценка {nft_price_text(n)}). Налог 5%:")}
    kind, text = prompts[act]
    await ask(cb, state, kind, text, nid=n["id"])


@flow("nft_rn")
async def f_nft_rn(m: Message, state: FSMContext, d, txt):
    if not 2 <= len(txt) <= 30:
        return await m.reply("Название от 2 до 30 символов.")
    if not q("SELECT 1 FROM nft_items WHERE id=? AND owner_id=?", (d["nid"], m.from_user.id), one=True) or not spend(m.from_user.id, 50000):
        await state.clear()
        return await m.reply("Нужно 50 000 RCOIN (или NFT не твой).")
    x("UPDATE nft_items SET name=? WHERE id=?", (txt, d["nid"]))
    await state.clear()
    await m.reply(f"✅ Название изменено на <b>{esc(txt)}</b>")


@flow("nft_ph")
async def f_nft_ph(m: Message, state: FSMContext, d, txt):
    if len(txt) > 8:
        return await m.reply("Отправь один эмодзи.")
    if not q("SELECT 1 FROM nft_items WHERE id=? AND owner_id=?", (d["nid"], m.from_user.id), one=True) or not spend(m.from_user.id, 50000):
        await state.clear()
        return await m.reply("Нужно 50 000 RCOIN (или NFT не твой).")
    x("UPDATE nft_items SET photo=? WHERE id=?", (txt, d["nid"]))
    await state.clear()
    await m.reply(f"✅ Фото теперь {esc(txt)}")


async def nft_transfer(uid: int, nid: int, target_token: str) -> str:
    if (target_token or "").strip().lstrip("@").lower() in ("rubinarxiv", "rubin_archive"):
        if not archive_take_nft(nid, uid):
            return "NFT не найден, не твой или стоит на продаже."
        return "✅ NFT отправлен в архив — его можно выиграть в апгрейдере."
    t = find_user(target_token)
    if not t:
        return "Игрок не найден (он должен запустить бота)."
    if t["user_id"] == uid:
        return "Нельзя передать самому себе."
    row = q("SELECT * FROM nft_items WHERE id=? AND owner_id=?", (nid, uid), one=True)
    if row and nft_is_infinite(row):
        return "NFT владельца нельзя передать."
    if x("UPDATE nft_items SET owner_id=? WHERE id=? AND owner_id=? AND for_sale=0", (t["user_id"], nid, uid))[0] != 1:
        return "NFT не найден, не твой или стоит на продаже."
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    try:
        await bot.send_message(t["user_id"], f"🎁 <b>Тебе передали NFT!</b>\n\n{nft_card(n)}")
    except Exception:
        pass
    return f"✅ NFT <b>{esc(n['name'])}</b> передан игроку {uname(t, False)}"


@flow("nft_tr")
async def f_nft_tr(m: Message, state: FSMContext, d, txt):
    r = await nft_transfer(m.from_user.id, d["nid"], txt)
    if r.startswith("Игрок не найден"):
        return await m.reply(r + " Введи другой ник или «отмена».")
    await state.clear()
    await m.reply(r)


@flow("nft_sl")
async def f_nft_sl(m: Message, state: FSMContext, d, txt):
    price = parse_amount(txt)
    if price <= 0:
        return await m.reply("Введи положительную цену.")
    if x("UPDATE nft_items SET for_sale=1, sale_price=? WHERE id=? AND owner_id=? AND for_sale=0", (price, d["nid"], m.from_user.id))[0] != 1:
        await state.clear()
        return await m.reply("Не удалось выставить NFT.")
    await state.clear()
    await m.reply(f"🛒 NFT #{d['nid']} выставлен на маркет за <b>{fmt(price)}</b> RCOIN.")


@dp.message(P("передать"))
async def cmd_transfer_item(message: Message):
    p = message.text.split()
    if len(p) >= 4 and p[1].lower() in ("нфт", "nft") and p[2].isdigit():
        return await message.reply(await nft_transfer(message.from_user.id, int(p[2]), p[3]))
    if len(p) >= 4 and p[1].lower() == "подарок":
        t = find_user(p[3])
        g = q("SELECT * FROM gifts WHERE code=?", (p[2].upper(),), one=True)
        if not t or not g or g["owner_id"] != message.from_user.id or g["used"]:
            return await message.reply("Подарок или игрок не найден.")
        x("UPDATE gifts SET owner_id=? WHERE id=? AND owner_id=? AND used=0", (t["user_id"], g["id"], message.from_user.id))
        try:
            await bot.send_message(t["user_id"], f"🎁 Тебе передали коллекционный бокс <code>{g['code']}</code>! Открой его в складе.")
        except Exception:
            pass
        return await message.reply(f"✅ Бокс передан игроку {uname(t, False)}")
    await message.reply(usage("<code>передать нфт ID @ник</code>\n<code>передать подарок КОД @ник</code>"))


@dp.message(P("подарок"))
async def cmd_gift(message: Message):
    p = message.text.split()
    if len(p) < 2:
        return await message.reply("Использование: <code>подарок GIFT-XXXXXXXXXX</code> — открыть коллекционный бокс по коду.")
    g = q("SELECT * FROM gifts WHERE code=?", (p[1].upper(),), one=True)
    if not g:
        return await message.reply(f"{E('lock')} Подарок не найден.")
    if g["used"]:
        return await message.reply(f"{E('lock')} Подарок уже открыт.")
    if g["owner_id"] not in (0, message.from_user.id):
        return await message.reply(f"{E('lock')} Этот подарок принадлежит другому игроку.")
    nid = gift_open(message.from_user.id, g["id"])
    if not nid:
        return await message.reply("Не удалось открыть подарок.")
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    await message.reply(box("🎉 <b>ПОДАРОК ОТКРЫТ!</b>", nft_card(n), "Улучшай в «склад» → NFT"))


# ============================ МАРКЕТ ============================
@view("market")
async def v_market(uid: int, private: bool):
    u = get_user(uid)
    cnt = q("SELECT COUNT(*) n FROM nft_items WHERE owner_id=?", (uid,), one=True)["n"]
    t = (f"{E('market')} <b>МАРКЕТ</b>\n\n{E('balance')} Баланс: {fmt(u['balance_coin'])} RCOIN\n{E('nft')} Твоих NFT: {cnt}\n\n"
         "🎁 <b>Коллекционные боксы</b> — внутри случайный новогодний или обычный NFT. Покупаешь → бокс в складе → открываешь → "
         "улучшаешь (модель, фон, фото, название).\n🛍 <b>Маркет игроков</b> — покупай и продавай NFT.\n🧰 <b>Магазин штук</b> — антилудо, щит, билеты.\n\n"
         + "\n".join(f"{RARITY_EMOJI[r]} {RARITY_NAME[r]} — {fmt(RARITY_BASE[r])}" for r in RARITIES))
    return t, kb([btn(f"🪙 Роликсы · {fmt(ROLLIX_PRICE)}", "mk:rollix", "nft")],
                 [btn("Купить боксы", "mk:boxes", "donate"), btn("Маркет игроков", "mk:list:0", "market")],
                 [btn("Магазин штук", "mk:shop", "settings"), btn("Мой склад", "menu:stash", "diamond")],
                 [btn("Назад", "menu:main", "door")])


reg_view("market", "маркет", "market")


@dp.callback_query(F.data.startswith("mk:"))
async def cb_market(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    uid = cb.from_user.id
    act = parts[1]
    if act == "rollix":
        stock = rollix_stock()
        text = (f"🪙 <b>РОЛИКСЫ</b>\n\n"
                f"Легендарный эксклюзив маркета. Всего в стоке: <b>{ROLLIX_TOTAL}</b>.\n"
                f"Осталось: <b>{fmt(stock)}</b> шт.\n"
                f"💰 Цена: <b>{fmt(ROLLIX_PRICE)}</b> RCOIN\n"
                f"⚡ Улучшение: <b>{fmt(ROLLIX_PRICE)}</b> RCOIN\n\n"
                "Стальной корпус, золотой рифлёный безель и чёрный циферблат — премиальная модель с космическим свечением.")
        rows = []
        if stock > 0:
            rows.append([btn(f"Купить за {fmt(ROLLIX_PRICE)}", "mk:rollix_buy", "donate", style="success")])
        rows.append([btn("Назад", "menu:market", "door")])
        try:
            raw = png_nft(488, "Роликсы", "🐧", "Космический", "Галактика", "epic", 1)
            await cb.message.answer_photo(BufferedInputFile(raw, filename="rollix.png"),
                                          caption=text, reply_markup=kb(*rows))
        except Exception:
            await safe_edit(cb, text, kb(*rows))
        return await ans(cb)
    if act == "rollix_buy":
        stock = rollix_stock()
        if stock <= 0:
            return await ans(cb, "Роликсы распроданы", True)
        if q("SELECT 1 FROM nft_items WHERE owner_id=? AND name='Роликсы'", (uid,), one=True):
            return await ans(cb, "У тебя уже есть Роликсы", True)
        if not spend(uid, ROLLIX_PRICE):
            return await ans(cb, f"Нужно {fmt(ROLLIX_PRICE)} RCOIN", True)
        kv_set("rollix:stock", str(stock - 1))
        treasury_add(ROLLIX_PRICE // 10)
        nid = make_nft(uid, "Роликсы", "epic", "🐧", "Эксклюзив маркета", ROLLIX_PRICE,
                       model="Космический", background="Галактика")
        n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
        raw = png_nft(nid, n["name"], n["photo"], n["model"], n["background"], n["rarity"], n["level"])
        try:
            await cb.message.answer_photo(BufferedInputFile(raw, filename=f"rollix_{nid}.png"),
                                          caption=nft_card(n),
                                          reply_markup=kb([btn("В профиль", f"nft:prof:{nid}", "profile")],
                                                          [btn("Маркет", "menu:market", "door")]))
        except Exception:
            await cb.message.answer(nft_card(n))
        return await ans(cb, "Роликсы куплены!", True)
    if act == "boxes":
        rows = [[btn(f"{RARITY_EMOJI[r]} {RARITY_NAME[r]} бокс — {fmt(RARITY_BASE[r])}", f"mk:buy:{r}")] for r in RARITIES]
        rows.append([btn("Назад", "menu:market", "door")])
        await safe_edit(cb, "🎁 <b>КОЛЛЕКЦИОННЫЕ БОКСЫ</b>\nВыбери бокс — он попадёт на твой склад, откроешь когда захочешь.", kb(*rows))
        return await ans(cb)
    if act == "buy":
        r = parts[2]
        if r not in RARITY_BASE:
            return await ans(cb, "Нет такого бокса", True)
        if not spend(uid, RARITY_BASE[r]):
            return await ans(cb, f"Нужно {fmt(RARITY_BASE[r])} RCOIN", True)
        treasury_add(RARITY_BASE[r] // 10)
        gid, code = make_gift(uid, r)
        await safe_edit(cb, box("🎁 <b>БОКС КУПЛЕН!</b>", f"{RARITY_EMOJI[r]} {RARITY_NAME[r]} бокс", f"Код: <code>{code}</code>", "Бокс лежит на складе."),
                        kb([btn("🎉 Открыть сейчас", f"inv:o:{gid}")], [btn("Ещё боксы", "mk:boxes"), btn("Склад", "menu:stash", "diamond")]))
        return await ans(cb, "Куплено!")
    if act == "list":
        page = int(parts[2])
        total = q("SELECT COUNT(*) n FROM nft_items WHERE for_sale=1", one=True)["n"]
        ns = q("SELECT * FROM nft_items WHERE for_sale=1 ORDER BY sale_price ASC LIMIT 6 OFFSET ?", (page * 6,))
        if not ns:
            await safe_edit(cb, "📭 На маркете пока нет NFT. Выставь свои из склада!", kb([btn("Назад", "menu:market", "door")]))
            return await ans(cb)
        lines = [f"{E('market')} <b>МАРКЕТ NFT</b> ({total})\n"]
        rows = []
        for n in ns:
            lines.append(f"{n['photo']} {RARITY_EMOJI[n['rarity']]} <b>{esc(n['name'])}</b> #{n['id']} · ур.{n['level']} · {esc(n['model'])}/{esc(n['background'])}\n   💰 {fmt(n['sale_price'])} · оценка {nft_price_text(n)}")
            rows.append([btn(f"Купить #{n['id']} · {fmt(n['sale_price'])}", f"mk:b:{n['id']}")])
        nav = []
        if page > 0:
            nav.append(btn("◀️", f"mk:list:{page - 1}"))
        if (page + 1) * 6 < total:
            nav.append(btn("▶️", f"mk:list:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([btn("Назад", "menu:market", "door")])
        await safe_edit(cb, "\n".join(lines), kb(*rows))
        return await ans(cb)
    if act == "b":
        n = q("SELECT * FROM nft_items WHERE id=? AND for_sale=1", (int(parts[2]),), one=True)
        if not n:
            return await ans(cb, "Уже продано", True)
        if n["owner_id"] == uid:
            return await ans(cb, "Это твой NFT", True)
        price = n["sale_price"]
        if not spend(uid, price):
            return await ans(cb, f"Нужно {fmt(price)} RCOIN", True)
        if x("UPDATE nft_items SET owner_id=?, for_sale=0, sale_price=0 WHERE id=? AND for_sale=1 AND owner_id=?", (uid, n["id"], n["owner_id"]))[0] != 1:
            add_coin(uid, price)
            return await ans(cb, "Уже продано", True)
        tax = price * 5 // 100
        treasury_add(tax)
        add_coin(n["owner_id"], price - tax)
        try:
            await bot.send_message(n["owner_id"], f"🛒 Твой NFT <b>{esc(n['name'])}</b> куплен за {fmt(price)} (налог 5%: {fmt(tax)}).")
        except Exception:
            pass
        await ans(cb, "NFT куплен!", True)
        return await cb_market(cb.model_copy(update={"data": "mk:list:0"}), state)
    if act == "shop":
        t = (f"🧰 <b>МАГАЗИН ШТУК</b>\n\n🚫 <b>Антилудо</b> — 100 000. Блокирует игры выбранному игроку на 5 минут "
             f"(или <code>/antiludo</code> ответом на сообщение).\n🛡 <b>Щит</b> — 150 000. 1 час защиты от антилудо.\n"
             f"🎟 <b>Лотерейный билет</b> — 10 000. Приз до x50!\n✏️ <b>Смена ника</b> — <code>сменить ник Имя</code> (150 000)\n"
             f"🏷 <b>Юзернейм</b> — <code>+юзер @ник</code> (100 000 000)")
        return await safe_edit(cb, t, kb([btn("🚫 Антилудо", "mk:anti"), btn("🛡 Щит", "mk:shield")], [btn("🎟 Билет", "mk:ticket")], [btn("Назад", "menu:market", "door")])) or await ans(cb)
    if act == "anti":
        return await ask(cb, state, "antiludo", "Кому наложить антилудо? Введи @юзернейм или ID (100 000 RCOIN):")
    if act == "shield":
        if not spend(uid, 150000):
            return await ans(cb, "Нужно 150 000 RCOIN", True)
        base = max(get_user(uid)["shield_until"], now())
        update_user(uid, shield_until=base + 3600)
        return await ans(cb, "🛡 Щит активен ещё час", True)
    if act == "ticket":
        if not spend(uid, 10000):
            return await ans(cb, "Нужно 10 000 RCOIN", True)
        mult = random.choices([0, 0.5, 1, 2, 5, 50], weights=[45, 20, 15, 12, 7.5, 0.5])[0]
        prize = int(10000 * mult)
        add_coin(uid, prize)
        return await ans(cb, f"🎟 Выпало x{mult}: +{fmt(prize)} RCOIN", True)


def apply_antiludo(att: Dict[str, Any], target: Dict[str, Any]) -> str:
    if target["user_id"] == att["user_id"]:
        return "Нельзя применить антилудо к себе."
    if target["shield_until"] > now():
        return f"🛡 У игрока щит ещё {dur(target['shield_until'] - now())}."
    if not spend(att["user_id"], 100_000):
        return "Нужно 100 000 RCOIN."
    treasury_add(100_000)
    update_user(target["user_id"], antiludo_until=now() + 300)
    return f"OK:🚫 <b>АНТИЛУДО!</b> Игрок <b>{uname(target, False)}</b> не сможет играть 5 минут. Списано 100 000 RCOIN."


@flow("antiludo")
async def f_antiludo(m: Message, state: FSMContext, d, txt):
    t = find_user(txt)
    if not t:
        return await m.reply("Игрок не найден. Введи другой ник или «отмена».")
    r = apply_antiludo(get_user(m.from_user.id), t)
    await state.clear()
    await m.reply(r[3:] if r.startswith("OK:") else r)
    if r.startswith("OK:"):
        try:
            await bot.send_message(t["user_id"], "🚫 <b>Тебя заблокировали в играх на 5 минут (антилудо)!</b>")
        except Exception:
            pass


@dp.message(P("антилудо", "antiludo"))
async def cmd_antiludo(message: Message):
    p = message.text.split()
    target = resolve_target(message, p[1] if len(p) > 1 else None)
    if not target:
        return await message.reply(usage("Ответь на сообщение игрока: <code>/antiludo</code>\nили <code>антилудо @ник</code>\nСтоимость 100 000 RCOIN, блок игр на 5 минут."))
    r = apply_antiludo(get_user(message.from_user.id), target)
    await message.reply(r[3:] if r.startswith("OK:") else f"{E('lock')} {r}")
    if r.startswith("OK:"):
        try:
            await bot.send_message(target["user_id"], "🚫 <b>Тебя заблокировали в играх на 5 минут (антилудо)!</b>")
        except Exception:
            pass


# ============================ ЗИМНИЕ ИВЕНТЫ ============================
STASH_CELLS, STASH_MIN, STASH_MAX = 3, 15_000, 1_000_000
BOSS_HP, BOSS_HP_FINAL = 1_000_000, 10_000_000
BOSS_REWARD, BOSS_REWARD_FINAL = 20_000_000, 100_000_000
WHEEL = [(5000, 20), (15000, 15), (50000, 12), (150000, 10), (500000, 7), (1500000, 4), (5000000, 1.5), (25000000, 0.4), (100000000, 0.1)]
QUESTS = [("games", "Сыграй 20 игр", 20, 250_000), ("wins", "Выиграй 10 раз", 10, 500_000),
          ("stash", "Открой зимний склад", 1, 100_000), ("boss", "Помоги Санте", 1, 150_000)]


def boss_state() -> Dict[str, Any]:
    d = today()
    r = q("SELECT * FROM event_progress WHERE id=1", one=True)
    nowd = datetime.now(MSK)
    final = nowd.month == 12 and nowd.day == 31
    mx = BOSS_HP_FINAL if final else BOSS_HP
    if not r or r["day"] != d or r["boss_max"] == 0:
        x("UPDATE event_progress SET boss_hp=?, boss_max=?, day=? WHERE id=1", (mx, mx, d))
        return {"hp": mx, "max": mx, "final": final}
    return {"hp": max(0, r["boss_hp"]), "max": r["boss_max"], "final": final}


def bar(cur: int, total: int, w: int = 12) -> str:
    f = int(w * cur / total) if total > 0 else 0
    return "▰" * f + "▱" * (w - f)


def boss_hit(uid: int, dmg: int) -> Optional[List[Tuple[int, int]]]:
    """Наносит урон. Если босс убит — выплачивает награду участникам и возвращает список (uid, сумма)."""
    st = boss_state()
    x("UPDATE event_progress SET boss_hp=" + ("GREATEST(0, boss_hp-%s)" if DATABASE_URL else "MAX(0, boss_hp-?)") + " WHERE id=1", (dmg,))
    x("INSERT INTO boss_hits(day,user_id,dmg) VALUES(?,?,?) ON CONFLICT(day,user_id) DO UPDATE SET dmg=dmg+excluded.dmg", (today(), uid, dmg))
    quest_inc(uid, "boss")
    hp = q("SELECT boss_hp FROM event_progress WHERE id=1", one=True)["boss_hp"]
    if hp > 0 or kv_get("boss_dead:" + today()):
        return None
    kv_set("boss_dead:" + today(), "1")
    pool = min(BOSS_REWARD_FINAL if st["final"] else BOSS_REWARD, treasury_get())
    if pool <= 0 or not treasury_take(pool):
        return []
    hits = q("SELECT user_id, dmg FROM boss_hits WHERE day=?", (today(),))
    total = sum(h["dmg"] for h in hits) or 1
    out = []
    for h in hits:
        amt = pool * h["dmg"] // total
        if amt > 0:
            add_coin(h["user_id"], amt)
            out.append((h["user_id"], amt))
    return out


async def boss_notify(payouts: Optional[List[Tuple[int, int]]]):
    if payouts is None:
        return
    for uid, amt in payouts:
        try:
            await bot.send_message(uid, f"🎅 <b>Санта побеждён!</b> Твоя доля награды: <b>+{fmt(amt)}</b> RCOIN")
            await asyncio.sleep(0.06)
        except Exception:
            pass
    try:
        await bot.send_message(ANNOUNCE_CHAT, f"🎅🎉 <b>Санта побеждён общими усилиями!</b> Награда {fmt(sum(a for _, a in payouts))} RCOIN разделена между участниками.")
    except Exception:
        pass


@view("events")
async def v_events(uid: int, private: bool):
    b = boss_state()
    pot = ev_pot()
    t = (f"{badge('ny')} <b>НОВОГОДНИЙ ИВЕНТ</b>\n\n"
         f"{E('games')} <b>Новогодние игры</b> — 7 игр, джекпот <b>{fmt(pot)}</b> RCOIN\n"
         f"   <code>игра снежки 10000</code> или кнопка ниже\n\n"
         f"{E('diamond')} <b>Зимний склад</b> — {STASH_CELLS} ячейки в день, приз {fmt(STASH_MIN)}–{fmt(STASH_MAX)} + сувениры\n"
         f"{E('crash')} <b>Санта-босс</b> — {fmt(b['hp'])}/{fmt(b['max'])} HP\n<code>{bar(b['max'] - b['hp'], b['max'])}</code>\n"
         f"{E('spin')} <b>Колесо удачи</b> — раз в 6 часов\n{E('treasury')} <b>Квесты</b> — ежедневные задания\n\n"
         "Помоги Санте монетами: <code>помочь санте 100к</code>")
    return t, kb([btn("Новогодние игры", "ev:games!", "games"), btn("Снежный марафон", "snowman:open", "item_1")],
                 [btn("Зимний склад", "ev:stash", "diamond"), btn("Санта-босс", "ev:boss", "crash")],
                 [btn("Колесо удачи", "ev:wheel", "spin"), btn("Квесты", "ev:quests", "treasury")],
                 [btn("Новогодняя галочка", "ev:nybadge", "ny"), btn("Чеканить NFT", "ev:mint", "nft")],
                 [btn("Мой склад", "menu:stash", "diamond")],
                 [btn("Назад", "menu:main", "door")])


reg_view("events", "ивенты", "ивент", "events")




# ============================ СНЕЖНЫЙ МАРАФОН ============================
SNOWMAN_NEED = 20
SNOWMAN_COOLDOWN = 20
SNOWMAN_PRIZE_MIN = 1_000_000_000
SNOWMAN_PRIZE_MAX = 10_000_000_000


def snowman_row(uid: int, day: Optional[str] = None) -> dict:
    day = day or today()
    row = q("SELECT * FROM snowman_daily WHERE user_id=? AND day=?", (uid, day), one=True)
    return row or {"user_id": uid, "day": day, "snowballs": 0, "snowmen": 0, "last_collect": 0, "updated_at": 0}


def snowman_collect(uid: int) -> dict:
    day = today()
    row = snowman_row(uid, day)
    wait = max(0, SNOWMAN_COOLDOWN - (now() - int(row.get("last_collect", 0) or 0)))
    if wait:
        return {"ok": False, "err": f"Следующая охота за снежками через {wait} сек.", "wait": wait}
    gained = random.randint(2, 5)
    x("INSERT INTO snowman_daily(user_id,day,snowballs,snowmen,last_collect,updated_at) VALUES(?,?,?,0,?,?) "
      "ON CONFLICT(user_id,day) DO UPDATE SET snowballs=snowman_daily.snowballs+excluded.snowballs, "
      "last_collect=excluded.last_collect, updated_at=excluded.updated_at",
      (uid, day, gained, now(), now()))
    row = snowman_row(uid, day)
    return {"ok": True, "gained": gained, "snowballs": int(row["snowballs"]), "snowmen": int(row["snowmen"])}


def snowman_build(uid: int) -> dict:
    day = today()
    row = snowman_row(uid, day)
    count = int(row["snowballs"]) // SNOWMAN_NEED
    if count < 1:
        return {"ok": False, "err": f"Нужно ещё {SNOWMAN_NEED - int(row['snowballs']) % SNOWMAN_NEED} снежков, чтобы слепить снеговика."}
    cost = count * SNOWMAN_NEED
    changed = x("UPDATE snowman_daily SET snowballs=snowballs-?, snowmen=snowmen+?, updated_at=? "
                "WHERE user_id=? AND day=? AND snowballs>=?", (cost, count, now(), uid, day, cost))[0]
    if not changed:
        return {"ok": False, "err": "Не удалось обновить снежки. Нажми ещё раз."}
    row = snowman_row(uid, day)
    return {"ok": True, "built": count, "snowballs": int(row["snowballs"]), "snowmen": int(row["snowmen"])}


def snowman_leaderboard(day: Optional[str] = None, limit: int = 10) -> list:
    day = day or today()
    return q("SELECT d.user_id,d.snowballs,d.snowmen,COALESCE(NULLIF(u.display_name,''),NULLIF(u.username,''),CAST(d.user_id AS TEXT)) AS name "
             "FROM snowman_daily d LEFT JOIN users u ON u.user_id=d.user_id WHERE d.day=? "
             "ORDER BY d.snowmen DESC,d.snowballs DESC,d.updated_at ASC LIMIT ?", (day, limit))


def snowman_text(uid: int) -> str:
    r = snowman_row(uid)
    top = snowman_leaderboard(limit=10)
    lines = ["⛄ <b>СНЕЖНЫЙ МАРАФОН</b>",
             f"❄️ Снежков собрано: <b>{fmt(r['snowballs'])}</b>",
             f"☃️ Снеговиков слеплено сегодня: <b>{fmt(r['snowmen'])}</b>",
             f"🧊 Для одного снеговика нужно <b>{SNOWMAN_NEED}</b> снежков.",
             "", "🏆 <b>ТОП ЗА СЕГОДНЯ</b>"]
    if top:
        for i, item in enumerate(top, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            lines.append(f"{medal} {esc(str(item['name'])[:24])} — <b>{fmt(item['snowmen'])}</b> ☃️ · {fmt(item['snowballs'])} ❄️")
    else:
        lines.append("Пока никто не начал марафон — стань первым!")
    lines += ["", "🎁 В конце дня топ-3 получают награды из казны: случайно от 1 до 10 млрд RCOIN каждому (если в казне достаточно средств).", "⏱ Сбор снежков доступен раз в 20 секунд."]
    return "\n".join(lines)


def distribute_snowman_rewards(day: str) -> list:
    """Однократно выплачивает топ-3 предыдущего дня из казны."""
    if kv_get("snowman:paid:" + day):
        return []
    winners = snowman_leaderboard(day, 3)
    paid = []
    for place, row in enumerate(winners, 1):
        exists = q("SELECT 1 FROM snowman_rewards WHERE day=? AND place=?", (day, place), one=True)
        if exists:
            continue
        prize = random.randint(SNOWMAN_PRIZE_MIN, SNOWMAN_PRIZE_MAX)
        # Сохраняем результат розыгрыша даже при пустой казне, чтобы не было двойных выплат.
        available = treasury_get()
        actual = min(prize, available) if available >= SNOWMAN_PRIZE_MIN else 0
        if actual >= SNOWMAN_PRIZE_MIN and treasury_take(actual):
            add_coin(int(row["user_id"]), actual)
            x("INSERT INTO snowman_rewards(day,user_id,place,amount,created_at) VALUES(?,?,?,?,?)",
              (day, int(row["user_id"]), place, actual, now()))
            paid.append((int(row["user_id"]), place, actual))
        else:
            x("INSERT INTO snowman_rewards(day,user_id,place,amount,created_at) VALUES(?,?,?,?,?)",
              (day, int(row["user_id"]), place, 0, now()))
    kv_set("snowman:paid:" + day, "1")
    return paid


@dp.message(P("snowman", "снеговик", "снеговики", "снежный марафон", "снежки собрать"))
async def cmd_snowman(message: Message):
    await message.reply(snowman_text(message.from_user.id), reply_markup=snowman_kb())


def snowman_kb() -> InlineKeyboardMarkup:
    return kb([btn("❄️ Собрать снежки", "snowman:collect", "item_1"),
               btn("☃️ Слепить снеговика", "snowman:build", "item_3")],
              [btn("🏆 Обновить топ", "snowman:open", "win")],
              [btn("↩️ К ивентам", "menu:events", "door")])


@dp.callback_query(F.data.startswith("snowman:"))
async def cb_snowman(cb: CallbackQuery):
    action = cb.data.split(":", 1)[1]
    uid = cb.from_user.id
    if action == "collect":
        result = snowman_collect(uid)
        if not result["ok"]:
            return await ans(cb, result["err"], True)
        await safe_edit(cb, snowman_text(uid), snowman_kb())
        return await ans(cb, f"+{result['gained']} ❄️ снежков!", True)
    if action == "build":
        result = snowman_build(uid)
        if not result["ok"]:
            return await ans(cb, result["err"], True)
        await safe_edit(cb, snowman_text(uid), snowman_kb())
        return await ans(cb, f"☃️ Слеплено снеговиков: {result['built']}!", True)
    await safe_edit(cb, snowman_text(uid), snowman_kb())
    await ans(cb)


# ============================ ЗИМНИЕ МИНИ-ИГРЫ (ивенты) ============================
SNOW_GAMES = {
    1: {"key": "snow", "name": "Снежки", "bp": (4.2, 4.2), "max": 0, "min": 5_000,
        "desc": "Три броска: 3 из 3 — победа x4.2"},
    2: {"key": "ice", "name": "Ледяная дорожка", "bp": (5.0, 5.0), "max": 0, "min": 10_000,
        "desc": "Угадай прорубь из 5 — победа x5"},
    3: {"key": "bear", "name": "Белый медведь", "bp": (3.0, 3.0), "max": 0, "min": 10_000,
        "desc": "Угадай лапу с рыбой из 3 — победа x3"},
    4: {"key": "santa", "name": "Сани Санты", "bp": (5.0, 5.0), "max": 0, "min": 25_000,
        "desc": "Довези сани до 5 000 км — победа x5"},
    5: {"key": "gift", "name": "Подарки", "bp": (3.0, 3.0), "max": 0, "min": 20_000,
        "desc": "Найди подарок в одной из трёх коробок — победа x3"},
    6: {"key": "mint", "name": "Пряничный забег", "bp": (5.0, 5.0), "max": 0, "min": 15_000,
        "desc": "Доберись до дома за 5 шагов — победа x5"},
}
EV_POT = "ev_pot"


def ev_pot(*_a) -> int:
    try:
        return int(kv_get(EV_POT) or 0)
    except Exception:
        return 0


def ev_add_pot(n: int):
    kv_set(EV_POT, str(ev_pot() + n))


def ev_award_snow(uid: int, bet: int) -> int:
    n = max(1, int(bet) // 10_000)
    u = get_user(uid)
    update_user(uid, ev_points=int(u.get("ev_points") or 0) + n)
    return n


EV_MINES_MIN = 10_000
EV_TOWER_MIN = 10_000
EV_ALIASES = {
    "снежки": "snow", "снежок": "snow", "1": "snow",
    "лёд": "ice", "лед": "ice", "ледяная": "ice", "дорожка": "ice", "2": "ice",
    "медведь": "bear", "мишка": "bear", "3": "bear",
    "сани": "santa", "санки": "santa", "4": "santa",
    "подарки": "gift", "подарок": "gift", "5": "gift",
    "пряники": "mint", "пряник": "mint", "забег": "mint", "6": "mint",
    "лабиринт": "lab", "лаб": "lab", "7": "lab",
}


def ev_game_index(key: str) -> int:
    return next((i for i, g in SNOW_GAMES.items() if g["key"] == key), 1)


def ev_games_view(uid: int) -> Tuple[str, InlineKeyboardMarkup]:
    u = get_user(uid)
    pot = ev_pot()
    lines = [f"{badge('ny')} <b>НОВОГОДНИЕ ИГРЫ</b> {E('item_6')}",
             f"<blockquote>{E('balance')} Баланс: <b>{fmt(u['balance_coin'])}</b> RCOIN\n"
             f"{E('item_7')} Джекпот ивентов: <b>{fmt(pot)}</b> RCOIN\n"
             f"{E('snowflake')} Снежинки: <b>{fmt(u.get('ev_points') or 0)}</b></blockquote>", ""]
    for i, g in SNOW_GAMES.items():
        lines.append(f"{E('item_' + str(i))} <b>{g['name']}</b> — {g['desc']}\n"
                     f"   Мин. <b>{fmt(g['min'])}</b> · выплата <b>x{g['bp'][0]:.1f}</b>")
    lines.append(f"{E('item_8')} <b>Ледяной лабиринт</b> — 3 развилки, выплата до <b>x5</b>\n"
                 f"   Мин. <b>{fmt(LAB_MIN)}</b>")
    lines.append(f"{E('mines')} <b>Снежные мины</b> — 5×5, 3 мины, забирай выигрыш до взрыва\n"
                 f"   Мин. <b>{fmt(EV_MINES_MIN)}</b>")
    lines.append(f"{E('games')} <b>Снежная башня</b> — 5 колонок, 9 уровней, до <b>x3.5</b>\n"
                 f"   Мин. <b>{fmt(EV_TOWER_MIN)}</b>")
    lines += ["", "<b>Как играть:</b> <code>игра снежки 10000</code>",
              "или нажми на игру — бот спросит ставку."]
    items = list(SNOW_GAMES.items())
    rows = []
    for j in range(0, len(items), 2):
        rows.append([btn(g["name"], f"evg:{g['key']}", icon=f"item_{i}") for i, g in items[j:j + 2]])
    rows.append([btn("Снежные мины", "evg:mines", "mines", style="success"),
                 btn("Снежная башня", "evg:tower", "games", style="success")])
    rows.append([btn("Ледяной лабиринт", "lab:new", icon="item_8", style="success")])
    rows.append([btn("Снежный марафон", "snowman:open", icon="item_1"),
                 btn("К ивентам", "menu:events", icon="door")])
    return "\n".join(lines), kb(*rows)


@dp.callback_query(F.data.startswith("evg:"))
async def cb_game_hint(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[1]
    if key in ("mines", "tower"):
        name = "Снежные мины" if key == "mines" else "Снежная башня"
        min_bet = EV_MINES_MIN if key == "mines" else EV_TOWER_MIN
        desc = ("5×5, 3 мины. Открывай клетки и забирай выигрыш до взрыва."
                if key == "mines" else
                "5 колонок, 9 уровней. Выбирай безопасную клетку и поднимайся выше.")
        return await ask(cb, state, "ev_bet",
                         f"❄️ <b>{name}</b>\n\n{desc}\n"
                         f"Минимальная ставка: <b>{fmt(min_bet)}</b> RCOIN.\n\nВведи сумму ставки:",
                         key=key)
    g = next((x for x in SNOW_GAMES.values() if x["key"] == key), None)
    if not g:
        return await ans(cb, "Игра не найдена", True)
    idx = ev_game_index(key)
    await ask(cb, state, "ev_bet",
              f"{E('item_' + str(idx))} <b>{g['name']}</b>\n\n{g['desc']}\n"
              f"Минимальная ставка: <b>{fmt(g['min'])}</b> RCOIN.\n\nВведи сумму ставки:",
              key=key)


@dp.callback_query(F.data == "ev:nybadge")
async def cb_ny_badge(cb: CallbackQuery):
    uid = cb.from_user.id
    if has_badge(uid, "ny"):
        return await ans(cb, "Новогодняя галочка уже у тебя!", True)
    price = 5_000_000_000
    ok = spend(uid, price)
    if ok:
        give_badge(uid, "ny")
        return await safe_edit(cb, f"{badge('ny')} <b>Новогодняя галочка получена!</b>", kb([btn("К ивентам", "menu:events", "door")]))
    raise_stars = f"Не хватает RCOIN — нужна {fmt(price)} или 5000 ⭐"
    await ans(cb, raise_stars, True)


def run_snow(uid: int, bet: int, key: str) -> str:
    g = next((x for x in SNOW_GAMES.values() if x["key"] == key), None)
    if not g or bet < g["min"]:
        return f"Минимальная ставка {fmt(g['min'] if g else 0)} RCOIN"
    if not spend(uid, bet):
        return "Недостаточно RCOIN"
    payout, detail = 0, ""
    if key == "snow":
        hits = sum(random.random() < (0.62 + 0.03 * bonus_mult(uid)) for _ in range(3))
        payout = int(bet * 4.2) if hits == 3 else 0
        detail = f"Попаданий: <b>{hits}/3</b>"
    elif key == "ice":
        pick, hole = random.randint(1, 5), random.randint(1, 5)
        payout = bet * 5 if pick == hole else 0
        detail = (f"Ты угадал прорубь №{hole} — победа x5!" if pick == hole
                  else f"Лёд выдержал. Прорубь была на №{hole}.")
    elif key == "bear":
        pick, fish = random.choice([1, 2, 3]), random.choice([1, 2, 3])
        payout = bet * 3 if pick == fish else 0
        detail = f"Лапа {pick}: {'есть рыба!' if pick == fish else 'пусто'}"
    elif key == "santa":
        step = random.choice([0, 1000, 2000, 3000, 4000, 5000])
        payout = bet * 5 if step >= 5000 else 0
        detail = f"Сани проехали <b>{step:,}</b> из 5 000 км".replace(",", " ")
    elif key == "gift":
        pick, gift = random.choice([1, 2, 3]), random.choice([1, 2, 3])
        payout = bet * 3 if pick == gift else 0
        detail = f"Ты открыл коробку №{pick}: {'подарок!' if pick == gift else 'мишура'}"
    else:
        step = random.randint(1, 5)
        payout = bet * 5 if step == 5 else 0
        detail = f"Пряничный человечек прошёл {step}/5 шагов"
    settle(uid, key, bet, payout, detail)
    if payout > bet:
        bonus = payout // 20
        ev_add_pot(bonus)
        detail += f"\n{E('item_7')} В джекпот ивентов ушло {fmt(bonus)}"
    bal = get_user(uid)["balance_coin"]
    head = f"{E('win')} <b>ПОБЕДА!</b> +{fmt(payout)} RCOIN" if payout > 0 else f"{E('lose')} <b>Провал.</b>"
    return f"{head}\n<blockquote>{detail}</blockquote>\n{E('balance')} Баланс: <b>{fmt(bal)}</b> RCOIN"


# ---------- ледяной лабиринт ----------
LAB_MIN = 10_000
LAB_LEVELS = 3
LAB_MULTS = [1.7, 2.8, 5.0]


def lab_cashout(bet: int, level: int) -> int:
    return int(bet * LAB_MULTS[max(0, level - 1)]) if level > 0 else 0


def lab_new(uid: int, bet: int) -> Optional[int]:
    if bet < LAB_MIN or not spend(uid, bet):
        return None
    safe = [random.choice("lr") for _ in range(LAB_LEVELS)]
    return sess_new(uid, "labyrinth", bet, {"safe": safe, "level": 0})


def lab_text(sid: int, s: dict, extra: str = "") -> str:
    st = s["state"]
    lvl = int(st.get("level", 0))
    bet = int(s["bet"])
    cash = lab_cashout(bet, lvl)
    path = "▰" * lvl + "▱" * (LAB_LEVELS - lvl)
    next_mult = LAB_MULTS[min(lvl, LAB_LEVELS - 1)]
    return (f"{E('item_8')} <b>ЛЕДЯНОЙ ЛАБИРИНТ</b>\n"
            f"<blockquote>{path}  <b>{lvl}/{LAB_LEVELS}</b>\n"
            f"Ставка: <b>{fmt(bet)}</b> RCOIN\n"
            f"Забрать сейчас: <b>{fmt(cash) if cash else '—'}</b> RCOIN\n"
            f"Следующий шаг: <b>x{next_mult:.1f}</b></blockquote>{extra}")


def lab_kb(sid: int, s: dict, over: bool = False) -> InlineKeyboardMarkup:
    st = s["state"]
    lvl = int(st.get("level", 0))
    if over:
        return kb([btn("Ещё раз", "lab:new", "item_8", style="success"),
                   btn("К играм", "ev:games!", "games", style="primary")])
    rows = [[btn("Влево", f"lab:m:{sid}:l", style="success"),
             btn("Вправо", f"lab:m:{sid}:r", style="success")]]
    if lvl > 0:
        rows.append([btn(f"Забрать {fmt(lab_cashout(int(s['bet']), lvl))}", f"lab:c:{sid}", style="primary")])
    rows.append([btn("Сдаться", f"lab:x:{sid}", style="danger")])
    return kb(*rows)


def lab_pick(sid: int, uid: int, side: str) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "labyrinth":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    st = s["state"]
    lvl = int(st.get("level", 0))
    if side not in ("l", "r") or lvl >= LAB_LEVELS:
        return {"err": "Неверный ход"}
    if side != st["safe"][lvl]:
        sess_close(sid, "lost")
        settle(uid, "labyrinth", int(s["bet"]), 0, f"level={lvl}")
        return {"status": "lost", "state": st, "bet": int(s["bet"]), "payout": 0}
    st["level"] = lvl + 1
    sess_save(sid, st)
    if st["level"] >= LAB_LEVELS:
        sess_close(sid, "won")
        pay = lab_cashout(int(s["bet"]), st["level"])
        settle(uid, "labyrinth", int(s["bet"]), pay, "level=3")
        return {"status": "won", "state": st, "bet": int(s["bet"]), "payout": pay}
    return {"status": "safe", "state": st, "bet": int(s["bet"]), "payout": 0}


def lab_cash(sid: int, uid: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "labyrinth":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    lvl = int(s["state"].get("level", 0))
    if lvl <= 0:
        return {"err": "Сначала пройди хотя бы один уровень"}
    sess_close(sid, "won")
    pay = lab_cashout(int(s["bet"]), lvl)
    settle(uid, "labyrinth", int(s["bet"]), pay, f"cashout={lvl}")
    return {"status": "won", "state": s["state"], "bet": int(s["bet"]), "payout": pay}


def lab_give_up(sid: int, uid: int) -> dict:
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["game"] != "labyrinth":
        return {"err": "Игра не найдена"}
    if s["status"] != "active":
        return {"err": "Игра уже завершена"}
    sess_close(sid, "lost")
    settle(uid, "labyrinth", int(s["bet"]), 0, "giveup")
    return {"status": "lost", "state": s["state"], "bet": int(s["bet"]), "payout": 0}


async def lab_offer(m: Message, bet: int):
    uid = m.from_user.id
    if bet < LAB_MIN:
        return await m.reply(f"Минимальная ставка <b>{fmt(LAB_MIN)}</b> RCOIN.")
    sid = lab_new(uid, bet)
    if not sid:
        return await m.reply("Недостаточно RCOIN для такой ставки.")
    s = sess_get(sid)
    await m.reply(lab_text(sid, s), reply_markup=lab_kb(sid, s))


@dp.message(P("лабиринт", "лаб"))
async def cmd_lab(message: Message, state: FSMContext):
    u = await gate(message, 1.5)
    if not u:
        return
    parts = (message.text or "").split()
    bet = parse_amount(parts[1], u["balance_coin"]) if len(parts) > 1 else 0
    if bet < LAB_MIN:
        return await message.reply("Использование: <code>лабиринт 10000</code>\n"
                                   f"Минимальная ставка <b>{fmt(LAB_MIN)}</b> RCOIN.")
    await lab_offer(message, bet)


@dp.callback_query(F.data.startswith("lab:"))
async def cb_lab(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    act = parts[1] if len(parts) > 1 else ""
    uid = cb.from_user.id
    if act == "new":
        return await ask(cb, state, "ev_bet",
                         f"{E('item_8')} <b>ЛЕДЯНОЙ ЛАБИРИНТ</b>\n\n"
                         "Три развилки. Ошибка — ставка сгорает. Дойди до конца и забери x5.\n"
                         f"Минимальная ставка: <b>{fmt(LAB_MIN)}</b> RCOIN.\n\nВведи сумму ставки:",
                         key="lab")
    try:
        sid = int(parts[2])
    except (IndexError, ValueError):
        return await ans(cb, "Игра не найдена", True)
    if act == "m" and len(parts) > 3:
        r = lab_pick(sid, uid, parts[3])
    elif act == "c":
        r = lab_cash(sid, uid)
    elif act == "x":
        r = lab_give_up(sid, uid)
    else:
        return await ans(cb, "Неверное действие", True)
    if r.get("err"):
        return await ans(cb, r["err"], True)
    s = sess_get(sid) or {"state": r["state"], "bet": r["bet"]}
    if r["status"] == "lost":
        text = lab_text(sid, s, "\n\n<b>Неверный ход.</b> Ставка сгорела.")
    elif r["status"] == "won":
        text = lab_text(sid, s, f"\n\n{E('win')} <b>Успех!</b> Забрано <b>+{fmt(r['payout'])}</b> RCOIN.")
    else:
        text = lab_text(sid, s, "\n\nВыбери сторону или забери деньги.")
    await safe_edit(cb, text, lab_kb(sid, s, over=r["status"] in ("won", "lost")))
    await ans(cb)


@dp.message(P("снежки", "лёд", "лед", "медведь", "сани", "подарки", "пряники"))
async def cmd_snow_games(message: Message):
    w = first_word(message.text)
    key = {"снежки": "snow", "лёд": "ice", "лед": "ice", "медведь": "bear", "сани": "santa",
           "подарки": "gift", "пряники": "mint"}.get(w)
    parts = message.text.split()
    bet = parse_amount(parts[1], get_user(message.from_user.id)["balance_coin"]) if len(parts) > 1 else 0
    if not key or bet <= 0:
        t, k = ev_games_view(message.from_user.id)
        return await message.reply(t, reply_markup=k)
    await message.reply(run_snow(message.from_user.id, bet, key))


@flow("ev_bet")
async def f_ev_bet(m: Message, state: FSMContext, d, txt):
    key = d.get("key")
    if key == "lab":
        u = get_user(m.from_user.id)
        bet = parse_amount(txt, u["balance_coin"])
        if bet < LAB_MIN:
            return await m.reply(f"Минимальная ставка <b>{fmt(LAB_MIN)}</b> RCOIN. Введи сумму ещё раз или «отмена».")
        await state.clear()
        return await lab_offer(m, bet)
    if key in ("mines", "tower"):
        u = get_user(m.from_user.id)
        bet = parse_amount(txt, u["balance_coin"])
        min_bet = EV_MINES_MIN if key == "mines" else EV_TOWER_MIN
        if bet < min_bet:
            return await m.reply(f"Минимальная ставка <b>{fmt(min_bet)}</b> RCOIN. Введи сумму ещё раз.")
        if not spend(m.from_user.id, bet):
            await state.clear()
            return await m.reply("Недостаточно RCOIN.")
        await state.clear()
        if key == "mines":
            sid = mines_start(m.from_user.id, bet, 3)
            st = sess_get(sid)["state"]
            st["ev"] = True
            sess_save(sid, st)
            ev_award_snow(m.from_user.id, bet)
            return await m.reply(mines_text(u, bet, st, "\n❄️ <i>Снежные мины: 3 мины</i>"),
                                 reply_markup=mines_kb(sid, st))
        sid = climb_start(m.from_user.id, bet, "tower", 1)
        st = sess_get(sid)["state"]
        st["ev"] = True
        sess_save(sid, st)
        ev_award_snow(m.from_user.id, bet)
        return await m.reply(climb_text(u, bet, st, "\n❄️ <i>Снежная башня</i>"),
                             reply_markup=climb_kb(sid, st))
    g = next((x for x in SNOW_GAMES.values() if x["key"] == key), None)
    if not g:
        await state.clear()
        return await m.reply("Игра не найдена. Напиши <code>игра</code>, чтобы открыть меню.")
    u = get_user(m.from_user.id)
    bet = parse_amount(txt, u["balance_coin"])
    if bet < g["min"]:
        return await m.reply(f"Минимальная ставка <b>{fmt(g['min'])}</b> RCOIN. Введи сумму ещё раз или «отмена».")
    await state.clear()
    ev_award_snow(m.from_user.id, bet)
    idx = ev_game_index(key)
    await m.reply(run_snow(m.from_user.id, bet, key),
                  reply_markup=kb([btn("Играть ещё", f"evg:{key}", icon=f"item_{idx}"),
                                   btn("Все игры", "ev:games!", icon="games")],
                                  [btn("К ивентам", "menu:events", "door")]))


@dp.message(P("игра", "зимняя игра", "зимние игры", "сыграть"))
async def cmd_play_event(message: Message, state: FSMContext):
    u = await gate(message, 1.5)
    if not u:
        return
    parts = (message.text or "").split()
    key, bet = None, 0
    for token in parts[1:]:
        low = token.lower()
        if not key and low in EV_ALIASES:
            key = EV_ALIASES[low]
        else:
            val = parse_amount(token, u["balance_coin"])
            if val > 0:
                bet = val
    if not key:
        t, k = ev_games_view(u["user_id"])
        return await message.reply(t, reply_markup=k)
    if key == "lab":
        if bet <= 0:
            return await step(message, state, "ev_bet",
                              f"{E('item_8')} <b>ЛЕДЯНОЙ ЛАБИРИНТ</b>\n\n"
                              "Три развилки. Ошибка — ставка сгорает. Дойди до конца и забери x5.\n"
                              f"Минимальная ставка: <b>{fmt(LAB_MIN)}</b> RCOIN.\n\nВведи сумму ставки:",
                              key="lab")
        if bet < LAB_MIN:
            return await message.reply(f"Минимальная ставка <b>{fmt(LAB_MIN)}</b> RCOIN.")
        return await lab_offer(message, bet)
    g = next((x for x in SNOW_GAMES.values() if x["key"] == key), None)
    if not g:
        return await message.reply("Игра не найдена. Напиши <code>игра</code>, чтобы открыть меню.")
    if bet <= 0:
        idx = ev_game_index(key)
        return await step(message, state, "ev_bet",
                          f"{E('item_' + str(idx))} <b>{g['name']}</b>\n\n{g['desc']}\n"
                          f"Минимальная ставка: <b>{fmt(g['min'])}</b> RCOIN.\n\nВведи сумму ставки:",
                          key=key)
    if bet < g["min"]:
        return await message.reply(f"Минимальная ставка <b>{fmt(g['min'])}</b> RCOIN.")
    ev_award_snow(u["user_id"], bet)
    await message.reply(run_snow(u["user_id"], bet, key),
                        reply_markup=kb([btn("Играть ещё", f"evg:{key}", icon=f"item_{ev_game_index(key)}"),
                                         btn("Все игры", "ev:games!", icon="games")],
                                        [btn("К ивентам", "menu:events", "door")]))


@dp.message(P("нг"))
async def cmd_ng(message: Message, state: FSMContext):
    u = await gate(message, 1.5)
    if not u:
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        return await message.reply(
            "Формат без кнопок:\n"
            "<code>нг мины 10000 3</code>\n"
            "<code>нг башня 10000 1</code>\n"
            "<code>нг лабиринт 10000</code>")
    game = parts[1].lower()
    bet = parse_amount(parts[2], u["balance_coin"])
    if bet <= 0:
        return await message.reply("Введи положительную ставку.")
    if game in ("мины", "мин", "mines"):
        cnt = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 3
        if not 1 <= cnt <= 10:
            return await message.reply("Мин от 1 до 10.")
        if bet < EV_MINES_MIN:
            return await message.reply(f"Минимальная ставка <b>{fmt(EV_MINES_MIN)}</b> RCOIN.")
        if not spend(u["user_id"], bet):
            return await message.reply("Недостаточно RCOIN.")
        sid = mines_start(u["user_id"], bet, cnt)
        st = sess_get(sid)["state"]
        st["ev"] = True
        sess_save(sid, st)
        n = ev_award_snow(u["user_id"], bet)
        return await message.reply(
            mines_text(u, bet, st, f"\n{E('snowflake')} Снежинок: <b>+{n}</b>"),
            reply_markup=mines_kb(sid, st))
    if game in ("башня", "башн", "tower"):
        bombs = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
        if not 1 <= bombs <= 3:
            return await message.reply("Мин в ряду от 1 до 3.")
        if bet < EV_TOWER_MIN:
            return await message.reply(f"Минимальная ставка <b>{fmt(EV_TOWER_MIN)}</b> RCOIN.")
        if not spend(u["user_id"], bet):
            return await message.reply("Недостаточно RCOIN.")
        sid = climb_start(u["user_id"], bet, "tower", bombs)
        st = sess_get(sid)["state"]
        st["ev"] = True
        sess_save(sid, st)
        n = ev_award_snow(u["user_id"], bet)
        return await message.reply(
            climb_text(u, bet, st, f"\n{E('snowflake')} Снежинок: <b>+{n}</b>"),
            reply_markup=climb_kb(sid, st))
    if game in ("лабиринт", "лаб", "lab"):
        if bet < LAB_MIN:
            return await message.reply(f"Минимальная ставка <b>{fmt(LAB_MIN)}</b> RCOIN.")
        return await lab_offer(message, bet)
    return await message.reply("Игра не найдена. Доступно: мины, башня, лабиринт.")


@dp.callback_query(F.data == "ev:games!")
async def cb_ev_games(cb: CallbackQuery):
    t, k = ev_games_view(cb.from_user.id)
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data.startswith("ev:"))
async def cb_events(cb: CallbackQuery, state: FSMContext):
    act = cb.data.split(":")[1]
    uid = cb.from_user.id
    u = get_user(uid)
    back = [btn("К ивентам", "menu:events", "door")]
    if act == "stash":
        used = u["ev_stash_used"] if u["ev_day"] == today() else 0
        if used >= STASH_CELLS:
            return await ans(cb, "Склад на сегодня уже открыт. Приходи завтра!", True)
        prize = int(STASH_MIN + (STASH_MAX - STASH_MIN) * random.random() ** 3)
        item = random.choice(list(SOUVENIRS)) if random.random() < 0.4 else None
        add_coin(uid, prize)
        update_user(uid, ev_day=today(), ev_stash_used=used + 1, ev_points=u["ev_points"] + 1)
        quest_inc(uid, "stash")
        line = ""
        if item:
            inv_add(uid, item)
            line = f"\n🎁 <b>Найден предмет:</b> {E(item)} <i>{SOUVENIRS[item]}</i>\n<blockquote>Предмет сохранён на твоём складе!</blockquote>"
        more = [btn("Открыть ещё", "ev:stash", "diamond")] if used + 1 < STASH_CELLS else []
        await safe_edit(cb, f"{E('diamond')} <b>ЗИМНИЙ СКЛАД</b>\n\n{E('win')} Ячейка {used + 1}/{STASH_CELLS}\nПриз: <b>+{fmt(prize)} RCOIN</b>{line}",
                        kb(more, back) if more else kb(back))
        return await ans(cb, f"+{fmt(prize)}")
    if act == "boss":
        b = boss_state()
        title = "Главный босс" if b["final"] else "Санта"
        can = u["ev_boss_day"] != today()
        top = q("SELECT u.display_name n, h.dmg d FROM boss_hits h JOIN users u ON u.user_id=h.user_id WHERE h.day=? ORDER BY h.dmg DESC LIMIT 3", (today(),))
        tl = "\n".join(f"{['🥇', '🥈', '🥉'][i]} {esc(r['n'] or 'Игрок')} — {fmt(r['d'])}" for i, r in enumerate(top)) or "—"
        mine = q("SELECT dmg FROM boss_hits WHERE day=? AND user_id=?", (today(), uid), one=True)
        rows = [[btn("Ударить (бесплатно, раз в день)" if can else "Удар уже сделан", "ev:hit", "crash" if can else "lock")],
                [btn("Помочь Санте монетами", "ev:santa", "balance")], back]
        await safe_edit(cb, f"{E('crash')} <b>БИТВА: {title.upper()}</b>\n\nHP: <b>{fmt(b['hp'])}</b> / {fmt(b['max'])}\n<code>{bar(b['max'] - b['hp'], b['max'])}</code>\n\n"
                            f"Твой урон сегодня: <b>{fmt(mine['dmg'] if mine else 0)}</b>\nТоп сегодня:\n{tl}\n\n"
                            f"Когда босс падает — награда из казны делится пропорционально урону.", kb(*rows))
        return await ans(cb)
    if act == "hit":
        if x("UPDATE users SET ev_boss_day=? WHERE user_id=? AND ev_boss_day!=?", (today(), uid, today()))[0] != 1:
            return await ans(cb, "Ты уже бил босса сегодня", True)
        dmg = random.randint(10_000, 120_000)
        reward = dmg // 2
        add_coin(uid, reward)
        kill = boss_hit(uid, dmg)
        b = boss_state()
        await safe_edit(cb, f"{E('win')} <b>УДАР!</b>\n\nУрон: <b>{fmt(dmg)}</b>\nНаграда: <b>+{fmt(reward)} RCOIN</b>\n\nHP: {fmt(b['hp'])}/{fmt(b['max'])}\n<code>{bar(b['max'] - b['hp'], b['max'])}</code>",
                        kb(back))
        await ans(cb, f"-{fmt(dmg)} HP")
        if kill is not None:
            asyncio.create_task(boss_notify(kill))
        return
    if act == "santa":
        return await ask(cb, state, "santa", "Сколько RCOIN отдать Санте? (урон = сумма; шанс найти сувенир растёт с суммой)")
    if act == "wheel":
        left = 6 * 3600 - (now() - u["ev_wheel_last"])
        if left > 0:
            return await ans(cb, f"Колесо будет доступно через {dur(left)}", True)
        if x("UPDATE users SET ev_wheel_last=? WHERE user_id=? AND ev_wheel_last=?", (now(), uid, u["ev_wheel_last"]))[0] != 1:
            return await ans(cb)
        prize = random.choices([p for p, _ in WHEEL], weights=[w for _, w in WHEEL])[0]
        add_coin(uid, prize)
        await safe_edit(cb, f"{E('spin')} <b>КОЛЕСО УДАЧИ</b>\n\n{E('win')} Выпало: <b>{fmt(prize)} RCOIN</b>", kb(back))
        return await ans(cb, f"+{fmt(prize)}")
    if act == "quests":
        lines, rows = [f"{E('treasury')} <b>КВЕСТЫ НА СЕГОДНЯ</b>\n"], []
        for key, title, goal, reward in QUESTS:
            val = quest_get(uid, key)
            claimed = quest_get(uid, "c:" + key)
            lines.append(f"{'✅' if val >= goal else '▫️'} {title} — {min(val, goal)}/{goal} · награда {fmt(reward)}" + (" · <i>получено</i>" if claimed else ""))
            if val >= goal and not claimed:
                rows.append([btn(f"Забрать: {title}", f"ev:q:{key}", "win")])
        rows.append(back)
        await safe_edit(cb, "\n".join(lines), kb(*rows))
        return await ans(cb)
    if act == "q":
        key = cb.data.split(":")[2]
        qd = next((z for z in QUESTS if z[0] == key), None)
        if not qd or quest_get(uid, key) < qd[2]:
            return await ans(cb, "Квест не выполнен", True)
        if x("INSERT OR IGNORE INTO quests(user_id,day,key,value) VALUES(?,?,?,1)", (uid, today(), "c:" + key))[0] != 1:
            return await ans(cb, "Уже получено", True)
        add_coin(uid, qd[3])
        await ans(cb, f"+{fmt(qd[3])} RCOIN", True)
        return await cb_events(cb.model_copy(update={"data": "ev:quests"}), state)


async def santa_help(uid: int, amount: int) -> Tuple[str, Optional[List[Tuple[int, int]]]]:
    if amount < 10_000:
        return "Минимальная помощь — 10 000 RCOIN.", None
    if not spend(uid, amount):
        return f"{E('lock')} Недостаточно RCOIN.", None
    treasury_add(amount // 10)
    kill = boss_hit(uid, amount)
    x("UPDATE users SET ev_points=ev_points+1 WHERE user_id=?", (uid,))
    item = ""
    if random.random() < min(0.9, amount / 200_000):
        k = random.choice(list(SOUVENIRS))
        inv_add(uid, k)
        item = f"\n🎁 Санта подарил: {E(k)} <i>{SOUVENIRS[k]}</i>"
    b = boss_state()
    return (f"{E('win')} <b>ПОМОЩЬ САНТЕ!</b>\n\n💸 Отдано: {fmt(amount)} RCOIN\n⚔️ Урон боссу: <b>{fmt(amount)}</b>{item}\n\n"
            f"HP: {fmt(b['hp'])}/{fmt(b['max'])}\n<code>{bar(b['max'] - b['hp'], b['max'])}</code>"), kill


@flow("santa")
async def f_santa(m: Message, state: FSMContext, d, txt):
    n = parse_amount(txt, get_user(m.from_user.id)["balance_coin"])
    if n <= 0:
        return await m.reply("Введи сумму.")
    text, kill = await santa_help(m.from_user.id, n)
    await state.clear()
    await m.reply(text)
    if kill is not None:
        asyncio.create_task(boss_notify(kill))


@dp.message(P("помочь", "помощь санте", "помог"))
async def cmd_santa(message: Message):
    p = message.text.split()
    if len(p) < 2 or p[1].lower() != "санте":
        return await message.reply("Использование: <code>помочь санте 100к</code>")
    amt = parse_amount(p[2], get_user(message.from_user.id)["balance_coin"]) if len(p) >= 3 else 0
    if amt <= 0:
        return await message.reply("Формат: <code>помочь санте 100к</code>")
    text, kill = await santa_help(message.from_user.id, amt)
    await message.reply(text)
    if kill is not None:
        asyncio.create_task(boss_notify(kill))


@dp.message(P("санте"))
async def cmd_santa2(message: Message):
    p = message.text.split()
    amt = parse_amount(p[1], get_user(message.from_user.id)["balance_coin"]) if len(p) >= 2 else 0
    if amt <= 0:
        return await message.reply("Формат: <code>санте 100к</code>")
    text, kill = await santa_help(message.from_user.id, amt)
    await message.reply(text)
    if kill is not None:
        asyncio.create_task(boss_notify(kill))


# ============================ АДМИН-ПАНЕЛЬ ============================
ADMIN_ACTIONS = {
    "give_coin": ("💰 Выдать RCOIN", True, ["Сумма RCOIN (1к, 1кк…)"]),
    "give_rbp": ("💎 Выдать RBP", True, ["Сумма RBP"]),
    "give_stars": ("⭐ Выдать Stars", True, ["Сумма Stars"]),
    "take_coin": ("💰 Снять RCOIN", True, ["Сумма RCOIN"]),
    "take_rbp": ("💎 Снять RBP", True, ["Сумма RBP"]),
    "take_stars": ("⭐ Снять Stars", True, ["Сумма Stars"]),
    "reset_coin": ("🔄 Обнулить RCOIN", True, []),
    "reset_bank": ("🏦 Обнулить банк", True, []),
    "reset_rbp": ("💎 Обнулить RBP", True, []),
    "reset_all": ("⚠️ Обнулить всё", True, []),
    "ban": ("🔨 Бан", True, ["Минуты (0 — навсегда)", "Причина"]),
    "mute": ("🔇 Мут", True, ["Минуты (0 — навсегда)", "Причина"]),
    "unban": ("✅ Разбан/размут", True, []),
    "rank_scammer": ("🚫 Ранг SCAMMER", True, []),
    "rank_admin": ("👑 Ранг ADMIN", True, []),
    "rank_donater": ("💵 Ранг DONATER", True, []),
    "rank_official": ("✅ Ранг VERIFIED", True, []),
    "rank_custom": ("🎖 Личный ранг", True, ["Название ранга (до 32 символов)"]),
    "rank_owner": ("👑 Ранг ВЛАДЕЛЕЦ", True, []),
    "rank_clear": ("🗑 Снять ранги", True, []),
    "treasury": ("🏦 Доступ к казне (вкл/выкл)", True, []),
    "info": ("ℹ️ Инфо об игроке", True, []),
    "history": ("📜 История игр игрока", True, []),
    "nft_create": ("🎨 Создать NFT игроку", True, ["Название NFT", "Редкость: none / rare / epic", "Оценка в RCOIN (или 0 — по редкости)", "Описание (или «-»)", "Номер NFT (ID) или 0 — авто", "Модель: Стандартный/Зимний/Снежный/Золотой/Неоновый/Призрачный/Космический или random", "Фон: Обычный/Морозный/Праздничный/Звёздный/Северное сияние/Галактика или random", "Фото: пришли фото или «-» — рисовать кодом"]),
    "nft_self": ("🎨 Создать NFT себе", False, ["Название NFT", "Редкость: none / rare / epic", "Оценка в RCOIN (или 0 — по редкости)", "Описание (или «-»)", "Номер NFT (ID) или 0 — авто", "Модель: Стандартный/Зимний/Снежный/Золотой/Неоновый/Призрачный/Космический или random", "Фон: Обычный/Морозный/Праздничный/Звёздный/Северное сияние/Галактика или random", "Фото: пришли фото или «-» — рисовать кодом"]),
    "gift_give": ("💌 Выдать подарок-бокс игроку", True, ["Редкость: none / rare / epic / random"]),
    "gift_gen": ("🎁 Сгенерировать подарок (код)", False, ["Редкость: none / rare / epic / random"]),
    "mailing": ("📨 Рассылка", False, ["Текст рассылки (HTML разрешён)"]),
}


def admin_kb() -> InlineKeyboardMarkup:
    a = lambda k: btn(ADMIN_ACTIONS[k][0], f"adm:{k}")
    return kb([a("ban"), a("mute")], [a("unban")],
              [a("give_coin"), a("give_rbp")], [a("give_stars")],
              [a("take_coin"), a("take_rbp")], [a("take_stars")],
              [a("reset_coin"), a("reset_bank")], [a("reset_rbp"), a("reset_all")],
              [a("rank_scammer"), a("rank_admin")], [a("rank_donater"), a("rank_official")],
              [a("rank_custom"), a("rank_owner")],
              [btn("🎖 Выдать себе", "adm:self", icon="admin"), btn("🛡 Галочки игроку", "adm:badges", "check")],
              [a("rank_clear"), a("treasury")],
              [btn("📊 Статистика", "adm:stats"), btn("👥 Игроки", "adm:users")],
              [a("mailing"), btn("💾 Выгрузка БД", "adm:export")],
              [a("info"), a("history")],
              [a("nft_self"), a("nft_create")], [a("gift_gen"), a("gift_give")],
              [btn("📦 Список подарков", "adm:gift_list")],
              [btn("🤖 Нейросеть", "adm:ai")])


@dp.message(P("адм1308", "admin", "админ"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ У вас нет прав администратора.")
    await state.clear()
    await message.reply(f"{E('admin')} <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=admin_kb())


@dp.message(Command("ticker"))
async def cmd_ticker(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Только для администрации.")
    text = (command.args or "").strip()
    if not text:
        return await message.reply(f"Текущая строка:\n<code>{esc(ui_ticker())}</code>\n\n"
                                   "Формат: <code>/ticker новый текст</code>")
    kv_set(UI_TICKER_KEY, text[:300])
    await message.reply("✅ Бегущая строка обновлена.")


@dp.message(Command("arenabonus"))
async def cmd_arena_bonus(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Только для администрации.")
    amount = parse_amount((command.args or "").strip(), get_user(message.from_user.id)["balance_coin"])
    if amount <= 0:
        return await message.reply("Формат: <code>/arenabonus 100кк</code>")
    res = ar_admin_bonus(message.from_user.id, amount)
    await message.reply(("✅ " if res.get("ok") else "❌ ") + str(res.get("msg") or res.get("err") or ""))


@dp.message(Command("newcollection"))
async def cmd_new_collection(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только владелец.")
    if (command.args or "").strip().upper() != "RESET":
        return await message.reply("⚠️ Это удалит <b>все NFT игроков</b> и лоты архива, нумерация начнётся с #1.\n"
                                   "Подтверди: <code>/newcollection RESET</code>")
    res = reset_nft_collection()
    await message.reply(f"✅ Новая коллекция: удалено <b>{res['items']}</b> NFT и <b>{res['lots']}</b> лотов. "
                        f"В архиве: {res['archive']}.")


def admin_exec(action: str, tid: Optional[int], a: List[str], by: int) -> str:
    u = get_user(tid) if tid else None
    nm = uname(u, False) if u else ""
    if action.startswith(("give_", "take_")):
        kind = action.split("_")[1]
        col = {"coin": "balance_coin", "rbp": "balance_point", "stars": "stars_balance"}[kind]
        amt = parse_amount(a[0])
        if amt <= 0:
            return "❌ Неверная сумма."
        if action.startswith("give_"):
            if kind == "coin":
                over = add_coin(tid, amt)
                note = f"\n🏛 Сверх лимита в Архив: <b>{fmt(over)}</b>" if over else ""
                return f"✅ Выдано {fmt(amt - over)} RCOIN игроку {nm} ({tid}){note}"
            x(f"UPDATE users SET {col}={col}+? WHERE user_id=?", (amt, tid))
            return f"✅ Выдано {fmt(amt)} {kind.upper()} игроку {nm} ({tid})"
        if not spend(tid, amt, col):
            return "❌ У игрока недостаточно средств."
        return f"✅ Снято {fmt(amt)} {kind.upper()} у {nm} ({tid})"
    if action == "reset_coin":
        update_user(tid, balance_coin=0)
    elif action == "reset_bank":
        update_user(tid, bank_balance=0)
    elif action == "reset_rbp":
        update_user(tid, balance_point=0)
    elif action == "reset_all":
        update_user(tid, balance_coin=0, balance_point=0, bank_balance=0, stars_balance=0, total_wins=0, total_losses=0, total_games=0)
    elif action in ("ban", "mute"):
        mins = int(a[0]) if a[0].isdigit() else 0
        until = 9_999_999_999 if mins == 0 else now() + mins * 60
        if action == "ban":
            update_user(tid, banned_until=until, ban_reason=a[1])
        else:
            update_user(tid, muted_until=until, mute_reason=a[1])
        return f"{'🔨 Бан' if action == 'ban' else '🔇 Мут'}: {nm} ({tid}) — {'навсегда' if mins == 0 else str(mins) + ' мин'}. Причина: {esc(a[1])}"
    elif action == "unban":
        update_user(tid, banned_until=0, ban_reason="", muted_until=0, mute_reason="")
    elif action.startswith("rank_"):
        if action == "rank_custom":
            title = (a[0] if a else "").strip()[:32] or "Новичок"
            update_user(tid, rank_title=title, is_scammer=0, is_donater=0, is_official=1)
            return f"🎖 Личный ранг «{esc(title)}» выдан {nm} ({tid})"
        if action == "rank_owner":
            if by != OWNER_ID:
                return "⛔ Ранг владельца может выдать только владелец."
            update_user(tid, rank_title="Владелец", is_official=1)
            return f"👑 Ранг владельца выдан {nm} ({tid})"
        if action == "rank_clear" and tid == OWNER_ID:
            return "⛔ Нельзя снять ранги у владельца."
        flags = dict(is_scammer=0, is_admin_rank=0, is_donater=0, is_official=0)
        names = {"rank_scammer": ("is_scammer", "SCAMMER"), "rank_admin": ("is_admin_rank", "ADMIN"),
                 "rank_donater": ("is_donater", "DONATER"), "rank_official": ("is_official", "VERIFIED")}
        if action in names:
            flags[names[action][0]] = 1
            update_user(tid, rank_title=names[action][1], **flags)
        else:
            update_user(tid, rank_title="Новичок", **flags)
    elif action == "treasury":
        new = 0 if u["treasury_access"] else 1
        update_user(tid, treasury_access=new)
        return f"🏦 Доступ к казне для {nm}: {'ВКЛЮЧЕН' if new else 'ВЫКЛЮЧЕН'}"
    elif action == "info":
        st = q("SELECT COUNT(*) n, SUM(is_win) w FROM bet_history WHERE user_id=?", (tid,), one=True)
        return (f"ℹ️ <b>{nm}</b> ({tid}) @{esc(u['username'] or '—')}\n💰 {fmt(u['balance_coin'])} RCOIN · 💎 {fmt(u['balance_point'])} RBP · 🏦 {fmt(u['bank_balance'])} · ⭐ {u['stars_balance']}\n"
                f"🎯 Игр {st['n']}, побед {st['w'] or 0}\n🏷 Ранг: {esc(u['rank_title'])}\n🚫 Бан: {'да' if u['banned_until'] > now() else 'нет'} · 🔇 Мут: {'да' if u['muted_until'] > now() else 'нет'}\n"
                f"🏛 Доступ к казне: {'да' if u['treasury_access'] else 'нет'}")
    elif action == "history":
        rows = q("SELECT game_type,bet_amount,win_amount,created_at FROM bet_history WHERE user_id=? ORDER BY id DESC LIMIT 15", (tid,))
        return "\n".join([f"📜 <b>История {nm}</b>"] + [f"{esc(r['game_type'])}: {fmt(r['bet_amount'])} → {fmt(r['win_amount'])} · {datetime.fromtimestamp(r['created_at'], MSK).strftime('%d.%m %H:%M')}" for r in rows]) if rows else "Пусто."
    elif action in ("nft_create", "nft_self"):
        owner = by if action == "nft_self" else tid
        u = get_user(owner)
        nm = uname(u, False)
        rar = a[1].lower()
        if rar in ("none", "нет", "-", "без"):
            rar = "common"
        if rar not in RARITY_BASE:
            return "❌ Неверная редкость. Можно: none, rare, epic."
        price = parse_amount(a[2]) or RARITY_BASE[rar]
        try:
            want_id = int((a[4] if len(a) > 4 else "0").strip() or 0)
        except (TypeError, ValueError):
            want_id = 0
        model_names = [m[0] for m in MODELS]
        bg_names = [b[0] for b in BGS]
        model = (a[5].strip() if len(a) > 5 else "")
        model = model if model in model_names else None
        background = (a[6].strip() if len(a) > 6 else "")
        background = background if background in bg_names else None
        photo = (a[7].strip() if len(a) > 7 else "")
        is_file = len(photo) > 40
        photo = None if is_file or not photo or photo.lower() in ("random", "-", "авто") else photo[:8]
        occupied = bool(want_id > 0 and q("SELECT 1 FROM nft_items WHERE id=?", (want_id,), one=True))
        nid = make_nft(owner, a[0][:30], rar, photo, "" if a[3] == "-" else a[3][:200], price,
                       model=model, background=background, nft_id=want_id)
        if rar in UPGRADE_RARITIES:
            x("UPDATE nft_items SET level=2 WHERE id=?", (nid,))
        if is_file:
            asyncio.get_event_loop().create_task(_attach_nft_photo(nid, a[0][:30], rar, a[7].strip()))
        else:
            make_nft_image(nid)
        note = " Номер уже существовал — данные и владелец перезаписаны." if occupied else ""
        whom = "тебе" if action == "nft_self" else nm
        return (f"🎨 NFT выдан {whom}:{note}\n"
                f"{nft_card(q('SELECT * FROM nft_items WHERE id=?', (nid,), one=True))}")
    elif action in ("gift_give", "gift_gen"):
        rar = a[0].lower()
        if rar == "random":
            rar = random.choice(RARITIES)
        if rar not in RARITY_BASE:
            return "❌ Неверная редкость."
        owner = tid if action == "gift_give" else by
        gid, code = make_gift(owner, rar)
        if action == "gift_give":
            asyncio.get_event_loop().create_task(_dm(tid, f"🎁 <b>Тебе подарили коллекционный бокс!</b>\n{RARITY_EMOJI[rar]} {RARITY_NAME[rar]}\nКод: <code>{code}</code>\nОткрой в «склад» → Боксы."))
            return f"💌 Бокс {RARITY_EMOJI[rar]} выдан {nm}. Код: <code>{code}</code>"
        return f"🎁 Подарок создан и лежит на твоём складе:\n{RARITY_EMOJI[rar]} {RARITY_NAME[rar]} · код <code>{code}</code>"
    return f"✅ Готово: {nm} ({tid})"


async def _attach_nft_photo(nid: int, title: str, rarity: str, file_id: str):
    """Фото из Telegram → карточка NFT. Ошибку не роняем: останется код-арт."""
    try:
        f = await bot.get_file(file_id)
        buf = await bot.download_file(f.file_path)
        data = buf.read() if hasattr(buf, "read") else bytes(buf)
        NFT_DIR.mkdir(parents=True, exist_ok=True)
        (NFT_DIR / f"photo_{nid}.png").write_bytes(data)
        card = _nft_photo_card(data, title, rarity, nid)
        (NFT_DIR / f"photo_{nid}_card.png").write_bytes(card)
        kv_set(f"nftimg:{nid}", f"photo_{nid}_card.png")
        kv_set(f"nftpng:{nid}", base64.b64encode(card).decode("ascii"))
        x("UPDATE nft_items SET photo='photo' WHERE id=?", (nid,))
    except Exception:
        log.exception("_attach_nft_photo %s", nid)
        make_nft_image(nid)


async def _dm(uid: int, text: str):
    try:
        await bot.send_message(uid, text)
    except Exception:
        pass


def admin_self_view(uid: int):
    rank = get_user(uid)["rank_title"] or "Новичок"
    text = (f"{E('admin')} <b>ВЫДАТЬ СЕБЕ</b>\n\n"
            f"Твой ранг: <b>{esc(rank)}</b>\n"
            "Выбери галочку или задай личный ранг.")
    rows = [[btn(BADGES[b]["title"], f"adm:selfb:{b}", icon=b)]
            for b in BADGE_ORDER if b != "dev" or uid == OWNER_ID]
    rows.append([btn("🎖 Свой ранг", "adm:selfrank")])
    rows.append([btn("Назад", "adm:menu", "door")])
    return text, kb(*rows)


@dp.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет прав", True)
    action = cb.data.split(":")[1]
    if action == "badges" or action.startswith("bg"):
        return await cb_adm_badges(cb, state)
    if action == "menu":
        await safe_edit(cb, f"{E('admin')} <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", admin_kb())
        return await ans(cb)
    if action == "self":
        t, k = admin_self_view(cb.from_user.id)
        await safe_edit(cb, t, k)
        return await ans(cb)
    if action.startswith("selfb"):
        parts = cb.data.split(":")
        key = parts[2] if len(parts) > 2 else ""
        if key not in BADGES:
            return await ans(cb, "Нет такой галочки", True)
        if key == "dev" and cb.from_user.id != OWNER_ID:
            return await ans(cb, "Галочку владельца может выдать только владелец", True)
        give_badge(cb.from_user.id, key)
        await ans(cb, f"Выдано: {BADGES[key]['title']}", True)
        t, k = admin_self_view(cb.from_user.id)
        return await safe_edit(cb, t, k)
    if action == "selfrank":
        return await ask(cb, state, "adm_selfrank", "Введи свой личный ранг (до 32 символов):")
    if action == "stats":
        r = q("SELECT COUNT(*) n, SUM(balance_coin) c, SUM(balance_point) p, SUM(bank_balance) b, SUM(stars_balance) s FROM users", one=True)
        bets = q("SELECT COUNT(*) n FROM bet_history", one=True)["n"]
        await cb.message.answer(f"📊 <b>СТАТИСТИКА</b>\n👥 Игроков: {fmt(r['n'])}\n💰 RCOIN: {fmt(r['c'] or 0)}\n💎 RBP: {fmt(r['p'] or 0)}\n🏦 В банках: {fmt(r['b'] or 0)}\n⭐ Stars: {fmt(r['s'] or 0)}\n"
                                f"🎯 Ставок: {fmt(bets)}\n🏛 Казна: {fmt(treasury_get())}")
        return await ans(cb)
    if action == "users":
        rows = q("SELECT user_id, display_name, balance_coin FROM users ORDER BY created_at DESC LIMIT 30")
        await cb.message.answer("👥 <b>Последние игроки</b>\n" + "\n".join(f"{r['user_id']} · {esc(r['display_name'] or '—')} · {fmt(r['balance_coin'])}" for r in rows))
        return await ans(cb)
    if action == "export":
        try:
            data = Path(DB_FILE).read_bytes()
            await cb.message.answer_document(BufferedInputFile(data, filename=f"backup_{now()}.db"), caption="💾 Копия базы данных")
        except Exception as e:
            await cb.message.answer(f"❌ {esc(str(e))}")
        return await ans(cb)
    if action == "gift_list":
        rows = q("SELECT code,rarity,owner_id,used FROM gifts ORDER BY id DESC LIMIT 15")
        await cb.message.answer("🎁 <b>Подарки (последние 15)</b>\n" + ("\n".join(f"<code>{r['code']}</code> {RARITY_EMOJI.get(r['rarity'], '')} — {'открыт' if r['used'] else ('у ' + str(r['owner_id']) if r['owner_id'] else 'в запасе')}" for r in rows) or "пусто"))
        return await ans(cb)
    if action not in ADMIN_ACTIONS:
        return await ans(cb, "Неизвестное действие", True)
    title, need_t, prompts = ADMIN_ACTIONS[action]
    if need_t:
        return await ask(cb, state, "adm_t", f"{title}\nВведи ID или @юзернейм игрока:", action=action)
    await ask(cb, state, "adm_a", f"{title}\n{prompts[0]}", action=action, answers=[])


async def adm_finish(m: Message, state: FSMContext, action: str, tid: int, answers: List[str]):
    await state.clear()
    if action == "mailing":
        asyncio.create_task(mailing(m, answers[0]))
        return await m.reply("📨 Рассылка запущена, пришлю отчёт.")
    await m.reply(admin_exec(action, tid, answers, m.from_user.id))


@flow("adm_t")
async def f_adm_t(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return await state.clear()
    t = find_user(txt)
    if not t:
        return await m.reply("Игрок не найден. Введи ID/@юзернейм или «отмена».")
    title, _, prompts = ADMIN_ACTIONS[d["action"]]
    if prompts:
        return await step(m, state, "adm_a", f"{title}\n{prompts[0]}", target=t["user_id"], answers=[])
    await adm_finish(m, state, d["action"], t["user_id"], [])


@flow("adm_a")
async def f_adm_a(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return await state.clear()
    title, _, prompts = ADMIN_ACTIONS[d["action"]]
    answers = list(d.get("answers", []))
    if m.photo:
        answers.append(m.photo[-1].file_id)
    elif m.document and str(m.document.mime_type or "").startswith("image/"):
        answers.append(m.document.file_id)
    elif m.text:
        answers.append(m.text.strip())
    if len(answers) < len(prompts):
        return await step(m, state, "adm_a", f"{title}\n{prompts[len(answers)]}", answers=answers)
    await adm_finish(m, state, d["action"], d.get("target", 0), answers)


@flow("adm_selfrank")
async def f_adm_selfrank(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return await state.clear()
    title = (txt or "").strip()[:32] or "Новичок"
    update_user(m.from_user.id, rank_title=title, is_scammer=0, is_donater=0, is_official=1)
    await state.clear()
    await m.reply(f"🎖 Личный ранг: <b>{esc(title)}</b>")


MAILING_ACTIVE = False


async def mailing(m: Message, text: str):
    """Рассылка. Формат: «текст» или «текст | Подпись кнопки | https://ссылка»."""
    global MAILING_ACTIVE
    if MAILING_ACTIVE:
        return await m.reply("⏳ Рассылка уже идёт.")
    markup = None
    parts = [p.strip() for p in text.split("|")]
    if len(parts) >= 3 and parts[2].startswith("http"):
        text = parts[0]
        markup = kb([btn(parts[1][:60] or "Открыть", url=parts[2])])
    MAILING_ACTIVE = True
    ids = [r["user_id"] for r in q("SELECT user_id FROM users")]
    ok = fail = 0
    try:
        for uid in ids:
            try:
                try:
                    await bot.send_message(uid, text[:4096], parse_mode=ParseMode.HTML, reply_markup=markup)
                except TelegramBadRequest:
                    await bot.send_message(uid, text[:4096], reply_markup=markup)
                ok += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.07)
    finally:
        MAILING_ACTIVE = False
    try:
        await m.reply(f"✅ <b>Рассылка завершена</b>\n👥 Всего: {len(ids)}\n✅ Доставлено: {ok}\n❌ Ошибок: {fail}")
    except Exception:
        pass


QUICK = {"выдать": "give_coin", "выдатьпоинт": "give_rbp", "снять": "take_coin", "забанить": "ban",
         "разбанить": "unban", "замутить": "mute", "размутить": "unban"}


@dp.message(P(*QUICK))
async def cmd_quick_admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ Нет прав!")
    p = message.text.split()
    cmd = first_word(message.text)
    action = QUICK[cmd]
    reply = bool(message.reply_to_message)
    if action in ("give_coin", "give_rbp", "take_coin"):
        if len(p) < 2:
            return await message.reply(f"Формат: <code>{cmd} СУММА ID/@ник</code> (или ответом: <code>{cmd} СУММА</code>)")
        t = resolve_target(message, p[2] if len(p) > 2 else None)
        if not t:
            return await message.reply("❌ Игрок не найден.")
        return await message.reply(admin_exec(action, t["user_id"], [p[1]], message.from_user.id))
    tok = None if reply else (p[1] if len(p) > 1 else None)
    t = resolve_target(message, tok)
    if not t:
        return await message.reply(f"Формат: <code>{cmd} ID/@ник [причина]</code> (или ответом на сообщение)")
    reason = " ".join(p[1:] if reply else p[2:]) or "Без причины"
    await message.reply(admin_exec(action, t["user_id"], ["0", reason], message.from_user.id))


# ============================ АВТО-ЧЕКИ ИЗ КАЗНЫ ============================
async def distribute_check(kind: str) -> bool:
    st = tset_get()
    amount = int(st.get("fri_amount" if kind == "fri" else "sat_amount") or 0)
    amount = max(1, amount)
    slots = int(st.get("auto_slots") or 0)
    chats = tset_chats()
    title = "🎄 ПЯТНИЧНЫЙ АВТО-ЧЕК" if kind == "fri" else "❄️ СУББОТНИЙ ИВЕНТ-ЧЕК"

    if kind == "daily":
        amount = max(1, int(st.get("daily_amount") or 100_000))
        ids = [r["user_id"] for r in q("SELECT user_id FROM users WHERE banned_until<=?", (now(),))]
        if not ids:
            return False
        total = amount * len(ids)
        if not treasury_take(total):
            log.warning("Авто-чек daily: в казне не хватает %s", fmt(total))
            await _dm(OWNER_ID, f"⚠️ Ежедневный чек не выдан: в казне {fmt(treasury_get())}, нужно {fmt(total)}.")
            return False
        cid = gen_code()
        x("INSERT INTO checks(check_id,owner_id,amount,max_activations,description,created_at) VALUES(?,?,?,?,?,?)",
          (cid, 0, amount, len(ids), "Ежедневный чек", now()))
        text = box("<b>🎁 ЕЖЕДНЕВНЫЙ ЧЕК</b>", f"💰 Тебе: <b>{fmt(amount)} RCOIN</b>",
                   "Нажми кнопку — чек активируется один раз.")
        markup = kb([btn(f"Забрать {fmt(amount)}", url=deeplink("check_" + cid), icon="check")])
        sent = 0
        for uid2 in ids:
            try:
                await bot.send_message(uid2, text, reply_markup=markup)
                sent += 1
            except Exception as e:
                log.debug("daily check dm %s: %s", uid2, e)
            await asyncio.sleep(0.04)
        if not sent:
            x("UPDATE checks SET is_active=0 WHERE check_id=?", (cid,))
            treasury_add(total)
            await _dm(OWNER_ID, "⚠️ Ежедневный чек не доставлен ни одному игроку.")
            return False
        log.info("Ежедневный чек %s: %s × %s", cid, fmt(amount), sent)
        return True

    if chats:
        if slots <= 0:
            slots = max(1, min(100, len(q("SELECT user_id FROM users"))))
        total = amount * slots
        if not treasury_take(total):
            log.warning("Авто-чек %s: в казне не хватает %s", kind, fmt(total))
            await _dm(OWNER_ID, f"⚠️ Авто-чек не выдан: в казне {fmt(treasury_get())}, нужно {fmt(total)}. Пополни казну.")
            return False
        cid = gen_code()
        x("INSERT INTO checks(check_id,owner_id,amount,max_activations,description,created_at) VALUES(?,?,?,?,?,?)",
          (cid, 0, amount, slots, "Авточек из казны", now()))
        text = box(f"<b>{title}</b>", f"💰 Чек: <b>{fmt(amount)} RCOIN</b>",
                   f"🎟 Активаций: <b>{fmt(slots)}</b>",
                   "Нажми кнопку — чек активируется один раз на игрока.")
        markup = kb([btn(f"Забрать {fmt(amount)}", url=deeplink("check_" + cid), icon="check")])
        sent = 0
        for ref in chats:
            try:
                await bot.send_message(chat_ref(ref), text, reply_markup=markup)
                sent += 1
            except Exception as e:
                log.warning("Авто-чек %s: чат %s — %s", kind, ref, e)
        if not sent:
            x("UPDATE checks SET is_active=0 WHERE check_id=?", (cid,))
            treasury_add(total)
            await _dm(OWNER_ID, "⚠️ Авто-чек не отправлен: проверь чаты в настройках казны.")
            return False
        log.info("Авто-чек %s: чек %s × %s в %s чатах", kind, fmt(amount), slots, sent)
        return True

    ids = [r["user_id"] for r in q("SELECT user_id FROM users WHERE banned_until<=?", (now(),))]
    if not ids:
        return False
    total = amount * len(ids)
    if not treasury_take(total):
        log.warning("Авто-чек %s: в казне не хватает %s", kind, fmt(total))
        await _dm(OWNER_ID, f"⚠️ Авто-чек не выдан: в казне {fmt(treasury_get())}, нужно {fmt(total)}. Пополни казну.")
        return False
    x("UPDATE users SET balance_coin=balance_coin+? WHERE banned_until<=?", (amount, now()))
    if kind == "sat":
        for uid in ids:
            inv_add(uid, random.choice(list(SOUVENIRS)))
    text = box(f"<b>{title}</b>", f"💰 Каждому игроку: <b>+{fmt(amount)} RCOIN</b> из казны" + ("\n🎁 + новогодний сувенир на склад!" if kind == "sat" else ""),
               "Заходи в бота и играй! 🚀")
    try:
        await bot.send_message(ANNOUNCE_CHAT, text)
    except Exception as e:
        log.warning("announce: %s", e)

    async def spam():
        for uid in ids:
            await _dm(uid, text)
            await asyncio.sleep(0.05)
    asyncio.create_task(spam())
    log.info("Авто-чек %s выдан %s игрокам", kind, len(ids))
    return True


async def db_backup_loop():
    """Раз в 30 минут копия SQLite-базы; старые копии чистятся."""
    while True:
        await asyncio.sleep(1800)
        try:
            path = backup_db()
            if path:
                folder = Path(path).parent
                files = sorted(folder.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
                for old in files[12:]:
                    old.unlink(missing_ok=True)
        except Exception:
            log.exception("db_backup_loop")


async def scheduler_loop():
    while True:
        try:
            n = datetime.now(MSK)
            d = today()
            prev_day = (n - timedelta(days=1)).strftime("%Y-%m-%d")
            if not kv_get("snowman:paid:" + prev_day):
                for winner_uid, place, amount in distribute_snowman_rewards(prev_day):
                    await _dm(winner_uid, f"⛄ <b>СНЕЖНЫЙ МАРАФОН ЗАВЕРШЁН!</b>\nТвоё место: <b>#{place}</b>\nНаграда из казны: <b>+{fmt(amount)} RCOIN</b>")
            if n.weekday() == 4 and n.hour >= 23 and not kv_get("auto:fri:" + d):
                if int(tset_get().get("auto_fri") or 0):
                    kv_set("auto:fri:" + d, "1")
                    await distribute_check("fri")
            if n.weekday() == 5 and n.hour >= 12 and not kv_get("auto:sat:" + d):
                if int(tset_get().get("auto_sat") or 0):
                    kv_set("auto:sat:" + d, "1")
                    await distribute_check("sat")
            if n.hour >= int(tset_get().get("daily_hour") or 12) and not kv_get("auto:daily:" + d):
                if int(tset_get().get("daily_enabled") or 0):
                    kv_set("auto:daily:" + d, "1")
                    await distribute_check("daily")
        except Exception:
            log.exception("scheduler")
        await asyncio.sleep(30)


@dp.message(Command("forcecheck"))
async def cmd_forcecheck(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        return
    kind = (command.args or "").strip()
    if kind not in ("fri", "sat"):
        return await message.reply("Использование: /forcecheck fri | sat  (тест авто-чека пятницы/субботы)")
    ok = await distribute_check(kind)
    await message.reply("✅ Выдано." if ok else "❌ Не выдано (нет игроков или мало в казне).")


@dp.message(Command("grantadmin"))
async def cmd_grant(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только владелец.")
    t = find_user((command.args or "").strip())
    if not t:
        return await message.reply("Использование: /grantadmin ID|@ник")
    update_user(t["user_id"], is_admin_rank=1, rank_title="ADMIN")
    await message.reply(f"✅ {uname(t, False)} теперь админ. Снять: /revokeadmin ID")


@dp.message(Command("revokeadmin"))
async def cmd_revoke(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        return await message.reply("⛔ Только владелец.")
    t = find_user((command.args or "").strip())
    if not t or t["user_id"] == OWNER_ID:
        return await message.reply("Использование: /revokeadmin ID|@ник")
    update_user(t["user_id"], is_admin_rank=0, rank_title="Новичок")
    await message.reply("✅ Права сняты.")


# ============================ ВЕБ-АПП: сервер ============================
def check_init(init: str) -> Optional[dict]:
    try:
        data = dict(parse_qsl(init, keep_blank_values=True))
        h = data.pop("hash", "")
        s = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(hmac.new(secret, s.encode(), hashlib.sha256).hexdigest(), h):
            return None
        if now() - int(data.get("auth_date", "0")) > 86400:
            return None
        return json.loads(data["user"])
    except Exception:
        return None


def api(fn):
    async def handler(request: web.Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        tu = check_init(str(body.get("init", "")))
        if not tu:
            return web.json_response({"ok": False, "err": "Открой приложение через бота в Telegram"})
        ensure_user(SimpleNamespace(id=tu["id"], username=tu.get("username", ""), first_name=tu.get("first_name", ""), last_name=tu.get("last_name", "")))
        u = get_user(tu["id"])
        if u["banned_until"] > now():
            return web.json_response({"ok": False, "err": "Ты забанен"})
        try:
            res = fn(u, body)
        except Exception:
            log.exception("api %s", fn.__name__)
            res = {"ok": False, "err": "Ошибка сервера"}
        res.setdefault("balance", get_user(u["user_id"])["balance_coin"])
        return web.json_response(res)
    return handler


def w_bet(u, body, lo: int = 10) -> int:
    try:
        bet = int(float(body.get("bet", 0)))
    except (TypeError, ValueError):
        return 0
    return bet if lo <= bet <= MAX_BET else 0


def w_err(msg: str) -> dict:
    return {"ok": False, "err": msg}


def w_spend(u, bet: int, lo: int = 10) -> Optional[dict]:
    if bet < lo:
        return w_err(f"Минимальная ставка {lo}")
    if not spend(u["user_id"], bet):
        return w_err("Недостаточно RCOIN")
    return None


# ---------- арена: квадратная сцена со ставками ----------
AR: Dict[str, Any] = {}
AR_HIST: List[dict] = []
AR_CD, AR_ROLL, AR_SHOW, AR_MAX = 15, 8, 9, 10
AR_MIN_BET = 1
ARENA_HEX = ["#ff8a3d", "#3d9bff", "#35d07f", "#b06bff", "#ffd23d", "#ff5c5c", "#2de2e6", "#c98bff", "#8dff6b", "#ff7ab8"]
ARENA_BLACK = "#111111"


def _ar_round_bet() -> int:
    for p in AR["players"].values():
        return int(p.get("bet", 0) or 0)
    return 0


def _ar_refund():
    for uid, p in list(AR["players"].items()):
        bet = int(p.get("bet", 0) or 0)
        if bet > 0:
            add_coin(uid, bet)


def _ar_save():
    """Страховка от перезапуска: сохраняем ставки активного лобби."""
    try:
        kv_set("arena:web", json.dumps({str(k): int(v.get("bet", 0) or 0) for k, v in AR["players"].items()}))
    except Exception:
        log.debug("arena save failed", exc_info=True)


def ar_restore():
    """После перезапуска возвращаем ставки и джекпот арены."""
    try:
        bonus = int(kv_get("arena:bonus") or 0)
        if bonus > 0:
            AR["bonus"] = bonus
    except Exception:
        pass
    raw = kv_get("arena:web")
    if not raw or raw in ("{}", "null"):
        return
    try:
        data = json.loads(raw)
        refunded = 0
        for uid, bet in (data or {}).items():
            bet = int(bet or 0)
            if bet > 0:
                add_coin(int(uid), bet)
                refunded += bet
        if refunded:
            log.warning("Арена: возвращены ставки после перезапуска — %s RCOIN", refunded)
    except Exception:
        log.exception("ar_restore")
    kv_set("arena:web", "{}")


def ar_reset(refund: bool = False):
    bonus = int(AR.get("bonus", 0) or 0)
    if refund:
        _ar_refund()
        try:
            kv_set("arena:web", "{}")
        except Exception:
            pass
    AR.clear()
    AR.update(phase="idle", players={}, t_cd=0.0, t_roll=0.0, t_done=0.0,
              winner=None, created=time.time(), bonus=bonus)


ar_reset()


def ar_zones(players: dict) -> list:
    """Кольцо делится на зоны по ставкам: чем больше ставка, тем шире сектор."""
    total = sum(max(0, int(p.get("bet", 0) or 0)) for p in players.values())
    n = max(1, len(players))
    zones = []
    acc = 0.0
    for uid, p in players.items():
        bet = max(0, int(p.get("bet", 0) or 0))
        share = (bet / total) if total else 1 / n
        start = acc
        acc += share
        zones.append({"id": uid, "name": p.get("name", ""), "color": p.get("color", "#3d9bff"),
                      "bet": bet, "share": round(share * 100, 1),
                      "start": round(start * 360, 2), "end": round(min(1.0, acc) * 360, 2)})
    return zones


def ar_tick():
    t = time.time()
    ph = AR["phase"]
    if ph == "countdown" and t >= AR["t_cd"] + AR_CD:
        ids = list(AR["players"])
        if not ids:
            ar_reset()
            return None
        weights = [max(1, int(AR["players"][i].get("bet", 0) or 0)) for i in ids]
        AR["winner"] = random.choices(ids, weights=weights, k=1)[0]
        AR["phase"], AR["t_roll"] = "rolling", t
        AR["zones"] = ar_zones(AR["players"])
    elif ph == "rolling" and t >= AR["t_roll"] + AR_ROLL:
        winner = AR["winner"]
        players = dict(AR["players"])
        pool = sum(int(p.get("bet", 0) or 0) for p in players.values())
        bonus = int(AR.get("bonus", 0) or 0)
        rake = pool // 10 if pool else 0
        prize = (pool - rake + bonus) if pool else 0
        payout = 0
        if pool > 0:
            treasury_add(rake)
            win_bet = int(players[winner].get("bet", 0) or 0)
            payout = int(prize * win_mult(winner)) if prize > win_bet > 0 else prize
            AR["bonus"] = 0
            try:
                kv_set("arena:bonus", "0")
            except Exception:
                pass
            for uid, p in players.items():
                settle(uid, "arena", int(p.get("bet", 0) or 0), prize if uid == winner else 0, "web arena")
            AR_HIST.insert(0, {"name": players[winner]["name"], "reward": f"{fmt(payout)} RCOIN", "paid": True})
        else:
            x("INSERT OR IGNORE INTO it_progress(user_id) VALUES(?)", (winner,))
            x("UPDATE it_progress SET xp=xp+25 WHERE user_id=?", (winner,))
            AR_HIST.insert(0, {"name": players[winner]["name"], "reward": "25 XP", "paid": False})
        del AR_HIST[6:]
        AR["phase"], AR["t_done"] = "done", t
        try:
            kv_set("arena:web", "{}")
        except Exception:
            pass
        return winner, payout
    elif ph == "done" and t >= AR["t_done"] + AR_SHOW:
        ar_reset()
    elif ph == "waiting" and t - AR["created"] > 600:
        ar_reset(refund=True)
    return None


async def arena_loop():
    while True:
        try:
            res = ar_tick()
            if res:
                winner, prize = res
                if prize:
                    await _dm(winner, f"{E('win')} <b>Арена завершена!</b> Ты забрал <b>{fmt(prize)}</b> RCOIN.")
                else:
                    await _dm(winner, f"{E('win')} <b>Арена завершена!</b> Ты получил <b>25 XP</b> за победу.")
        except Exception:
            log.exception("arena_loop")
        await asyncio.sleep(0.5)


def ar_state(uid: int) -> dict:
    t = time.time()
    pl = AR["players"]
    ids = list(pl)
    count = len(ids)
    ph = AR["phase"]
    pool = sum(int(p.get("bet", 0) or 0) for p in pl.values())
    bonus = int(AR.get("bonus", 0) or 0)
    players = []
    for i in ids:
        bet = int(pl[i].get("bet", 0) or 0)
        pct = round(bet * 100 / pool, 1) if pool else round(100 / max(count, 1), 1)
        players.append({"id": i, "name": pl[i]["name"], "color": pl[i]["color"], "pct": pct,
                        "avatar": pl[i].get("avatar", ""), "bet": bet, "you": i == uid})
    winner_idx = ids.index(AR["winner"]) if AR.get("winner") in ids else -1
    return {"phase": ph, "players": players, "pool": pool + bonus, "bonus": bonus, "bet": _ar_round_bet(), "you": uid in pl,
            "your_bet": int(pl[uid].get("bet", 0) or 0) if uid in pl else 0,
            "cd_left": max(0.0, AR["t_cd"] + AR_CD - t) if ph == "countdown" else 0,
            "roll_total": AR_ROLL, "roll_elapsed": min(AR_ROLL, t - AR["t_roll"]) if ph == "rolling" else (AR_ROLL if ph == "done" else 0),
            "winner_idx": winner_idx, "history": AR_HIST, "max": AR_MAX,
            "zones": ar_zones(pl) if count else [],
            "roll_stop": round(AR["t_roll"] + AR_ROLL, 3) if ph == "rolling" else 0,
            "min_bet": AR_MIN_BET, "rake": pool // 10, "prize": pool - pool // 10 + bonus,
            "free": pool == 0 and bonus == 0}


def a_arena(u, body):
    ar_tick()
    return {"ok": True, "state": ar_state(u["user_id"])}


def a_arena_join(u, body):
    ar_tick()
    uid = u["user_id"]
    if uid in AR["players"]:
        return {"ok": True, "state": ar_state(uid)}
    if AR["phase"] not in ("idle", "waiting", "countdown"):
        return w_err("Раунд уже идёт — дождись следующего")
    if len(AR["players"]) >= AR_MAX:
        return w_err("Арена заполнена")
    try:
        bet = int(float(body.get("bet", 0) or 0))
    except (TypeError, ValueError):
        bet = 0
    if bet < AR_MIN_BET:
        return w_err(f"Минимальная ставка {fmt(AR_MIN_BET)} RCOIN")
    if not spend(uid, bet):
        return w_err("Недостаточно RCOIN")
    name = re.sub(r"<[^>]+>", "", uname(u, False))
    requested = str(body.get("color", "")).lower()
    if requested == ARENA_BLACK and not is_premium(uid):
        requested = ""
    used = {p.get("color") for p in AR["players"].values()}
    allowed = set(ARENA_HEX) | {ARENA_BLACK}
    if requested not in allowed or requested in used:
        requested = ""
    color = requested or next((c for c in ARENA_HEX if c not in used), ARENA_HEX[0])
    photo = str(body.get("photo_url", ""))[:500]
    ok_photo = photo.startswith("https://t.me/i/userpic/") or photo.startswith("https://telegram.org/")
    m = re.fullmatch(r"/nft/(\d+)", photo)
    if m:
        ok_photo = q("SELECT 1 FROM nft_items WHERE id=? AND owner_id=?", (int(m.group(1)), uid), one=True) is not None
    if not ok_photo:
        photo = ""
    AR["players"][uid] = {"name": name, "color": color, "avatar": photo, "bet": bet}
    t = time.time()
    if len(AR["players"]) == 1:
        AR["phase"], AR["created"] = "waiting", t
    elif AR["phase"] != "countdown":
        AR["phase"], AR["t_cd"] = "countdown", t
    _ar_save()
    return {"ok": True, "state": ar_state(uid), "balance": int(get_user(uid)["balance_coin"])}


def a_arena_add(u, body):
    ar_tick()
    uid = u["user_id"]
    if uid not in AR["players"]:
        return w_err("Сначала войди в лобби")
    if AR["phase"] not in ("waiting", "countdown"):
        return w_err("Добавить ставку можно до старта шарика")
    try:
        extra = int(float(body.get("bet", 0) or 0))
    except (TypeError, ValueError):
        extra = 0
    if extra < AR_MIN_BET:
        return w_err(f"Минимальная добавка {fmt(AR_MIN_BET)} RCOIN")
    if not spend(uid, extra):
        return w_err("Недостаточно RCOIN")
    AR["players"][uid]["bet"] = int(AR["players"][uid].get("bet", 0) or 0) + extra
    _ar_save()
    return {"ok": True, "state": ar_state(uid), "balance": int(get_user(uid)["balance_coin"])}


def a_arena_leave(u, body):
    uid = u["user_id"]
    if AR["phase"] != "waiting" or uid not in AR["players"]:
        return w_err("Покинуть лобби можно до начала отсчёта")
    bet = int(AR["players"][uid].get("bet", 0) or 0)
    del AR["players"][uid]
    if bet:
        add_coin(uid, bet)
    if not AR["players"]:
        ar_reset()
    _ar_save()
    return {"ok": True, "state": ar_state(uid), "balance": int(get_user(uid)["balance_coin"])}


def ar_admin_bonus(uid: int, amount: int) -> dict:
    """Админ добавляет джекпот в арену из своего баланса."""
    if not is_admin(uid):
        return w_err("Только для администрации")
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return w_err("Неверная сумма")
    if amount <= 0:
        return w_err("Сумма должна быть больше нуля")
    if not spend(uid, amount):
        return w_err("Недостаточно RCOIN")
    AR["bonus"] = int(AR.get("bonus", 0) or 0) + amount
    try:
        kv_set("arena:bonus", str(AR["bonus"]))
    except Exception:
        log.debug("arena bonus save", exc_info=True)
    return {"ok": True, "bonus": AR["bonus"], "msg": f"Бонус арены +{fmt(amount)}"}


# ---------- мини-игры ----------
def a_snowman_state(u, body):
    row = snowman_row(u["user_id"])
    return {"ok": True, "snowballs": int(row["snowballs"]), "snowmen": int(row["snowmen"]),
            "leaderboard": [{"name": str(r["name"]), "snowballs": int(r["snowballs"]), "snowmen": int(r["snowmen"])} for r in snowman_leaderboard(limit=10)],
            "need": SNOWMAN_NEED, "cooldown": max(0, SNOWMAN_COOLDOWN - (now() - int(row["last_collect"] or 0)))}

def a_snowman_collect(u, body):
    return snowman_collect(u["user_id"])

def a_snowman_build(u, body):
    return snowman_build(u["user_id"])


def a_me(u, body):
    uid = u["user_id"]
    stats = q("SELECT COUNT(*) n, SUM(CASE WHEN is_win=1 THEN 1 ELSE 0 END) w, SUM(CASE WHEN bet_amount>win_amount THEN bet_amount-win_amount ELSE 0 END) lost FROM bet_history WHERE user_id=?", (uid,), one=True)
    bid = int(u.get("balance_nft_id") or 0)
    pid = int(u.get("profile_nft_id") or 0)
    return {"ok": True, "name": re.sub(r"<[^>]+>", "", uname(u, False)), "id": uid,
            "balance": u["balance_coin"], "rbp": u["balance_point"], "games": stats["n"] or 0,
            "wins": u["total_wins"] or stats["w"] or 0, "lost": int(stats["lost"] or 0),
            "rank": u["rank_title"] or "Новичок",
            "premium": is_premium(uid),
            "is_admin": is_admin(uid),
            "ticker": ui_ticker(),
            "theme": ui_theme(),
            "badges": [{"key": b, "role": BADGES[b]["role"], "title": BADGES[b]["title"],
                        "emoji_id": BADGES[b].get("id") or ""} for b in profile_badges(uid) if b in BADGES],
            "nft_balance_url": f"/nft/{bid}" if bid else "",
            "nft_profile_url": f"/nft/{pid}" if pid else "",
            "photo_url": str(body.get("photo_url", ""))[:500]}


def a_coin(u, body):
    bet = w_bet(u, body)
    side = body.get("side")
    if side not in ("heads", "tails"):
        return w_err("Выбери сторону")
    e = w_spend(u, bet)
    if e:
        return e
    res = random.choice(["heads", "tails"])
    pay = int(bet * 1.95) if res == side else 0
    settle(u["user_id"], "coin", bet, pay, res)
    return {"ok": True, "result": res, "win": pay > 0, "payout": pay}


def a_dice(u, body):
    bet = w_bet(u, body)
    try:
        chance = int(body.get("chance", 50))
    except (TypeError, ValueError):
        return w_err("Неверный шанс")
    if not 5 <= chance <= 90:
        return w_err("Шанс от 5% до 90%")
    e = w_spend(u, bet)
    if e:
        return e
    roll = round(random.uniform(0, 100), 2)
    pay = int(bet * 95 / chance) if roll < chance else 0
    settle(u["user_id"], "webdice", bet, pay, f"{roll}<{chance}")
    return {"ok": True, "roll": roll, "win": pay > 0, "payout": pay}


CRASH_RATE = 0.08


def crash_view(s: dict) -> dict:
    st = s["state"]
    if s["status"] != "active":
        return {"ok": True, **st.get("res", {"status": "crashed", "mult": 1.0})}
    m = math.exp(CRASH_RATE * (time.time() - st["t0"]))
    if m >= st["cp"]:
        if sess_close(s["id"], "lost"):
            settle(s["user_id"], "webcrash", s["bet"], 0, f"cp={st['cp']}")
        st["res"] = {"status": "crashed", "mult": st["cp"], "payout": 0}
        sess_save(s["id"], st)
        return {"ok": True, **st["res"]}
    return {"ok": True, "status": "run", "mult": round(m, 2)}


def a_crash_start(u, body):
    bet = w_bet(u, body)
    e = w_spend(u, bet)
    if e:
        return e
    sid = sess_new(u["user_id"], "webcrash", bet, {"cp": crash_point(), "t0": time.time()})
    return {"ok": True, "id": sid}


def a_crash_poll(u, body):
    s = sess_get(int(body.get("id", 0)))
    if not s or s["user_id"] != u["user_id"] or s["game"] != "webcrash":
        return w_err("Игра не найдена")
    return crash_view(s)


def a_crash_cash(u, body):
    s = sess_get(int(body.get("id", 0)))
    if not s or s["user_id"] != u["user_id"] or s["game"] != "webcrash":
        return w_err("Игра не найдена")
    v = crash_view(s)
    if v.get("status") != "run":
        return v
    st = s["state"]
    mult = math.floor(v["mult"] * 100) / 100
    if not sess_close(s["id"], "won"):
        return crash_view(sess_get(s["id"]))
    pay = int(s["bet"] * mult)
    settle(u["user_id"], "webcrash", s["bet"], pay, f"x{mult}")
    st["res"] = {"status": "won", "mult": mult, "payout": pay, "cp": st["cp"]}
    sess_save(s["id"], st)
    return {"ok": True, **st["res"]}


def mines_resp(r: dict) -> dict:
    if "err" in r:
        return w_err(r["err"])
    st = r["state"]
    over = r["status"] in ("lost", "won")
    out = {"ok": True, "status": r["status"], "open": st["open"], "m": st["m"],
           "mult": r.get("mult") or mines_mult(st["m"], len(st["open"])), "payout": r.get("payout", 0)}
    if over:
        out["mines"] = st["mines"]
    return out


def a_mines_start(u, body):
    bet = w_bet(u, body)
    try:
        m = int(body.get("mines", 3))
    except (TypeError, ValueError):
        m = 3
    if not 1 <= m <= 10:
        return w_err("Мин: от 1 до 10")
    e = w_spend(u, bet)
    if e:
        return e
    return {"ok": True, "id": mines_start(u["user_id"], bet, m), "m": m, "open": [], "mult": 1.0}


def a_mines_open(u, body):
    return mines_resp(mines_open(int(body.get("id", 0)), u["user_id"], int(body.get("i", -1))))


def a_mines_cash(u, body):
    return mines_resp(mines_cash(int(body.get("id", 0)), u["user_id"]))


WEBAPP_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover,user-scalable=no">
<title>RUBIN</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{
  --a1:#7c5cff;--a2:#4f8bff;--a3:#c06bff;
  --glass:linear-gradient(158deg,rgba(255,255,255,.085),rgba(255,255,255,.022));
  --stroke:rgba(255,255,255,.12);--stroke2:rgba(255,255,255,.2);
  --t1:#f3f4fb;--t2:#9ea2ba;--t3:#6b6f88;
  --gold:#ffd98a;--ok:#4ce0a4;--bad:#ff6b85;
  --nav:calc(88px + env(safe-area-inset-bottom));--r:24px;
}
html,body{height:100%}
body{font-family:"Inter","SF Pro Display",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  color:var(--t1);background:#050609;-webkit-font-smoothing:antialiased;overflow-x:hidden;
  padding:calc(8px + env(safe-area-inset-top)) 12px calc(var(--nav) + 18px);min-height:100vh}
body:before{content:"";position:fixed;inset:-10%;z-index:-2;pointer-events:none;background:
  radial-gradient(58% 42% at 82% -4%,color-mix(in srgb,var(--a1) 42%,transparent),transparent 70%),
  radial-gradient(52% 36% at 4% 14%,color-mix(in srgb,var(--a2) 30%,transparent),transparent 72%),
  radial-gradient(64% 44% at 46% 108%,color-mix(in srgb,var(--a3) 26%,transparent),transparent 74%),#050609;
  filter:blur(6px)}
body:after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.55;
  background-image:linear-gradient(rgba(255,255,255,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.02) 1px,transparent 1px);
  background-size:48px 48px;
  -webkit-mask-image:radial-gradient(circle at 50% 8%,#000 0,transparent 72%);mask-image:radial-gradient(circle at 50% 8%,#000 0,transparent 72%)}
body.wall:before{opacity:0}
body.wall:after{opacity:0}
body.wall{background-size:cover;background-position:center;background-attachment:fixed}
body.wall .glass{background:rgba(9,10,17,.66)}
.wrap{max-width:720px;margin:auto}
svg.i{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;display:block;flex:none}
svg.i.xs{width:13px;height:13px}svg.i.sm{width:16px;height:16px}svg.i.lg{width:26px;height:26px}svg.i.xl{width:34px;height:34px}
svg.i.fill{fill:currentColor;stroke:none}

/* ---------- шапка ---------- */
.top{display:flex;align-items:center;gap:10px;margin:2px 2px 12px}
.ava{width:44px;height:44px;border-radius:15px;flex:none;display:grid;place-items:center;overflow:hidden;
  font-weight:900;font-size:16px;color:#f0eaff;background:linear-gradient(150deg,var(--a1),var(--a3));
  box-shadow:0 8px 22px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.4);border:1px solid rgba(255,255,255,.2)}
.ava img{width:100%;height:100%;object-fit:cover}
.top .who{flex:1;min-width:0}
.who b{display:block;font-size:14px;font-weight:800;letter-spacing:-.1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.who small{display:flex;align-items:center;gap:5px;margin-top:3px;color:var(--t2);font-size:10.5px;font-weight:700}
.who small svg{color:var(--gold)}
.balpill{display:flex;align-items:center;gap:7px;padding:9px 13px;border-radius:16px;font-weight:850;font-size:13px;
  background:var(--glass);border:1px solid var(--stroke);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}
.balpill svg{color:var(--gold)}
/* ---------- стекло ---------- */
.glass{position:relative;background:var(--glass);border:1px solid var(--stroke);border-radius:var(--r);
  backdrop-filter:blur(22px) saturate(1.4);-webkit-backdrop-filter:blur(22px) saturate(1.4);
  box-shadow:0 20px 50px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.07)}
.glass.hi{background:linear-gradient(160deg,rgba(255,255,255,.11),rgba(255,255,255,.025))}
.pad{padding:16px}
.page{display:none}.page.active{display:block;animation:fadeUp .26s cubic-bezier(.2,.8,.2,1)}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.h{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
.h h2{font-size:15.5px;font-weight:850;letter-spacing:-.2px}
.sub{color:var(--t2);font-size:12px;line-height:1.55}
.tiny{color:var(--t3);font-size:10.5px;line-height:1.5}
.chip{display:inline-flex;align-items:center;gap:5px;height:25px;padding:0 10px;border-radius:999px;font-size:10px;font-weight:800;
  color:#d9dcf1;background:rgba(255,255,255,.06);border:1px solid var(--stroke)}
.chip.a{color:#c9d8ff;border-color:rgba(124,92,255,.45);background:rgba(124,92,255,.16)}
.chip.g{color:#ffe7b3;border-color:rgba(255,217,138,.35);background:rgba(255,217,138,.11)}
.chip.ok{color:#abf5d4;border-color:rgba(76,224,164,.35);background:rgba(76,224,164,.12)}
/* ---------- баланс ---------- */
.hero{padding:18px 16px 15px;overflow:hidden;border-radius:28px}
.hero:before{content:"";position:absolute;right:-70px;top:-90px;width:240px;height:240px;border-radius:50%;
  background:radial-gradient(circle,color-mix(in srgb,var(--a1) 55%,transparent),transparent 68%);filter:blur(14px)}
.hero .lbl{position:relative;font-size:9.5px;letter-spacing:.22em;text-transform:uppercase;color:#a6aecb;font-weight:800}
.hero .amt{position:relative;display:flex;align-items:baseline;gap:8px;margin:5px 0 14px}
.hero .amt b{font-size:clamp(30px,9.4vw,40px);font-weight:900;letter-spacing:-1.6px;line-height:1}
.hero .amt span{font-size:11.5px;font-weight:800;color:#a6aecb;letter-spacing:.08em}
.acts{position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.act{border:1px solid var(--stroke);border-radius:17px;background:rgba(255,255,255,.055);color:#e9ebf7;
  padding:11px 2px 9px;font:800 9.5px/1.1 inherit;display:grid;gap:7px;place-items:center;cursor:pointer;transition:.16s}
.act:active{transform:scale(.96);background:rgba(124,92,255,.22);border-color:rgba(124,92,255,.5)}
.act svg{color:#c4cbf0;width:20px;height:20px}
/* ---------- кейсы ---------- */
.cases{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.case{position:relative;overflow:hidden;border-radius:20px;border:1px solid var(--stroke);padding:12px;cursor:pointer;
  background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.018));transition:.16s}
.case:active{transform:scale(.985)}
.case:before{content:"";position:absolute;inset:-40% -30% auto auto;width:150px;height:150px;border-radius:50%;
  background:radial-gradient(circle,var(--c,#7c5cff),transparent 68%);opacity:.55;filter:blur(18px)}
.case .tag{position:absolute;top:10px;right:10px;font-size:8px;letter-spacing:.1em;font-weight:900;color:#e2e5f5;
  text-transform:uppercase;background:rgba(0,0,0,.32);border:1px solid var(--stroke);padding:3px 7px;border-radius:999px}
.case .art{position:relative;width:58px;height:58px;border-radius:17px;display:grid;place-items:center;color:#fff;
  background:linear-gradient(150deg,rgba(255,255,255,.26),rgba(255,255,255,.04));border:1px solid var(--stroke2);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.3),0 8px 18px rgba(0,0,0,.35)}
.case .art svg{width:30px;height:30px;stroke-width:1.5}
.case b{display:block;font-size:12.5px;margin-top:11px;letter-spacing:-.1px}
.case .pr{display:flex;align-items:center;gap:5px;margin-top:5px;font-size:11px;font-weight:800;color:#cbd2f0}
.case .pr svg{color:var(--gold)}
.case .op{width:100%;margin-top:9px;border-radius:13px;padding:9px;border:1px solid rgba(255,255,255,.15);
  color:#fff;font:800 11.5px inherit;cursor:pointer;
  background:linear-gradient(150deg,var(--a1),var(--a2));box-shadow:0 8px 20px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.3)}
/* ---------- NFT ---------- */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.nft{border-radius:19px;overflow:hidden;border:1px solid var(--stroke);background:rgba(6,7,12,.7);cursor:pointer;transition:.16s}
.nft:active{transform:scale(.985)}
.nft .im{position:relative;aspect-ratio:1;background:#06070c;overflow:hidden}
.nft .im img{width:100%;height:100%;object-fit:cover;display:block}
.nft .num{position:absolute;right:7px;top:7px;font-size:10px;font-weight:900;padding:3px 8px;border-radius:999px;
  background:rgba(0,0,0,.55);border:1px solid var(--stroke2);backdrop-filter:blur(8px)}
.nft .lvl{position:absolute;left:7px;top:7px;font-size:8.5px;font-weight:900;padding:3px 7px;border-radius:999px;
  background:linear-gradient(150deg,var(--a1),var(--a3));box-shadow:0 4px 12px rgba(0,0,0,.4)}
.nft .inf{padding:8px 9px 10px}
.nft .nm{font-size:11px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nft .rw{display:flex;justify-content:space-between;gap:6px;margin-top:4px;font-size:9px;color:var(--t2);font-weight:700}
.nft .rar{margin-top:6px;font-size:8.5px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:#8c90a8}
.nft .rar.rare{color:#b9a4ff}.nft .rar.epic{color:#ffcf8a}
/* ---------- апгрейдер ---------- */
.dial{position:relative;width:min(80vw,300px);aspect-ratio:1;margin:6px auto 2px;display:grid;place-items:center}
.dial svg.base{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.dial .core{position:absolute;inset:29%;border-radius:50%;display:grid;place-items:center;text-align:center;overflow:hidden;
  background:radial-gradient(circle at 50% 32%,rgba(46,52,84,.98),rgba(7,8,14,.99) 78%);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.09),0 0 30px rgba(0,0,0,.9),0 0 60px color-mix(in srgb,var(--a1) 28%,transparent)}
.dial .core img{width:100%;height:100%;object-fit:cover}
.dial .core .ph{display:grid;gap:4px;place-items:center;color:#8e94b4}
.dial .core .ph small{font-size:9px;font-weight:800;letter-spacing:.08em;color:#6f7593}
.dial .core .pct{font-size:clamp(20px,7vw,30px);font-weight:900;letter-spacing:-1px}
.dial .core .pct.zero{color:#6f7593}
.dial .arrow{position:absolute;left:50%;top:-9px;transform:translateX(-50%);color:#fff;z-index:3;
  filter:drop-shadow(0 4px 10px rgba(0,0,0,.7));transition:none}
.dial .arrow svg{width:22px;height:22px;fill:currentColor;stroke:none}
.dial .beam{position:absolute;left:50%;top:0;width:2px;height:50%;transform-origin:50% 100%;transform:translateX(-50%) rotate(0deg);z-index:2;
  background:linear-gradient(to top,rgba(255,255,255,0),rgba(255,255,255,.55));transition:transform 4.6s cubic-bezier(.12,.85,.06,1)}
.dial .beam.zero{transition:none;opacity:0}
.dial.spinning .core{animation:pulse .7s ease-in-out infinite}
@keyframes pulse{50%{box-shadow:inset 0 0 0 1px rgba(255,255,255,.16),0 0 40px color-mix(in srgb,var(--a1) 55%,transparent)}}
.dial svg.base .zone{transition:opacity .35s}
.slotrow{display:flex;align-items:center;gap:8px;margin-top:14px}
.slot{flex:1;display:flex;align-items:center;gap:9px;min-width:0;padding:10px;border-radius:16px;cursor:pointer;
  border:1px dashed var(--stroke2);background:rgba(255,255,255,.03)}
.slot.filled{border-style:solid;border-color:rgba(124,92,255,.5);background:rgba(124,92,255,.1)}
.slot .sid{width:34px;height:34px;border-radius:11px;flex:none;display:grid;place-items:center;overflow:hidden;
  background:rgba(255,255,255,.07);color:#b9c0e2}
.slot .sid img{width:100%;height:100%;object-fit:cover}
.slot .tx{min-width:0}
.slot .tx small{display:block;font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:#8d92ad;font-weight:800}
.slot .tx b{display:block;font-size:11px;font-weight:800;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.slotrow .toarrow{color:#8d92ad;flex:none}
.modebar{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.mode{display:flex;align-items:center;justify-content:center;gap:7px;padding:11px;border-radius:15px;cursor:pointer;
  border:1px solid var(--stroke);background:rgba(255,255,255,.04);color:#cfd4ec;font:800 11.5px inherit}
.mode.on{background:linear-gradient(150deg,rgba(124,92,255,.45),rgba(79,139,255,.28));border-color:rgba(124,92,255,.55);color:#fff}
.betrow{display:flex;align-items:center;gap:8px;margin-top:12px}
.betrow input{flex:1;min-width:0;padding:12px 13px;border-radius:14px;border:1px solid var(--stroke2);background:rgba(0,0,0,.45);
  color:#fff;font:800 14px inherit;outline:none;appearance:none}
.betrow input:focus{border-color:rgba(124,92,255,.75);box-shadow:0 0 0 3px rgba(124,92,255,.16)}
.mini{border:1px solid var(--stroke2);background:rgba(255,255,255,.06);color:#dde1f4;border-radius:12px;
  padding:11px 12px;font:800 11.5px inherit;cursor:pointer;flex:none}
.mini:active{transform:scale(.96)}
.sumline{text-align:center;font-size:11.5px;color:#c6cce6;margin:12px 0 9px;min-height:17px;line-height:1.4}
.go{width:100%;border:1px solid rgba(255,255,255,.16);border-radius:18px;padding:14px;color:#fff;cursor:pointer;
  background:linear-gradient(150deg,var(--a1),var(--a2));font:900 14.5px inherit;display:flex;align-items:center;justify-content:center;gap:8px;
  box-shadow:0 16px 34px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.35)}
.go:disabled{opacity:.4;box-shadow:none;cursor:default}
.go:active:not(:disabled){transform:scale(.99)}
/* ---------- майнинг ---------- */
.fan{position:relative;width:min(56vw,212px);aspect-ratio:1;margin:14px auto 6px;border-radius:50%;display:grid;place-items:center;
  animation:rot 7s linear infinite;
  background:conic-gradient(from 0deg,#111a3a,color-mix(in srgb,var(--a2) 85%,#000),#dfe6ff,color-mix(in srgb,var(--a1) 90%,#000),#111a3a);
  box-shadow:0 0 0 8px rgba(255,255,255,.045),0 0 0 9px rgba(255,255,255,.09),0 24px 60px color-mix(in srgb,var(--a1) 40%,transparent)}
.fan:before{content:"";position:absolute;inset:14px;border-radius:50%;
  background:repeating-conic-gradient(from 0deg,rgba(255,255,255,.26) 0 7deg,transparent 7deg 34deg);
  -webkit-mask:radial-gradient(circle,transparent 0 30%,#000 31%);mask:radial-gradient(circle,transparent 0 30%,#000 31%)}
.fan:after{content:"";position:absolute;inset:36%;border-radius:50%;
  background:radial-gradient(circle at 34% 26%,#fff,#8ea6ff 42%,color-mix(in srgb,var(--a2) 90%,#000));
  box-shadow:0 0 28px rgba(160,180,255,.85),inset 0 2px 8px rgba(255,255,255,.6)}
.fan svg{position:relative;z-index:2;color:#0d1230;filter:drop-shadow(0 2px 5px rgba(255,255,255,.4))}
@keyframes rot{to{transform:rotate(360deg)}}
.srv{display:flex;align-items:center;gap:10px;padding:11px;border-radius:16px;border:1px solid var(--stroke);
  background:rgba(255,255,255,.035);margin-top:8px}
.srv .icw{width:36px;height:36px;border-radius:12px;flex:none;display:grid;place-items:center;color:#c3cbf0;background:rgba(124,92,255,.18)}
.srv b{display:block;font-size:12px}.srv small{display:block;color:var(--t2);font-size:9.5px;margin-top:2px}
.srv.own{border-color:rgba(76,224,164,.32);background:rgba(76,224,164,.07)}
.srv.own .icw{background:rgba(76,224,164,.18);color:var(--ok)}
.srv .buy{border:0;border-radius:11px;padding:9px 12px;cursor:pointer;color:#fff;font:800 11px inherit;
  background:linear-gradient(150deg,var(--a1),var(--a2))}
/* ---------- арена ---------- */
.arena{position:relative;width:min(94vw,420px);aspect-ratio:1;margin:8px auto 0}
.arena svg{width:100%;height:100%;overflow:visible}
.arena .lbl{fill:#080910;font-weight:900;font-size:10.5px;font-family:inherit}
.arena-core{position:absolute;inset:30%;border-radius:50%;display:grid;place-items:center;text-align:center;
  background:radial-gradient(circle at 50% 32%,rgba(34,38,64,.97),rgba(6,7,12,.99) 76%);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.1),inset 0 0 40px #000,0 18px 46px rgba(0,0,0,.6)}
.arena-core b{display:block;font-size:clamp(22px,7vw,32px);font-weight:900;letter-spacing:-1px}
.arena-core small{display:block;font-size:9px;letter-spacing:.18em;color:#98a0c0;font-weight:800;margin-top:4px}
.arena-core .cd{display:block;font-size:clamp(16px,5vw,22px);font-weight:900;margin-top:8px}
.arena-core .cd em{font-style:normal;font-size:1.6em;color:#fff}
.plist{display:grid;gap:7px;margin-top:12px}
.pl{display:flex;align-items:center;gap:9px;padding:10px;border-radius:15px;border:1px solid var(--stroke);background:rgba(255,255,255,.035)}
.pl.me{border-color:rgba(124,92,255,.5);background:rgba(124,92,255,.12)}
.pl.win{border-color:rgba(255,217,138,.6);background:rgba(255,217,138,.13);box-shadow:0 0 24px rgba(255,217,138,.22)}
.pl .dot{width:10px;height:10px;border-radius:50%;flex:none;box-shadow:0 0 12px currentColor;background:currentColor}
.pl .who2{flex:1;min-width:0;font-size:12.5px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pl .stake{font-size:11px;font-weight:800;color:#d3d9ee}
.pl .pc{min-width:46px;text-align:right;font-size:10.5px;font-weight:900;color:#b8c4ff}
.waiting{display:grid;place-items:center;gap:8px;padding:26px 10px;border-radius:18px;border:1px dashed var(--stroke2);
  color:var(--t2);font-size:12px;text-align:center;margin-top:10px}
.btnrow{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:8px}
.btnrow button{border:1px solid var(--stroke2);background:rgba(255,255,255,.05);color:#dde1f4;border-radius:12px;
  padding:10px 4px;font:800 11.5px inherit;cursor:pointer}
.btnrow button.on{background:linear-gradient(150deg,var(--a1),var(--a2));border-color:transparent;color:#fff}
/* ---------- профиль ---------- */
.stats{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:11px}
.st{padding:12px;border-radius:17px;border:1px solid var(--stroke);background:rgba(255,255,255,.035)}
.st span{display:block;color:var(--t2);font-size:10px;font-weight:700;margin-bottom:3px}
.st b{font-size:15px}
.themes{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.th{width:46px;height:46px;border-radius:15px;border:1px solid var(--stroke2);cursor:pointer;position:relative}
.th.on{outline:2px solid #8fa8ff;outline-offset:2px}
.th i{position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-style:normal;font-size:16px;font-weight:900}
.uprow{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
/* ---------- кнопки/ряды ---------- */
.btn{width:100%;border:1px solid rgba(255,255,255,.14);border-radius:16px;padding:12px 14px;cursor:pointer;
  font:850 13px inherit;color:#fff;display:flex;align-items:center;justify-content:center;gap:8px;
  background:linear-gradient(150deg,var(--a1),var(--a2));box-shadow:0 12px 26px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.3)}
.btn:active{transform:scale(.99)}
.btn.ghost{background:rgba(255,255,255,.06);border-color:var(--stroke2);box-shadow:none;color:#e3e6f6}
.btn.green{background:linear-gradient(150deg,#3fe0a0,#12a174)}
.btn.red{background:linear-gradient(150deg,#ff7f95,#c22147)}
.btn:disabled{opacity:.45}
.btn.sm{padding:9px 12px;font-size:11.5px;border-radius:12px;width:auto}
.btn.xs{padding:7px 10px;font-size:10.5px;border-radius:10px;width:auto}
.rowz{display:flex;gap:8px}.rowz>*{min-width:0;flex:1}
a.btn{text-decoration:none}
/* ---------- навигация ---------- */
.nav{position:fixed;z-index:40;left:50%;transform:translateX(-50%);bottom:calc(10px + env(safe-area-inset-bottom));
  width:min(540px,calc(100% - 16px));display:grid;grid-template-columns:repeat(6,1fr);gap:2px;padding:6px;border-radius:26px;
  background:rgba(10,11,18,.8);border:1px solid rgba(255,255,255,.1);
  backdrop-filter:blur(26px) saturate(1.6);-webkit-backdrop-filter:blur(26px) saturate(1.6);
  box-shadow:0 18px 50px rgba(0,0,0,.7),inset 0 1px 0 rgba(255,255,255,.08)}
.nav button{border:0;background:transparent;color:#6e7288;font:800 8.5px/1.1 inherit;padding:8px 1px;border-radius:19px;
  display:grid;gap:4px;place-items:center;cursor:pointer;transition:.16s}
.nav button svg{width:20px;height:20px}
.nav button.on{color:#fff;background:linear-gradient(160deg,rgba(124,92,255,.5),rgba(20,24,48,.85));
  box-shadow:inset 0 0 0 1px rgba(150,160,255,.4),0 8px 18px rgba(0,0,0,.4)}
/* ---------- модалки ---------- */
.modal{position:fixed;inset:0;z-index:60;display:none;align-items:flex-end;justify-content:center;
  background:rgba(2,3,7,.72);backdrop-filter:blur(10px);padding:10px}
.modal.show{display:flex}
.sheet{width:min(680px,100%);max-height:86vh;overflow:auto;border-radius:26px;padding:16px;
  background:linear-gradient(168deg,#171a2a,#080910);border:1px solid rgba(255,255,255,.13);
  box-shadow:0 -22px 60px #000c;animation:sheetUp .24s cubic-bezier(.2,.8,.2,1)}
@keyframes sheetUp{from{transform:translateY(26px);opacity:.3}to{transform:none;opacity:1}}
.shead{display:flex;align-items:center;justify-content:space-between;gap:9px;margin-bottom:12px}
.shead h3{font-size:15.5px;display:flex;align-items:center;gap:8px;min-width:0}
.xb{width:33px;height:33px;border-radius:50%;flex:none;cursor:pointer;border:1px solid var(--stroke2);
  background:rgba(255,255,255,.06);color:#d3d8ee;display:grid;place-items:center}
.pickgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.pick{border:1px solid var(--stroke);background:rgba(255,255,255,.04);border-radius:14px;padding:7px;cursor:pointer}
.pick img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;background:#06070c;display:block}
.pick b{display:block;font-size:10.5px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pick small{display:block;color:var(--t2);font-size:9px;margin-top:2px}
.pick.on{border-color:#8fa8ff;box-shadow:0 0 0 1px rgba(143,168,255,.6) inset}
.fullimg{width:100%;border-radius:18px;border:1px solid var(--stroke);background:#06070c;display:block}
label{display:block;color:var(--t2);font-size:10.5px;font-weight:800;margin:11px 0 5px;letter-spacing:.03em}
input[type=text],input[type=number],select{width:100%;padding:12px 13px;border-radius:14px;border:1px solid var(--stroke2);
  background:rgba(0,0,0,.45);color:#fff;font:800 14px inherit;outline:none;appearance:none}
input:focus,select:focus{border-color:rgba(124,92,255,.75);box-shadow:0 0 0 3px rgba(124,92,255,.16)}
input[type=file]{width:100%;font-size:11px;color:var(--t2)}
.empty{text-align:center;padding:24px 12px;color:var(--t2);font-size:12px}
.hide{display:none!important}
.toast{position:fixed;left:50%;bottom:calc(var(--nav) + 10px);transform:translate(-50%,14px);opacity:0;pointer-events:none;
  background:#1a1e34;border:1px solid rgba(143,168,255,.35);padding:10px 15px;border-radius:13px;font-size:12px;font-weight:800;
  transition:.2s;z-index:90;max-width:90%;text-align:center}
.toast.show{opacity:1;transform:translate(-50%,0)}
.confetti{position:fixed;inset:0;pointer-events:none;z-index:95;overflow:hidden}
.confetti i{position:absolute;width:7px;height:12px;border-radius:2px;animation:fall linear forwards}
@keyframes fall{to{transform:translateY(112vh) rotate(680deg)}}
@media(min-width:620px){.cases{grid-template-columns:repeat(3,1fr)}.grid{grid-template-columns:repeat(3,1fr)}
 .stats{grid-template-columns:repeat(4,1fr)}.pickgrid{grid-template-columns:repeat(3,1fr)}}
/* ================= GLASS 2.0 / THEMES / TICKER ================= */
:root{--bg:#040405;--panel:#08090d}
html[data-theme="iphone"]{--a1:#0a84ff;--a2:#5e5ce6;--a3:#64d2ff}
html[data-theme="android"]{--a1:#7c4dff;--a2:#00bfa6;--a3:#ff4081}
html[data-theme="ruby"]{--a1:#ff5470;--a2:#b3123b;--a3:#ff8a5c}
html[data-theme="ice"]{--a1:#7fdcff;--a2:#2f7fd8;--a3:#b6f2ff}
html[data-theme="emerald"]{--a1:#4ce39a;--a2:#12855c;--a3:#9dffcf}
html[data-theme="violet"]{--a1:#b06bff;--a2:#5b21b6;--a3:#e0a8ff}
html[data-theme="light"]{--a1:#0a84ff;--a2:#5e5ce6;--a3:#34c759}
html.light{
  --bg:#eef1f8;--t1:#10131b;--t2:#5b6272;--t3:#8a91a1;
  --glass:linear-gradient(158deg,rgba(255,255,255,.86),rgba(255,255,255,.58));
  --stroke:rgba(15,23,42,.10);--stroke2:rgba(15,23,42,.16);
}
html.light body{background:var(--bg);color:var(--t1)}
html.light body:before{background:
  radial-gradient(58% 42% at 82% -4%,rgba(10,132,255,.22),transparent 70%),
  radial-gradient(52% 36% at 4% 14%,rgba(94,92,230,.16),transparent 72%),
  radial-gradient(64% 44% at 46% 108%,rgba(52,199,89,.14),transparent 74%),#eef1f8;filter:none}
html.light body:after{opacity:.18;background-image:linear-gradient(rgba(15,23,42,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(15,23,42,.06) 1px,transparent 1px)}
html.light .glass{box-shadow:0 20px 50px rgba(30,45,80,.12),inset 0 1px 0 rgba(255,255,255,.9)}
html.light .glass.hi{background:linear-gradient(160deg,rgba(255,255,255,.95),rgba(255,255,255,.6))}
html.light .act,html.light .mode,html.light .mini,html.light .slot,html.light .srv,html.light .pl,html.light .st{color:#10131b;background:rgba(255,255,255,.48);border-color:rgba(15,23,42,.12)}
html.light .nft{background:rgba(255,255,255,.62);border-color:rgba(15,23,42,.1)}
html.light .nft .im{background:#e6ebf5}
html.light .nft .num{background:rgba(255,255,255,.8);color:#10131b}
html.light .sheet{background:linear-gradient(168deg,#fbfcff,#e9eef8);color:#10131b;border-color:rgba(15,23,42,.12)}
html.light .nav{background:rgba(255,255,255,.78);border-color:rgba(15,23,42,.1);box-shadow:0 18px 50px rgba(30,45,80,.18),inset 0 1px 0 rgba(255,255,255,.9)}
html.light .nav button{color:#7a8190}
html.light .nav button.on{color:#10131b;background:linear-gradient(160deg,rgba(10,132,255,.18),rgba(255,255,255,.9));box-shadow:inset 0 0 0 1px rgba(10,132,255,.25)}
html.light input,html.light select,html.light .betrow input{background:rgba(255,255,255,.8);color:#10131b;border-color:rgba(15,23,42,.14)}
html.light .toast{background:#fff;color:#10131b;border-color:rgba(10,132,255,.28);box-shadow:0 12px 30px rgba(30,45,80,.18)}
html.light .modal{background:rgba(210,219,234,.62)}
html.light .pick{background:rgba(255,255,255,.55)}
html.light .pick img,html.light .fullimg{background:#e6ebf5}
html.light .chip{color:#394052;background:rgba(15,23,42,.05);border-color:rgba(15,23,42,.1)}
html.light .case{background:linear-gradient(160deg,rgba(255,255,255,.82),rgba(255,255,255,.5))}
html.light .tag{background:rgba(255,255,255,.7);color:#10131b}
html.light .dial .core{background:radial-gradient(circle at 50% 32%,#fbfdff,#dfe6f2 78%);box-shadow:inset 0 0 0 1px rgba(15,23,42,.08),0 0 40px rgba(10,132,255,.18)}
html.light .arena-core{background:radial-gradient(circle at 50% 32%,#fbfdff,#e2e8f4 78%);box-shadow:inset 0 0 0 1px rgba(15,23,42,.08),inset 0 0 40px rgba(255,255,255,.8),0 18px 46px rgba(30,45,80,.16)}
html.light .arena-core small{color:#6b7280}
html.light .arena .lbl{fill:#10131b}
html.light .beam{background:linear-gradient(to top,rgba(10,132,255,0),rgba(10,132,255,.55))}
html.light .ticker,html.light .upg-ticker{background:linear-gradient(90deg,rgba(255,255,255,.2),rgba(255,255,255,.72),rgba(255,255,255,.2))}
html.light .ticker-track span{color:#4b5565}
html.light .themePick{background:rgba(255,255,255,.5)}

body{background:var(--bg,#040405)}
body:before{filter:blur(10px)}
body:after{opacity:.35}
.glass{background:var(--glass);border-color:var(--stroke);backdrop-filter:blur(28px) saturate(1.55);-webkit-backdrop-filter:blur(28px) saturate(1.55);
  box-shadow:0 22px 60px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.09),inset 0 -1px 0 rgba(0,0,0,.22)}
.glass:after{content:"";position:absolute;left:12%;right:12%;top:0;height:1px;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.45),transparent);opacity:.7}
@supports (padding:max(0px)){body{padding-left:max(12px,env(safe-area-inset-left));padding-right:max(12px,env(safe-area-inset-right))}}

/* бегущая строка */
.ticker,.upg-ticker{position:relative;overflow:hidden;margin:0 2px 12px;border-radius:15px;padding:8px 0;
  border:1px solid var(--stroke);background:linear-gradient(90deg,rgba(255,255,255,.03),rgba(255,255,255,.09),rgba(255,255,255,.03));
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 7%,#000 93%,transparent);
  mask-image:linear-gradient(90deg,transparent,#000 7%,#000 93%,transparent)}
.upg-ticker{margin:0 0 10px}
.ticker-track{display:flex;width:max-content;animation:marquee 32s linear infinite;will-change:transform}
.ticker-track span{display:block;white-space:nowrap;padding-right:38px;font:800 10px/1.25 inherit;
  letter-spacing:.16em;text-transform:uppercase;color:var(--t2)}
@keyframes marquee{to{transform:translateX(-50%)}}

/* апгрейдер 2.0 */
.upg-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:4px}
.upg-kicker{display:flex;align-items:center;gap:7px;font-size:9px;font-weight:900;letter-spacing:.2em;
  color:var(--a1);text-transform:uppercase}
.upg-kicker .live{width:7px;height:7px;border-radius:50%;background:var(--a1);
  box-shadow:0 0 0 0 color-mix(in srgb,var(--a1) 60%,transparent);animation:live 1.8s infinite}
@keyframes live{70%{box-shadow:0 0 0 8px transparent}100%{box-shadow:0 0 0 0 transparent}}
.upg-title{font-size:23px;font-weight:900;letter-spacing:-.6px;margin-top:2px}
.upg-sub{font-size:10.5px;color:var(--t3);margin-top:3px}
.upg-card{overflow:hidden}
.upg-card:before{content:"";position:absolute;inset:-40% 26% auto;height:70%;pointer-events:none;
  background:radial-gradient(circle,color-mix(in srgb,var(--a1) 22%,transparent),transparent 70%);filter:blur(30px)}
.dial{width:min(84vw,330px);margin-top:10px}
.dial-aura{position:absolute;inset:-12%;border-radius:50%;pointer-events:none;
  background:radial-gradient(circle,color-mix(in srgb,var(--a1) 28%,transparent),transparent 62%);
  filter:blur(18px);animation:aura 4.5s ease-in-out infinite}
@keyframes aura{50%{transform:scale(1.06);opacity:.8}}
.dial:after{content:"";position:absolute;inset:-2.5%;border-radius:50%;pointer-events:none;
  border:1px dashed color-mix(in srgb,var(--a1) 55%,transparent);opacity:.55;animation:ringSpin 22s linear infinite}
.dial.spinning:after{animation-duration:2.2s}
@keyframes ringSpin{to{transform:rotate(360deg)}}
.dial .spark{position:absolute;width:4px;height:4px;border-radius:50%;background:var(--a3);
  box-shadow:0 0 12px var(--a1);opacity:.8;animation:floaty 5s ease-in-out infinite}
.dial .s1{left:8%;top:18%}.dial .s2{right:10%;top:26%;animation-delay:-1.2s}
.dial .s3{left:18%;bottom:12%;animation-delay:-2.4s}.dial .s4{right:16%;bottom:18%;animation-delay:-3.1s}
@keyframes floaty{50%{transform:translateY(-9px) scale(1.3);opacity:.35}}
.dial .core{box-shadow:inset 0 0 0 1px rgba(255,255,255,.12),0 0 40px color-mix(in srgb,var(--a1) 35%,transparent),0 0 90px rgba(0,0,0,.8)}
.dial .beam{background:linear-gradient(to top,rgba(255,255,255,0),var(--a3));
  box-shadow:0 0 18px color-mix(in srgb,var(--a1) 70%,transparent)}
.chance-line{display:flex;align-items:center;gap:12px;margin:2px 2px 0;padding:10px 12px;border-radius:16px;
  border:1px solid var(--stroke);background:rgba(255,255,255,.035)}
.chance-line b{display:block;font-size:19px;font-weight:900;letter-spacing:-.6px;line-height:1;color:var(--a3)}
.chance-line span{display:block;font-size:8.5px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;
  color:var(--t3);margin-top:3px}
.chancebar{flex:1;height:8px;border-radius:99px;background:rgba(0,0,0,.45);overflow:hidden;border:1px solid var(--stroke)}
.chancebar i{display:block;height:100%;width:0;border-radius:inherit;transition:width .35s cubic-bezier(.2,.8,.2,1);
  background:linear-gradient(90deg,var(--a2),var(--a1),var(--a3));
  box-shadow:0 0 14px color-mix(in srgb,var(--a1) 60%,transparent)}
.betrow .mini.on{background:linear-gradient(150deg,var(--a1),var(--a2));border-color:transparent;color:#fff}
.betpresets{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:7px}
.betpresets .mini{width:100%}
.go{position:relative;overflow:hidden;letter-spacing:.02em}
.go:after{content:"";position:absolute;top:0;bottom:0;width:45%;left:-60%;transform:skewX(-18deg);pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);animation:shine 3.2s infinite}
@keyframes shine{0%,55%{left:-60%}85%,100%{left:130%}}
.go:disabled:after{display:none}

/* карточки и темы */
.nft{box-shadow:0 10px 30px rgba(0,0,0,.35);background:linear-gradient(180deg,rgba(15,17,24,.9),rgba(5,6,9,.92))}
.nft .im{aspect-ratio:1300/680}
.pick img{aspect-ratio:1300/680}
.nft .im img{transition:transform .6s cubic-bezier(.2,.8,.2,1)}
.nft:active .im img{transform:scale(1.04)}
.nft .nm{font-size:11.5px}
.themes{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.th{width:auto;height:62px;border-radius:16px;overflow:hidden;position:relative}
.th i{position:absolute;top:6px;right:7px;inset:auto;width:16px;height:16px;border-radius:50%;
  background:rgba(0,0,0,.4);display:grid;place-items:center;font-size:10px;color:#fff}
.th span{position:absolute;left:6px;right:6px;bottom:5px;font-size:8px;font-weight:800;text-align:center;
  color:#fff;text-shadow:0 1px 3px #000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.arena-add{display:flex;gap:8px;margin-top:8px}
.arena-add input{flex:1;min-width:0;padding:12px 13px;border-radius:14px;border:1px solid var(--stroke2);
  background:rgba(0,0,0,.45);color:#fff;font:800 14px inherit;outline:none;appearance:none}
.arena-add input:focus{border-color:rgba(124,92,255,.75);box-shadow:0 0 0 3px rgba(124,92,255,.16)}

@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-home" viewBox="0 0 24 24"><path d="m3 10.5 9-7 9 7V20a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></symbol>
<symbol id="i-gift" viewBox="0 0 24 24"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8M12 8v13"/><path d="M12 8S10.5 3 8 3a2.5 2.5 0 0 0 0 5m4 0c2 0 4-5 6.5-5a2.5 2.5 0 0 1 0 5z"/></symbol>
<symbol id="i-cards" viewBox="0 0 24 24"><rect x="3" y="6" width="12" height="15" rx="2"/><path d="M7 3h10a2 2 0 0 1 2 2v11"/><path d="M6 11h6M6 15h6"/></symbol>
<symbol id="i-swap" viewBox="0 0 24 24"><circle cx="8" cy="8" r="3.2"/><circle cx="16" cy="16" r="3.2"/><path d="M11.5 11.5 6 17M12.5 12.5 18 7" opacity=".5"/></symbol>
<symbol id="i-user" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></symbol>
<symbol id="i-coin" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v9M9.8 9.6h4.4M9.8 14.4h4.4"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 3.2 14.5 9l6.3.5-4.8 4.1 1.5 6.2-5.5-3.4-5.5 3.4 1.5-6.2L3.2 9.5 9.5 9z"/></symbol>
<symbol id="i-spark" viewBox="0 0 24 24"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></symbol>
<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h13M13 7l5 5-5 5"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
<symbol id="i-down" viewBox="0 0 24 24"><path d="M12 4v13M6.5 11.5 12 17l5.5-5.5M5 20h14"/></symbol>
<symbol id="i-share" viewBox="0 0 24 24"><path d="M12 15V3M8 7l4-4 4 4"/><path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></symbol>
<symbol id="i-drop" viewBox="0 0 24 24"><path d="M12 4v11M7 10l5 5 5-5M4 20h16"/></symbol>
<symbol id="i-lock" viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2.4"/><path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10"/></symbol>
<symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 2.5 5 13h6l-1 8.5L19 11h-6z"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 3 5 6v6c0 4.2 3 7.4 7 9 4-1.6 7-4.8 7-9V6z"/></symbol>
<symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.6"/></symbol>
<symbol id="i-life" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.4"/><path d="M12 3v5.6M12 15.4V21M3 12h5.6M15.4 12H21"/></symbol>
<symbol id="i-crown" viewBox="0 0 24 24"><path d="M3 8.5 6.5 17h11L21 8.5l-5 3.2L12 5l-4 6.7z"/></symbol>
<symbol id="i-tree" viewBox="0 0 24 24"><path d="M12 3 6 11h3l-3 5h12l-3-5h3zM12 16v5"/></symbol>
<symbol id="i-penguin" viewBox="0 0 24 24"><ellipse cx="12" cy="13" rx="6.4" ry="8"/><ellipse cx="12" cy="14.6" rx="3.5" ry="5.2" opacity=".45"/><path d="M10.6 8.6v.2M13.4 8.6v.2M11.2 11.2h1.6M10 22l1-2.5M14 22l-1-2.5"/></symbol>
<symbol id="i-capy" viewBox="0 0 24 24"><path d="M4 20v-5.5A6.5 6.5 0 0 1 15.6 9.4l2.6 2a2 2 0 0 1-1.4 3.6H11"/><path d="M9.2 10.2v.2M7.4 3.6 8.8 6"/></symbol>
<symbol id="i-palm" viewBox="0 0 24 24"><path d="M11 21c0-6 1-10 4-13"/><path d="M15 8c2-2 4.5-2 5.5-.5M15 8c-1-2.6-3.4-3.6-5-2.6M15 8c.6-2.6-.6-4.6-2.4-4.8M15 8c2.6-.8 3.6-3 2.6-4.4"/><path d="M4 21h13"/></symbol>
<symbol id="i-planet" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5.6"/><ellipse cx="12" cy="12" rx="10" ry="3.6" transform="rotate(-22 12 12)"/></symbol>
<symbol id="i-neon" viewBox="0 0 24 24"><rect x="3.5" y="6" width="17" height="12" rx="3"/><path d="M7.5 12h2l1.5-3 2 6 1.5-3h2"/></symbol>
<symbol id="i-cup" viewBox="0 0 24 24"><path d="M5 8h9v7a4.5 4.5 0 0 1-9 0z"/><path d="M14 9.5h2.5a2.5 2.5 0 0 1 0 5H14"/><path d="M6 21h9"/></symbol>
<symbol id="i-cat" viewBox="0 0 24 24"><path d="M5 9 4 4l4 2.5M19 9l1-5-4 2.5"/><path d="M4.5 11a7.5 7.5 0 0 1 15 0v3.5a4 4 0 0 1-4 4h-7a4 4 0 0 1-4-4z"/><path d="M9 12v.2M15 12v.2M12 15v.2"/></symbol>
<symbol id="i-snow" viewBox="0 0 24 24"><path d="M12 3v18M4.2 7.5l15.6 9M19.8 7.5 4.2 16.5"/><path d="M9.4 4.6 12 6.4l2.6-1.8M9.4 19.4 12 17.6l2.6 1.8"/></symbol>
<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 7H4c0-1 2-2 2-7z"/><path d="M10 20a2 2 0 0 0 4 0"/></symbol>
<symbol id="i-mine" viewBox="0 0 24 24"><path d="M4 20 14 10"/><path d="M12 12c2.5-4 6-6 9-6-1 3-3 6.5-7 9z"/></symbol>
<symbol id="i-server" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.2M7 16.5h.2"/></symbol>
<symbol id="i-support" viewBox="0 0 24 24"><path d="M4 13a8 8 0 0 1 16 0"/><rect x="2.5" y="13" width="4" height="6" rx="2"/><rect x="17.5" y="13" width="4" height="6" rx="2"/><path d="M20 19a4 4 0 0 1-4 3h-2"/></symbol>
<symbol id="i-gear" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5 7.4 7.4M16.6 16.6l1.9 1.9M18.5 5.5l-1.9 1.9M7.4 16.6l-1.9 1.9"/></symbol>
<symbol id="i-trophy" viewBox="0 0 24 24"><path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 5.5H5.5A2.5 2.5 0 0 0 8 10.5M16 5.5h2.5A2.5 2.5 0 0 1 16 10.5"/><path d="M12 13v4M8.5 21h7"/></symbol>
<symbol id="i-image" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8.5" cy="9.5" r="1.6"/><path d="m4 18 5-5 3.5 3.5L16 13l4 4"/></symbol>
<symbol id="i-medal" viewBox="0 0 24 24"><circle cx="12" cy="15" r="5.5"/><path d="M8.5 10 6 3h4l2 5 2-5h4l-2.5 7"/></symbol>
<symbol id="i-diamond" viewBox="0 0 24 24"><path d="M12 3 21 9.5 12 21 3 9.5z"/><path d="M3 9.5h18M12 3v18" opacity=".35"/></symbol>
<symbol id="i-head" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M12 2 4 9.5l8 12.5 8-12.5z"/></symbol>
</defs></svg>

<main class="wrap">
  <header class="top">
    <div class="ava" id="avaBox">?</div>
    <div class="who"><b id="hName">Игрок</b><small id="hRank"><svg class="i xs"><use href="#i-medal"/></svg><span>Новичок</span></small></div>
    <div class="balpill"><svg class="i sm"><use href="#i-coin"/></svg><span id="topBal">—</span></div>
  </header>

  <div class="ticker glass" id="tickerBar"><div class="ticker-track" id="tickerTrack"></div></div>

  <section id="home" class="page active">
    <div class="glass hi hero">
      <div class="lbl">Баланс</div>
      <div class="amt"><b id="heroBal">—</b><span>RCOIN</span></div>
      <div class="acts">
        <button class="act" onclick="go('cases')"><svg class="i"><use href="#i-gift"/></svg>Кейсы</button>
        <button class="act" onclick="go('nft')"><svg class="i"><use href="#i-cards"/></svg>NFT</button>
        <button class="act" onclick="go('arena')"><svg class="i"><use href="#i-trophy"/></svg>Арена</button>
        <button class="act" onclick="go('mining')"><svg class="i"><use href="#i-mine"/></svg>Майнинг</button>
      </div>
    </div>
    <div class="stats">
      <div class="glass st"><span>Сыграно</span><b id="stGames">—</b></div>
      <div class="glass st"><span>Победы</span><b id="stWins">—</b></div>
      <div class="glass st"><span>Рейтинг</span><b id="stRank">—</b></div>
      <div class="glass st"><span>Проиграно</span><b id="stLost">—</b></div>
    </div>
    <div class="glass pad" style="margin-top:10px">
      <div class="h"><h2>Как это работает</h2><span class="chip a">3 шага</span></div>
      <p class="sub">Открой кейс — придёт модель с личным номером.</p>
      <p class="sub" style="margin-top:5px">Улучши её — откроются фон, уникальная картинка и одна из двух редкостей.</p>
      <p class="sub" style="margin-top:5px">Ставь NFT в апгрейдере или отправляй в архив.</p>
    </div>
  </section>

  <section id="cases" class="page">
    <div class="glass pad">
      <div class="h"><h2>Кейсы</h2><span class="chip" id="caseCount">0</span></div>
      <p class="sub" style="margin-bottom:11px">В каждом — модель с номером. Фон и редкость открываются после улучшения.</p>
      <div class="cases" id="caseGrid"><div class="empty">Загрузка…</div></div>
    </div>
  </section>

  <section id="nft" class="page">
    <div class="glass pad">
      <div class="h"><h2>Коллекция</h2><span class="chip" id="nftCount">0</span></div>
      <div class="rowz" style="margin-bottom:11px">
        <button class="btn green" onclick="mintNft()"><svg class="i sm"><use href="#i-spark"/></svg>Создать · 10 000</button>
        <button class="btn ghost hide" id="adminCreateBtn" onclick="openAdminCreate()"><svg class="i sm"><use href="#i-plus"/></svg>Кастом</button>
      </div>
      <div class="grid" id="nftGrid"><div class="empty" style="grid-column:1/-1">Загрузка…</div></div>
    </div>
  </section>

  <section id="mining" class="page">
    <div class="glass hi pad" style="text-align:center">
      <span class="chip a">RUBIN MINING</span>
      <div class="amt" style="position:static;justify-content:center;margin:8px 0 2px"><b id="minePending" style="font-size:clamp(26px,8vw,34px);font-weight:900;letter-spacing:-1.2px">0</b><span style="font-size:11px;color:#a6aecb;font-weight:800">RCOIN</span></div>
      <div class="sub" id="mineRate">0 RCOIN/сутки</div>
      <div class="fan"><svg class="i xl"><use href="#i-mine"/></svg></div>
      <div class="sub" id="mineEta">—</div>
      <div class="rowz" style="margin-top:13px">
        <button class="btn green" onclick="mineCollect()"><svg class="i sm"><use href="#i-drop"/></svg>Снять</button>
        <button class="btn ghost" onclick="mineScroll()"><svg class="i sm"><use href="#i-server"/></svg>Серверы</button>
      </div>
    </div>
    <div class="glass pad" style="margin-top:10px" id="mineServersBox">
      <div class="h"><h2>Серверы</h2><span class="chip" id="mineServers">0</span></div>
      <div id="mineShop"><div class="empty">Загрузка…</div></div>
    </div>
  </section>

  <section id="upgrade" class="page">
    <div class="glass pad upg-card">
      <div class="upg-head">
        <div>
          <div class="upg-kicker"><span class="live"></span> APGRADER 2.0</div>
          <h2 class="upg-title">Апгрейдер</h2>
          <div class="upg-sub">Чёрная коллекция · честный шанс · комиссия в пул</div>
        </div>
        <span class="chip a" id="modeChip">NFT → NFT</span>
      </div>
      <div class="dial" id="dialBox">
        <div class="dial-aura"></div>
        <svg class="base" viewBox="0 0 240 240">
          <defs>
            <linearGradient id="gw" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--a3)"/><stop offset="1" style="stop-color:var(--a1)"/></linearGradient>
            <radialGradient id="gglow" cx="50%" cy="50%" r="50%"><stop offset="0" style="stop-color:var(--a1)" stop-opacity=".4"/><stop offset="1" style="stop-color:var(--a1)" stop-opacity="0"/></radialGradient>
          </defs>
          <circle cx="120" cy="120" r="104" fill="none" stroke="rgba(255,255,255,.055)" stroke-width="26"/>
          <circle cx="120" cy="120" r="117" fill="none" stroke="rgba(255,255,255,.06)"/>
          <g id="zoneWrap"></g>
          <circle cx="120" cy="120" r="88" fill="url(#gglow)"/>
          <circle cx="120" cy="120" r="104" fill="none" stroke="rgba(255,255,255,.14)" stroke-width="1"/>
          <circle cx="120" cy="120" r="78" fill="none" stroke="rgba(255,255,255,.1)" stroke-width="1"/>
        </svg>
        <div class="beam zero" id="beam"></div>
        <div class="core" id="dialCore"><div class="ph"><svg class="i lg"><use href="#i-plus"/></svg><small>выбери NFT</small></div></div>
        <div class="arrow"><svg viewBox="0 0 24 24"><path d="M12 2 4 9.5l8 12.5 8-12.5z"/></svg></div>
        <span class="spark s1"></span><span class="spark s2"></span><span class="spark s3"></span><span class="spark s4"></span>
      </div>
      <div class="chance-line">
        <div style="min-width:76px"><b id="chancePct">0%</b><span>шанс выигрыша</span></div>
        <div class="chancebar"><i id="chanceBar"></i></div>
      </div>
      <div class="slotrow">
        <div class="slot" id="slotFrom" onclick="ePicker('mine')">
          <div class="sid"><svg class="i sm"><use href="#i-plus"/></svg></div>
          <div class="tx"><small>Что улучшаем</small><b>Выбрать NFT</b></div>
        </div>
        <div class="toarrow"><svg class="i sm"><use href="#i-arrow"/></svg></div>
        <div class="slot" id="slotTo" onclick="ePicker('target')">
          <div class="sid"><svg class="i sm"><use href="#i-crown"/></svg></div>
          <div class="tx"><small>Цель</small><b>Любой предмет</b></div>
        </div>
      </div>
      <div class="modebar">
        <button class="mode on" id="modeNft" onclick="eMode('nft',event)"><svg class="i sm"><use href="#i-cards"/></svg>NFT → NFT</button>
        <button class="mode" id="modeCoins" onclick="eMode('coins',event)"><svg class="i sm"><use href="#i-coin"/></svg>NFT → RCOIN</button>
      </div>
      <div class="betrow">
        <input id="betInput" aria-label="Сумма ставки в RCOIN" type="number" min="0" step="1000" value="0" inputmode="numeric" placeholder="0" oninput="eBet()">
        <button class="mini" onclick="eBet(0)">0</button>
        <button class="mini" onclick="eBet(10000)">10к</button>
      </div>
      <div class="betpresets">
        <button class="mini" onclick="eBet(100000)">100к</button>
        <button class="mini" onclick="eBet(1000000)">1кк</button>
        <button class="mini" onclick="eBet(10000000)">10кк</button>
        <button class="mini" onclick="eBet(100000000)">100кк</button>
      </div>
      <div class="sumline" id="sumLine">Выберите NFT и введите сумму, чтобы открыть полосу выигрыша</div>
      <button class="go" id="upgBtn" disabled onclick="eSpin()">
        <svg class="i sm"><use href="#i-bolt"/></svg><span id="upgText">Улучшить</span>
      </button>
      <p class="tiny" style="text-align:center;margin-top:9px">RCOIN списываются в момент прокрутки. При ошибке деньги возвращаются.</p>
    </div>
    <div class="stats">
      <div class="glass st"><span>Пул выплат</span><b id="pool">0</b></div>
      <div class="glass st"><span>NFT в архиве</span><b id="archCount">0</b></div>
    </div>
    <div class="glass pad" style="margin-top:10px">
      <div class="h"><h2>Лоты архива</h2><span class="chip g">можно выиграть</span></div>
      <div class="pickgrid" id="lots"><div class="empty">Загрузка…</div></div>
    </div>
  </section>

  <section id="arena" class="page">
    <div class="glass pad">
      <div class="h"><h2>Арена</h2><div style="display:flex;gap:6px;align-items:center">
        <span class="chip g" id="arenaBonusChip">+0</span>
        <span class="chip ok" id="onlineChip"><svg class="i xs fill"><use href="#i-life"/></svg>0/2</span></div></div>
      <div class="arena">
        <svg viewBox="0 0 400 400">
          <circle cx="200" cy="200" r="150" fill="none" stroke="rgba(255,255,255,.05)" stroke-width="46"/>
          <g id="zoneRing"></g>
          <circle cx="200" cy="200" r="128" fill="none" stroke="rgba(255,255,255,.1)"/>
          <circle cx="200" cy="200" r="172" fill="none" stroke="rgba(255,255,255,.1)"/>
          <g id="ballG"><circle id="arenaBallGlow" cx="200" cy="50" r="20" fill="#fff" opacity=".16"/><circle id="arenaBall" cx="200" cy="50" r="11" fill="#fff" stroke="rgba(0,0,0,.35)" stroke-width="2"/></g>
        </svg>
        <div class="arena-core"><div><b id="arenaBank">0</b><small>БАНК RCOIN</small><div class="cd" id="arenaState">—</div></div></div>
      </div>
      <div class="plist" id="apList"><div class="waiting"><svg class="i lg"><use href="#i-user"/></svg>Ждём игроков</div></div>
      <p class="tiny" id="apHint" style="margin-top:9px;text-align:center">Ставка в пул, ширина твоей зоны на кольце = сила. После второго игрока идут 15 секунд — и шарик идёт по кольцу.</p>
      <div class="betrow">
        <input id="arenaBetInput" aria-label="Ставка на арене в RCOIN" type="number" min="1" step="1000" value="10000" inputmode="numeric">
        <button class="mini" data-b="10000" onclick="abPreset(10000,this)">10к</button>
        <button class="mini" data-b="100000" onclick="abPreset(100000,this)">100к</button>
        <button class="mini" data-b="1000000" onclick="abPreset(1000000,this)">1кк</button>
      </div>
      <div class="arena-add hide" id="arenaAddRow">
        <input id="arenaAddInput" aria-label="Добавить в банк арены" type="number" min="1" step="1000" value="10000" inputmode="numeric">
        <button class="mini" onclick="arenaAdd()">+ В банк</button>
      </div>
      <div class="rowz" style="margin-top:9px">
        <button class="btn" id="arenaJoinBtn" onclick="arenaJoin()"><svg class="i sm"><use href="#i-plus"/></svg>Войти</button>
        <button class="btn ghost hide" id="arenaLeaveBtn" onclick="arenaLeave()"><svg class="i sm"><use href="#i-x"/></svg>Выйти</button>
      </div>
    </div>
    <div class="glass pad" style="margin-top:10px">
      <div class="h"><h2>История</h2><span class="chip">последние</span></div>
      <div id="arenaHist" class="tiny">Пока нет завершённых раундов</div>
    </div>
  </section>

  <section id="profile" class="page">
    <div class="glass hi pad">
      <div style="display:flex;gap:12px;align-items:center">
        <div class="ava" id="pAva" style="width:60px;height:60px;border-radius:19px;font-size:21px">?</div>
        <div style="flex:1;min-width:0"><h2 id="pName" style="font-size:17px;font-weight:900">Игрок</h2><div class="sub" id="pRank">Новичок</div></div>
      </div>
      <div class="stats">
        <div class="glass st"><span>Баланс</span><b id="pBal">0</b></div>
        <div class="glass st"><span>RBP</span><b id="pRbp">0</b></div>
      </div>
      <a class="btn ghost" style="margin-top:10px" href="https://t.me/RubinHelpSBbot" target="_blank" rel="noopener"><svg class="i sm"><use href="#i-support"/></svg>Поддержка @RubinHelpSBbot</a>
    </div>
    <div class="glass pad" style="margin-top:10px">
      <div class="h"><h2>Тема и обои</h2><span class="chip a">свои</span></div>
      <div class="themes" id="themeRow"></div>
      <div class="uprow">
        <label class="btn ghost sm" style="margin:0;cursor:pointer;flex:1"><svg class="i sm"><use href="#i-image"/></svg>Свои обои
          <input id="wallFile" type="file" accept="image/*" style="display:none" onchange="wallUpload(this)"></label>
        <button class="btn ghost sm" style="flex:1;margin:0" onclick="wallReset()"><svg class="i sm"><use href="#i-x"/></svg>Сбросить</button>
      </div>
      <p class="tiny" style="margin-top:8px">Обои хранятся только на этом устройстве.</p>
    </div>
    <div class="glass pad hide" style="margin-top:10px" id="adminPanel">
      <div class="h"><h2>Админ-панель</h2><span class="chip g">WEB</span></div>
      <label>Бегущая строка для всех</label>
      <input id="admTicker" type="text" maxlength="180" placeholder="RUBIN · NEW BLACK COLLECTION ·">
      <button class="btn" style="margin-top:8px" onclick="adminSaveTicker()">Сохранить тикер</button>
      <div class="rowz" style="margin-top:8px">
        <button class="btn ghost" onclick="adminRedrawNfts()">Перерисовать NFT</button>
      </div>
      <button class="btn red" style="margin-top:8px" onclick="adminResetAsk()">Новая коллекция NFT</button>
      <p class="tiny" style="margin-top:6px">Удалит старые NFT и начнёт нумерацию с #1. Только для владельца.</p>
      <label>Бонус в арену, RCOIN</label>
      <div class="betrow"><input id="admArenaBonus" type="number" min="0" step="1000" value="1000000" inputmode="numeric">
        <button class="mini" onclick="adminArenaBonus()">В банк</button></div>
      <p class="tiny" id="admStatus" style="margin-top:8px"></p>
    </div>
    <div class="glass pad" style="margin-top:10px">
      <div class="h"><h2>Правила</h2><span class="chip">честно</span></div>
      <p class="sub">Модель с номером — без редкости. Улучшение открывает уникальную картинку и одну из двух редкостей, а админ может выдать редкость или кастомный NFT сразу. RCOIN — игровая валюта без реальной стоимости.</p>
    </div>
  </section>
</main>

<nav class="nav">
  <button class="on" data-page="home" onclick="go('home')"><svg class="i"><use href="#i-home"/></svg>Главная</button>
  <button data-page="cases" onclick="go('cases')"><svg class="i"><use href="#i-gift"/></svg>Кейсы</button>
  <button data-page="nft" onclick="go('nft')"><svg class="i"><use href="#i-cards"/></svg>NFT</button>
  <button data-page="upgrade" onclick="go('upgrade')"><svg class="i"><use href="#i-swap"/></svg>Апгрейд</button>
  <button data-page="mining" onclick="go('mining')"><svg class="i"><use href="#i-mine"/></svg>Майнинг</button>
  <button data-page="profile" onclick="go('profile')"><svg class="i"><use href="#i-user"/></svg>Я</button>
</nav>

<div class="toast" id="toast"></div>
<div class="modal" id="modal" onclick="if(event.target===this)closeModal()"><div class="sheet" id="sheet"></div></div>

<script>
/* ============ база ============ */
var tg = window.Telegram && window.Telegram.WebApp;
if (tg) { try { tg.ready(); tg.expand(); tg.setHeaderColor('#050609'); tg.setBackgroundColor('#050609'); } catch(e){} }
var INIT = tg ? tg.initData : '';
var TU = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
var $ = function(id){ return document.getElementById(id); };
var fmt = function(n){ return Math.floor(Number(n)||0).toLocaleString('ru-RU').replace(/,/g,' '); };
var num = function(v){ return Math.max(0, Math.floor(Number(v)||0)); };
var safe = function(s){ return String(s==null?'':s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
var icon = function(n, cls){ return '<svg class="i '+(cls||'')+'"><use href="#i-'+n+'"/></svg>'; };
var ME=null, CASES=[], NFTS=[], AR=null, SERVER_THEME='obsidian';
var mineTimer=null, mineBase=0, mineRate=0, mineTs=0;

function xhr(path, body, cb){
  var done = false;
  function fin(res){ if(done) return; done = true; cb(res); }
  var payload = JSON.stringify(Object.assign({init:INIT, photo_url:TU.photo_url||''}, body||{}));
  if (window.fetch) {
    fetch('/api/'+path, {method:'POST', headers:{'Content-Type':'application/json'}, body:payload})
      .then(function(r){ return r.text().then(function(t){ var j; try { j = JSON.parse(t); } catch(e) { j = {ok:false, err:'Ошибка сервера ('+r.status+')'}; } fin(j); }); })
      .catch(function(){ fin({ok:false, err:'Нет соединения с сервером'}); });
    return;
  }
  // запасной путь, если XHR из fetch недоступен в старом WebView
  var x = new XMLHttpRequest();
  x.open('POST', '/api/'+path); x.setRequestHeader('Content-Type','application/json');
  x.onload = function(){ var j; try { j = JSON.parse(x.responseText); } catch(e) { j = {ok:false, err:'Ошибка сервера ('+x.status+')'}; } fin(j); };
  x.onerror = function(){ fin({ok:false, err:'Нет соединения с сервером'}); };
  x.send(payload);
}
function api(path, body){ return new Promise(function(res){ xhr(path, body, res); }); }
function toast(t){ var e=$('toast'); e.textContent=t; e.classList.add('show'); clearTimeout(toast.t); toast.t=setTimeout(function(){ e.classList.remove('show'); },2600); }
function haptic(){ try { tg.HapticFeedback.impactOccurred('light'); } catch(e){} }
function setBal(v){ if(v==null) return; var s=fmt(v); $('topBal').textContent=s; $('heroBal').textContent=s; $('pBal').textContent=s; if(ME) ME.balance=v; }
function setTicker(t){
  var text = String(t||'').trim() || 'RUBIN · NEW BLACK COLLECTION · АПГРЕЙДЕР 2.0 · ';
  var chunk = safe(text) + ' · ' + safe(text) + ' · ' + safe(text);
  ['tickerTrack','upgTickerTrack'].forEach(function(id){
    var e = $(id); if(e) e.innerHTML = '<span>'+chunk+'</span><span>'+chunk+'</span>';
  });
}
function go(p){
  Array.prototype.forEach.call(document.querySelectorAll('.page'), function(e){ e.classList.toggle('active', e.id===p); });
  Array.prototype.forEach.call(document.querySelectorAll('.nav button'), function(e){ e.classList.toggle('on', e.dataset.page===p); });
  window.scrollTo({top:0,behavior:'smooth'});
  if(p==='cases') loadCases();
  if(p==='nft') loadNfts();
  if(p==='mining') loadMining(); else stopMining();
  if(p==='upgrade'){ if(!NFTS.length) loadNfts(); loadArchive(); }
  if(p==='arena') arenaStart();
}
function boot(){
  api('me').then(function(j){
    if(!j.ok){ toast(j.err||'Открой приложение через бота'); return; }
    ME = j; setBal(j.balance);
    if(j.theme) SERVER_THEME = j.theme;
    setTicker(j.ticker);
    applyTheme();
    var nm = j.name || 'Игрок';
    $('hName').textContent = nm; $('pName').textContent = nm;
    $('pRank').textContent = j.rank || 'Новичок';
    $('stGames').textContent = fmt(j.games); $('stWins').textContent = fmt(j.wins);
    $('stRank').textContent = j.rank || '—'; $('stLost').textContent = fmt(j.lost);
    $('pRbp').textContent = fmt(j.rbp);
    var src = j.nft_profile_url || j.photo_url || '';
    ['avaBox','pAva'].forEach(function(id){ var el=$(id);
      if(src){ el.innerHTML='<img src="'+safe(src)+'" alt="">'; } else el.textContent=(nm||'?').slice(0,1).toUpperCase(); });
    if(j.is_admin){ var b=$('adminCreateBtn'); if(b) b.classList.remove('hide');
      var ap=$('adminPanel'); if(ap) ap.classList.remove('hide');
      var at=$('admTicker'); if(at) at.value=j.ticker||''; }
    loadCases();
  });
}

/* ============ кейсы ============ */
var CASE_ICON = {ny:'tree', gta:'palm', capy:'capy', penguin:'penguin', space:'planet',
  gold:'crown', cyber:'neon', cozy:'cup', meme:'cat', premium:'diamond', winter:'snow'};
function caseIcon(key, cls){ return icon(CASE_ICON[key]||'gift', cls||'lg'); }
function loadCases(){
  if(CASES.length) return renderCases();
  api('cases_state').then(function(j){
    if(!j.ok) return;
    CASES = j.cases||[]; if(j.balance!=null) setBal(j.balance); renderCases();
  });
}
function renderCases(){
  $('caseCount').textContent = CASES.length;
  var g=$('caseGrid');
  if(!CASES.length){ g.innerHTML='<div class="empty">Нет кейсов</div>'; return; }
  g.innerHTML = CASES.map(function(c){
    return '<div class="case" style="--c:'+safe(c.accent||'#7c5cff')+'">'
      +'<span class="tag">'+safe(c.tag)+'</span>'
      +'<div class="art">'+caseIcon(c.key)+'</div>'
      +'<b>'+safe(c.name)+'</b>'
      +'<div class="pr">'+icon('coin','xs')+fmt(c.price)+' RCOIN</div>'
      +'<button class="op" onclick="openCase(\''+safe(c.key)+'\')">Открыть</button></div>';
  }).join('');
}
function openCase(key){
  var c = CASES.filter(function(x){ return x.key===key; })[0]; if(!c) return;
  showSheet('<div style="text-align:center;padding:14px"><div style="display:grid;place-items:center;color:#c9d3ff">'+caseIcon(c.key,'xl')+'</div>'
    +'<h3 style="margin-top:10px">'+safe(c.name)+'</h3><p class="sub" style="margin-top:5px">Открываем…</p></div>');
  api('case_open', {key:key}).then(function(j){
    if(!j.ok){ closeModal(); return toast(j.err||'Не удалось'); }
    if(j.balance!=null) setBal(j.balance);
    haptic(); confetti(70);
    showSheet('<div style="text-align:center"><span class="chip a">'+safe(j.case)+'</span>'
      +'<img class="fullimg" src="'+safe(j.url)+'" alt="" style="margin:10px 0">'
      +'<h3>'+safe(j.name)+' <span class="chip">#'+j.id+'</span></h3>'
      +'<p class="sub" style="margin-top:5px">Модель: '+safe(j.model)+' · фон и редкость откроются после улучшения</p>'
      +'<button class="btn" style="margin-top:12px" onclick="closeModal();go(\'nft\')">'+icon('cards','sm')+'В коллекцию</button>'
      +'<button class="btn ghost" style="margin-top:8px" onclick="closeModal();go(\'upgrade\')">'+icon('swap','sm')+'К апгрейду</button></div>');
    NFTS=[]; loadNfts();
  });
}

/* ============ NFT ============ */
function loadNfts(){
  return api('nft_state').then(function(j){
    if(!j.ok) return;
    NFTS = j.items||[]; if(j.balance!=null) setBal(j.balance);
    $('nftCount').textContent = NFTS.length;
    var g=$('nftGrid');
    if(!NFTS.length){ g.innerHTML='<div class="empty" style="grid-column:1/-1">Пусто. Открой кейс или создай NFT.</div>'; return; }
    g.innerHTML = NFTS.map(function(n){
      var rk = n.rarity_key || 'common';
      return '<div class="nft" onclick="openNft('+n.id+')"><div class="im">'
        +'<img src="'+safe(n.url)+'" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'">'
        +'<span class="num">#'+n.id+'</span>'+(n.level>1?'<span class="lvl">LVL '+n.level+'</span>':'')
        +'</div><div class="inf"><div class="nm">'+safe(n.name)+'</div>'
        +'<div class="rw"><span>'+safe(n.model)+'</span><span>'+fmt(n.value)+'</span></div>'
        +'<div class="rar '+(rk==='rare'?'rare':rk==='epic'?'epic':'')+'">'+safe(n.rarity)+'</div></div></div>';
    }).join('');
    if($('upgrade').classList.contains('active')) eRender();
  });
}
function findNft(id){ return NFTS.filter(function(x){ return x.id===id; })[0]; }
function mintNft(){
  api('nft_mint').then(function(j){
    if(!j.ok) return toast(j.err||'Не удалось');
    toast(j.msg||'NFT создан'); NFTS=[]; loadNfts();
  });
}
function openNft(id){
  var n = findNft(id);
  var paint = function(n){
    if(!n) return toast('NFT не найден');
    showSheet('<div><div class="shead"><h3>'+safe(n.name)+' <span class="chip">#'+n.id+'</span></h3>'
      +'<button class="xb" onclick="closeModal()">'+icon('x','sm')+'</button></div>'
      +'<img class="fullimg" src="'+safe(n.url)+'" alt="">'
      +'<div class="stats"><div class="st"><span>Модель</span><b>'+safe(n.model)+'</b></div>'
      +'<div class="st"><span>Редкость</span><b>'+safe(n.rarity)+'</b></div>'
      +'<div class="st"><span>Уровень</span><b>'+n.level+'</b></div>'
      +'<div class="st"><span>Оценка</span><b>'+fmt(n.value)+'</b></div></div>'
      +'<button class="btn green" style="margin-top:12px" onclick="upgradeNft('+n.id+')">'+icon('bolt','sm')+'Улучшить · '+fmt(n.upgrade_cost)+'</button>'
      +'<div class="rowz" style="margin-top:8px"><button class="btn ghost" onclick="pinNft('+n.id+',\'profile\')">'+icon('user','sm')+'В профиль</button>'
      +'<button class="btn ghost" onclick="pinNft('+n.id+',\'balance\')">'+icon('coin','sm')+'В баланс</button></div>'
      +'<button class="btn red" style="margin-top:8px" onclick="archiveNft('+n.id+')">'+icon('lock','sm')+'В NFT-архив</button></div>');
  };
  if(n) return paint(n);
  loadNfts().then(function(){ paint(findNft(id)); });
}
function upgradeNft(id){
  var b = document.querySelector('#sheet .btn.green');
  if(b){ b.disabled=true; b.innerHTML='Улучшаем…'; }
  api('nft_upgrade', {id:id}).then(function(j){
    if(!j.ok){ toast(j.err||'Не удалось'); if(b){ b.disabled=false; b.innerHTML=icon('bolt','sm')+'Улучшить'; } return; }
    if(j.balance!=null) setBal(j.balance);
    NFTS=[]; loadNfts();
    var it=j.item;
    showSheet('<div style="text-align:center"><span class="chip a">УЛУЧШЕНИЕ</span>'
      +'<img class="fullimg" src="'+safe(it.url)+'" alt="" style="margin:10px 0">'
      +'<h3>'+safe(it.name)+' <span class="chip">#'+it.id+'</span></h3>'
      +'<p class="sub" style="margin-top:5px">'+safe(it.rarity)+' · '+safe(it.model)+' · уровень '+it.level+'</p>'
      +'<button class="btn" style="margin-top:12px" onclick="closeModal()">Готово</button></div>');
    haptic(); confetti(90); toast('Редкость: '+it.rarity);
  });
}
function pinNft(id,target){ api('nft_set',{id:id,target:target}).then(function(j){ if(!j.ok) return toast(j.err||'Ошибка'); toast(j.msg||'Готово'); NFTS=[]; loadNfts(); boot(); }); }
function archiveNft(id){ api('nft_to_archive',{id:id}).then(function(j){ if(!j.ok) return toast(j.err||'Ошибка'); toast('NFT в архиве'); closeModal(); NFTS=[]; loadNfts(); }); }

/* ============ админ ============ */
function openAdminCreate(){
  showSheet('<div><div class="shead"><h3>Кастомный NFT</h3><button class="xb" onclick="closeModal()">'+icon('x','sm')+'</button></div>'
    +'<label>Название</label><input id="acName" type="text" maxlength="30" placeholder="Капибара босс">'
    +'<label>Личный номер (0 — выдаст автоматически)</label><input id="acNum" type="number" min="0" value="0" inputmode="numeric">'
    +'<label>Редкость</label><select id="acRar"><option value="none">Без редкости (откроется после улучшения)</option><option value="rare">Редкий</option><option value="epic">Эпический</option></select>'
    +'<label>Модель</label><select id="acModel"><option value="">Случайная</option><option>Стандартный</option><option>Зимний</option><option>Снежный</option><option>Золотой</option><option>Неоновый</option><option>Призрачный</option><option>Космический</option></select>'
    +'<label>Своё фото (необязательно)</label><input id="acFile" type="file" accept="image/*">'
    +'<button class="btn" style="margin-top:12px" onclick="adminCreate()">Создать</button>'
    +'<p class="tiny" style="margin-top:8px">Номер должен быть свободен. Фото до 8 МБ, картинка генерируется на сервере.</p></div>');
}
function adminCreate(){
  var name=($('acName').value||'').trim(); if(!name) return toast('Введи название');
  var rar=$('acRar').value, body={name:name, number:num($('acNum').value), model:$('acModel').value, rarity:(rar==='none'?'common':rar)};
  var f=$('acFile').files && $('acFile').files[0];
  if(!f){ return send(); }
  if(f.size>8*1024*1024) return toast('Фото до 8 МБ');
  var fr = new FileReader();
  fr.onload = function(){ body.image = fr.result; send(); };
  fr.onerror = function(){ send(); };
  fr.readAsDataURL(f);
  function send(){
    api('admin_nft_create', body).then(function(j){
      if(!j.ok) return toast(j.err||'Не удалось');
      toast(j.msg||'Создан'); closeModal(); NFTS=[]; loadNfts();
    });
  }
}

function admStatus(t){ var e=$('admStatus'); if(e) e.textContent=t||''; }
function adminSaveTicker(){
  var text=($('admTicker').value||'').trim();
  if(!text) return toast('Введи текст');
  api('admin_ui',{action:'ticker',text:text}).then(function(j){
    if(!j.ok) return toast(j.err||'Ошибка');
    setTicker(text); admStatus('Тикер обновлён'); toast('Тикер обновлён');
  });
}
function adminRedrawNfts(){
  api('admin_ui',{action:'redraw'}).then(function(j){
    if(!j.ok) return toast(j.err||'Ошибка');
    NFTS=[]; loadNfts(); toast('Кэш NFT сброшен'); admStatus('NFT перерисуются при открытии');
  });
}
function adminResetAsk(){
  showSheet('<div><div class="shead"><h3>Новая коллекция NFT</h3><button class="xb" onclick="closeModal()">'+icon('x','sm')+'</button></div>'
    +'<p class="sub">Будут удалены все NFT игроков и лоты архива. Нумерация начнётся с #1. Это необратимо.</p>'
    +'<label>Введи RESET для подтверждения</label><input id="admConfirm" type="text" placeholder="RESET">'
    +'<button class="btn red" style="margin-top:10px" onclick="adminResetConfirm()">Удалить и создать заново</button></div>');
}
function adminResetConfirm(){
  var c=($('admConfirm').value||'').trim().toUpperCase();
  api('admin_ui',{action:'reset',confirm:c}).then(function(j){
    if(!j.ok) return toast(j.err||'Ошибка');
    closeModal(); NFTS=[]; loadNfts(); loadArchive(); boot();
    toast('Коллекция пересоздана'); admStatus('Удалено '+j.items+' NFT, лотов '+j.lots);
  });
}
function adminArenaBonus(){
  var amount=num($('admArenaBonus').value);
  if(!amount) return toast('Введи сумму');
  api('admin_ui',{action:'arena_bonus',amount:amount}).then(function(j){
    if(!j.ok) return toast(j.err||'Ошибка');
    if(j.balance!=null) setBal(j.balance); admStatus('Бонус арены: '+fmt(j.bonus)); toast('Бонус добавлен');
  });
}

/* ============ майнинг ============ */
function loadMining(){
  api('mining_state').then(function(j){
    if(!j.ok) return toast(j.err||'Недоступно');
    mineBase=num(j.pending); mineRate=num(j.rate); mineTs=Date.now();
    stopMining(); mineTimer=setInterval(mineTick,1000); mineTick();
    $('mineRate').textContent=fmt(j.rate)+' RCOIN/сутки';
    var owned=(j.servers||[]).filter(function(s){ return s.owned; });
    $('mineServers').textContent=owned.length+' серверов';
    var perHour=Math.floor(j.rate/24);
    var left=j.rate>0?Math.max(0,Math.ceil(((j.cap||j.rate*30)-j.pending)/j.rate*24)):0;
    $('mineEta').textContent='≈ '+fmt(perHour)+' в час · полный сбор через '+(j.rate>0?left+' ч':'—');
    var box=$('mineShop'); box.innerHTML='';
    (j.servers||[]).forEach(function(s){
      var d=document.createElement('div'); d.className='srv'+(s.owned?' own':'');
      d.innerHTML='<div class="icw">'+icon('server')+'</div><div style="flex:1;min-width:0"><b>'+safe(s.name)+'</b><small>'+fmt(s.per_day)+'/сутки'+(s.owned?' · '+Math.ceil(s.left/86400)+' дн.':'')+'</small></div>';
      if(!s.owned){ var b=document.createElement('button'); b.className='buy'; b.textContent=fmt(s.cost); b.onclick=function(){ mineBuy(s.tier); }; d.appendChild(b); }
      box.appendChild(d);
    });
  });
}
function stopMining(){ if(mineTimer){ clearInterval(mineTimer); mineTimer=null; } }
function mineTick(){ $('minePending').textContent = fmt(Math.floor(mineBase + mineRate*((Date.now()-mineTs)/1000)/86400)); }
function mineScroll(){ $('mineServersBox').scrollIntoView({behavior:'smooth',block:'center'}); }
function mineBuy(tier){ api('mining_buy',{tier:tier}).then(function(j){ if(!j.ok) return toast(j.err||'Не куплено'); if(j.balance!=null) setBal(j.balance); toast(j.msg||'Куплено'); loadMining(); }); }
function mineCollect(){ api('mining_collect').then(function(j){ if(!j.ok) return toast(j.err||'Пусто'); if(j.balance!=null) setBal(j.balance); toast(j.msg+(j.archived?' · '+fmt(j.archived)+' в архив':'')); haptic(); loadMining(); }); }

/* ============ апгрейдер ============ */
var E = { mode:'nft', id:0, target:'', bet:0 };
var TARGET_LABEL = {'':'Любой предмет','rare':'Только редкий','epic':'Только эпический','suit':'Лот из архива'};
function eMode(m, ev){
  if(ev) ev.preventDefault();
  E.mode = m;
  $('modeNft').classList.toggle('on', m==='nft');
  $('modeCoins').classList.toggle('on', m==='coins');
  $('modeChip').textContent = m==='nft' ? 'NFT → NFT' : 'NFT → RCOIN';
  eRender();
}
function eBet(v){
  if(v===undefined){ E.bet = num($('betInput').value); }
  else { E.bet = v; $('betInput').value = v; }
  eRender();
}
function eChance(){
  var n = findNft(E.id);
  if(!n) return 0;
  var base = (n.rarity_key==='epic') ? 60 : (n.rarity_key==='rare') ? 45 : 30;
  var bonus = Math.min(10, Math.floor(num(E.bet) / 100000000));
  return Math.max(3, Math.min(88, base + bonus));
}
function zonePath(ch){
  var a = Math.max(2.5, ch*3.6);                 // сектор от -90° по часовой
  var x0=120, y0=120, R=104;
  var p0=[x0, y0-R], e=(-90+a)*Math.PI/180;
  var p1=[x0+R*Math.cos(e), y0+R*Math.sin(e)];
  var d = 'M'+x0+' '+y0+' L'+p0[0]+' '+p0[1]+' A'+R+' '+R+' 0 '+(a>180?1:0)+' 1 '+p1[0].toFixed(2)+' '+p1[1].toFixed(2)+' Z';
  return {d:d, span:a};
}
function eRender(){
  var n = findNft(E.id);
  var ch = eChance();
  var cp=$('chancePct'); if(cp) cp.textContent = ch ? ch+'%' : '0%';
  var cb=$('chanceBar'); if(cb) cb.style.width = (ch||0)+'%';
  // зона выигрыша: только при внесённой сумме/NFT, иначе полосы нет
  var zw = $('zoneWrap');
  zw.innerHTML = ch>0 ? '<path d="'+zonePath(ch).d+'" fill="url(#gw)" opacity=".92"/>' : '';
  var core = $('dialCore');
  if(n){
    core.innerHTML = '<img src="'+safe(n.url)+'" alt="" onerror="this.style.display=\'none\'">';
  } else {
    core.innerHTML = '<div class="ph">'+icon('plus','lg')+'<small>выбери NFT</small></div>';
  }
  var b = $('beam');
  b.classList.toggle('zero', ch<=0);
  $('slotFrom').className = 'slot'+(n?' filled':'');
  $('slotFrom').innerHTML = n
    ? '<div class="sid"><img src="'+safe(n.url)+'" alt=""></div><div class="tx"><small>Что улучшаем</small><b>#'+n.id+' '+safe(n.name)+'</b></div>'
    : '<div class="sid">'+icon('plus','sm')+'</div><div class="tx"><small>Что улучшаем</small><b>Выбрать NFT</b></div>';
  $('slotTo').innerHTML = '<div class="sid">'+icon(E.target==='suit'?'lock':'crown','sm')+'</div><div class="tx"><small>Цель</small><b>'+(E.target==='suit'?'Лот архива':(TARGET_LABEL[E.target]||'Любой предмет'))+'</b></div>';
  var line = 'Выберите NFT — шанс и сектор появятся сразу';
  if(n && E.mode==='nft') line = 'Ставка: #'+n.id+' '+safe(n.name)+(E.bet?' + '+fmt(E.bet)+' RCOIN':'')+' → '+($('slotTo').querySelector('b').textContent)+' · шанс '+ch+'%';
  if(n && E.mode==='coins') line = 'Из #'+n.id+' получим '+fmt(eCoins())+' RCOIN · шанс '+ch+'%';
  $('sumLine').innerHTML = line;
  var ready = ch>0;
  var btn=$('upgBtn'); btn.disabled=!ready;
  $('upgText').textContent = ready ? 'Улучшить · '+ch+'%' : (n ? 'Введите сумму' : 'Выберите NFT');
}
function eCoins(){
  var n = findNft(E.id); if(!n) return 0;
  return Math.round((num(n.value)+num(E.bet))*1.6);
}
function ePicker(kind){
  var html='<div class="shead"><h3>'+(kind==='mine'?'Что улучшаем':'Цель')+'</h3><button class="xb" onclick="closeModal()">'+icon('x','sm')+'</button></div>';
  if(kind==='target'){
    var opts=[['','Любой предмет','из всех'],['rare','Только редкий','после улучшения'],['epic','Только эпический','после улучшения']];
    html+='<div class="pickgrid">'+opts.map(function(o){
      return '<div class="pick '+(E.target===o[0]?'on':'')+'" onclick="eSetTarget(\''+o[0]+'\')"><b>'+o[1]+'</b><small>'+o[2]+'</small></div>';
    }).join('')+'</div>';
    var lots=(AR&&AR.gifts)||[];
    if(lots.length){
      html+='<p class="tiny" style="margin:12px 0 6px">Или конкретный лот архива</p><div class="pickgrid">'
        + lots.slice(0,9).map(function(x){
          return '<div class="pick '+(E.target===('a:'+x.id)?'on':'')+'" onclick="eSetTarget(\'a:'+x.id+'\')">'
            + '<img src="'+safe(x.url)+'" alt=""><b>'+safe(x.name)+'</b><small>'+safe(x.rarity)+(x.price?' · '+fmt(x.price):'')+'</small></div>';
        }).join('')+'</div>';
    }
  } else {
    if(!NFTS.length) html+='<div class="empty">Нет NFT. Открой кейс или создай NFT.</div>';
    else html+='<div class="pickgrid">'+NFTS.map(function(n){
      return '<div class="pick '+(E.id===n.id?'on':'')+'" onclick="ePick('+n.id+')">'
        +'<img src="'+safe(n.url)+'" alt=""><b>#'+n.id+' '+safe(n.name)+'</b><small>'+safe(n.model)+' · '+fmt(n.value)+'</small></div>';
    }).join('')+'</div>';
  }
  showSheet(html);
}
function eSetTarget(v){ E.target=v; closeModal(); eRender(); }
function ePick(id){ E.id = (E.id===id ? 0 : id); closeModal(); eRender(); }
function eSpin(){
  var ch=eChance(); if(!ch) return;
  var n = findNft(E.id); if(!n) return;
  var btn=$('upgBtn'); btn.disabled=true;
  var btnText=$('upgText'); if(btnText) btnText.textContent='Крутим…';
  var box=$('dialBox'), beam=$('beam');
  box.classList.add('spinning');
  var body = {ids:[E.id], bet:E.bet, target:(E.target==='suit'?'':E.target), mode:E.mode};
  if(E.target && E.target.indexOf('a:')===0) body.lot = num(E.target.slice(2));
  api('archive_spin', body).then(function(j){
    if(!j.ok){
      toast(j.err||'Не удалось'); if(j.balance!=null) setBal(j.balance);
      box.classList.remove('spinning'); eRender(); return;
    }
    var chNow = j.chance || ch;
    var span = zonePath(chNow).span;
    var win = !!j.win;
    var turns = 5 + Math.floor(Math.random()*3);
    var targetDeg;
    if(win){
      var off = span*(0.18 + Math.random()*0.64);
      targetDeg = turns*360 + (360 - off);
    } else {
      var gap = Math.max(4, 360 - span);
      var off2 = span + gap*(0.25 + Math.random()*0.5);
      targetDeg = turns*360 + (360 - off2);
    }
    beam.classList.remove('zero');
    beam.style.transition = 'none';
    beam.style.transform = 'translateX(-50%) rotate(0deg)';
    /* 1 кадр форсируем, чтобы переход реально запустился */
    beam.getBoundingClientRect();
    beam.style.transition = 'transform 4.4s cubic-bezier(.12,.85,.06,1)';
    beam.style.transform = 'translateX(-50%) rotate('+targetDeg+'deg)';
    setTimeout(function(){
      box.classList.remove('spinning');
      if(j.balance!=null) setBal(j.balance);
      if(win){
        confetti(140); haptic();
        showSheet('<div style="text-align:center"><span class="chip ok">ПОБЕДА</span>'
          +(j.url?'<img class="fullimg" src="'+safe(j.url)+'" alt="" style="margin:10px 0">':'')
          +'<h3>'+safe(j.name||'Выигрыш')+'</h3>'
          +'<p class="sub" style="margin-top:5px">Шанс: '+chNow+'% · '+safe(j.rarity||'')+'</p>'
          +'<button class="btn" style="margin-top:12px" onclick="closeModal()">Забрать</button></div>');
      } else {
        showSheet('<div style="text-align:center"><span class="chip">БЕЗ ВЫИГРЫША</span>'
          +'<div style="display:grid;place-items:center;height:70px;color:#8b90ad">'+icon('drop','lg')+'</div>'
          +'<h3>NFT ушли в архив</h3><p class="sub" style="margin-top:5px">Шанс был '+chNow+'%</p>'
          +'<button class="btn ghost" style="margin-top:12px" onclick="closeModal()">Закрыть</button></div>');
      }
      E.id=0; E.bet=0; E.target=''; $('betInput').value=0;
      NFTS=[]; loadNfts(); loadArchive();
    }, 4500);
  });
}
function loadArchive(){
  api('archive_state').then(function(j){
    if(!j.ok) return;
    AR=j; $('pool').textContent=fmt(j.pool); $('archCount').textContent=fmt(j.archive);
    var box=$('lots');
    if(!j.gifts||!j.gifts.length) box.innerHTML='<div class="empty" style="grid-column:1/-1">Архив пуст</div>';
    else box.innerHTML=j.gifts.slice(0,6).map(function(x){
      return '<div class="pick"><img src="'+safe(x.url)+'" alt="" loading="lazy"><b>'+safe(x.name)+'</b><small>'+safe(x.rarity)+'</small></div>';
    }).join('');
    if($('upgrade').classList.contains('active')) eRender();
  });
}

/* ============ модалки / эффекты ============ */
function showSheet(h){ $('sheet').innerHTML=h; $('modal').classList.add('show'); }
function closeModal(){ $('modal').classList.remove('show'); }
function confetti(n){
  var box=document.createElement('div'); box.className='confetti';
  var cols=['#7c5cff','#4f8bff','#ffd98a','#4ce0a4','#fff'];
  for(var i=0;i<(n||80);i++){
    var s=document.createElement('i');
    s.style.left=(Math.random()*100)+'%'; s.style.top='-20px';
    s.style.background=cols[i%cols.length];
    s.style.animationDuration=(1.5+Math.random()*1.8)+'s';
    s.style.animationDelay=(Math.random()*.4)+'s';
    box.appendChild(s);
  }
  document.body.appendChild(box); setTimeout(function(){ box.remove(); },4200);
}

/* ============ арена ============ */
var ARA = { state:null, poll:null, stage:null, cdT:null, lastPhase:'' };
function polar(cx, cy, r, deg){ var a=(deg-90)*Math.PI/180; return [cx+r*Math.cos(a), cy+r*Math.sin(a)]; }
function arcPath(cx, cy, r, from, to){
  var p0=polar(cx,cy,r,from), p1=polar(cx,cy,r,to), large=(to-from)>180?1:0;
  return 'M'+p0[0].toFixed(2)+' '+p0[1].toFixed(2)+' A'+r+' '+r+' 0 '+large+' 1 '+p1[0].toFixed(2)+' '+p1[1].toFixed(2);
}
function arenaZones(){
  var st=ARA.state; if(!st) return [];
  if(st.zones && st.zones.length) return st.zones;
  var ps=st.players||[], n=ps.length||1;
  return ps.map(function(p,i){ return {id:p.id,name:p.name,color:p.color,bet:p.bet,start:i*360/n,end:(i+1)*360/n}; });
}
function drawZones(winId){
  var g=$('zoneRing'); if(!g) return;
  var zs=arenaZones(), ns='http://www.w3.org/2000/svg';
  g.innerHTML='';
  zs.forEach(function(z){
    var from=z.start+0.8, to=Math.max(from+0.4, z.end-0.8);
    var p=document.createElementNS(ns,'path');
    p.setAttribute('d', arcPath(200,200,150,from,to));
    p.setAttribute('stroke', z.color||'#7c5cff');
    p.setAttribute('stroke-width','46');
    p.setAttribute('fill','none');
    p.setAttribute('opacity', winId!=null && z.id!==winId ? '.3' : '1');
    g.appendChild(p);
    var mid=(from+to)/2, tp=polar(200,200,150,mid), t=document.createElementNS(ns,'text');
    t.setAttribute('x',tp[0]); t.setAttribute('y',tp[1]+4);
    t.setAttribute('text-anchor','middle'); t.setAttribute('class','lbl');
    t.textContent=(z.name||'?').slice(0,8);
    g.appendChild(t);
  });
}
function ballAt(deg, r){
  var p=polar(200,200,r||129,deg);
  $('arenaBall').setAttribute('cx',p[0]); $('arenaBall').setAttribute('cy',p[1]);
  $('arenaBallGlow').setAttribute('cx',p[0]); $('arenaBallGlow').setAttribute('cy',p[1]);
}
function renderArena(){
  var st=ARA.state; if(!st) return;
  var ps=st.players||[];
  $('arenaBank').textContent = fmt(st.pool||0);
  $('arenaBonusChip').textContent = '+'+fmt(st.bonus||0);
  $('onlineChip').innerHTML = icon('life','xs fill')+ps.length+'/2';
  var winId = (st.winner_idx>=0 && ps[st.winner_idx]) ? ps[st.winner_idx].id : null;
  drawZones(winId);
  var lbl = st.phase==='idle' ? 'Свободно' : st.phase==='waiting' ? 'Ждём игрока'
    : st.phase==='countdown' ? '' : st.phase==='rolling' ? 'Крутится' : 'Победитель';
  if(st.phase==='countdown'){
    var left = Math.max(0, Math.ceil(st.cd_left||0));
    $('arenaState').innerHTML = 'Старт через<br><em>'+left+'</em>';
  } else {
    $('arenaState').textContent = lbl;
  }
  var list=$('apList');
  if(!ps.length){ list.innerHTML='<div class="waiting">'+icon('user','lg')+'Ждём игроков</div>'; }
  else list.innerHTML = ps.map(function(p,i){
    return '<div class="pl'+(p.you?' me':'')+((st.phase==='done'&&st.winner_idx===i)?' win':'')+'">'
      +'<span class="dot" style="color:'+safe(p.color||'#7c5cff')+'"></span>'
      +'<span class="who2">'+safe(p.name)+(p.you?' <span class="chip a" style="height:18px;font-size:8px;padding:0 6px">ты</span>':'')+'</span>'
      +'<span class="stake">'+(st.free?'бесплатно':fmt(p.bet)+' RCOIN')+'</span>'
      +'<span class="pc">'+p.pct+' %</span></div>';
  }).join('');
  var joined=!!st.you, locked=['idle','waiting','countdown'].indexOf(st.phase)<0;
  $('arenaJoinBtn').classList.toggle('hide', joined);
  $('arenaLeaveBtn').classList.toggle('hide', !joined || locked);
  $('arenaBetInput').disabled = joined || locked;
  var canAdd = joined && !locked && (st.phase==='waiting' || st.phase==='countdown');
  var addRow=$('arenaAddRow'); if(addRow) addRow.classList.toggle('hide', !canAdd);
  var addInput=$('arenaAddInput'); if(addInput) addInput.disabled = !canAdd;
  $('arenaHist').innerHTML = (st.history&&st.history.length)
    ? st.history.map(function(h){ return '<div style="padding:5px 0;border-bottom:1px solid rgba(255,255,255,.06)">'+safe(h.name)+' · '+safe(h.reward)+'</div>'; }).join('')
    : 'Пока нет завершённых раундов';
  if(st.phase==='rolling') animateBall();
  else if(st.phase==='done' && st.winner_idx>=0 && ps[st.winner_idx]){
    var z=arenaZones().filter(function(z){ return z.id===ps[st.winner_idx].id; })[0];
    ballAt(z ? (z.start+z.end)/2 : 0);
  } else ballAt(0);
}
function animateBall(){
  var st=ARA.state; if(!st) return;
  var total=(st.roll_total||8)*1000;
  var left=Math.max(0, total - (st.roll_elapsed||0)*1000);
  var key = st.roll_stop || 0;
  if(!ARA.stage || ARA.stage.key!==key){
    var zs=arenaZones();
    var wp=(st.winner_idx>=0 && st.players[st.winner_idx])
      ? zs.filter(function(z){ return z.id===st.players[st.winner_idx].id; })[0] : null;
    ARA.stage = {key:key, t0:performance.now(), dur:Math.max(600,left),
      end: wp ? (wp.start+wp.end)/2 : 0, wobble:(Math.random()*2-1)*14};
  }
  var s=ARA.stage;
  var k=Math.min(1,(performance.now()-s.t0)/s.dur);
  var e=1-Math.pow(1-k,2.4);
  var jiggle=(1-k)*Math.sin(performance.now()/85)*1.5;
  ballAt(1080*(1-k)*(1-k) + s.end*e + jiggle);
  if(k<1) requestAnimationFrame(animateBall);
}
function pollArena(){
  api('arena').then(function(j){
    if(j.ok){ ARA.state=j.state; renderArena(); if(j.balance!=null) setBal(j.balance); }
    ARA.poll=setTimeout(pollArena, (ARA.state && ['countdown','rolling'].indexOf(ARA.state.phase)>=0) ? 500 : 1400);
  });
}
function arenaStart(){ if(!ARA.poll) pollArena(); }
function abPreset(v, btn){
  $('arenaBetInput').value=v;
  Array.prototype.forEach.call(document.querySelectorAll('#arena .mini'), function(b){ b.classList.toggle('on', Number(b.dataset.b)===v); });
}
function arenaJoin(){
  var bet=Math.max(1,num($('arenaBetInput').value));
  api('arena_join',{bet:bet}).then(function(j){
    if(!j.ok) return toast(j.err||'Не удалось войти');
    ARA.state=j.state; if(j.balance!=null) setBal(j.balance); renderArena(); haptic(); toast('Ты в лобби');
  });
}
function arenaLeave(){
  api('arena_leave').then(function(j){
    if(!j.ok) return toast(j.err||'Не удалось');
    ARA.state=j.state; if(j.balance!=null) setBal(j.balance); renderArena(); toast('Ставка возвращена');
  });
}
function arenaAdd(){
  var bet=Math.max(1,num($('arenaAddInput').value));
  api('arena_add',{bet:bet}).then(function(j){
    if(!j.ok) return toast(j.err||'Не удалось добавить');
    ARA.state=j.state; if(j.balance!=null) setBal(j.balance); renderArena(); haptic(); toast('Ставка усилена');
  });
}

/* ============ темы и обои ============ */
var THEMES = [
  {key:'obsidian', name:'Обсидиан', a1:'#d8b46a', a2:'#8f6a2a', a3:'#ffe6b0'},
  {key:'iphone',   name:'iPhone',   a1:'#0a84ff', a2:'#5e5ce6', a3:'#64d2ff'},
  {key:'android',  name:'Android',  a1:'#7c4dff', a2:'#00bfa6', a3:'#ff4081'},
  {key:'ruby',     name:'Рубин',    a1:'#ff5470', a2:'#b3123b', a3:'#ff8a5c'},
  {key:'ice',      name:'Лёд',      a1:'#7fdcff', a2:'#2f7fd8', a3:'#b6f2ff'},
  {key:'emerald',  name:'Изумруд',  a1:'#4ce39a', a2:'#12855c', a3:'#9dffcf'},
  {key:'violet',   name:'Фиолет',   a1:'#b06bff', a2:'#5b21b6', a3:'#e0a8ff'},
  {key:'light',    name:'Свет',     a1:'#0a84ff', a2:'#5e5ce6', a3:'#34c759', light:true}
];
var store = {
  get:function(k){ try { return localStorage.getItem(k); } catch(e) { return null; } },
  set:function(k,v){ try { localStorage.setItem(k,v); return true; } catch(e) { return false; } },
  del:function(k){ try { localStorage.removeItem(k); } catch(e) {} }
};
function applyTheme(){
  var key = store.get('rubin_theme') || SERVER_THEME || 'obsidian';
  var wall = store.get('rubin_wall') || '';
  var t = THEMES.filter(function(x){ return x.key===key; })[0] || THEMES[0];
  var rs = document.documentElement.style;
  rs.setProperty('--a1', t.a1); rs.setProperty('--a2', t.a2); rs.setProperty('--a3', t.a3);
  document.documentElement.setAttribute('data-theme', t.key);
  document.documentElement.classList.toggle('light', !!t.light);
  document.body.classList.toggle('wall', !!wall);
  document.body.style.backgroundImage = wall ? 'url("'+wall+'")' : '';
  try { if(tg){ tg.setHeaderColor(t.light?'#eef1f8':'#040405'); tg.setBackgroundColor(t.light?'#eef1f8':'#040405'); } } catch(e){}
  var row=$('themeRow');
  if(row) row.innerHTML = THEMES.map(function(x){
    return '<button class="th '+(x.key===key?'on':'')+'" title="'+x.name+'" data-k="'+x.key+'" '
      +'style="background:linear-gradient(150deg,'+x.a1+','+x.a3+')" onclick="setTheme(\''+x.key+'\')">'
      +'<i>'+(x.key===key?'✓':'')+'</i><span>'+x.name+'</span></button>';
  }).join('');
}
function setTheme(k){
  if(!store.set('rubin_theme',k)) toast('Не удалось сохранить тему');
  applyTheme();
  var t=THEMES.filter(function(x){ return x.key===k; })[0];
  toast('Тема: '+(t?t.name:k));
}
function wallUpload(inp){
  var f=inp.files && inp.files[0]; if(!f) return;
  if(f.size>3*1024*1024) return toast('Файл до 3 МБ');
  var fr=new FileReader();
  fr.onload=function(){
    if(!store.set('rubin_wall', fr.result)) return toast('Не хватило памяти — выбери фото поменьше');
    applyTheme(); toast('Обои установлены');
  };
  fr.readAsDataURL(f); inp.value='';
}
function wallReset(){ store.del('rubin_wall'); applyTheme(); toast('Обои сброшены'); }

document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });
eMode('nft', null);
applyTheme();
boot();
document.querySelectorAll('script[src*=telegram-web-app]').forEach(function(s){ s.remove(); });
</script>
</body>
</html>
"""

async def page(request: web.Request):
    return web.Response(text=WEBAPP_HTML, content_type="text/html", charset="utf-8",
                        headers={"Cache-Control": "no-store, max-age=0"})


async def health(request: web.Request):
    return web.Response(text="RCOIN OK")


async def _prices(request: web.Request):
    try:
        return web.json_response(api_prices())
    except Exception:
        return web.json_response({"price": 1000, "tick": 60, "series": []})


async def _keepalive():
    """Render: раз в 10 минут дёргаем свой /health, чтобы инстанс не засыпал."""
    if not WEBAPP_URL:
        return
    import urllib.request
    while True:
        try:
            urllib.request.urlopen(WEBAPP_URL + "/health", timeout=10).read()
        except Exception:
            pass
        await asyncio.sleep(600)


async def start_web():
    app = web.Application(client_max_size=20 * 1024 * 1024)
    app.router.add_get("/", page)
    app.router.add_get("/webapp", page)
    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)
    app.router.add_get("/nft/{nid}", nft_asset)
    app.router.add_get("/archive/{aid}", archive_asset)
    app.router.add_get("/banner", banner_asset)
    app.router.add_get("/logo", logo_asset)
    app.router.add_get("/wall", wall_asset)
    app.router.add_get("/fan", mining_fan_asset)
    app.router.add_get("/emoji/{eid}", emoji_asset)
    # Веб-приложение: бесплатная арена со ставками в игровой валюте, карьера и симулятор рынка.
    routes = {"me": a_me, "arena": a_arena, "arena_join": a_arena_join, "arena_add": a_arena_add, "arena_leave": a_arena_leave,
              "snowman_state": a_snowman_state, "snowman_collect": a_snowman_collect, "snowman_build": a_snowman_build}
    routes.update({"trade_state": api_trade_state, "trade_buy": api_trade_buy,
                   "trade_sell": api_trade_sell, "it_state": api_it_state,
                   "it_task": api_it_task, "nft_state": api_nft_state, "nft_mint": api_nft_mint, "nft_set": api_nft_set,
                   "mining_state": api_mining_state, "mining_buy": api_mining_buy, "mining_collect": api_mining_collect,
                   "archive_state": api_archive_state, "archive_spin": api_archive_spin,
                   "nft_photo": api_nft_photo, "nft_to_archive": api_nft_to_archive,
                   "archive_spin_coins": api_archive_spin_coins,
                   "cases_state": api_cases_state, "case_open": api_case_open,
                   "nft_upgrade": api_nft_upgrade, "admin_nft_create": api_admin_nft_create,
                   "admin_ui": api_admin_ui})
    for name, fn in routes.items():
        app.router.add_post("/api/" + name, api(fn))
    app.router.add_get("/api/prices", _prices)
    asyncio.create_task(_keepalive())
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Веб-сервер на порту %s, WEBAPP_URL=%s", PORT, WEBAPP_URL or "(не задан)")


# ============================ ОШИБКИ / НЕИЗВЕСТНЫЕ КОМАНДЫ / ЗАПУСК ============================
@dp.error()
async def on_error(event: ErrorEvent):
    global PREMIUM_ICONS, PREMIUM_EMOJI
    exc = event.exception
    s = str(exc).lower()
    log.error("Ошибка обработчика: %r", exc, exc_info=exc)
    if isinstance(exc, TelegramBadRequest):
        if "icon" in s and PREMIUM_ICONS:
            PREMIUM_ICONS = False
            await _dm(OWNER_ID, "⚠️ Telegram отклонил иконки на кнопках — отключил их автоматически. Включить обратно: PREMIUM_ICONS=1 (нужен Premium у владельца бота).")
        elif ("emoji" in s or "document_invalid" in s) and PREMIUM_EMOJI:
            PREMIUM_EMOJI = False
            await _dm(OWNER_ID, "⚠️ Telegram отклонил премиум-эмодзи в тексте — отключил их автоматически.")
    upd = event.update
    try:
        if upd.message:
            await upd.message.reply("⚠️ Что-то пошло не так. Повтори команду ещё раз.")
        elif upd.callback_query:
            await upd.callback_query.answer("⚠️ Ошибка, попробуй ещё раз", show_alert=True)
    except Exception:
        pass
    return True


@dp.message(F.text.startswith("/"))
async def unknown_command(message: Message, state: FSMContext):
    await state.clear()
    cmd = (message.text or "").split()[0]
    await message.reply(f"Команда <code>{esc(cmd)}</code> не найдена.\n\nОткрой /start или /menu, список — <code>помощь</code>.")


async def main():
    global bot, BOT_USERNAME
    if not BOT_TOKEN:
        log.error("BOT_TOKEN не задан! Создай/перевыпусти токен в @BotFather и добавь переменную окружения BOT_TOKEN.")
        return
    init_db()
    normalize_balances()
    migrate_nft_art()
    ensure_owner_nft()
    ar_restore()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(PremiumOut())
    bot.session.middleware(EmojiFallback())
    try:
        me = await bot.get_me()
    except Exception as e:
        log.error("Неверный BOT_TOKEN: %s", e)
        return
    BOT_USERNAME = me.username or BOT_USERNAME
    log.info("Бот запущен: @%s", BOT_USERNAME)
    await validate_emoji_ids()
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await bot.set_my_commands([BotCommand(command="start", description="Главное меню и баланс"),
                                   BotCommand(command="menu", description="Меню"),
                                   BotCommand(command="games", description="Список игр"),
                                   BotCommand(command="treyding", description="Трейдинг: курс, покупка, продажа"),
                                   BotCommand(command="rabota", description="Работа: IT-сфера, задания"),
                                   BotCommand(command="badges", description="Галочки профиля"),
                                   BotCommand(command="zp", description="Зарплата за активность в чате"),
                                   BotCommand(command="snowman", description="Снежный марафон и топ дня"),
                                   BotCommand(command="mining", description="Майнинг: серверы и добыча"),
                                   BotCommand(command="archive", description="Архив: что сверх лимита баланса"),
                                   BotCommand(command="help", description="Помощь")])
        if WEBAPP_URL:
            from aiogram.types import MenuButtonWebApp
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Арена", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e:
        log.warning("set_my_commands/menu: %s", e)
    await start_web()
    asyncio.create_task(warm_nft_emojis())
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(arena_loop())
    asyncio.create_task(db_backup_loop())
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except (asyncio.CancelledError, KeyboardInterrupt):
            raise
        except Exception:
            log.exception("Поллинг упал — перезапуск через 5 секунд")
            await asyncio.sleep(5)


# =====================================================================
#                          ГАЛОЧКИ (BADGES)
# =====================================================================
BADGES = {
    "dev": {"id": "5251635454041675257", "fallback": "👑", "title": "Владелец", "role": "Owner",
            "price_coin": 0, "price_stars": 0, "buyable": False},
    "moder": {"id": "5766894601709296405", "fallback": "🛡", "title": "Модератор", "role": "Moder",
              "price_coin": 0, "price_stars": 0, "buyable": False},
    "support": {"id": "5888937609253623352", "fallback": "🎧", "title": "Поддержка", "role": "Support",
                "price_coin": 0, "price_stars": 0, "buyable": False},
    "tester": {"id": "5888937609253623352", "fallback": "🧪", "title": "Тестер", "role": "Tester",
                "price_coin": 0, "price_stars": 0, "buyable": False},
    "premium2": {"id": "5789568614533176726", "fallback": "💎", "title": "Premium", "role": "Premium",
                 "price_coin": 0, "price_stars": 0, "buyable": False},
    "rubin": {"id": "5341454906807034418", "fallback": "💠", "title": "Rubin Premium", "role": "Premium",
              "price_coin": 0, "price_stars": 299, "buyable": True, "premium": True},
    "black": {"id": "5789386473560088107", "fallback": "☑️", "title": "Чёрная галочка", "role": "Donate",
              "price_coin": 5_000_000_000, "price_stars": 500, "buyable": True},
    "blue": {"id": "5810189259327413739", "fallback": "✔️", "title": "Синяя галочка", "role": "Verified",
             "price_coin": 2_500_000_000, "price_stars": 250, "buyable": True},
    "ny": {"id": "5954111328493771983", "fallback": "🎄", "title": "Новогодняя", "role": "Event",
           "price_coin": 5_000_000_000, "price_stars": 0, "buyable": True},
}
BADGE_ORDER = ["dev", "moder", "support", "tester", "premium2", "rubin", "black", "blue", "ny"]
BADGE_RANK = {
    "dev": ("Владелец", {"is_official": 1}),
    "moder": ("Moder", {"is_official": 1}),
    "support": ("Support", {"is_official": 1}),
    "tester": ("Tester", {"is_official": 1}),
    "rubin": ("Premium", {"is_donater": 1}),
    "premium2": ("Premium", {"is_donater": 1}),
    "black": ("Donate", {"is_donater": 1}),
    "blue": ("Лудоман", {}),
    "ny": ("Event", {"is_official": 1}),
}
MAX_PROFILE_BADGES = 4


def badge(key: str) -> str:
    b = BADGES.get(key)
    if not b:
        return ""
    if PREMIUM_EMOJI and b["id"]:
        return f'<tg-emoji emoji-id="{b["id"]}">{b["fallback"]}</tg-emoji>'
    return b["fallback"]


def badge_text(key: str) -> str:
    # InlineKeyboardButton.text не поддерживает HTML <tg-emoji>; ID эмодзи
    # передаётся через icon_custom_emoji_id в btn(), а здесь только короткая подпись.
    b = BADGES[key]
    return f"{b['fallback']} {b['title']}"


def init_tables():
    for sql in (
        "CREATE TABLE IF NOT EXISTS user_badges(user_id INTEGER, badge TEXT, got_at INTEGER DEFAULT 0, slot INTEGER DEFAULT 0, PRIMARY KEY(user_id,badge))",
        "CREATE TABLE IF NOT EXISTS user_premium(user_id INTEGER PRIMARY KEY, until INTEGER DEFAULT 0, bought_at INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS salary_log(user_id INTEGER, day TEXT, amount INTEGER, PRIMARY KEY(user_id,day))",
        "CREATE TABLE IF NOT EXISTS chat_activity(user_id INTEGER, day TEXT, msg_count INTEGER DEFAULT 0, PRIMARY KEY(user_id,day))",
        "CREATE TABLE IF NOT EXISTS trade_holdings(user_id INTEGER PRIMARY KEY, coins REAL DEFAULT 0, avg_price REAL DEFAULT 0, invested INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS trade_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, side TEXT, amount REAL, price REAL, coins INTEGER, ts INTEGER)",
        "CREATE TABLE IF NOT EXISTS it_progress(user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, coins INTEGER DEFAULT 0, tasks_done INTEGER DEFAULT 0, last_task INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS snowman_daily(user_id INTEGER, day TEXT, snowballs INTEGER DEFAULT 0, snowmen INTEGER DEFAULT 0, last_collect INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, PRIMARY KEY(user_id,day))",
        "CREATE TABLE IF NOT EXISTS snowman_rewards(day TEXT, user_id INTEGER, place INTEGER, amount INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0, PRIMARY KEY(day,place))",
        "CREATE TABLE IF NOT EXISTS mining_servers(user_id INTEGER, tier INTEGER, bought_at INTEGER DEFAULT 0, expires_at INTEGER DEFAULT 0, PRIMARY KEY(user_id,tier))",
        "CREATE TABLE IF NOT EXISTS nft_archive(id INTEGER PRIMARY KEY AUTOINCREMENT, rarity TEXT, name TEXT, photo TEXT, model TEXT, background TEXT, price INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS upg_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, nft_id INTEGER, rarity TEXT, result TEXT, chance INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY, owner_id INTEGER, bet INTEGER DEFAULT 0, players TEXT DEFAULT '[]', status TEXT DEFAULT 'wait', created_at INTEGER DEFAULT 0)",
    ):
        x(sql)


# ---------------- операции ----------------
def has_badge(uid: int, key: str) -> bool:
    return q("SELECT 1 FROM user_badges WHERE user_id=? AND badge=?", (uid, key), one=True) is not None


def give_badge(uid: int, key: str) -> bool:
    if key not in BADGES:
        return False
    created = x("INSERT OR IGNORE INTO user_badges(user_id,badge,got_at,slot) VALUES(?,?,?,0)", (uid, key, now()))[0]
    if created:
        if BADGES[key].get("premium"):
            set_premium(uid, 30 * 86400)
        sync_badge_rank(uid)
    return bool(created)


def take_badge(uid: int, key: str) -> bool:
    if key not in BADGES:
        return False
    if uid == OWNER_ID and key == "dev":
        return False
    removed = x("DELETE FROM user_badges WHERE user_id=? AND badge=?", (uid, key))[0]
    if removed:
        if BADGES[key].get("premium"):
            x("UPDATE user_premium SET until=0 WHERE user_id=?", (uid,))
        u = get_user(uid)
        title = BADGE_RANK.get(key, (None,))[0]
        if title and (u["rank_title"] or "Новичок") == title:
            if not sync_badge_rank(uid):
                update_user(uid, rank_title="Новичок")
    return bool(removed)


def my_badges(uid: int):
    if uid == OWNER_ID and "dev" in BADGES and not has_badge(uid, "dev"):
        give_badge(uid, "dev")
    have = {r["badge"] for r in q("SELECT badge FROM user_badges WHERE user_id=?", (uid,))}
    return [b for b in BADGE_ORDER if b in have]


def sync_badge_rank(uid: int) -> Optional[str]:
    """Ранг по старшей галочке. Ранг, выданный админом вручную, не перезаписываем."""
    u = get_user(uid)
    if int(u.get("is_admin_rank") or 0) or int(u.get("is_official") or 0):
        return None
    have = set(my_badges(uid))
    for key in BADGE_ORDER:
        if key in have and key in BADGE_RANK:
            title, flags = BADGE_RANK[key]
            update_user(uid, rank_title=title, **flags)
            return title
    return None


def profile_badges(uid: int):
    owned = my_badges(uid)
    pinned = [r["badge"] for r in q("SELECT badge FROM user_badges WHERE user_id=? AND slot=1", (uid,)) if r["badge"] in BADGES]
    if not pinned:
        pinned = owned
    if uid == OWNER_ID and "dev" in owned:
        pinned = ["dev"] + [b for b in pinned if b != "dev"]
    order = {b: i for i, b in enumerate(BADGE_ORDER)}
    pinned.sort(key=lambda b: order.get(b, 99))
    return pinned[:MAX_PROFILE_BADGES]


def pin_badge(uid: int, key: str) -> bool:
    used = q("SELECT COUNT(*) n FROM user_badges WHERE user_id=? AND slot=1", (uid,), one=True)["n"]
    if used >= MAX_PROFILE_BADGES:
        return False
    return x("UPDATE user_badges SET slot=1 WHERE user_id=? AND badge=?", (uid, key))[0] == 1


def unpin_badge(uid: int, key: str):
    x("UPDATE user_badges SET slot=0 WHERE user_id=? AND badge=?", (uid, key))


def set_premium(uid: int, seconds: int):
    greatest = "GREATEST(user_premium.until, EXCLUDED.until)" if DATABASE_URL else "MAX(until, excluded.until)"
    x("INSERT INTO user_premium(user_id,until,bought_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET "
      f"until={greatest}, bought_at=excluded.bought_at", (uid, now() + int(seconds), now()))


def premium_left(uid: int) -> int:
    r = q("SELECT until FROM user_premium WHERE user_id=?", (uid,), one=True)
    return max(0, (r["until"] if r else 0) - now())


def is_premium(uid: int) -> bool:
    return premium_left(uid) > 0 or has_badge(uid, "rubin") or has_badge(uid, "premium2")


def win_mult(uid: int) -> float:
    return 1.5 if is_premium(uid) else 1.0


def bonus_mult(uid: int) -> int:
    return 2 if is_premium(uid) else 1


def rank_line(uid: int) -> str:
    u = get_user(uid)
    parts = []
    if u.get("profile_emoji"):
        fb = esc(u.get("profile_emoji_fb") or "✨")[:8]
        parts.append(f'<tg-emoji emoji-id="{u["profile_emoji"]}">{fb}</tg-emoji>')
    parts.append(f"<b>{esc(u['rank_title'] or 'Новичок')}</b>")
    parts += [badge(b) for b in profile_badges(uid)]
    return " ".join(parts)


# =====================================================================
#                        НОВЫЙ ФОРМАТ БАЛАНСА
# =====================================================================
def mono(n: int) -> str:
    return f"{int(n):,}".replace(",", "'")


def nft_photo(uid: int, kind: str = "balance"):
    """Фото NFT для баланса/профиля: только явно выбранное игроком."""
    u = get_user(uid)
    col = "profile_nft_id" if kind == "profile" else "balance_nft_id"
    chosen = int(u.get(col) or 0)
    if not chosen:
        return "", ""
    r = q("SELECT id,name,photo,model,background,rarity,level FROM nft_items WHERE id=? AND owner_id=?", (chosen, uid), one=True)
    if not r:
        return "", ""
    cap = f"🖼 #{r['id']} · {r['name']}"
    image_id = int(r["id"])
    if kv_get(f"nftpng:{image_id}"):
        return f"db:{image_id}", cap
    p = (r["photo"] or "").strip()
    if p.startswith("http"):
        return p, cap
    local = (kv_get(f"nftimg:{image_id}") or "").strip()
    if local:
        candidate = Path(local)
        if not candidate.is_absolute():
            candidate = NFT_DIR / candidate.name
        if candidate.exists():
            return str(candidate), cap
    try:
        raw = png_nft(image_id, r["name"], r.get("photo", ""), r.get("model", ""), r.get("background", ""), r.get("rarity", "common"), int(r.get("level", 1)))
        kv_set(f"nftpng:{image_id}", base64.b64encode(raw).decode("ascii"))
        return f"db:{image_id}", cap
    except Exception as e:
        log.warning("nft_photo regen: %s", e)
    return "", cap


NFT_BG_PALETTES = {
    "Обычный": ((83, 45, 146), (132, 78, 188), (255, 170, 240)),
    "Морозный": ((7, 18, 34), (16, 60, 86), (120, 225, 255)),
    "Праздничный": ((30, 10, 24), (95, 22, 44), (255, 170, 90)),
    "Звёздный": ((10, 8, 30), (42, 22, 82), (185, 150, 255)),
    "Северное сияние": ((4, 22, 26), (8, 74, 72), (80, 255, 190)),
    "Галактика": ((14, 6, 32), (56, 12, 96), (255, 110, 220)),
}
NFT_RARITY_COLOR = {"common": (198, 202, 212), "uncommon": (160, 190, 220),
                    "rare": (214, 182, 116), "epic": (255, 226, 174),
                    "legendary": (255, 236, 190)}
NFT_MODEL_ACCENT = {"Зимний": (150, 220, 255), "Снежный": (230, 245, 255),
                    "Золотой": (255, 205, 100), "Неоновый": (255, 90, 220),
                    "Призрачный": (200, 180, 255), "Космический": (255, 125, 235)}


def _nft_star_points(cx, cy, outer, inner, points=5, rot=-90):
    pts = []
    for i in range(points * 2):
        ang = math.radians(rot + i * 180 / points)
        rr = outer if i % 2 == 0 else inner
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    return pts


def _nft_tree(d, cx, cy, accent):
    """Ёлка: три пушистых яруса, снег на ветках, гирлянда, звезда."""
    d.rounded_rectangle((cx - 12, cy + 52, cx + 12, cy + 96), radius=5, fill=(122, 82, 52))
    layers = [(cy - 118, cy + 42, 96), (cy - 62, cy + 74, 112), (cy + 2, cy + 106, 128)]
    for top, bot, half in layers:
        mid = (top + bot) // 2
        d.polygon([(cx, top), (cx - half, bot), (cx + half, bot)], fill=(22, 118, 74))
        d.polygon([(cx, top + 8), (cx - int(half * .92), bot - 10), (cx + int(half * .92), bot - 10)],
                  fill=(30, 152, 98))
        for k in range(4):
            x0 = cx - half + 18 + k * (2 * half - 36) // 3
            d.ellipse((x0 - 9, bot - 20, x0 + 9, bot - 6), fill=(240, 250, 255, 210))
        d.line((cx - half + 16, mid, cx + half - 16, mid), fill=(255, 196, 96, 150), width=3)
        for k in range(6):
            x0 = cx - half + 26 + k * (2 * half - 52) // 5
            d.ellipse((x0 - 4, mid - 14 - (k % 2) * 8, x0 + 4, mid - 6 - (k % 2) * 8),
                      fill=(255, 90, 120) if k % 2 else (255, 214, 120))
    d.polygon(_nft_star_points(cx, cy - 132, 24, 10), fill=(255, 226, 120))
    d.ellipse((cx - 6, cy - 138, cx + 6, cy - 126), fill=(255, 255, 235, 200))


def _nft_gift(d, cx, cy, accent):
    """Подарок: коробка с бантом, снежинками и лентой."""
    d.rounded_rectangle((cx - 80, cy - 52, cx + 80, cy + 86), radius=14, fill=(178, 34, 52))
    d.rounded_rectangle((cx - 80, cy - 52, cx + 80, cy - 10), radius=14, fill=(206, 46, 66))
    d.rectangle((cx - 92, cy - 84, cx + 92, cy - 46), fill=(224, 66, 86))
    d.rectangle((cx - 14, cy - 84, cx + 14, cy + 86), fill=(255, 210, 96))
    d.ellipse((cx - 50, cy - 128, cx - 2, cy - 74), fill=(255, 210, 96))
    d.ellipse((cx + 2, cy - 128, cx + 50, cy - 74), fill=(255, 210, 96))
    d.ellipse((cx - 20, cy - 108, cx + 20, cy - 76), fill=(224, 66, 86))
    for x0, y0, s in ((cx - 56, cy + 12, 9), (cx + 44, cy + 46, 7), (cx + 56, cy - 24, 6)):
        for ang in (0, 60, 120):
            a = math.radians(ang)
            d.line((x0 - math.cos(a) * s, y0 - math.sin(a) * s, x0 + math.cos(a) * s, y0 + math.sin(a) * s),
                   fill=(255, 255, 255, 210), width=2)


def _nft_snowman(d, cx, cy, accent):
    """Снеговик как на референсе: цилиндр с лентой, шарф, ветки-руки, пуговицы."""
    snow, shade = (246, 251, 255), (206, 224, 240)
    base = cy + 128          # низ снеговика
    # руки-ветки
    for sx in (-1, 1):
        x0 = cx + sx * 92
        d.line((x0, base - 96, x0 + sx * 60, base - 128), fill=(122, 88, 58), width=8)
        d.line((x0 + sx * 26, base - 110, x0 + sx * 44, base - 146), fill=(122, 88, 58), width=6)
        d.line((x0 + sx * 46, base - 120, x0 + sx * 74, base - 104), fill=(122, 88, 58), width=6)
    # тело: два шара с бликом слева и тенью справа
    layers = ((cx - 104, base - 132, cx + 104, base, 0), (cx - 72, base - 226, cx + 72, base - 112, 1),
              (cx - 54, base - 328, cx + 54, base - 218, 2))
    for x0, y0, x1, y1, _ in layers:
        d.ellipse((x0, y0, x1, y1), fill=snow)
        w2 = (x1 - x0) // 2
        d.ellipse((cx + int(w2 * .18), y0 + 8, x1, y1), fill=shade)
        d.ellipse((x0, y0, cx + int(w2 * .3), y1), fill=snow)
    hy = base - 276          # центр головы по Y
    # лицо: глаза, нос-морковка, рот
    for dx in (-19, 19):
        d.ellipse((cx + dx - 9, hy - 18, cx + dx + 9, hy), fill=(28, 32, 44))
        d.ellipse((cx + dx - 6, hy - 15, cx + dx - 1, hy - 9), fill=(255, 255, 255, 220))
    d.polygon([(cx - 4, hy + 6), (cx + 44, hy + 16), (cx - 4, hy + 26)], fill=(242, 148, 58))
    for dx in (-7, 3, 13):
        d.ellipse((cx + dx - 3, hy + 40, cx + dx + 3, hy + 46), fill=(58, 62, 76))
    # шарф
    d.rounded_rectangle((cx - 58, base - 228, cx + 58, base - 188), radius=12, fill=(200, 48, 60))
    for k in range(5):
        x0 = cx - 50 + k * 25
        d.rectangle((x0, base - 228, x0 + 12, base - 216), fill=(238, 238, 246))
    d.polygon([(cx + 14, base - 216), (cx + 50, base - 164), (cx + 20, base - 158)], fill=(178, 38, 52))
    # цилиндр
    d.rectangle((cx - 46, base - 404, cx + 46, base - 332), fill=(34, 38, 50))
    d.rectangle((cx - 46, base - 368, cx + 46, base - 352), fill=(190, 44, 58))
    d.rounded_rectangle((cx - 68, base - 344, cx + 68, base - 320), radius=10, fill=(44, 48, 62))
    # пуговицы
    for yy in (base - 96, base - 62, base - 28):
        d.ellipse((cx - 8, yy - 8, cx + 8, yy + 8), fill=(40, 46, 60))
    # снежок на плечах
    for k in range(9):
        x0 = cx - 94 + k * 24
        d.ellipse((x0 - 5, base - 140 + (k % 3) * 3, x0 + 7, base - 126 + (k % 3) * 3),
                  fill=(255, 255, 255, 230))


def _nft_snowflake(d, cx, cy, accent):
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        x2, y2 = cx + math.cos(a) * 96, cy + math.sin(a) * 96
        d.line((cx, cy, x2, y2), fill=(235, 250, 255), width=7)
        for side in (-1, 1):
            b = math.radians(ang + side * 28)
            x3, y3 = cx + math.cos(a) * 62 + math.cos(b) * 22, cy + math.sin(a) * 62 + math.sin(b) * 22
            d.line((cx + math.cos(a) * 62, cy + math.sin(a) * 62, x3, y3), fill=(180, 235, 255), width=5)
    d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=(255, 255, 255))


def _nft_santa(d, cx, cy, accent):
    d.ellipse((cx - 48, cy - 30, cx + 48, cy + 70), fill=(250, 214, 186))
    d.ellipse((cx - 55, cy + 18, cx + 55, cy + 108), fill=(250, 252, 255))
    d.polygon([(cx - 62, cy - 40), (cx, cy - 155), (cx + 62, cy - 40)], fill=(205, 42, 58))
    d.ellipse((cx - 9, cy - 155, cx + 25, cy - 125), fill=(250, 252, 255))
    d.rectangle((cx - 68, cy - 52, cx + 68, cy - 32), fill=(250, 252, 255))
    d.ellipse((cx - 30, cy - 8, cx - 17, cy + 5), fill=(30, 38, 52))
    d.ellipse((cx + 17, cy - 8, cx + 30, cy + 5), fill=(30, 38, 52))
    d.ellipse((cx - 9, cy + 8, cx + 9, cy + 22), fill=(232, 110, 100))


def _nft_planet(d, cx, cy, accent):
    d.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), fill=(70, 40, 130))
    d.ellipse((cx - 70, cy - 78, cx + 42, cy - 4), fill=(120, 80, 200, 150))
    d.ellipse((cx - 148, cy - 30, cx + 148, cy + 34), outline=(255, 160, 235), width=9)
    for ang in (18, 160, 265):
        a = math.radians(ang)
        x, y = cx + math.cos(a) * 126, cy + math.sin(a) * 58
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 245, 220))


def _nft_robot(d, cx, cy, accent):
    d.rounded_rectangle((cx - 66, cy - 70, cx + 66, cy + 58), radius=22, fill=(180, 205, 230))
    d.rounded_rectangle((cx - 48, cy - 48, cx + 48, cy + 26), radius=16, fill=(24, 34, 50))
    d.ellipse((cx - 32, cy - 28, cx - 8, cy - 4), fill=accent)
    d.ellipse((cx + 8, cy - 28, cx + 32, cy - 4), fill=accent)
    d.rectangle((cx - 22, cy + 6, cx + 22, cy + 16), fill=(120, 230, 200))
    d.line((cx, cy - 70, cx, cy - 108), fill=(210, 230, 250), width=6)
    d.ellipse((cx - 10, cy - 120, cx + 10, cy - 100), fill=(255, 190, 90))


def _nft_bear(d, cx, cy, accent):
    d.ellipse((cx - 86, cy - 70, cx + 86, cy + 92), fill=(142, 92, 58))
    d.ellipse((cx - 88, cy - 94, cx - 38, cy - 40), fill=(142, 92, 58))
    d.ellipse((cx + 38, cy - 94, cx + 88, cy - 40), fill=(142, 92, 58))
    d.ellipse((cx - 48, cy - 16, cx + 48, cy + 70), fill=(218, 176, 128))
    d.ellipse((cx - 32, cy - 38, cx - 16, cy - 22), fill=(30, 30, 34))
    d.ellipse((cx + 16, cy - 38, cx + 32, cy - 22), fill=(30, 30, 34))
    d.ellipse((cx - 15, cy - 14, cx + 15, cy + 8), fill=(32, 30, 34))
    d.arc((cx - 30, cy + 4, cx + 30, cy + 44), 10, 170, fill=(80, 50, 30), width=4)


def _nft_penguin(d, cx, cy, accent):
    d.ellipse((cx - 78, cy - 78, cx + 78, cy + 100), fill=(28, 42, 62))
    d.ellipse((cx - 52, cy - 38, cx + 52, cy + 82), fill=(245, 250, 255))
    d.ellipse((cx - 30, cy - 58, cx - 12, cy - 40), fill=(250, 250, 255))
    d.ellipse((cx + 12, cy - 58, cx + 30, cy - 40), fill=(250, 250, 255))
    d.ellipse((cx - 22, cy - 56, cx - 18, cy - 47), fill=(20, 24, 32))
    d.ellipse((cx + 18, cy - 56, cx + 22, cy - 47), fill=(20, 24, 32))
    d.polygon([(cx - 13, cy - 38), (cx + 13, cy - 38), (cx, cy - 22)], fill=(255, 165, 60))
    d.ellipse((cx - 96, cy - 10, cx - 62, cy + 66), fill=(28, 42, 62))
    d.ellipse((cx + 62, cy - 10, cx + 96, cy + 66), fill=(28, 42, 62))


def _nft_crown(d, cx, cy, accent):
    d.polygon([(cx - 92, cy + 58), (cx - 72, cy - 46), (cx - 24, cy + 8), (cx, cy - 76),
               (cx + 24, cy + 8), (cx + 72, cy - 46), (cx + 92, cy + 58)], fill=(255, 205, 70))
    d.rectangle((cx - 92, cy + 58, cx + 92, cy + 88), fill=(232, 170, 45))
    for x, col in ((cx - 50, (255, 90, 110)), (cx, (90, 200, 255)), (cx + 50, (150, 255, 150))):
        d.ellipse((x - 10, cy + 56, x + 10, cy + 76), fill=col)


def _nft_cocktail(d, cx, cy, accent):
    d.polygon([(cx - 62, cy - 84), (cx + 62, cy - 84), (cx, cy + 42)], fill=(120, 230, 255, 120))
    d.polygon([(cx - 48, cy - 54), (cx + 48, cy - 54), (cx, cy + 22)], fill=(255, 120, 150))
    d.line((cx, cy + 42, cx, cy + 100), fill=(220, 245, 255), width=7)
    d.line((cx - 40, cy + 100, cx + 40, cy + 100), fill=(220, 245, 255), width=7)
    d.line((cx + 8, cy - 84, cx + 44, cy - 150), fill=(255, 210, 90), width=6)
    d.ellipse((cx + 28, cy - 166, cx + 70, cy - 124), fill=(255, 170, 70))


def _nft_blob(d, cx, cy, accent):
    """Плюшевый персонаж в стиле Plush Pepe: объём, свечение, большие глаза и сердечко."""
    r, g, b = accent[:3]
    light = (min(255, r + 78), min(255, g + 78), min(255, b + 82))
    deep = (int(r * .52), int(g * .48), int(b * .58))
    for pad, a in ((30, 22), (20, 34), (12, 52)):
        d.ellipse((cx - 96 - pad, cy - 100 - pad, cx + 96 + pad, cy + 104 + pad), fill=accent + (a,))
    d.ellipse((cx - 88, cy - 98, cx + 88, cy + 102), fill=deep + (242,))
    d.ellipse((cx - 84, cy - 94, cx + 84, cy + 94), fill=accent + (248,))
    d.ellipse((cx - 62, cy - 84, cx - 14, cy - 36), fill=light + (70,))
    d.ellipse((cx - 54, cy - 76, cx - 20, cy - 46), fill=(255, 255, 255, 55))
    for dx in (-36, 36):
        d.ellipse((cx + dx - 28, cy - 62, cx + dx + 28, cy + 2), fill=(255, 255, 255, 255))
        d.ellipse((cx + dx - 15, cy - 50, cx + dx + 15, cy - 10), fill=(32, 48, 82, 255))
        d.ellipse((cx + dx - 9, cy - 45, cx + dx + 1, cy - 33), fill=(255, 255, 255, 240))
        d.ellipse((cx + dx + 3, cy - 20, cx + dx + 11, cy - 12), fill=(255, 255, 255, 175))
    d.arc((cx - 22, cy + 12, cx + 22, cy + 44), 16, 164, fill=(38, 22, 40, 236), width=7)
    d.ellipse((cx - 74, cy - 4, cx - 50, cy + 12), fill=(255, 140, 180, 70))
    d.ellipse((cx + 50, cy - 4, cx + 74, cy + 12), fill=(255, 140, 180, 70))
    d.ellipse((cx - 74, cy + 86, cx - 22, cy + 122), fill=accent + (255,))
    d.ellipse((cx + 22, cy + 86, cx + 74, cy + 122), fill=accent + (255,))
    d.ellipse((cx - 80, cy + 48, cx - 30, cy + 78), fill=accent + (255,))
    d.ellipse((cx + 30, cy + 48, cx + 80, cy + 78), fill=accent + (255,))
    hx, hy = cx, cy + 74
    d.ellipse((hx - 26, hy - 18, hx + 2, hy + 8), fill=(255, 84, 138, 255))
    d.ellipse((hx - 2, hy - 18, hx + 26, hy + 8), fill=(255, 84, 138, 255))
    d.polygon([(hx - 24, hy - 6), (hx + 24, hy - 6), (hx, hy + 22)], fill=(255, 84, 138, 255))
    d.ellipse((hx - 16, hy - 12, hx - 6, hy - 2), fill=(255, 255, 255, 140))
    d.polygon(_nft_star_points(cx + 76, cy - 70, 17, 7), fill=(255, 250, 214))
    d.polygon(_nft_star_points(cx - 74, cy - 58, 10, 4), fill=(255, 250, 214, 190))


def _nft_rollix(d, cx, cy, accent):
    d.ellipse((cx - 92, cy - 62, cx + 92, cy + 104), fill=(48, 112, 232))
    d.ellipse((cx - 62, cy - 20, cx + 62, cy + 94), fill=(208, 238, 255))
    d.ellipse((cx - 72, cy - 96, cx + 72, cy + 10), fill=(66, 142, 255))
    d.ellipse((cx - 38, cy - 24, cx + 38, cy - 2), fill=(255, 255, 255))
    d.ellipse((cx - 20, cy - 20, cx - 8, cy - 8), fill=(18, 24, 38))
    d.ellipse((cx + 8, cy - 20, cx + 20, cy - 8), fill=(18, 24, 38))
    d.polygon([(cx - 18, cy + 4), (cx + 18, cy + 4), (cx, cy + 26)], fill=(255, 158, 52))
    d.ellipse((cx - 48, cy + 88, cx - 4, cy + 112), fill=(255, 158, 52))
    d.ellipse((cx + 4, cy + 88, cx + 48, cy + 112), fill=(255, 158, 52))
    d.arc((cx - 74, cy - 6, cx + 74, cy + 96), 20, 160, fill=(255, 210, 84, 220), width=7)
    d.ellipse((cx - 18, cy + 62, cx + 18, cy + 96), fill=(255, 210, 84))
    d.ellipse((cx - 10, cy + 70, cx + 10, cy + 88), fill=(25, 35, 55))
    d.arc((cx - 70, cy - 106, cx + 70, cy - 46), 200, 340, fill=(255, 255, 255, 170), width=4)


def _nft_cat(d, cx, cy, accent):
    d.polygon([(cx - 80, cy - 48), (cx - 58, cy - 120), (cx - 24, cy - 62)], fill=(224, 150, 78))
    d.polygon([(cx + 80, cy - 48), (cx + 58, cy - 120), (cx + 24, cy - 62)], fill=(224, 150, 78))
    d.polygon([(cx - 68, cy - 58), (cx - 56, cy - 102), (cx - 35, cy - 66)], fill=(255, 170, 170))
    d.polygon([(cx + 68, cy - 58), (cx + 56, cy - 102), (cx + 35, cy - 66)], fill=(255, 170, 170))
    d.ellipse((cx - 86, cy - 62, cx + 86, cy + 86), fill=(236, 166, 86))
    d.ellipse((cx - 58, cy - 18, cx - 18, cy + 20), fill=(30, 40, 34))
    d.ellipse((cx + 18, cy - 18, cx + 58, cy + 20), fill=(30, 40, 34))
    d.ellipse((cx - 50, cy - 14, cx - 34, cy + 4), fill=(120, 230, 120))
    d.ellipse((cx + 34, cy - 14, cx + 50, cy + 4), fill=(120, 230, 120))
    d.polygon([(cx - 9, cy + 24), (cx + 9, cy + 24), (cx, cy + 38)], fill=(255, 140, 150))
    d.arc((cx - 30, cy + 34, cx - 4, cy + 54), 10, 170, fill=(80, 45, 30), width=3)
    d.arc((cx + 4, cy + 34, cx + 30, cy + 54), 10, 170, fill=(80, 45, 30), width=3)
    for y in (cy + 4, cy + 26, cy + 48):
        d.line((cx - 104, y, cx - 78, y + 6), fill=(255, 240, 210, 150), width=2)
        d.line((cx + 78, y + 6, cx + 104, y), fill=(255, 240, 210, 150), width=2)
    for i in range(7):
        x = cx - 62 + i * 20
        d.ellipse((x - 3, cy - 70 + (i % 2) * 5, x + 3, cy - 64 + (i % 2) * 5), fill=(255, 205, 90))


def _nft_capy(d, cx, cy, accent):
    """Капибара: округлое тело, квадратная морда, маленькие уши и спокойный взгляд."""
    fur = (158, 118, 80, 255)
    dark = (124, 88, 58, 255)
    d.ellipse((cx - 118, cy - 40, cx + 118, cy + 132), fill=fur)
    d.ellipse((cx - 86, cy - 120, cx + 86, cy + 46), fill=fur)
    for dx in (-58, 58):
        d.ellipse((cx + dx - 17, cy - 136, cx + dx + 17, cy - 102), fill=dark)
    d.ellipse((cx - 62, cy - 30, cx + 62, cy + 60), fill=(182, 142, 102, 255))
    d.ellipse((cx - 18, cy + 8, cx + 18, cy + 44), fill=(48, 32, 26, 255))
    for dx in (-38, 38):
        d.ellipse((cx + dx - 12, cy - 66, cx + dx + 12, cy - 42), fill=(28, 22, 20, 255))
        d.ellipse((cx + dx - 4, cy - 62, cx + dx + 2, cy - 54), fill=(255, 255, 255, 220))
    d.arc((cx - 24, cy + 30, cx + 24, cy + 62), 15, 165, fill=(48, 32, 26, 255), width=5)
    d.ellipse((cx - 116, cy + 112, cx - 46, cy + 146), fill=dark)
    d.ellipse((cx + 46, cy + 112, cx + 116, cy + 146), fill=dark)
    d.ellipse((cx - 126, cy + 26, cx - 92, cy + 92), fill=dark)
    d.ellipse((cx + 92, cy + 26, cx + 126, cy + 92), fill=dark)


def _nft_mammoth(d, cx, cy, accent):
    d.ellipse((cx - 112, cy - 42, cx + 78, cy + 104), fill=(150, 98, 62))
    d.ellipse((cx - 82, cy - 96, cx + 26, cy + 12), fill=(170, 112, 72))
    d.ellipse((cx - 104, cy - 70, cx - 52, cy + 20), fill=(132, 84, 54))
    d.ellipse((cx - 62, cy - 78, cx - 40, cy - 56), fill=(24, 30, 36))
    d.line((cx - 48, cy - 40, cx - 70, cy + 40, cx - 42, cy + 62), fill=(196, 142, 98), width=18)
    d.line((cx - 48, cy - 40, cx - 70, cy + 40, cx - 42, cy + 62), fill=(218, 166, 118), width=8)
    d.polygon([(cx - 54, cy + 20), (cx - 26, cy + 12), (cx - 44, cy + 62)], fill=(248, 238, 210))
    d.polygon([(cx - 30, cy + 14), (cx - 6, cy + 6), (cx - 24, cy + 58)], fill=(238, 228, 200))
    d.ellipse((cx - 30, cy + 58, cx - 10, cy + 76), fill=(90, 55, 40))
    d.ellipse((cx + 36, cy - 30, cx + 74, cy + 8), fill=(120, 72, 46))
    for y in (cy + 20, cy + 48):
        d.line((cx - 20, y, cx + 20, y), fill=(120, 72, 46), width=4)


def _nft_orange(d, cx, cy, accent):
    d.ellipse((cx - 92, cy - 84, cx + 92, cy + 100), fill=(255, 150, 50))
    d.ellipse((cx - 70, cy - 58, cx - 18, cy - 6), fill=(255, 190, 100, 130))
    d.ellipse((cx - 10, cy - 108, cx + 12, cy - 80), fill=(70, 170, 90))
    d.polygon([(cx + 2, cy - 90), (cx + 38, cy - 112), (cx + 30, cy - 78)], fill=(64, 160, 84))
    for x, y in ((cx - 34, cy + 6), (cx + 22, cy + 30), (cx - 4, cy + 58)):
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 210, 130))


def _nft_sock(d, cx, cy, accent):
    d.polygon([(cx - 46, cy - 92), (cx + 34, cy - 92), (cx + 34, cy + 42),
               (cx + 88, cy + 42), (cx + 88, cy + 92), (cx - 46, cy + 92)],
              fill=(215, 80, 90))
    d.rectangle((cx - 46, cy - 92, cx + 34, cy - 58), fill=(250, 245, 235))
    d.rectangle((cx - 46, cy + 58, cx + 88, cy + 92), fill=(250, 245, 235))
    d.ellipse((cx + 28, cy + 22, cx + 62, cy + 56), fill=(28, 32, 40))
    for i in range(3):
        d.line((cx - 30 + i * 22, cy - 30, cx - 30 + i * 22, cy + 40), fill=(255, 220, 220, 90), width=3)


def _nft_dumpling(d, cx, cy, accent):
    d.ellipse((cx - 96, cy - 52, cx + 96, cy + 92), fill=(245, 226, 185))
    for i in range(7):
        x = cx - 72 + i * 24
        d.arc((x - 14, cy - 62, x + 14, cy - 34), 200, 340, fill=(210, 170, 120), width=4)
    d.ellipse((cx - 42, cy - 12, cx - 22, cy + 8), fill=(80, 55, 40))
    d.ellipse((cx + 22, cy - 12, cx + 42, cy + 8), fill=(80, 55, 40))
    d.arc((cx - 22, cy + 18, cx + 22, cy + 46), 10, 170, fill=(160, 100, 70), width=4)


def _nft_bubble(d, cx, cy, accent):
    d.ellipse((cx - 102, cy - 20, cx + 54, cy + 110), fill=(120, 220, 255, 70))
    d.ellipse((cx + 6, cy - 78, cx + 98, cy + 14), fill=(255, 180, 240, 80))
    d.ellipse((cx - 74, cy - 98, cx - 4, cy - 28), fill=(180, 255, 210, 80))
    for x, y, r in ((cx - 40, cy + 40, 7), (cx + 50, cy - 32, 6), (cx - 10, cy - 60, 5),
                    (cx + 70, cy + 64, 4), (cx - 88, cy + 72, 4)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 180))


def _nft_salad(d, cx, cy, accent):
    d.ellipse((cx - 112, cy + 8, cx + 112, cy + 94), fill=(180, 220, 235))
    d.ellipse((cx - 100, cy - 10, cx + 100, cy + 70), fill=(80, 160, 90))
    for x, y, col in ((cx - 50, cy + 10, (220, 90, 80)), (cx + 10, cy - 2, (245, 220, 120)),
                      (cx + 50, cy + 20, (230, 160, 70)), (cx - 16, cy + 34, (240, 240, 220))):
        d.ellipse((x - 22, y - 18, x + 22, y + 18), fill=col)
    d.ellipse((cx - 104, cy + 52, cx + 104, cy + 102), fill=(190, 230, 245))


def _nft_dragon(d, cx, cy, accent):
    d.polygon([(cx - 88, cy + 18), (cx - 34, cy - 76), (cx + 34, cy - 76), (cx + 88, cy + 18),
               (cx + 54, cy + 94), (cx - 54, cy + 94)], fill=(70, 170, 120))
    d.polygon([(cx - 62, cy - 62), (cx - 92, cy - 130), (cx - 30, cy - 86)], fill=(60, 145, 100))
    d.polygon([(cx + 62, cy - 62), (cx + 92, cy - 130), (cx + 30, cy - 86)], fill=(60, 145, 100))
    d.ellipse((cx - 50, cy - 34, cx - 18, cy - 2), fill=(255, 230, 90))
    d.ellipse((cx + 18, cy - 34, cx + 50, cy - 2), fill=(255, 230, 90))
    d.ellipse((cx - 42, cy - 26, cx - 26, cy - 10), fill=(20, 30, 24))
    d.ellipse((cx + 26, cy - 26, cx + 42, cy - 10), fill=(20, 30, 24))
    d.arc((cx - 34, cy + 10, cx + 34, cy + 52), 10, 170, fill=(30, 80, 52), width=5)
    d.polygon([(cx - 12, cy + 60), (cx, cy + 78), (cx + 12, cy + 60)], fill=(255, 180, 80))


def _nft_unicorn(d, cx, cy, accent):
    d.ellipse((cx - 80, cy - 50, cx + 80, cy + 88), fill=(248, 236, 255))
    d.polygon([(cx - 32, cy - 120), (cx, cy - 60), (cx + 32, cy - 120)], fill=(255, 210, 100))
    d.line((cx, cy - 118, cx, cy - 150), fill=(255, 235, 160), width=4)
    d.polygon([(cx - 80, cy - 52), (cx - 100, cy - 122), (cx - 52, cy - 66)], fill=(240, 220, 255))
    d.polygon([(cx + 80, cy - 52), (cx + 100, cy - 122), (cx + 52, cy - 66)], fill=(240, 220, 255))
    d.ellipse((cx - 46, cy - 18, cx - 18, cy + 10), fill=(100, 80, 160))
    d.ellipse((cx + 18, cy - 18, cx + 46, cy + 10), fill=(100, 80, 160))
    d.ellipse((cx - 10, cy + 16, cx + 10, cy + 30), fill=(255, 160, 190))
    for i, col in enumerate(((255, 140, 200), (150, 220, 255), (255, 220, 120))):
        d.arc((cx - 70 + i * 12, cy - 70 + i * 10, cx + 10 + i * 12, cy + 20 + i * 10), 200, 340, fill=col, width=5)


def _nft_deer(d, cx, cy, accent):
    d.ellipse((cx - 72, cy - 40, cx + 72, cy + 80), fill=(160, 105, 65))
    d.ellipse((cx - 48, cy + 6, cx + 48, cy + 76), fill=(205, 150, 100))
    d.line((cx - 48, cy - 44, cx - 86, cy - 120), fill=(120, 80, 50), width=7)
    d.line((cx + 48, cy - 44, cx + 86, cy - 120), fill=(120, 80, 50), width=7)
    for sx in (-1, 1):
        x = cx + sx * 70
        d.line((x, cy - 90, x + sx * 26, cy - 120), fill=(120, 80, 50), width=5)
        d.line((x, cy - 70, x + sx * 22, cy - 74), fill=(120, 80, 50), width=5)
    d.ellipse((cx - 40, cy - 12, cx - 20, cy + 8), fill=(28, 28, 34))
    d.ellipse((cx + 20, cy - 12, cx + 40, cy + 8), fill=(28, 28, 34))
    d.ellipse((cx - 14, cy + 26, cx + 14, cy + 44), fill=(30, 30, 36))
    d.ellipse((cx - 5, cy + 50, cx + 5, cy + 60), fill=(255, 160, 150))


def _nft_kind(photo: str, title: str) -> str:
    t = str(title or "").lower()
    rules = [
        (("роликс",), "rollix"),
        (("капибар", "capy", "капик"), "capy"),
        (("gta", "вайс", "vice city"), "gta"),
        (("мамонт", "слон"), "mammoth"),
        (("кот", "котик", "кошка", "cat"), "cat"),
        (("снегов", "снеговик"), "snowman"),
        (("ёлка", "елка", "ель", "tree"), "tree"),
        (("подар", "gift", "бокс"), "gift"),
        (("снежин", "frost"), "snowflake"),
        (("дед мороз", "санта", "santa"), "santa"),
        (("олен", "deer"), "deer"),
        (("дракон", "dragon"), "dragon"),
        (("единорог", "unicorn"), "unicorn"),
        (("корон", "король", "crown"), "crown"),
        (("бокал", "шампан", "cocktail"), "cocktail"),
        (("косм", "галакт", "планет", "луна", "space"), "planet"),
        (("робот", "robot"), "robot"),
        (("медвед", "мишк", "bear"), "bear"),
        (("пингв", "penguin"), "penguin"),
        (("мандарин", "апельсин", "orange"), "orange"),
        (("носок", "sock"), "sock"),
        (("пельмен", "dumpling"), "dumpling"),
        (("пузыр", "bubble"), "bubble"),
        (("оливье", "салат", "salad"), "salad"),
        (("меч", "клинок", "sword"), "sword"),
    ]
    for keys, kind in rules:
        if any(k in t for k in keys):
            return kind
    p = str(photo or "")
    photo_rules = [
        (("🐱", "🐈", "😺"), "cat"), (("🎄", "🌲"), "tree"), (("🎁",), "gift"),
        (("⛄",), "snowman"), (("❄",), "snowflake"), (("🎅",), "santa"),
        (("🌌",), "planet"), (("🤖",), "robot"), (("🐻", "🧸"), "bear"),
        (("🐧",), "penguin"), (("🍊",), "orange"), (("🧦",), "sock"),
        (("🥟",), "dumpling"), (("🫧",), "bubble"), (("🥗",), "salad"),
        (("👑",), "crown"), (("🥂",), "cocktail"), (("🦌",), "deer"),
        (("🐲", "🐉"), "dragon"), (("🦄",), "unicorn"),
    ]
    for keys, kind in photo_rules:
        if any(k in p for k in keys):
            return kind
    return "blob"


def _nft_aura(d, model: str, cx: int, cy: int, accent, rnd):
    if model == "Неоновый":
        for rr in (118, 148):
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=accent + (110,), width=3)
    elif model in ("Космический", "Звёздный"):
        for _ in range(14):
            a = rnd.uniform(0, math.tau)
            rr = rnd.uniform(100, 160)
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.72
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 245, 220, 220))
    elif model in ("Зимний", "Снежный"):
        for _ in range(10):
            x, y = cx + rnd.randint(-150, 150), cy + rnd.randint(-130, 130)
            d.line((x - 7, y, x + 7, y), fill=(220, 245, 255, 130), width=2)
            d.line((x, y - 7, x, y + 7), fill=(220, 245, 255, 130), width=2)
    elif model == "Золотой":
        for ang in range(0, 360, 30):
            a = math.radians(ang)
            d.line((cx + math.cos(a) * 118, cy + math.sin(a) * 118,
                    cx + math.cos(a) * 154, cy + math.sin(a) * 154), fill=(255, 215, 110, 110), width=3)


def _nft_font(bold: bool, size: int):
    import glob as _g
    pats = ([str(NFT_DIR / 'fonts' / n) for n in ('DejaVuSans-Bold.ttf', 'Inter-Bold.ttf', 'Roboto-Bold.ttf')]
            if bold else
            [str(NFT_DIR / 'fonts' / n) for n in ('DejaVuSans.ttf', 'Inter-Regular.ttf', 'Roboto-Regular.ttf')])
    pats += (['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf'] if bold
             else ['C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf'])
    pats += ['/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''),
             '/usr/share/fonts/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''),
             '/usr/share/fonts/TTF/DejaVuSans%s.ttf' % ('-Bold' if bold else '')]
    pats += _g.glob('/usr/share/fonts/**/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), recursive=True)
    pats += _g.glob('/usr/local/share/fonts/**/*%s*.ttf' % ('Bold' if bold else 'Regular'), recursive=True)
    for p in pats:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _nft_center_text(d, w: int, y: int, text: str, font, fill):
    box = d.textbbox((0, 0), text, font=font)
    d.text(((w - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


def _nft_tile(d, x: int, y: int, s: int, alpha: int):
    """Полупрозрачный подарочный жетон на фоне, как на референсе."""
    d.rounded_rectangle((x - s, y - s * .75, x + s, y + s * .9), radius=max(3, s // 3),
                        fill=(255, 255, 255, alpha // 4), outline=(255, 255, 255, alpha), width=2)
    d.rectangle((x - s * .12, y - s * .75, x + s * .12, y + s * .9), fill=(255, 255, 255, alpha // 2))
    d.ellipse((x - s * .58, y - s * 1.15, x - s * .02, y - s * .62), outline=(255, 255, 255, alpha), width=2)
    d.ellipse((x + s * .02, y - s * 1.15, x + s * .58, y - s * .62), outline=(255, 255, 255, alpha), width=2)
    d.ellipse((x - s * .28, y - s * .05, x + s * .28, y + s * .42), outline=(255, 255, 255, alpha), width=2)


def _nft_bg_decor(d, background: str, rnd: random.Random, w: int, h: int, accent):
    bg = str(background)
    for _ in range(14):
        x = rnd.randrange(w)
        y = rnd.randrange(h)
        r = rnd.randint(30, 95)
        d.ellipse((x - r, y - r, x + r, y + r), fill=accent + (rnd.randint(7, 20),))

    if bg in ("Морозный", "Северное сияние"):
        for _ in range(30):
            x, y = rnd.randrange(w), rnd.randrange(h)
            rr = rnd.randint(3, 10)
            for ang in (0, 60, 120):
                a = math.radians(ang)
                dx, dy = math.cos(a) * rr, math.sin(a) * rr
                d.line((x - dx, y - dy, x + dx, y + dy), fill=(230, 248, 255, rnd.randint(35, 80)), width=1)
    elif bg in ("Звёздный", "Галактика"):
        for _ in range(42):
            x, y = rnd.randrange(w), rnd.randrange(h)
            rr = rnd.randint(3, 9)
            d.polygon(_nft_star_points(x, y, rr, max(1, rr * .35), 4, rnd.randint(0, 90)),
                      fill=(255, 245, 220, rnd.randint(50, 160)))
        for i in range(3):
            d.arc((-220 + i * 110, 20 + i * 28, w + 220 - i * 80, 310 + i * 18),
                  195, 345, fill=(255, 150, 240, 22), width=26)
    elif bg == "Праздничный":
        for _ in range(46):
            x, y = rnd.randrange(w), rnd.randrange(h)
            rr = rnd.randint(2, 6)
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 220, 120, rnd.randint(45, 120)))
        for _ in range(5):
            x, y = rnd.randrange(30, w - 30), rnd.randrange(20, 90)
            d.arc((x - 70, y - 30, x + 70, y + 45), 200, 340, fill=(255, 210, 120, 55), width=3)
    elif bg == "Северное сияние":
        for i in range(4):
            d.arc((-260 + i * 130, 15 + i * 22, w + 260 - i * 90, 300 + i * 24),
                  195, 345, fill=(110, 255, 210, 28), width=24)
    else:
        for row in range(-1, 6):
            for col in range(0, 8):
                x = 45 + col * 105 + (row % 2) * 52
                y = 42 + row * 92
                _nft_tile(d, x, y, 20, 25)

    d.polygon([(0, h), (int(w * .42), 0), (int(w * .70), 0), (int(w * .18), h)],
              fill=(255, 255, 255, 9))


def _nft_accessory(d, model: str, seed: int, cx: int, cy: int, accent):
    rnd = random.Random(seed * 131 + 7)
    m = str(model)
    if m == "Зимний":
        d.rounded_rectangle((cx - 58, cy - 148, cx + 58, cy - 102), radius=26, fill=(198, 48, 72))
        d.rectangle((cx - 58, cy - 114, cx + 58, cy - 96), fill=(246, 250, 255))
        d.ellipse((cx - 12, cy - 174, cx + 12, cy - 150), fill=(246, 250, 255))
    elif m == "Снежный":
        d.arc((cx - 96, cy - 122, cx + 96, cy + 30), 198, 342, fill=(225, 245, 255, 190), width=8)
        for x in (cx - 90, cx + 90):
            d.ellipse((x - 24, cy - 88, x + 24, cy - 40), fill=(238, 248, 255))
            d.ellipse((x - 12, cy - 76, x + 12, cy - 52), fill=(170, 210, 240))
    elif m == "Золотой":
        d.polygon([(cx - 58, cy - 118), (cx - 42, cy - 166), (cx - 12, cy - 132),
                   (cx, cy - 178), (cx + 12, cy - 132), (cx + 42, cy - 166), (cx + 58, cy - 118)],
                  fill=(255, 211, 84))
        d.rectangle((cx - 58, cy - 120, cx + 58, cy - 102), fill=(225, 164, 45))
        for x, col in ((cx - 30, (255, 80, 110)), (cx, (80, 205, 255)), (cx + 30, (110, 240, 150))):
            d.ellipse((x - 7, cy - 116, x + 7, cy - 102), fill=col)
    elif m == "Неоновый":
        for dx in (-36, 36):
            d.rounded_rectangle((cx + dx - 33, cy - 70, cx + dx + 33, cy + 8), radius=18,
                                outline=accent + (235,), width=4)
        d.line((cx - 10, cy - 34, cx + 10, cy - 34), fill=accent + (235,), width=4)
    elif m == "Призрачный":
        d.ellipse((cx - 62, cy - 166, cx + 62, cy - 132), outline=(255, 255, 255, 185), width=7)
        d.arc((cx - 62, cy - 166, cx + 62, cy - 132), 200, 340, fill=accent + (120,), width=3)
    elif m == "Космический":
        d.ellipse((cx - 88, cy - 105, cx + 88, cy + 82), outline=(180, 220, 255, 120), width=5)
        d.line((cx, cy - 105, cx, cy - 138), fill=(210, 235, 255, 180), width=4)
        d.ellipse((cx - 8, cy - 148, cx + 8, cy - 132), fill=(255, 190, 90))
    else:
        d.rounded_rectangle((cx - 60, cy + 70, cx + 60, cy + 102), radius=10, fill=(212, 76, 92))
        d.rectangle((cx + 28, cy + 92, cx + 48, cy + 146), fill=(212, 76, 92))
    d.polygon(_nft_star_points(cx + rnd.randint(52, 76), cy - rnd.randint(34, 62), 11, 4), fill=accent + (220,))


ROLLIX_WATCH_ASSET = Path(__file__).with_name("rollix-watch-base.jpg")
_ROLLIX_BASE_CACHE = None


def _rollix_base_image():
    global _ROLLIX_BASE_CACHE
    if _ROLLIX_BASE_CACHE is None:
        try:
            _ROLLIX_BASE_CACHE = Image.open(ROLLIX_WATCH_ASSET).convert("RGB")
        except Exception:
            _ROLLIX_BASE_CACHE = False
    return _ROLLIX_BASE_CACHE or None


def _nft_gradient(w: int, h: int, top, bottom):
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
    return strip.resize((w, h), Image.BILINEAR)


def _nft_spark(d, x, y, r, color, alpha=220):
    d.line((x - r, y, x + r, y), fill=color + (alpha,), width=2)
    d.line((x, y - r, x, y + r), fill=color + (alpha,), width=2)
    d.line((x - r // 2, y - r // 2, x + r // 2, y + r // 2), fill=color + (alpha // 2,), width=1)
    d.line((x - r // 2, y + r // 2, x + r // 2, y - r // 2), fill=color + (alpha // 2,), width=1)


def _nft_premium_bg(w: int, h: int, accent, rarity: str, seed: int):
    """Чёрный студийный фон: мягкий свет, дымка, боке, блик на полу, зерно."""
    rnd = random.Random(seed ^ 0x5EEDBEEF)
    top = (4 + accent[0] // 42, 4 + accent[1] // 42, 6 + accent[2] // 38)
    im = _nft_gradient(w, h, top, (0, 0, 0)).convert("RGBA")

    haze = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(haze, "RGBA")
    for _ in range(8):
        cx, cy = rnd.randint(-120, w + 120), rnd.randint(-80, int(h * .72))
        rx, ry = rnd.randint(160, 430), rnd.randint(120, 310)
        hd.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=accent + (rnd.randint(3, 9),))
    haze = haze.filter(ImageFilter.GaussianBlur(90))
    im = Image.alpha_composite(im, haze)

    key = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    kd = ImageDraw.Draw(key, "RGBA")
    cx, cy = w // 2, int(h * .40)
    for rr, aa in ((470, 26), (330, 38), (215, 52), (140, 66)):
        kd.ellipse((cx - rr, cy - int(rr * .6), cx + rr, cy + int(rr * .6)),
                   fill=(255, 246, 228, aa))
    key = key.filter(ImageFilter.GaussianBlur(80))
    im = Image.alpha_composite(im, key)

    bokeh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh, "RGBA")
    for _ in range(13):
        r = rnd.randint(8, 38)
        x, y = rnd.randrange(w), rnd.randrange(int(h * .06), int(h * .68))
        col = rnd.choice((accent, (255, 242, 214), (150, 185, 255), (255, 255, 255)))
        a = rnd.randint(10, 28)
        bd.ellipse((x - r, y - r, x + r, y + r), fill=col + (a // 3,), outline=col + (a,),
                   width=max(1, r // 9))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(5))
    im = Image.alpha_composite(im, bokeh)

    floor = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(floor, "RGBA")
    fy = int(h * .80)
    for rr, aa in ((250, 18), (170, 26), (100, 34)):
        fd.ellipse((cx - rr, fy - rr // 5, cx + rr, fy + rr // 5), fill=accent + (aa,))
    fd.rectangle((0, fy, w, h), fill=(0, 0, 0, 140))
    floor = floor.filter(ImageFilter.GaussianBlur(45))
    im = Image.alpha_composite(im, floor)

    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim, "RGBA")
    top_y = int(h * .82)
    span = max(1, h - top_y)
    for i in range(span):
        sd.line((0, top_y + i, w, top_y + i), fill=(0, 0, 0, int(175 * (i / span) ** 1.25)))
    im = Image.alpha_composite(im, scrim)

    beam = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    be = ImageDraw.Draw(beam, "RGBA")
    be.polygon([(int(w * .12), 0), (int(w * .30), 0), (int(w * .58), h), (int(w * .40), h)],
               fill=(255, 255, 255, 5))
    beam = beam.filter(ImageFilter.GaussianBlur(22))
    im = Image.alpha_composite(im, beam)

    mask = Image.radial_gradient("L").resize((w, h), Image.BILINEAR)
    alpha = mask.point(lambda v: int((v / 255) ** 1.9 * 238))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    black.putalpha(alpha)
    im = Image.alpha_composite(im, black)

    try:
        noise = Image.effect_noise((w, h), 9).convert("L")
        grain = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        grain.putalpha(noise.point(lambda v: int(v * .038)))
        im = Image.alpha_composite(im, grain)
    except Exception:
        pass
    return im


def _nft_diamond(d, cx: int, cy: int, r: int, color=(255, 255, 255)):
    d.polygon([(cx, cy - r), (cx + r, cy - r // 4), (cx, cy + r), (cx - r, cy - r // 4)],
              fill=color + (235,))
    d.line((cx - r, cy - r // 4, cx + r, cy - r // 4), fill=(20, 20, 26, 190), width=2)
    d.line((cx, cy - r, cx, cy + r), fill=(20, 20, 26, 150), width=2)
    d.polygon([(cx - r, cy - r // 4), (cx, cy - r), (cx, cy + r)], fill=(255, 255, 255, 40))


def _nft_pill(d, x: int, y: int, text: str, font, icon: bool = False, right: bool = False):
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    padx, pady = 22, 11
    iw = 30 if icon else 0
    pw = tw + padx * 2 + iw
    ph = th + pady * 2
    if right:
        x -= pw
    d.rounded_rectangle((x, y, x + pw, y + ph), radius=ph // 2, fill=(0, 0, 0, 155),
                        outline=(255, 255, 255, 42), width=2)
    tx = x + padx
    if icon:
        _nft_diamond(d, tx + 9, y + ph // 2, 10)
        tx += iw
    d.text((tx, y + (ph - th) / 2 - box[1]), text, font=font, fill=(255, 255, 255, 238))
    return pw


def _nft_top_pills(im, seed: int):
    w = im.width
    d = ImageDraw.Draw(im, "RGBA")
    f = _nft_font(True, 25)
    _nft_pill(d, 34, 30, "RUBIN", f, icon=True)
    _nft_pill(d, w - 34, 30, f"#{seed}", f, right=True)


def _nft_bottom_labels(im, title: str, rarity: str, model: str, accent, big: bool = False,
                       background: str = "", level: int = 1):
    w, h = im.size
    d = ImageDraw.Draw(im, "RGBA")
    f1 = _nft_font(True, 34 if big else 27)
    f2 = _nft_font(False, 14)
    name = (title or "NFT").upper()[:26]
    d.text((38, h - 100), name, font=f1, fill=(255, 255, 255, 235))
    pct_m = next((int(round(w)) for nm, _, w in MODELS if nm == model), 0)
    if int(level or 1) <= 1:
        sub = f"{model or 'Стандартный'} · без редкости"
    else:
        sub = f"{RARITY_NAME.get(str(rarity), str(rarity).title())} · {model or 'Стандартный'}"
    sub += f" {pct_m}%" if pct_m else ""
    if background:
        bg = bg_label(background)
        pct_b = next((int(round(x)) for nm, _, x in BGS if nm == bg), 0)
        if pct_b:
            sub += f" · {bg} {pct_b}%"
    d.text((40, h - 62), sub, font=f2, fill=(255, 255, 255, 155))
    d.text((w - 40 - d.textlength("RUBIN NFT", font=f2), h - 62), "RUBIN NFT", font=f2,
           fill=accent + (200,))


def _nft_frame(im, rarity: str):
    w, h = im.size
    d = ImageDraw.Draw(im, "RGBA")
    rc = NFT_RARITY_COLOR.get(str(rarity), NFT_RARITY_COLOR["common"])
    d.rounded_rectangle((14, 14, w - 14, h - 14), radius=34, outline=rc + (150,), width=3)
    d.rounded_rectangle((22, 22, w - 22, h - 22), radius=28, outline=(255, 255, 255, 26), width=1)
    for x, y, sx, sy in ((38, 38, 1, 1), (w - 38, 38, -1, 1), (38, h - 38, 1, -1), (w - 38, h - 38, -1, -1)):
        d.line((x, y, x + sx * 26, y), fill=rc + (190,), width=3)
        d.line((x, y, x, y + sy * 26), fill=rc + (190,), width=3)


NFT_ART_DIR = Path(__file__).with_name("nft_art")
_AI_ART = {}


def _cut_bg(im):
    """Убирает тёмный фон по контуру (flood fill от краёв)."""
    from collections import deque
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    q = deque()

    def is_bg(x, y):
        r, g, b, a = px[x, y]
        hi, lo = max(r, g, b), min(r, g, b)
        return hi < 92 and (hi - lo) < 18

    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and is_bg(x, y):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and is_bg(x, y):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        r, g, b, a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and is_bg(nx, ny):
                seen[ny * w + nx] = 1
                q.append((nx, ny))
    im.thumbnail((760, 760), Image.LANCZOS)
    return im


def _ai_art():
    """Внешний арт (GigaChat/Kandinsky) с готовым фоном, случайный из набора."""
    if "imgs" in _AI_ART:
        return _AI_ART["imgs"][0] if _AI_ART["imgs"] else None
    imgs = []
    for path in []:
        try:
            im = Image.open(path).convert("RGBA")
            im.thumbnail((1000, 1000), Image.LANCZOS)
            imgs.append(im)
        except Exception:
            log.exception("ai art %s", path.name)
    _AI_ART["imgs"] = imgs
    return imgs[0] if imgs else None


def _nft_capy_card(seed: int, title: str, rarity: str, model: str = "") -> bytes:
    """Капибара — рисуется кодом."""
    w, h = 1200, 780
    im = Image.new("RGB", (w, h), (238, 231, 214))
    d = ImageDraw.Draw(im, "RGBA")
    for gy in range(40, h, 96):
        for gx in range(40, w, 96):
            d.ellipse((gx - 7, gy - 3, gx + 7, gy + 11), fill=(206, 190, 160, 80))
    d.ellipse((w // 2 - 210, h - 150, w // 2 + 210, h - 100), fill=(196, 176, 146, 110))
    cx, cy = w // 2, h // 2 + 30
    fur = (162, 122, 86, 255)
    dark = (132, 96, 64, 255)
    # тело и голова капибары: тяжёлая нижняя часть и прямоугольная морда
    d.ellipse((cx - 196, cy - 30, cx + 196, cy + 158), fill=fur)
    d.rounded_rectangle((cx - 142, cy - 202, cx + 142, cy + 34), radius=68, fill=fur)
    for dx in (-104, 104):
        d.ellipse((cx + dx - 26, cy - 214, cx + dx + 26, cy - 158), fill=dark)
    d.rounded_rectangle((cx - 78, cy - 78, cx + 78, cy + 40), radius=34, fill=(184, 144, 106, 255))
    for dx in (-22, 22):
        d.ellipse((cx + dx - 8, cy - 14, cx + dx + 8, cy + 4), fill=(52, 34, 28, 255))
    d.arc((cx - 30, cy + 8, cx + 30, cy + 44), 15, 165, fill=(52, 34, 28, 255), width=5)
    for dx in (-76, 76):
        d.ellipse((cx + dx - 17, cy - 122, cx + dx + 17, cy - 88), fill=(28, 22, 18, 255))
        d.ellipse((cx + dx - 5, cy - 116, cx + dx + 3, cy - 106), fill=(255, 255, 255, 225))
    # листик на голове
    d.ellipse((cx + 54, cy - 244, cx + 92, cy - 218), fill=(96, 170, 104, 255))
    d.line((cx + 70, cy - 224, cx + 96, cy - 246), fill=(60, 132, 76, 255), width=4)
    d.ellipse((cx - 170, cy + 132, cx - 46, cy + 170), fill=dark)
    d.ellipse((cx + 46, cy + 132, cx + 170, cy + 170), fill=dark)
    d.text((34, h - 34), (model or "Стандартный")[:24], font=_nft_font(False, 24),
           fill=(120, 104, 84, 210), anchor="lb")
    d.text((w - 34, h - 34), f"#{seed}", font=_nft_font(False, 26), fill=(120, 104, 84, 220), anchor="rb")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_snow_card(seed: int, title: str, rarity: str, model: str = "") -> bytes:
    """Снеговик — новогодняя карточка кодом."""
    w, h = 1200, 780
    im = Image.new("RGB", (w, h), (16, 26, 44))
    d = ImageDraw.Draw(im, "RGBA")
    import random as _rnd
    rr = _rnd.Random(seed)
    for _ in range(120):
        x, y = rr.randrange(w), rr.randrange(h)
        d.ellipse((x, y, x + 4, y + 4), fill=(255, 255, 255, rr.randint(40, 140)))
    d.ellipse((w // 2 - 220, h - 130, w // 2 + 220, h - 90), fill=(255, 255, 255, 30))
    cx, cy = w // 2, h // 2 + 40
    d.ellipse((cx - 130, cy - 20, cx + 130, cy + 200), fill=(246, 250, 255, 255))
    d.ellipse((cx - 100, cy - 130, cx + 100, cy + 60), fill=(250, 252, 255, 255))
    d.ellipse((cx - 72, cy - 230, cx + 72, cy - 100), fill=(252, 253, 255, 255))
    for dx in (-26, 26):
        d.ellipse((cx + dx - 8, cy - 190, cx + dx + 8, cy - 174), fill=(30, 34, 48, 255))
    d.polygon([(cx, cy - 170), (cx + 54, cy - 150), (cx, cy - 138)], fill=(255, 152, 64, 255))
    d.rectangle((cx - 74, cy - 262, cx + 74, cy - 226), fill=(200, 34, 54))
    d.rectangle((cx - 100, cy - 232, cx + 100, cy - 214), fill=(228, 44, 66))
    d.ellipse((cx - 96, cy - 30, cx + 96, cy + 30), fill=(200, 34, 54))
    d.ellipse((cx - 40, cy + 30, cx - 8, cy + 56), fill=(40, 44, 60, 255))
    d.ellipse((cx + 8, cy + 30, cx + 40, cy + 56), fill=(40, 44, 60, 255))
    for i, yy in enumerate((cy + 100, cy + 140, cy + 180)):
        d.ellipse((cx - 8, yy, cx + 8, yy + 16), fill=(60, 66, 84, 255))
    d.text((34, h - 34), (model or "Стандартный")[:24], font=_nft_font(False, 24),
           fill=(220, 230, 245, 220), anchor="lb")
    d.text((w - 34, h - 34), f"#{seed}", font=_nft_font(False, 26), fill=(220, 230, 245, 235), anchor="rb")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_vice_card(seed: int, title: str, rarity: str, model: str = "") -> bytes:
    """Неоновая вайс-карточка с римской VI: закат, пальмы, сетка. Рисуется кодом."""
    w, h = 1200, 780
    im = Image.new("RGB", (w, h), (24, 8, 40))
    d = ImageDraw.Draw(im)
    top = (46, 10, 72)
    mid = (196, 44, 120)
    bot = (255, 156, 80)
    for y in range(h):
        k = y / h
        if k < 0.55:
            t = k / 0.55
            col = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
        else:
            t = (k - 0.55) / 0.45
            col = tuple(int(mid[i] + (bot[i] - mid[i]) * t) for i in range(3))
        d.line((0, y, w, y), fill=col)

    # солнце с полосами
    cx, cy, r = w // 2, int(h * 0.46), 210
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 214, 130))
    for i in range(7):
        yy = cy + 20 + i * 26
        d.rectangle((cx - r, yy, cx + r, yy + 10), fill=(255, 138, 96))

    # пальмы
    def palm(px, flip=1):
        d.line((px, h - 40, px + 18 * flip, h - 250), fill=(38, 12, 46), width=14)
        lx, ly = px + 18 * flip, h - 250
        for dx, dy in ((-70, -34), (-46, -70), (0, -84), (46, -70), (70, -34)):
            d.line((lx, ly, lx + dx * flip, ly + dy), fill=(28, 8, 36), width=16)
            d.ellipse((lx + dx * flip - 26, ly + dy - 16, lx + dx * flip + 26, ly + dy + 16),
                      fill=(28, 8, 36))

    palm(120, 1)
    palm(w - 120, -1)

    # неоновая сетка
    d.line((0, h - 120, w, h - 120), fill=(255, 90, 200), width=4)
    for i in range(0, w + 1, 120):
        d.line((w // 2, h - 120, i, h), fill=(255, 120, 210), width=2)
    for i in range(1, 5):
        yy = h - 120 + int((h - (h - 120)) * (i / 5) ** 1.6)
        d.line((0, yy, w, yy), fill=(255, 120, 210), width=2)

    # VI
    f = _nft_font(True, 300)
    txt = "VI"
    tw = d.textlength(txt, font=f)
    tx, ty = (w - tw) / 2, h * 0.16
    for ox, oy in ((-8, 0), (8, 0), (0, -8), (0, 8)):
        d.text((tx + ox, ty + oy), txt, font=f, fill=(70, 10, 60))
    d.text((tx, ty), txt, font=f, fill=(255, 255, 255))

    d.text((34, h - 34), (model or "Vice")[:24], font=_nft_font(False, 24), fill=(255, 240, 250, 230), anchor="lb")
    d.text((w - 34, h - 34), f"#{seed}", font=_nft_font(False, 26), fill=(255, 240, 250, 235), anchor="rb")

    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


GTA_LOGO_ASSET = Path(__file__).with_name("gta6_logo.jpg")
_GTA_LOGO_CACHE = None


def _gta_logo():
    """Логотип GTA 6 без белого фона по краям (внутренний белый остаётся)."""
    global _GTA_LOGO_CACHE
    if _GTA_LOGO_CACHE is not None:
        return _GTA_LOGO_CACHE or None
    try:
        from collections import deque
        im = Image.open(GTA_LOGO_ASSET).convert("RGBA")
        w, h = im.size
        px = im.load()
        seen = bytearray(w * h)
        qq = deque()

        def white(x, y):
            r, g, b, a = px[x, y]
            return a > 0 and min(r, g, b) > 224 and max(r, g, b) - min(r, g, b) < 26

        for x in range(w):
            for y in (0, h - 1):
                if not seen[y * w + x] and white(x, y):
                    seen[y * w + x] = 1
                    qq.append((x, y))
        for y in range(h):
            for x in (0, w - 1):
                if not seen[y * w + x] and white(x, y):
                    seen[y * w + x] = 1
                    qq.append((x, y))
        while qq:
            x, y = qq.popleft()
            px[x, y] = (255, 255, 255, 0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and white(nx, ny):
                    seen[ny * w + nx] = 1
                    qq.append((nx, ny))
        box = im.getbbox()
        if box:
            im = im.crop(box)
        im.thumbnail((560, 560), Image.LANCZOS)
        _GTA_LOGO_CACHE = im
    except Exception:
        log.exception("gta logo")
        _GTA_LOGO_CACHE = False
    return _GTA_LOGO_CACHE or None


def _nft_gta_card(seed: int, title: str, rarity: str, model: str = "") -> bytes:
    """GTA 6: закат Vice City, пальмы, неоновая сетка и официальный знак VI."""
    w, h = 1200, 780
    im = Image.new("RGB", (w, h), (24, 8, 40))
    d = ImageDraw.Draw(im)
    top, mid, bot = (38, 8, 64), (188, 38, 120), (255, 158, 82)
    for y in range(h):
        k = y / h
        if k < 0.56:
            t = k / 0.56
            col = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
        else:
            t = (k - 0.56) / 0.44
            col = tuple(int(mid[i] + (bot[i] - mid[i]) * t) for i in range(3))
        d.line((0, y, w, y), fill=col)
    cx, cy, r = w // 2, int(h * 0.42), 230
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 218, 145))
    for i in range(8):
        yy = cy + 12 + i * 27
        d.rectangle((cx - r, yy, cx + r, yy + 11), fill=(255, 132, 96))
    for px, flip in ((110, 1), (w - 110, -1)):
        d.line((px, h - 30, px + 22 * flip, h - 270), fill=(30, 8, 38), width=15)
        lx, ly = px + 22 * flip, h - 270
        for dx, dy in ((-76, -36), (-50, -76), (0, -92), (50, -76), (76, -36)):
            d.line((lx, ly, lx + dx * flip, ly + dy), fill=(22, 6, 30), width=17)
            d.ellipse((lx + dx * flip - 28, ly + dy - 17, lx + dx * flip + 28, ly + dy + 17),
                      fill=(22, 6, 30))
    d.line((0, h - 120, w, h - 120), fill=(255, 84, 202), width=4)
    for i in range(0, w + 1, 120):
        d.line((w // 2, h - 120, i, h), fill=(255, 120, 214), width=2)
    for i in range(1, 5):
        yy = h - 120 + int(120 * (i / 5) ** 1.6)
        d.line((0, yy, w, yy), fill=(255, 120, 214), width=2)
    logo = _gta_logo()
    if logo is not None:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        halo = Image.new("RGBA", logo.size, (255, 120, 220, 255))
        halo.putalpha(logo.split()[3].filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * .85)))
        glow.alpha_composite(halo, ((w - logo.width) // 2, (h - logo.height) // 2 - 16))
        im = Image.alpha_composite(im.convert("RGBA"), glow)
        im.alpha_composite(logo, ((w - logo.width) // 2, (h - logo.height) // 2 - 16))
        d = ImageDraw.Draw(im, "RGBA")
    else:
        f = _nft_font(True, 300)
        txt = "VI"
        tw = d.textlength(txt, font=f)
        d.text(((w - tw) / 2, h * 0.16), txt, font=f, fill=(255, 255, 255))
    d.text((34, h - 34), (model or "Vice City")[:24], font=_nft_font(False, 24),
           fill=(255, 244, 250, 235), anchor="lb")
    d.text((w - 34, h - 34), f"#{seed}", font=_nft_font(False, 26), fill=(255, 244, 250, 240), anchor="rb")
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_penguin_card(seed: int, title: str, rarity: str, model: str = "") -> bytes:
    """Пингвин с ножом — рисуется кодом, без внешних файлов."""
    w, h = 1200, 780
    im = Image.new("RGB", (w, h), (238, 227, 206))
    d = ImageDraw.Draw(im, "RGBA")
    # узор на фоне
    for gy in range(40, h, 96):
        for gx in range(40, w, 96):
            d.ellipse((gx - 7, gy - 3, gx + 7, gy + 11), fill=(206, 188, 158, 90))
            d.polygon([(gx - 5, gy + 4), (gx + 5, gy + 4), (gx, gy + 14)], fill=(206, 188, 158, 90))
    # тень
    d.ellipse((w // 2 - 190, h - 150, w // 2 + 190, h - 96), fill=(196, 176, 146, 110))

    cx, cy = w // 2, h // 2 + 20
    body = (44, 78, 150, 255)
    dark = (30, 56, 116, 255)
    # тело
    d.ellipse((cx - 150, cy - 150, cx + 150, cy + 170), fill=body)
    # живот
    d.ellipse((cx - 96, cy - 70, cx + 96, cy + 160), fill=(168, 206, 240, 255))
    d.ellipse((cx - 80, cy - 40, cx + 80, cy + 150), fill=(232, 244, 255, 255))
    # ласты
    d.ellipse((cx - 176, cy - 40, cx - 116, cy + 90), fill=dark)
    d.ellipse((cx + 116, cy - 40, cx + 176, cy + 60), fill=dark)
    # глаза
    for dx in (-46, 46):
        d.ellipse((cx + dx - 34, cy - 96, cx + dx + 34, cy - 26), fill=(255, 255, 255, 255))
        d.ellipse((cx + dx - 16, cy - 80, cx + dx + 16, cy - 42), fill=(20, 26, 40, 255))
        d.ellipse((cx + dx - 8, cy - 74, cx + dx + 2, cy - 60), fill=(255, 255, 255, 240))
    # клюв
    d.ellipse((cx - 26, cy - 34, cx + 26, cy + 6), fill=(240, 160, 70, 255))
    d.arc((cx - 26, cy - 26, cx + 26, cy + 12), 20, 160, fill=(190, 112, 40, 255), width=4)
    # лапы
    d.ellipse((cx - 78, cy + 150, cx - 18, cy + 182), fill=(240, 160, 70, 255))
    d.ellipse((cx + 18, cy + 150, cx + 78, cy + 182), fill=(240, 160, 70, 255))
    # нож в правой ласте
    kx, ky = cx + 120, cy + 10
    d.rounded_rectangle((kx - 4, ky - 6, kx + 56, ky + 12), 6, fill=(214, 222, 232, 255))
    d.polygon([(kx + 56, ky - 6), (kx + 78, ky + 3), (kx + 56, ky + 12)], fill=(228, 236, 246, 255))
    d.rounded_rectangle((kx - 24, ky - 2, kx - 2, ky + 8), 4, fill=(34, 34, 40, 255))
    # модель и номер
    name = (model or "Стандартный")[:24]
    d.text((34, h - 34), name, font=_nft_font(False, 24),
           fill=(120, 104, 84, 210), anchor="lb")
    d.text((w - 34, h - 34), f"#{seed}", font=_nft_font(False, 26),
           fill=(120, 104, 84, 220), anchor="rb")

    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_ai_card(seed: int, title: str, rarity: str, art: "Image.Image") -> bytes:
    """Лежачая карточка 3:2: арт по центру, размытый фон по бокам, номер сверху."""
    w, h = 1200, 800
    a = art.convert("RGB")

    bg = a.copy()
    scale = max(w / bg.width, h / bg.height)
    bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2,
                  (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
    bg = bg.filter(ImageFilter.GaussianBlur(26))
    bg = ImageEnhance.Brightness(bg).enhance(0.42)

    fh = h
    fw = int(a.width * (fh / a.height))
    fg = a.resize((fw, fh), Image.LANCZOS)
    canvas = bg.convert("RGBA")
    canvas.alpha_composite(fg.convert("RGBA"), ((w - fw) // 2, 0))

    d = ImageDraw.Draw(canvas, "RGBA")
    d.rounded_rectangle((w - 210, 26, w - 26, 78), 18, fill=(0, 0, 0, 120))
    d.text((w - 118, 52), f"#{seed}", font=_nft_font(True, 30),
           fill=(255, 255, 255, 235), anchor="mm")

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_character_card(seed: int, title: str, photo: str, model: str,
                        background: str, rarity: str, level: int) -> bytes:
    if photo != "photo":
        ai = _ai_art()
        if ai is not None:
            return _nft_ai_card(seed, title, rarity, ai)
        low = (title or "").lower()
        if any(k in low for k in ("gta", "vice", "вайс")):
            return _nft_vice_card(seed, title, rarity, model)
        if any(k in low for k in ("капибар", "capy", "капик")):
            return _nft_capy_card(seed, title, rarity, model)
        if any(k in low for k in ("снег", "нов", "зим", "ёлк", "елк", "холод", "санта", "подар")):
            return _nft_snow_card(seed, title, rarity, model)
        return _nft_penguin_card(seed, title, rarity, model)
    w, h = 1280, 720
    v = nft_variant(seed)
    accent = NFT_MODEL_ACCENT.get(str(model), v["accent"])
    im = _nft_gradient(w, h, v["top"], v["mid"]).convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov, "RGBA")
    for rr, aa in ((520, 12), (400, 16), (300, 22), (200, 30)):
        do.ellipse((w // 2 - rr, h // 2 - rr, w // 2 + rr, h // 2 + rr), fill=accent + (aa,))
    rnd = random.Random(seed * 7919 + 3)
    _nft_bg_decor(do, v["background"], rnd, w, h, accent)
    im = Image.alpha_composite(im, ov)
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((w // 2 - 330, h - 180, w // 2 + 330, h + 60), fill=(0, 0, 0, 90))
    d.ellipse((w // 2 - 250, h - 170, w // 2 + 250, h - 40), fill=accent + (18,))

    small = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
    cd = ImageDraw.Draw(small, "RGBA")
    cd.ellipse((88, 346, 332, 402), fill=(0, 0, 0, 90))
    kind = _nft_kind(photo, title)
    models = {
        "tree": _nft_tree, "gift": _nft_gift, "snowman": _nft_snowman,
        "snowflake": _nft_snowflake, "santa": _nft_santa, "planet": _nft_planet,
        "robot": _nft_robot, "bear": _nft_bear, "penguin": _nft_penguin,
        "crown": _nft_crown, "cocktail": _nft_cocktail, "blob": _nft_blob,
        "cat": _nft_cat, "capy": _nft_capy, "mammoth": _nft_mammoth, "orange": _nft_orange,
        "sock": _nft_sock, "dumpling": _nft_dumpling, "bubble": _nft_bubble,
        "salad": _nft_salad, "dragon": _nft_dragon, "unicorn": _nft_unicorn,
        "deer": _nft_deer, "rollix": _nft_rollix,
    }
    ai = _ai_art()
    if ai is not None:
        char = ai.copy()
        if char.size != (760, 760):
            canvas = Image.new("RGBA", (760, 760), (0, 0, 0, 0))
            canvas.alpha_composite(char, ((760 - char.width) // 2, (760 - char.height) // 2))
            char = canvas
    else:
        models.get(kind, _nft_blob)(cd, 210, 195, accent)
        _nft_accessory(cd, str(model), seed, 210, 195, accent)
        char = small.resize((760, 760), Image.LANCZOS)

    # Объём: мягкий блик от центра, контровой свет и затемнение снизу.
    alpha0 = char.split()[3]
    light = Image.radial_gradient("L").resize((760, 760))
    light = light.point(lambda v: int((255 - v) * .16))
    hl = Image.new("RGBA", (760, 760), (255, 255, 255, 0))
    hl.putalpha(ImageChops.multiply(light, alpha0))
    char = Image.alpha_composite(char, hl)
    rim_a = ImageChops.subtract(alpha0, ImageChops.offset(alpha0, 4, 4))
    rim_a = rim_a.filter(ImageFilter.GaussianBlur(1)).point(lambda v: int(v * .75))
    rim = Image.new("RGBA", (760, 760), (255, 255, 255, 255))
    rim.putalpha(rim_a)
    char = Image.alpha_composite(char, rim)
    shade = Image.linear_gradient("L").resize((760, 760)).point(lambda v: int(v * .24))
    sh = Image.new("RGBA", (760, 760), (0, 0, 0, 255))
    sh.putalpha(ImageChops.multiply(shade, alpha0))
    char = Image.alpha_composite(char, sh)

    alpha = char.split()[3]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (760, 760), (0, 0, 0, 255))
    sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * .62)))
    shadow.alpha_composite(sh, (w // 2 - 380, 22))
    im = Image.alpha_composite(im, shadow)

    glow = Image.new("RGBA", (760, 760), accent + (255,))
    glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * .50)))
    gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl.alpha_composite(glow, (w // 2 - 380, 0))
    im = Image.alpha_composite(im, gl)
    im.alpha_composite(char, (w // 2 - 380, 0))

    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(seed * 7919 + 17)
    for _ in range(20):
        _nft_spark(d, rnd.randrange(50, w - 50), rnd.randrange(110, h - 130),
                   rnd.randint(2, 7), (255, 246, 220), rnd.randint(40, 130))

    _nft_top_pills(im, seed)
    _nft_bottom_labels(im, title, rarity, model, accent, background=background, level=level)
    _nft_frame(im, rarity)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


NFT_MODEL_PALETTE = {
    "Стандартный": ((24, 26, 38), (52, 58, 84), (196, 206, 232)),
    "Зимний": ((8, 20, 38), (22, 64, 96), (168, 232, 255)),
    "Снежный": ((14, 18, 34), (56, 84, 120), (236, 248, 255)),
    "Золотой": ((26, 16, 8), (92, 62, 18), (255, 214, 120)),
    "Неоновый": ((18, 6, 30), (86, 18, 96), (255, 120, 232)),
    "Призрачный": ((16, 14, 30), (58, 48, 92), (206, 192, 255)),
    "Космический": ((8, 6, 26), (48, 16, 88), (255, 140, 230)),
}

# Палитры уникальны для каждого NFT: выбираются детерминированно по номеру,
# поэтому карточка на сервере и картинка в вебке всегда совпадают.
NFT_BG_PALETTES = {
    "Обычный": ((28, 20, 52), (86, 48, 140), (232, 200, 255)),
    "Морозный": ((6, 16, 34), (18, 62, 88), (140, 232, 255)),
    "Праздничный": ((34, 8, 22), (104, 20, 48), (255, 176, 96)),
    "Звёздный": ((10, 8, 34), (46, 22, 92), (196, 160, 255)),
    "Северное сияние": ((3, 22, 26), (6, 76, 72), (84, 255, 190)),
    "Галактика": ((14, 4, 34), (60, 10, 100), (255, 116, 224)),
}

ARCHETYPES = ["tree", "gift", "snowman", "snowflake", "santa", "planet", "robot", "bear",
              "penguin", "crown", "cocktail", "blob", "cat", "capy", "mammoth", "orange",
              "sock", "dumpling", "bubble", "salad", "dragon", "unicorn", "deer"]

VARIANT_SEEDS = [
    "Ледяная", "Неоновая", "Золотая", "Полярная", "Мятная", "Закатная", "Хромовая",
    "Лиловая", "Аметистовая", "Лазурная", "Пепельная", "Радужная", "Космическая",
    "Кибер", "Ретро", "Голографическая", "Изумрудная", "Медная", "Жемчужная", "Огненная",
]


def nft_variant(seed: int) -> dict:
    """Фон, модель и декоративные детали по номеру NFT — стабильно между перерисовками."""
    rnd = random.Random(int(seed) * 7919 + 41)
    palette = rnd.choice(list(NFT_BG_PALETTES.values()))
    model = rnd.choice([m[0] for m in MODELS])
    bg = rnd.choice([b[0] for b in BGS])
    named = [(n, p) for n, p in NFT_BG_PALETTES.items() if p == palette]
    return {"top": palette[0], "mid": palette[1], "accent": palette[2],
            "model": model, "background": bg,
            "palette_name": named[0][0] if named else "Обычный",
            "archetype": rnd.choice(ARCHETYPES),
            "variant": rnd.choice(VARIANT_SEEDS),
            "hue": rnd.randint(-26, 26),
            "ornament": rnd.choice(("stars", "snow", "bokeh", "grid", "rays"))}


def _nft_sword(d, cx, cy, accent):
    """Меч с лентой и листьями — для кастомных NFT."""
    for ang in (-38, -12, 18, 44):
        a = math.radians(ang)
        lx, ly = cx + math.cos(a) * 78, cy + math.sin(a) * 74
        d.ellipse((lx - 26, ly - 54, lx + 26, ly + 54), fill=(34, 132, 64))
        d.line((lx, ly - 44, lx, ly + 44), fill=(20, 90, 45), width=3)
    d.polygon([(cx - 26, cy - 150), (cx + 26, cy - 150), (cx + 18, cy + 120),
               (cx, cy + 180), (cx - 18, cy + 120)], fill=(198, 204, 214))
    d.polygon([(cx - 10, cy - 145), (cx + 4, cy - 145), (cx + 4, cy + 110),
               (cx - 2, cy + 160)], fill=(240, 244, 250))
    d.rounded_rectangle((cx - 70, cy - 160, cx + 70, cy - 130), 12, fill=(160, 166, 178))
    d.rounded_rectangle((cx - 60, cy - 156, cx + 60, cy - 136), 8, fill=(210, 216, 226))
    d.rounded_rectangle((cx - 18, cy - 250, cx + 18, cy - 160), 10, fill=(48, 52, 64))
    for i in range(5):
        d.line((cx - 14, cy - 240 + i * 16, cx + 14, cy - 240 + i * 16),
               fill=(70, 76, 90), width=3)
    d.ellipse((cx - 30, cy - 282, cx + 30, cy - 238), fill=(190, 196, 206))
    d.ellipse((cx - 90, cy - 150, cx - 10, cy - 80), fill=(180, 24, 40))
    d.ellipse((cx + 10, cy - 150, cx + 90, cy - 80), fill=(180, 24, 40))
    d.polygon([(cx - 40, cy - 110), (cx - 90, cy + 40), (cx - 60, cy + 50),
               (cx - 10, cy - 100)], fill=(200, 30, 48))
    d.polygon([(cx + 10, cy - 100), (cx + 60, cy + 60), (cx + 90, cy + 40),
               (cx + 40, cy - 110)], fill=(200, 30, 48))


def _nft_figure_image(seed: int, title: str, archetype: str, model: str, accent,
                      max_w: int, max_h: int) -> "Image.Image":
    """Возвращает обрезанную и масштабированную фигуру без фона."""
    v = nft_variant(seed)
    if not archetype:
        archetype = _nft_kind("", title)
        if archetype == "blob":
            archetype = v["archetype"]
    fig = Image.new("RGBA", (1200, 980), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fig, "RGBA")
    figures = {
        "tree": _nft_tree, "gift": _nft_gift, "snowman": _nft_snowman, "snowflake": _nft_snowflake,
        "santa": _nft_santa, "planet": _nft_planet, "robot": _nft_robot, "bear": _nft_bear,
        "penguin": _nft_penguin, "crown": _nft_crown, "cocktail": _nft_cocktail, "blob": _nft_blob,
        "cat": _nft_cat, "capy": _nft_capy, "mammoth": _nft_mammoth, "orange": _nft_orange,
        "sock": _nft_sock, "dumpling": _nft_dumpling, "bubble": _nft_bubble, "salad": _nft_salad,
        "dragon": _nft_dragon, "unicorn": _nft_unicorn, "deer": _nft_deer, "sword": _nft_sword,
        "rollix": _nft_rollix,
    }
    figures.get(archetype, _nft_blob)(fd, 600, 730, accent)
    box = fig.getbbox()
    fig = fig.crop(box) if box else fig
    scale = min(max_w / max(1, fig.width), max_h / max(1, fig.height))
    return fig.resize((max(1, int(fig.width * scale)), max(1, int(fig.height * scale))), Image.LANCZOS)


def _nft_figure_canvas(seed: int, title: str, archetype: str, model: str, accent,
                       w: int, h: int, max_w: int = 700, max_h: int = 600,
                       with_shadow: bool = True, center_y: Optional[int] = None) -> "Image.Image":
    """Рисует фигуру в полный холст — общая база для старых карточек."""
    fig = _nft_figure_image(seed, title, archetype, model, accent, max_w, max_h)
    char = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cy = int(center_y) if center_y is not None else int(h * .50)
    char.alpha_composite(fig, ((w - fig.width) // 2, cy - fig.height // 2))
    return char


def _nft_unique_scene(seed: int, title: str, model: str, background: str, rarity: str,
                      level: int, archetype: str = "", variant: str = "") -> bytes:
    """Премиальная чёрная карточка: студийный свет, объём, отражение и глубина."""
    w, h = 1280, 720
    v = nft_variant(seed)
    if model:
        top, mid, accent = NFT_MODEL_PALETTE.get(str(model), (v["top"], v["mid"], v["accent"]))
    else:
        top, mid, accent = v["top"], v["mid"], v["accent"]
    im = _nft_premium_bg(w, h, accent, rarity, seed)
    if not archetype:
        archetype = _nft_kind("", title)
        if archetype == "blob":
            archetype = v["archetype"]
    char = _nft_figure_canvas(seed, title, archetype, model, accent, w, h, 700, 430, True, 395)
    alpha = char.split()[3]
    gloss = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    light = Image.linear_gradient("L").resize((w, h), Image.BILINEAR).point(
        lambda v: int((1 - v / 255) * 46))
    gloss.putalpha(ImageChops.multiply(alpha, light))
    char = Image.alpha_composite(char, gloss)
    alpha = char.split()[3]

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * .72)))
    shadow.alpha_composite(sh, (0, 26))
    im = Image.alpha_composite(im, shadow)

    glow = Image.new("RGBA", (w, h), accent + (255,))
    glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * .40)))
    im = Image.alpha_composite(im, glow)

    rim_a = ImageChops.subtract(alpha, ImageChops.offset(alpha, 3, 3))
    rim_a = rim_a.filter(ImageFilter.GaussianBlur(1)).point(lambda v: int(v * .80))
    rim = Image.new("RGBA", (w, h), (255, 240, 220, 255))
    rim.putalpha(rim_a)
    im = Image.alpha_composite(im, rim)
    im.alpha_composite(char, (0, 0))

    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(int(seed) * 104729 + 17)
    for _ in range(14):
        x, y = rnd.randrange(40, w - 40), rnd.randrange(80, h - 100)
        rr = rnd.randint(1, 2)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 246, 224, rnd.randint(18, 55)))

    _nft_top_pills(im, seed)
    label_model = f"{model or v['model']} · {variant or v['variant']}"
    _nft_bottom_labels(im, title, rarity, label_model, accent, level=level, background=background)
    _nft_frame(im, rarity)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_blank_card(seed: int, title: str, rarity: str, level: int, model: str = "",
                    background: str = "") -> bytes:
    """Запечатанная чёрная карточка: силуэт модели, свет и номер. Без геометрии."""
    w, h = 1280, 720
    top, mid, accent = NFT_MODEL_PALETTE.get(str(model), NFT_MODEL_PALETTE["Стандартный"])
    im = _nft_premium_bg(w, h, accent, rarity, seed)
    v = nft_variant(seed)
    kind = _nft_kind("", title)
    if kind == "blob":
        kind = v["archetype"]
    char = _nft_figure_canvas(seed, title, kind, model, accent, w, h, 480, 300, False, 440)
    bb = char.getbbox()
    if bb:
        obj = char.crop(bb)
        mask = obj.split()[3].filter(ImageFilter.GaussianBlur(1))
        grad = _nft_gradient(obj.width, obj.height, (220, 224, 236), (42, 46, 60)).convert("RGBA")
        sil = Image.new("RGBA", obj.size, (0, 0, 0, 0))
        sil.paste(grad, (0, 0), mask)

        glow = Image.new("RGBA", (w, h), accent + (255,))
        gmask = Image.new("L", (w, h), 0)
        gmask.paste(mask, ((w - obj.width) // 2, int(h * .46) - obj.height // 2))
        glow.putalpha(gmask.filter(ImageFilter.GaussianBlur(28)).point(lambda x: int(x * .42)))
        im = Image.alpha_composite(im, glow)
        im.alpha_composite(sil, ((w - sil.width) // 2, int(h * .46) - obj.height // 2))

    d = ImageDraw.Draw(im, "RGBA")
    _nft_center_text(d, w, 64, "S E A L E D", _nft_font(True, 15), accent + (230,))
    _nft_center_text(d, w, 96, "БАЗОВАЯ МОДЕЛЬ", _nft_font(True, 22), (255, 255, 255, 225))
    _nft_center_text(d, w, 128, "арт и редкость — после улучшения",
                     _nft_font(False, 16), (230, 232, 245, 165))
    _nft_top_pills(im, seed)
    _nft_bottom_labels(im, title, rarity, model or "Стандартный", accent, level=level, background=background)
    _nft_frame(im, rarity)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _nft_watch_card(seed: int, title: str, model: str, background: str,
                    rarity: str, level: int) -> bytes:
    w, h = 1280, 720
    accent = (218, 178, 98)
    im = _nft_premium_bg(w, h, accent, rarity, seed)
    base = _rollix_base_image()
    if base is None:
        return _nft_character_card(seed, title, "🐧", model, background, rarity, level)

    watch = base.resize((820, 820), Image.LANCZOS)
    watch = ImageEnhance.Contrast(watch).enhance(1.14)
    watch = ImageEnhance.Color(watch).enhance(1.06)
    lum = watch.convert("L").point(lambda v: 0 if v < 9 else min(255, int(v * 1.3)))
    core = Image.new("L", (820, 820), 0)
    ImageDraw.Draw(core).ellipse((62, 62, 758, 758), fill=255)
    mask = ImageChops.lighter(lum, core).filter(ImageFilter.GaussianBlur(1.15))
    watch = watch.convert("RGBA")
    watch.putalpha(mask)
    glow = Image.new("RGBA", (820, 820), accent + (255,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(44)).point(lambda v: int(v * .85)))
    gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl.alpha_composite(glow, (w // 2 - 410, h // 2 - 410))
    im = Image.alpha_composite(im, gl)
    im.alpha_composite(watch, (w // 2 - 410, h // 2 - 410))

    d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(seed * 104729 + 3)
    for _ in range(18):
        _nft_spark(d, rnd.randrange(40, w - 40), rnd.randrange(90, h - 110),
                   rnd.randint(2, 8), (255, 232, 170), rnd.randint(35, 145))

    _nft_top_pills(im, seed)
    _nft_bottom_labels(im, title or "Роликсы", rarity, "Швейцарский механизм", accent, big=True, level=level)
    _nft_frame(im, rarity)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


GMINES_PALETTES = {
    "Чёрный бархат": {"bg": (10, 10, 12), "ink": (246, 242, 232), "accent": (216, 180, 106)},
    "Обсидиан": {"bg": (27, 36, 48), "ink": (245, 248, 255), "accent": (120, 190, 255)},
    "Дым": {"bg": (239, 228, 207), "ink": (35, 32, 28), "accent": (180, 40, 60)},
    "Нуар": {"bg": (18, 201, 232), "ink": (255, 255, 255), "accent": (0, 80, 120)},
    "Оникс": {"bg": (14, 58, 58), "ink": (235, 255, 250), "accent": (80, 220, 190)},
    "Полночь": {"bg": (26, 42, 90), "ink": (240, 245, 255), "accent": (120, 160, 255)},
}


def _nft_shade(color, factor, alpha=255):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3]) + (alpha,)


def _nft_palette(background, seed):
    key = bg_label(background)
    pal = GMINES_PALETTES.get(key)
    if pal:
        return pal
    keys = list(GMINES_PALETTES)
    return GMINES_PALETTES[keys[int(seed) % len(keys)]]


def _nft_symbol_tile(kind: str, size: int, color) -> Image.Image:
    tile = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile, "RGBA")
    c = size
    if kind == "paw":
        d.ellipse((c - size * .30, c - size * .02, c + size * .30, c + size * .34), fill=color)
        for dx, dy in ((-.30, -.18), (-.10, -.30), (.10, -.30), (.30, -.18)):
            r = size * .13
            x, y = c + dx * size, c + dy * size
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    elif kind == "snow":
        for ang in (0, 60, 120):
            a = math.radians(ang)
            dx, dy = math.cos(a) * size * .36, math.sin(a) * size * .36
            d.line((c - dx, c - dy, c + dx, c + dy), fill=color, width=max(2, size // 14))
            for side in (-1, 1):
                b = math.radians(ang + side * 35)
                d.line((c + dx * .55, c + dy * .55,
                        c + dx * .55 + math.cos(b) * size * .16,
                        c + dy * .55 + math.sin(b) * size * .16),
                       fill=color, width=max(2, size // 16))
    elif kind == "gamepad":
        d.rounded_rectangle((c - size * .42, c - size * .20, c + size * .42, c + size * .24),
                            radius=size * .14, fill=color)
        d.ellipse((c - size * .52, c - size * .16, c - size * .16, c + size * .34), fill=color)
        d.ellipse((c + size * .16, c - size * .16, c + size * .52, c + size * .34), fill=color)
    elif kind == "star":
        d.polygon(_nft_star_points(c, c, size * .44, size * .13, 4, -90), fill=color)
    elif kind == "crown":
        d.polygon([(c - size * .42, c + size * .26), (c - size * .34, c - size * .22),
                   (c - size * .10, c + size * .02), (c, c - size * .36),
                   (c + size * .10, c + size * .02), (c + size * .34, c - size * .22),
                   (c + size * .42, c + size * .26)], fill=color)
    elif kind == "magnifier":
        d.ellipse((c - size * .34, c - size * .34, c + size * .18, c + size * .18),
                  outline=color, width=max(2, size // 10))
        d.line((c + size * .08, c + size * .08, c + size * .44, c + size * .44),
               fill=color, width=max(2, size // 9))
    else:
        d.ellipse((c - size * .34, c - size * .34, c + size * .34, c + size * .34),
                  outline=color, width=max(2, size // 10))
        d.line((c, c - size * .20, c, c + size * .20), fill=color, width=max(2, size // 12))
        d.line((c - size * .20, c, c + size * .20, c), fill=color, width=max(2, size // 12))
    return tile


def _nft_watermark_kind(kind: str, title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ("меч", "клинок", "sword")):
        return "magnifier"
    if any(k in t for k in ("гейм", "gamer", "кибер", "cyber", "неон")):
        return "gamepad"
    if kind in ("cat", "capy", "bear", "deer", "penguin", "mammoth", "unicorn", "dragon", "blob"):
        return "paw"
    if kind in ("tree", "gift", "snowman", "snowflake", "santa"):
        return "snow"
    if kind in ("robot", "rollix"):
        return "gamepad"
    if kind in ("planet", "crown", "cocktail"):
        return "star"
    return "coin"


def _nft_watermark(im, kind: str, ink):
    w, h = im.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    size = 48
    step_x, step_y = 230, 190
    for row in range(-1, 5):
        for col in range(-1, 7):
            x = col * step_x + (row % 2) * step_x // 2
            y = row * step_y
            angle = (col * 13 + row * 27) % 44 - 22
            tile = _nft_symbol_tile(kind, size, ink + (255,))
            tile = tile.rotate(angle, resample=Image.BICUBIC, expand=True)
            layer.alpha_composite(tile, (x, y))
    alpha = layer.split()[3].point(lambda v: int(v * .08))
    layer.putalpha(alpha)
    im.alpha_composite(layer)


def _nft_card_character(fig, sealed: bool = False):
    if fig is None:
        return None
    alpha = fig.split()[3]
    outline_mask = alpha.filter(ImageFilter.MaxFilter(9))
    pad = 10
    canvas = Image.new("RGBA", (fig.width + pad * 2, fig.height + pad * 2), (0, 0, 0, 0))
    outline = Image.new("RGBA", canvas.size, (18, 18, 24, 255))
    om = Image.new("L", canvas.size, 0)
    om.paste(outline_mask, (pad, pad))
    outline.putalpha(om.point(lambda v: int(v * .85)))
    canvas.alpha_composite(outline, (0, 0))
    f = fig.convert("RGBA")
    if sealed:
        f = ImageEnhance.Color(f).enhance(.70)
        f = ImageEnhance.Brightness(f).enhance(.95)
    a = f.split()[3]
    gloss = Image.new("RGBA", f.size, (255, 255, 255, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse((int(f.width * .12), int(f.height * .05),
                int(f.width * .62), int(f.height * .48)), fill=(255, 255, 255, 90))
    gloss = gloss.filter(ImageFilter.GaussianBlur(16))
    gloss.putalpha(ImageChops.multiply(gloss.split()[3], a))
    f = Image.alpha_composite(f, gloss)
    shade = Image.linear_gradient("L").resize(f.size).point(lambda v: int(v * .22))
    sh = Image.new("RGBA", f.size, (0, 0, 0, 255))
    sh.putalpha(ImageChops.multiply(shade, a))
    f = Image.alpha_composite(f, sh)
    canvas.alpha_composite(f, (pad, pad))
    return canvas


def _nft_brand(im, ink):
    d = ImageDraw.Draw(im, "RGBA")
    f = _nft_font(True, 46)
    text = "RUBIN"
    d.text((42, 30), text, font=f, fill=ink + (245,))
    tw = d.textlength(text, font=f)
    sx = 42 + int(tw) - 4
    d.polygon(_nft_star_points(sx, 26, 15, 4, 4, -90), fill=ink + (245,))
    d.text((44, 86), "NFT COLLECTION", font=_nft_font(False, 15), fill=ink + (145,))


def _nft_number_band(im, seed: int, ink, band):
    w, h = im.size
    d = ImageDraw.Draw(im, "RGBA")
    d.polygon([(w - 340, h), (w, h - 340), (w, h - 250), (w - 250, h)], fill=band)
    f = _nft_font(True, 44)
    txt = f"#{seed}"
    tw = int(d.textlength(txt, font=f))
    layer = Image.new("RGBA", (tw + 60, 100), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.text((28, 20), txt, font=f, fill=(0, 0, 0, 90))
    dl.text((25, 17), txt, font=f, fill=(255, 255, 255, 245))
    layer = layer.rotate(-45, expand=True, resample=Image.BICUBIC)
    im.alpha_composite(layer, (w - layer.width - 2, h - layer.height - 2))


def _nft_watch_art():
    base = _rollix_base_image()
    if base is None:
        return None
    watch = base.resize((820, 820), Image.LANCZOS)
    watch = ImageEnhance.Contrast(watch).enhance(1.14)
    watch = ImageEnhance.Color(watch).enhance(1.06)
    lum = watch.convert("L").point(lambda v: 0 if v < 9 else min(255, int(v * 1.3)))
    core = Image.new("L", (820, 820), 0)
    ImageDraw.Draw(core).ellipse((62, 62, 758, 758), fill=255)
    mask = ImageChops.lighter(lum, core).filter(ImageFilter.GaussianBlur(1.15))
    watch = watch.convert("RGBA")
    watch.putalpha(mask)
    return watch


def _nft_gmines_card(seed: int, title: str, model: str, background: str, rarity: str,
                     level: int, sealed: bool = False, art=None) -> bytes:
    """Карточка в стиле примеров: цветной фон, водяные знаки, бренд и номер."""
    w, h = 1300, 680
    pal = _nft_palette(background, seed)
    bg, ink, accent = pal["bg"], pal["ink"], pal["accent"]
    im = Image.new("RGB", (w, h), bg).convert("RGBA")

    mask = Image.radial_gradient("L").resize((w, h), Image.BILINEAR)
    dark = mask.point(lambda v: int((v / 255) ** 2 * 34))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    black.putalpha(dark)
    im = Image.alpha_composite(im, black)

    kind = _nft_kind("", title)
    if kind == "blob":
        kind = nft_variant(seed)["archetype"]
    _nft_watermark(im, _nft_watermark_kind(kind, title), ink)

    if art is None:
        fig = _nft_figure_image(seed, title, kind, model, accent, int(w * .54), int(h * .68))
        art = _nft_card_character(fig, sealed)
    else:
        a = art.convert("RGBA")
        scale = min(w * .62 / max(1, a.width), h * .82 / max(1, a.height))
        a = a.resize((max(1, int(a.width * scale)), max(1, int(a.height * scale))), Image.LANCZOS)
        art = _nft_card_character(a, False)

    x = (w - art.width) // 2
    y = int(h * .52) - art.height // 2
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", art.size, (0, 0, 0, 255))
    sh.putalpha(art.split()[3].filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * .35)))
    shadow.alpha_composite(sh, (x, y + 14))
    im = Image.alpha_composite(im, shadow)
    im.alpha_composite(art, (x, y))

    _nft_brand(im, ink)
    if sealed:
        d = ImageDraw.Draw(im, "RGBA")
        d.text((44, 116), "SEALED · АРТ ОТКРОЕТСЯ ПОСЛЕ УЛУЧШЕНИЯ",
               font=_nft_font(True, 13), fill=ink + (150,))
    _nft_number_band(im, seed, ink, _nft_shade(bg, .74, 200))

    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def png_nft(seed: int, title: str, photo: str = "", model: str = "",
            background: str = "", rarity: str = "common", level: int = 1) -> bytes:
    """NFT в стиле примеров: цветной фон, водяные знаки, бренд и номер."""
    if photo == "blank":
        return _nft_gmines_card(seed, title, model, background, rarity, level, sealed=True)
    if photo == "photo":
        fp = NFT_DIR / f"photo_{seed}.png"
        if fp.is_file():
            try:
                return _nft_photo_card(fp.read_bytes(), title, rarity, seed)
            except Exception:
                log.exception("photo nft card")
    if photo and (NFT_DIR / str(photo)).is_file():
        try:
            return _nft_photo_card((NFT_DIR / str(photo)).read_bytes(), title, rarity, seed)
        except Exception:
            log.exception("photo nft card")
    if _nft_kind(photo, title) == "rollix":
        art = _nft_watch_art()
        if art is not None:
            return _nft_gmines_card(seed, title, model, background, rarity, level,
                                    sealed=level <= 1, art=art)
    return _nft_gmines_card(seed, title, model, background, rarity, level, sealed=level <= 1)


def make_nft_image(nid: int) -> Optional[bytes]:
    """Рисует карточку NFT и кладёт PNG в kv, чтобы она пережила рестарт."""
    r = q("SELECT id,name,photo,model,background,rarity,level FROM nft_items WHERE id=?", (int(nid),), one=True)
    if not r:
        return None
    try:
        raw = png_nft(int(r["id"]), r["name"], r.get("photo") or "", r.get("model") or "",
                      r.get("background") or "", r.get("rarity") or "common", int(r.get("level") or 1))
        kv_set(f"nftpng:{nid}", base64.b64encode(raw).decode("ascii"))
        kv_set(f"nftsvg:{nid}", "")
        return raw
    except Exception:
        log.exception("make_nft_image %s", nid)
        return None


def migrate_nft_art() -> int:
    """Сбрасывает старый кэш картинок, чтобы все NFT перерисовались в новом стиле."""
    try:
        if kv_get("nftart:version") == str(NFT_ART_VERSION):
            return 0
        n = x("DELETE FROM kv WHERE key LIKE 'nftpng:%' OR key LIKE 'nftsvg:%'")[0]
        kv_set("nftart:version", str(NFT_ART_VERSION))
        log.info("NFT-арт v%s: сброшено %s старых превью", NFT_ART_VERSION, n)
        return n
    except Exception:
        log.exception("migrate_nft_art")
        return 0


def redraw_nft_art() -> int:
    """Принудительно перерисовать все NFT при следующем открытии."""
    n = x("DELETE FROM kv WHERE key LIKE 'nftpng:%' OR key LIKE 'nftsvg:%'")[0]
    kv_set("nftart:version", str(NFT_ART_VERSION))
    return n


def reset_nft_collection() -> dict:
    """Новая коллекция: удаляет старые NFT и лоты, начинает нумерацию с #1."""
    old_items = int(q("SELECT COUNT(*) c FROM nft_items", one=True)["c"])
    old_lots = archive_count()
    x("DELETE FROM nft_items")
    x("DELETE FROM nft_archive")
    x("UPDATE users SET balance_nft_id=0, profile_nft_id=0")
    try:
        x("DELETE FROM kv WHERE key LIKE 'nftpng:%' OR key LIKE 'nftimg:%' OR key LIKE 'nftsvg:%'")
    except Exception:
        log.debug("reset nft kv", exc_info=True)
    try:
        if DATABASE_URL:
            x("ALTER SEQUENCE nft_items_id_seq RESTART WITH 1")
            x("ALTER SEQUENCE nft_archive_id_seq RESTART WITH 1")
        else:
            x("DELETE FROM sqlite_sequence WHERE name IN ('nft_items','nft_archive')")
    except Exception:
        log.debug("reset nft sequence", exc_info=True)
    kv_set("nftart:version", str(NFT_ART_VERSION))
    seed_nft_archive()
    ensure_owner_nft()
    log.warning("Коллекция NFT пересоздана: удалено %s NFT и %s лотов", old_items, old_lots)
    return {"items": old_items, "lots": old_lots, "archive": archive_count()}


def balance_text(uid: int) -> str:
    u = get_user(uid)
    lost = q("SELECT SUM(CASE WHEN bet_amount>win_amount THEN bet_amount-win_amount ELSE 0 END) v "
             "FROM bet_history WHERE user_id=?", (uid,), one=True)["v"] or 0
    games = u["total_games"] or q("SELECT COUNT(*) n FROM bet_history WHERE user_id=?", (uid,), one=True)["n"] or 0
    prem = premium_left(uid)
    text = (f"{E('balance')} <b>Баланс: {fmt(u['balance_coin'])} RCOIN</b>\n"
            f"<code>·····················</code>\n\n"
            f"<blockquote>{E('games')} Сыграно игр: <b>{fmt(games)}</b>\n"
            f"{E('profile')} Ранг: {rank_line(uid)}\n"
            f"{E('win')} Выиграно дуэлей: <b>{fmt(u['total_wins'])}</b>\n"
            f"{E('lose')} Проиграно RCOIN: <b>{fmt(int(lost))}</b></blockquote>")
    if prem:
        text += f"\n💠 Premium: <b>{dur(prem)}</b> · шанс ×1.5 · бонус ×2"
    return text


def daily5_available(uid: int) -> bool:
    row = q("SELECT status,opened,streak FROM daily5 WHERE user_id=? AND day=?", (uid, today()), one=True)
    if not row:
        return True
    if row["status"] != "open":
        return False
    try:
        opened = json.loads(row["opened"] or "[]")
    except Exception:
        opened = []
    return len(opened) < db5_cfg(int(row["streak"] or 1))[0]


def nft_public_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("db:") and WEBAPP_URL:
        try:
            return f"{WEBAPP_URL}/nft/{int(url.split(':', 1)[1])}"
        except (TypeError, ValueError):
            return ""
    return ""


def balance_kb(uid: int) -> InlineKeyboardMarkup:
    """Кнопки баланса — вертикально, недоступные бонусы скрываются."""
    rows = []
    if bonus_state(get_user(uid))[0]:
        rows.append([btn("Бонус", "bal:bonus", "donate", style="success")])
    if daily5_available(uid):
        rows.append([btn("Ежедневный", "bal:daily", "star", style="success")])
    rows.append([btn("Заработать", "bal:earn", "balance", style="primary")])
    return kb(*rows)


async def send_balance(message: Message, uid: int):
    url, cap = nft_photo(uid, "balance")
    public = nft_public_url(url)
    text = balance_text(uid)
    markup = balance_kb(uid)
    preview = LinkPreviewOptions(url=public, prefer_large_media=True, show_above_text=True) if public else None
    await message.reply(text, reply_markup=markup, link_preview_options=preview)


async def send_profile_photo(message: Message, uid: int):
    url, cap = nft_photo(uid, "profile")
    public = nft_public_url(url)
    text = (f"{E('profile')} <b>Профиль</b>\n{rank_line(uid)}\n{cap}").strip()
    preview = LinkPreviewOptions(url=public, prefer_large_media=True, show_above_text=True) if public else None
    await message.reply(text, link_preview_options=preview)


@dp.callback_query(F.data == "bal:main")
async def cb_balance(cb: CallbackQuery):
    uid = cb.from_user.id
    await safe_edit(cb, balance_text(uid), balance_kb(uid))
    await ans(cb)


@dp.callback_query(F.data == "bal:bonus")
async def cb_bonus(cb: CallbackQuery):
    uid = cb.from_user.id
    ok, left = bonus_state(get_user(uid))
    if not ok:
        return await ans(cb, f"Бонус доступен через {dur(left)}", True)
    update_user(uid, bonus_last_time=now())
    amount = BONUS_AMOUNT * bonus_mult(uid)
    add_coin(uid, amount)
    await safe_edit(cb, balance_text(uid), balance_kb(uid))
    await ans(cb, f"+{fmt(amount)} RCOIN", True)


@dp.callback_query(F.data == "bal:daily")
async def cb_daily(cb: CallbackQuery):
    t, k = await VIEWS["db5"](cb.from_user.id, True)
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data == "bal:earn")
async def cb_earn(cb: CallbackQuery):
    t, k = await VIEWS["earn"](cb.from_user.id, True)
    await safe_edit(cb, t, k)
    await ans(cb)


# =====================================================================
#                      ЗАРПЛАТА ЗА АКТИВНОСТЬ (/зп)
# =====================================================================
SALARY_MIN_PER_MSG = 5_000
SALARY_MAX_PER_MSG = 15_000


def salary_reward(uid: int) -> int:
    """5 000 за сообщение, до 15 000 при активности за день (shortcut: без истории прошлых дней)."""
    row = q("SELECT msg_count FROM chat_activity WHERE user_id=? AND day=?", (uid, today()), one=True)
    msgs = int(row["msg_count"] or 0) if row else 1
    return min(SALARY_MAX_PER_MSG, SALARY_MIN_PER_MSG + msgs * 50)


async def track_activity(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    tu = message.from_user
    if not tu or tu.is_bot or not (message.text or message.caption):
        return
    x("INSERT INTO chat_activity(user_id,day,msg_count) VALUES(?,?,1) "
      "ON CONFLICT(user_id,day) DO UPDATE SET msg_count=msg_count+1", (tu.id, today()))
    if not user_exists(tu.id):
        get_user(tu.id)
    x("UPDATE users SET salary_pending=salary_pending+? WHERE user_id=?", (salary_reward(tu.id), tu.id))


class ActivityTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            try:
                await track_activity(event)
            except Exception:
                log.exception("activity tracking failed")
        return await handler(event, data)


# Count group activity before command handlers run.
dp.message.outer_middleware(ActivityTrackingMiddleware())


def salary_amount(uid: int) -> tuple:
    row = q("SELECT msg_count FROM chat_activity WHERE user_id=? AND day=?", (uid, today()), one=True)
    msgs = row["msg_count"] if row else 0
    u = get_user(uid)
    return int(u.get("salary_pending") or 0), msgs


def salary_view(uid: int):
    amount, msgs = salary_amount(uid)
    text = (f"💼 <b>ЗАРПЛАТА ЗА АКТИВНОСТЬ</b>\n\n"
            f"💬 Сообщений в чате сегодня: <b>{fmt(msgs)}</b>\n"
            f"💰 За сообщение: <b>{fmt(SALARY_MIN_PER_MSG)}–{fmt(SALARY_MAX_PER_MSG)}</b> RCOIN (растёт с активностью)\n"
            f"🔥 Накоплено: <b>{fmt(amount)}</b> RCOIN\n\n"
            + ("✅ Всё выплачено. Пиши ещё — начисления продолжаются!"
               if amount <= 0 else "🎁 Доступно к получению — нажми «Забрать»!"))
    rows = [[btn(f"Забрать {fmt(amount)} RCOIN", "zp:get")] if amount > 0 else [btn("Нет начислений", "noop")]]
    return text, kb(*rows)


@dp.message(P("зп", "зарплата", "zp", "salary"))
async def cmd_salary(message: Message):
    t, k = salary_view(message.from_user.id)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data == "zp:get")
async def cb_salary(cb: CallbackQuery):
    uid = cb.from_user.id
    u = get_user(uid)
    amount = int(u.get("salary_pending") or 0)
    if amount <= 0:
        return await ans(cb, "Нет начислений — напиши сообщение в чат", True)
    ok = x("UPDATE users SET balance_coin=balance_coin+?, salary_pending=0 "
           "WHERE user_id=? AND salary_pending=?", (amount, uid, amount))[0]
    if not ok:
        return await ans(cb, "Начисления уже изменились, попробуй ещё раз", True)
    quest_inc(uid, "salary")
    t, k = salary_view(uid)
    await safe_edit(cb, t, k)
    await ans(cb, f"+{fmt(amount)} RCOIN!", True)


# =====================================================================
#                           ТРЕЙДИНГ
# =====================================================================
TICK = 60


def price_at(ts: float) -> float:
    """Детерминированный курс: одинаков для бота, Web App и после рестарта."""
    t = ts / TICK
    k = int(t)
    f = t - k
    def val(i):
        r = random.Random(i)
        return 950 + 350 * math.sin(i / 97.0) + 180 * math.sin(i / 23.0 + 1.7) + r.uniform(-25, 25)
    a, b = val(k), val(k + 1)
    smooth = f * f * (3 - 2 * f)
    return max(80.0, round(a + (b - a) * smooth, 2))


def market_price(ts: float = None) -> float:
    return price_at(time.time() if ts is None else ts)


def chart(n: int = 48) -> str:
    k = int(time.time() / TICK)
    vals = [price_at((k - n + 1 + i) * TICK) for i in range(n)]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    blocks = "▁▂▃▄▅▆▇█"
    return "".join(blocks[min(7, int((v - lo) / span * 7.99))] for v in vals)


def holding(uid: int) -> dict:
    return q("SELECT coins,avg_price,invested FROM trade_holdings WHERE user_id=?", (uid,), one=True) \
        or {"coins": 0.0, "avg_price": 0.0, "invested": 0}


def trade_view(uid: int):
    p = market_price()
    prev = price_at((int(time.time() / TICK) - 1) * TICK)
    h = holding(uid)
    value = int(h["coins"] * p)
    pl = value - int(h["invested"])
    up = p >= prev
    sign = "+" if up else ""
    prem = is_premium(uid)
    text = (f"📈 <b>ТРЕЙДИНГ RCOIN</b>\n\n"
            f"{'📈' if up else '📉'} Курс: <b>{p:.2f}</b> RCOIN <i>({sign}{(p - prev) / prev * 100:.2f}%)</i>\n"
            f"<code>{chart()}</code>\n\n"
            f"💼 В портфеле: <b>{h['coins']:.2f}</b> v-RCOIN\n"
            f"💰 Стоимость: <b>{fmt(value)}</b> RCOIN\n"
            f"📥 Вложено: {fmt(int(h['invested']))} RCOIN\n"
            f"{'🟢' if pl >= 0 else '🔴'} P/L: <b>{sign}{fmt(pl)}</b> RCOIN\n\n"
            f"💵 Свободно: <b>{fmt(get_user(uid)['balance_coin'])}</b> RCOIN"
            + ("\n💠 Premium: прибыль ×1.5 при продаже" if prem else ""))
    rows = [[btn(f"🟢 КУПИТЬ — {p:.2f}", "trade:buy")],
            [btn(f"🔴 ПРОДАТЬ — {p:.2f}", "trade:sell")],
            [btn("Купить 100 000", "trade:qb:100000"), btn("Продать всё", "trade:qa")],
            [btn("📊 График", "trade:chart"), btn("💼 Портфель", "trade:port")],
            [btn("Назад", "bal:main", "door")]]
    return text, kb(*rows)


def buy(uid: int, amount: int) -> str:
    if amount < 1_000:
        return "❌ Минимум 1 000 RCOIN"
    p = market_price()
    if not spend(uid, amount):
        return "❌ Недостаточно RCOIN"
    coins = amount / p
    h = holding(uid)
    new_coins = h["coins"] + coins
    new_inv = int(h["invested"]) + amount
    x("INSERT INTO trade_holdings(user_id,coins,avg_price,invested) VALUES(?,?,?,?) "
      "ON CONFLICT(user_id) DO UPDATE SET coins=excluded.coins, avg_price=excluded.avg_price, invested=excluded.invested",
      (uid, new_coins, new_inv / new_coins if new_coins else p, new_inv))
    x("INSERT INTO trade_logs(user_id,side,amount,price,coins,ts) VALUES(?,?,?,?,?,?)",
      (uid, "buy", amount, p, int(coins), now()))
    quest_inc(uid, "trade")
    return f"🟢 Куплено {coins:.2f} v-RCOIN по {p:.2f}"


def sell(uid: int, coins: float) -> str:
    h = holding(uid)
    if h["coins"] <= 0:
        return "❌ У тебя нет v-RCOIN"
    coins = min(float(coins), h["coins"])
    if coins <= 0:
        return "❌ Введи количество"
    p = market_price()
    gross = int(coins * p)
    if is_premium(uid) and gross > int(h["invested"]) * (coins / max(h["coins"], 1e-9)):
        profit = gross - int(h["avg_price"] * coins)
        if profit > 0:
            gross += int(profit * 0.5)
    fee = gross // 100
    net = gross - fee
    add_coin(uid, net)
    left = max(0.0, h["coins"] - coins)
    x("UPDATE trade_holdings SET coins=?, invested=? WHERE user_id=?",
      (left, max(0, int(h["invested"]) - int(h["avg_price"] * coins)), uid))
    x("INSERT INTO trade_logs(user_id,side,amount,price,coins,ts) VALUES(?,?,?,?,?,?)",
      (uid, "sell", coins, p, net, now()))
    return f"🔴 Продано {coins:.2f} v-RCOIN → +{fmt(net)} RCOIN (комиссия {fmt(fee)})"


@dp.message(P("трейдинг", "биржа", "курс", "trade", "трейд"))
async def cmd_trade(message: Message):
    t, k = trade_view(message.from_user.id)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data.startswith("trade:"))
async def cb_trade(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    act = cb.data.split(":")
    p = market_price()
    if act[1] == "buy":
        return await ask(cb, state, "trade_buy", f"🟢 Сколько RCOIN вложить? Курс {p:.2f}.\nНапример: <code>100к</code>, <code>1кк</code> или <code>все</code>")
    if act[1] == "sell":
        h = holding(uid)
        if h["coins"] <= 0:
            return await ans(cb, "У тебя нет v-RCOIN", True)
        return await ask(cb, state, "trade_sell", f"🔴 Сколько v-RCOIN продать? В наличии {h['coins']:.2f}.\nНапример: <code>5</code> или <code>все</code>")
    if act[1] == "qb":
        await safe_edit(cb, trade_view(uid)[0], trade_view(uid)[1])
        return await ans(cb, buy(uid, int(act[2])), True)
    if act[1] == "qa":
        h = holding(uid)
        msg = sell(uid, h["coins"]) if h["coins"] > 0 else "❌ У тебя нет v-RCOIN"
        await safe_edit(cb, trade_view(uid)[0], trade_view(uid)[1])
        return await ans(cb, msg, True)
    if act[1] == "chart":
        rows = [[btn("🌐 Live-график в Web App", web=WEBAPP_URL + "?tab=trade")]] if WEBAPP_URL else []
        rows.append([btn("Назад", "trade:menu", "door")])
        return await (safe_edit(cb, f"📊 <b>КУРС RCOIN</b>\n\n<code>{chart(60)}</code>\n\nСейчас: <b>{p:.2f}</b> RCOIN", kb(*rows)) or ans(cb))
    if act[1] == "port":
        h = holding(uid)
        logs = q("SELECT side,amount,price,ts FROM trade_logs WHERE user_id=? ORDER BY id DESC LIMIT 8", (uid,))
        hist = "\n".join(
            f"{'🟢' if r['side'] == 'buy' else '🔴'} {'купил' if r['side'] == 'buy' else 'продал'} "
            f"{r['amount']:.2f} по {r['price']:.2f} · {datetime.fromtimestamp(r['ts'], MSK).strftime('%d.%m %H:%M')}"
            for r in logs) or "сделок ещё не было"
        text = (f"💼 <b>ПОРТФЕЛЬ</b>\n\nv-RCOIN: <b>{h['coins']:.2f}</b>\n"
                f"Стоимость: <b>{fmt(int(h['coins'] * p))}</b> RCOIN\nВложено: {fmt(int(h['invested']))}\n\n"
                f"<b>История сделок:</b>\n{hist}")
        await safe_edit(cb, text, kb([btn("Назад", "trade:menu", "door")]))
        return await ans(cb)
    if act[1] == "menu":
        t, k = trade_view(uid)
        await safe_edit(cb, t, k)
        return await ans(cb)


@flow("trade_buy")
async def flow_buy(m: Message, state: FSMContext, d, txt):
    uid = m.from_user.id
    amount = parse_amount(txt, get_user(uid)["balance_coin"])
    await state.clear()
    await m.reply(buy(uid, amount) if amount > 0 else "❌ Введи сумму")
    t, k = trade_view(uid)
    await m.answer(t, reply_markup=k)


@flow("trade_sell")
async def flow_sell(m: Message, state: FSMContext, d, txt):
    uid = m.from_user.id
    h = holding(uid)
    raw = (txt or "").strip().lower().replace(",", ".").replace(" ", "")
    if raw in ("все", "всё", "all", "max"):
        coins = h["coins"]
    else:
        try:
            coins = float(raw)
        except ValueError:
            coins = 0.0
    await state.clear()
    await m.reply(sell(uid, coins) if coins > 0 else "❌ Введи количество")
    t, k = trade_view(uid)
    await m.answer(t, reply_markup=k)


# =====================================================================
#                       РАБОТА: IT-СФЕРА (/работа)
# =====================================================================
IT_TASKS = [
    ("🐞 Фикс бага", "Найди причину падения в логах", 0.74, 12_000),
    ("🔍 Ревью PR", "Проверь пул-реквест коллеги", 0.86, 9_000),
    ("🚀 Деплой на прод", "Собери образ и выкати релиз", 0.66, 26_000),
    ("🗄 Оптимизация БД", "Добавь индекс, ускорь запрос", 0.62, 42_000),
    ("🔌 Новый API-эндпоинт", "Сделай метод /api/v2/items", 0.70, 33_000),
    ("🛡 Пентест", "Найди уязвимость в сервисе", 0.44, 78_000),
    ("🤖 Обучение модели", "Дообучи модель на новых данных", 0.38, 95_000),
    ("🏛 Архитектура", "Спроектируй схему микросервисов", 0.33, 160_000),
]
IT_EVENTS = [
    ("🔥 Хакатон выходного дня", "Три дня без сна — зато MVP готов", 1.5),
    ("📦 Релиз крупной версии", "Дедлайн горел, но всё вышло в срок", 2.0),
    ("🚨 Прод упал в 3:00", "Инцидент, фикс и постмортем", 2.5),
    ("💬 Собес в BigTech", "Оффер мечты после пяти раундов", 3.0),
]
IT_STAGES = [(1, "Стажёр"), (3, "Junior"), (6, "Middle"), (10, "Senior"), (15, "Team Lead"), (21, "CTO")]


def it_row(uid: int) -> dict:
    r = q("SELECT * FROM it_progress WHERE user_id=?", (uid,), one=True)
    if not r:
        x("INSERT OR IGNORE INTO it_progress(user_id) VALUES(?)", (uid,))
        r = q("SELECT * FROM it_progress WHERE user_id=?", (uid,), one=True)
    return r


def it_stage(level: int) -> str:
    name = IT_STAGES[0][1]
    for need, nm in IT_STAGES:
        if level >= need:
            name = nm
    return name


def it_view(uid: int):
    r = it_row(uid)
    left = 60 - (now() - r["last_task"])
    text = (f"💻 <b>РАБОТА · IT-СФЕРА</b>\n\n"
            f"👔 Должность: <b>{it_stage(r['level'])}</b> (ур. {r['level']})\n"
            f"⭐ Опыт: <b>{fmt(r['xp'])}</b> XP\n"
            f"💰 Заработано: <b>{fmt(r['coins'])}</b> RCOIN\n"
            f"✅ Заданий выполнено: <b>{fmt(r['tasks_done'])}</b>\n\n"
            + (f"⏳ Следующее задание через {dur(left)}" if left > 0 else "🎯 Можно брать задание!"))
    rows = [[btn(f"⏳ Перерыв {dur(left)}" if left > 0 else "🚀 Взять задание", "noop" if left > 0 else "it:task")],
            [btn("🎲 Событие дня", "it:event")],
            [btn("🏆 Топ сотрудников", "it:top"), btn("📜 Резюме", "it:cv")],
            [btn("Назад", "bal:main", "door")]]
    return text, kb(*rows)


@dp.message(P("работа", "ит", "work", "job"))
async def cmd_it(message: Message):
    t, k = it_view(message.from_user.id)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data == "it:task")
async def cb_it_task(cb: CallbackQuery):
    uid = cb.from_user.id
    r = it_row(uid)
    if now() - r["last_task"] < 60:
        return await ans(cb, f"Перерыв {dur(60 - (now() - r['last_task']))}", True)
    title, desc, chance, base = random.choice(IT_TASKS)
    ok = random.random() < min(0.95, chance + 0.02 * r["level"])
    x("UPDATE it_progress SET last_task=? WHERE user_id=?", (now(), uid))
    if ok:
        amount = int(base * (1 + 0.15 * r["level"]) * (1.5 if is_premium(uid) else 1.0))
        xp = random.randint(10, 25)
        add_coin(uid, amount)
        x("UPDATE it_progress SET coins=coins+?, xp=xp+?, tasks_done=tasks_done+1, level=level+1 WHERE user_id=?",
          (amount, xp, uid))
        quest_inc(uid, "it")
        body = f"🟢 <b>Успех!</b>\n+{fmt(amount)} RCOIN · +{xp} XP"
    else:
        x("UPDATE it_progress SET tasks_done=tasks_done+1 WHERE user_id=?", (uid,))
        body = "🔴 <b>Не вышло.</b> Код вернули на доработку, попробуй ещё."
    text = f"{title}\n<i>{desc}</i>\n\n{body}"
    await safe_edit(cb, text, kb([btn("К работам", "it:menu", "door")]))
    await ans(cb, "Готово!" if ok else "Провал", True)


@dp.callback_query(F.data == "it:event")
async def cb_it_event(cb: CallbackQuery):
    uid = cb.from_user.id
    if q("SELECT 1 FROM quests WHERE user_id=? AND day=? AND key='it_event'", (uid, today()), one=True):
        return await ans(cb, "Событие дня уже было", True)
    x("INSERT INTO quests(user_id,day,key,value) VALUES(?,?,?,1)", (uid, today(), "it_event"))
    r = it_row(uid)
    title, desc, mult = random.choice(IT_EVENTS)
    amount = int(random.randint(60_000, 200_000) * (1 + 0.2 * r["level"]) * mult)
    add_coin(uid, amount)
    x("UPDATE it_progress SET coins=coins+?, xp=xp+40 WHERE user_id=?", (amount, uid))
    await safe_edit(cb, f"{title}\n<i>{desc}</i>\n\n🎉 Бонус: <b>+{fmt(amount)}</b> RCOIN · +40 XP",
                         kb([btn("К работам", "it:menu", "door")]))
    await ans(cb, f"+{fmt(amount)}", True)


@dp.callback_query(F.data == "it:top")
async def cb_it_top(cb: CallbackQuery):
    rows = q("SELECT u.display_name n, p.level l, p.coins c FROM it_progress p "
             "JOIN users u ON u.user_id=p.user_id ORDER BY p.level DESC, p.coins DESC LIMIT 10")
    body = "\n".join(f"{i + 1}. {esc(r['n'] or 'Игрок')} — ур. {r['l']} · {fmt(r['c'])}" for i, r in enumerate(rows)) or "—"
    await safe_edit(cb, f"🏆 <b>ТОП IT-СОТРУДНИКОВ</b>\n\n{body}", kb([btn("Назад", "it:menu", "door")]))
    await ans(cb)


@dp.callback_query(F.data == "it:cv")
async def cb_it_cv(cb: CallbackQuery):
    uid = cb.from_user.id
    r = it_row(uid)
    await safe_edit(cb, (f"📜 <b>РЕЗЮМЕ</b>\n\n👤 {uname(get_user(uid), False)}\n"
                              f"👔 {it_stage(r['level'])} · ур. {r['level']}\n⭐ XP: {fmt(r['xp'])}\n"
                              f"✅ Заданий: {fmt(r['tasks_done'])}\n💰 Заработано: {fmt(r['coins'])} RCOIN\n"
                              f"💠 Premium: {'активен' if is_premium(uid) else 'нет'}"),
                        kb([btn("Назад", "it:menu", "door")]))
    await ans(cb)


@dp.callback_query(F.data == "it:menu")
async def cb_it_menu(cb: CallbackQuery):
    t, k = it_view(cb.from_user.id)
    await safe_edit(cb, t, k)
    await ans(cb)


# =====================================================================
#                       ГАЛОЧКИ: МЕНЮ И ВЫДАЧА
# =====================================================================
def badges_view(uid: int):
    have = my_badges(uid)
    pinned = profile_badges(uid)
    prem = premium_left(uid)
    rank = get_user(uid)["rank_title"] or "Новичок"
    lines = ["🛡 <b>ГАЛОЧКИ</b>\n",
             f"🏷 Твой ранг: <b>{esc(rank)}</b>\n"]
    if have:
        lines.append("<b>Твои галочки:</b>")
        for b in have:
            role = BADGES[b]["role"]
            mark = " <i>(в профиле)</i>" if b in pinned else ""
            lines.append(f"{badge(b)} <b>{role}</b> · {BADGES[b]['title']}{mark}")
    else:
        lines.append("<i>Галочек пока нет.</i>")
    lines.append(f"\n<b>Профиль:</b> {' '.join(badge(b) for b in pinned) if pinned else '—'} ({len(pinned)}/{MAX_PROFILE_BADGES})")
    if prem:
        lines.append(f"💠 Premium: <b>{dur(prem)}</b> · шанс победы ×1.5 · бонус ×2 · смена ника")
    lines.append("\n<i>При покупке галочки ранг профиля меняется автоматически.</i>")
    rows = []
    if have:
        rows.append([btn("➕ Добавить в профиль", "badges:add")])
        rows.append([btn("➖ Убрать из профиля", "badges:del")])
    for b in BADGE_ORDER:
        if b not in have and BADGES[b]["buyable"]:
            price = BADGES[b]["price_coin"]
            cost = (f"{price // 1_000_000_000}ккк RCOIN" if price >= 10 ** 9 else f"{fmt(price)} RCOIN")
            if BADGES[b]["price_stars"]:
                cost += f" / {BADGES[b]['price_stars']}⭐"
            rows.append([btn(f"Купить {BADGES[b]['title']} — {cost}", f"badges:buy:{b}", icon=b)])
    rows.append([btn("Назад", "bal:main", "door")])
    return "\n".join(lines), kb(*rows)


def badges_pin_view(uid: int, remove: bool = False):
    have = my_badges(uid)
    if not have:
        return "😔 У тебя нет галочек.", kb([btn("Назад", "badges:menu", "door")])
    pinned = profile_badges(uid)
    rows = []
    for b in have:
        is_in = q("SELECT 1 FROM user_badges WHERE user_id=? AND badge=? AND slot=1", (uid, b), one=True)
        if remove and not is_in:
            continue
        mark = "✓" if is_in else "＋"
        rows.append([btn(f"{mark} {BADGES[b]['title']}", f"badges:{'unpin' if remove else 'pin'}:{b}", icon=b)])
    if not rows:
        return "В профиле сейчас нет галочек.", kb([btn("Назад", "badges:menu", "door")])
    rows.append([btn("Готово", "badges:menu", "door")])
    head = "➖ <b>Убрать из профиля</b>" if remove else "➕ <b>Добавить в профиль</b>"
    return f"{head}\nВыбрано {len(pinned)}/{MAX_PROFILE_BADGES}. Нажми на галочку.", kb(*rows)


@dp.message(P("галочки", "галки", "badges"))
async def cmd_badges(message: Message):
    t, k = badges_view(message.from_user.id)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data == "badges:menu")
async def cb_badges_menu(cb: CallbackQuery):
    t, k = badges_view(cb.from_user.id)
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data == "badges:add")
async def cb_badges_add(cb: CallbackQuery):
    t, k = badges_pin_view(cb.from_user.id)
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data == "badges:del")
async def cb_badges_del(cb: CallbackQuery):
    t, k = badges_pin_view(cb.from_user.id, remove=True)
    await safe_edit(cb, t, k)
    await ans(cb)


@dp.callback_query(F.data.startswith("badges:"))
async def cb_badges_action(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split(":")
    act = parts[1]
    if act == "pin":
        if not has_badge(uid, parts[2]):
            return await ans(cb, "Нет такой галочки", True)
        if not pin_badge(uid, parts[2]):
            return await ans(cb, f"Максимум {MAX_PROFILE_BADGES} галочки в профиле", True)
        await ans(cb, "Добавлена")
    elif act == "unpin":
        unpin_badge(uid, parts[2])
        await ans(cb, "Убрана")
    elif act == "buy":
        b = parts[2]
        if b not in BADGES or not BADGES[b]["buyable"]:
            return await ans(cb, "Нельзя купить", True)
        if has_badge(uid, b):
            return await ans(cb, "Уже есть", True)
        price = BADGES[b]["price_coin"]
        if price:
            if not spend(uid, price):
                return await ans(cb, f"Нужно {fmt(price)} RCOIN", True)
            give_badge(uid, b)
            rank = get_user(uid)["rank_title"] or "Новичок"
            await ans(cb, f"Куплено: {BADGES[b]['title']}! Ранг: {rank}", True)
        else:
            await ans(cb, f"Оплата Stars: {BADGES[b]['price_stars']}⭐ — напиши админу", True)
            return await safe_edit(cb, (f"{badge(b)} <b>{BADGES[b]['title']}</b>\n\n"
                                             f"Цена: {BADGES[b]['price_stars']} ⭐ Telegram Stars.\n"
                                             f"Напиши администратору, он выдаст галочку после оплаты."),
                                       kb([btn("Назад", "badges:menu", "door")]))
        t, k = badges_view(uid)
        return await safe_edit(cb, t, k)
    t, k = badges_pin_view(uid, remove=(act == "unpin"))
    await safe_edit(cb, t, k)


# =====================================================================
#                      АДМИН: ГАЛОЧКИ / PREMIUM
# =====================================================================
def adm_badges_view(uid: int):
    text = "🛡 <b>УПРАВЛЕНИЕ ГАЛОЧКАМИ</b>\n\nВыбери галочку, затем введи ID или @ник игрока."
    rows = [[btn(f"Выдать {BADGES[b]['title']}", f"adm:bg:{b}", icon=b)] for b in BADGE_ORDER]
    rows.append([btn("Снять галочку", "adm:bgrm")])
    rows.append([btn("💠 Premium 30 дней", "adm:bgprem", icon="diamond")])
    rows.append([btn("🎖 Выдать себе", "adm:self")])
    rows.append([btn("Назад", "adm:menu", "door")])
    return text, kb(*rows)


@dp.callback_query(F.data.startswith("adm:bg"))
async def cb_adm_badges(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет прав", True)
    parts = cb.data.split(":")
    act = parts[1]
    if act == "bg":
        key = parts[2]
        if key == "dev" and cb.from_user.id != OWNER_ID:
            return await ans(cb, "Галочку владельца может выдать только владелец", True)
        return await ask(cb, state, "adm_badge", f"Выдать {BADGES[key]['title']}\nВведи ID игрока:", badge=key)
    if act == "bgrm":
        rows = [[btn(f"Снять {BADGES[b]['title']}", f"adm:bgd:{b}", icon=b)] for b in BADGE_ORDER]
        rows.append([btn("Назад", "adm:badges", "door")])
        return await (safe_edit(cb, "Снять какую галочку?", kb(*rows)) or ans(cb))
    if act == "bgd":
        return await ask(cb, state, "adm_badge_del", f"Снять {BADGES[parts[2]]['title']}\nВведи ID игрока:", badge=parts[2])
    if act == "bgprem":
        return await ask(cb, state, "adm_premium", "Выдать Premium на 30 дней\nВведи ID игрока:")
    if act == "bgself":
        set_premium(cb.from_user.id, 30 * 86400)
        give_badge(cb.from_user.id, "premium2")
        await ans(cb, "Premium выдан тебе на 30 дней", True)
        return await (safe_edit(cb, adm_badges_view(cb.from_user.id)[0], adm_badges_view(cb.from_user.id)[1]) or None)
    t, k = adm_badges_view(cb.from_user.id)
    await safe_edit(cb, t, k)


async def _badge_flow(m: Message, state: FSMContext, key: str, remove: bool = False):
    if key == "dev" and m.from_user.id != OWNER_ID:
        await state.clear()
        return await m.reply("⛔ Галочку владельца может выдавать только владелец.")
    t = find_user((m.text or "").strip())
    if not t:
        return await m.reply("❌ Игрок не найден. Введи ID или @ник.")
    await state.clear()
    if remove:
        if take_badge(t["user_id"], key):
            await m.reply(f"✅ Снята {BADGES[key]['title']} у {esc(t['display_name'] or str(t['user_id']))}")
        else:
            await m.reply("⛔ Эту галочку снять нельзя.")
    else:
        give_badge(t["user_id"], key)
        await m.reply(f"✅ Выдана {BADGES[key]['title']} игроку {esc(t['display_name'] or str(t['user_id']))}")


@flow("adm_badge")
async def flow_adm_badge(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return
    await _badge_flow(m, state, d["badge"])


@flow("adm_badge_del")
async def flow_adm_badge_del(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return
    await _badge_flow(m, state, d["badge"], remove=True)


@flow("adm_premium")
async def flow_adm_premium(m: Message, state: FSMContext, d, txt):
    if not is_admin(m.from_user.id):
        return
    t = find_user((m.text or "").strip())
    if not t:
        return await m.reply("❌ Игрок не найден.")
    await state.clear()
    set_premium(t["user_id"], 30 * 86400)
    await m.reply(f"💠 Premium на 30 дней выдан {esc(t['display_name'] or str(t['user_id']))}")


# =====================================================================
#                   NFT-КАРТИНКИ И БАЛАНС С ФОТО
# =====================================================================
def svg_nft(seed: int, title: str) -> str:
    rnd = random.Random(seed)
    h1 = rnd.randint(0, 359)
    h2 = (h1 + rnd.randint(90, 200)) % 360
    blobs = []
    for _ in range(7):
        blobs.append(f'<circle cx="{rnd.randint(30, 470)}" cy="{rnd.randint(30, 250)}" r="{rnd.randint(15, 80)}" '
                     f'fill="hsl({rnd.choice([h1, h2, (h1 + 40) % 360])},{rnd.randint(55, 90)}%,{rnd.randint(45, 70)}%)" '
                     f'opacity="{rnd.uniform(0.12, 0.35):.2f}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="hsl({h1},70%,26%)"/><stop offset="1" stop-color="hsl({h2},72%,16%)"/>'
            '</linearGradient></defs><rect width="640" height="360" fill="url(#g)"/>' + "".join(blobs) +
            f'<text x="28" y="322" fill="rgba(255,255,255,.95)" font-family="Segoe UI,Arial" font-size="30" '
            f'font-weight="800">{esc(title)[:26]}</text>'
            f'<text x="28" y="352" fill="rgba(255,255,255,.55)" font-family="Segoe UI,Arial" font-size="16">'
            f'RCOIN NFT #{seed}</text></svg>')


def mint_nft(uid: int) -> tuple:
    if not spend(uid, MINT_COST):
        return False, f"❌ Отчеканить NFT стоит {fmt(MINT_COST)} RCOIN"
    pick = random.choice(NFT_POOL["common"] + NFT_POOL["rare"] + NFT_POOL["epic"])
    name = pick[0]
    nid = make_nft(uid, name, "common", "blank", "Базовая модель. Арт откроется после улучшения.", MINT_COST)
    row = q("SELECT model FROM nft_items WHERE id=?", (nid,), one=True) or {}
    make_nft_image(nid)
    return True, (f"{nft_emoji(nid)} <b>NFT отчеканен!</b>\n<b>{esc(name)}</b> <code>#{nid}</code>\n"
                  f"🎭 Модель: {esc(row.get('model') or 'Стандартный')}\n"
                  f"✨ Редкость: появится после улучшения\n\n"
                  f"<i>Пока это карточка с моделью и номером — улучши NFT, чтобы открыть арт.</i>")


@dp.callback_query(F.data == "ev:mint")
async def cb_ev_mint(cb: CallbackQuery):
    ok, msg = mint_nft(cb.from_user.id)
    await safe_edit(cb, msg, kb([btn("Отчеканить ещё", "ev:mint"), btn("Баланс", "bal:main", "door")]))
    await ans(cb, "Готово" if ok else "Мало RCOIN", True)


# =====================================================================
#                       ПЕРЕОФОРМЛЕНИЕ ГЛАВНОГО МЕНЮ
# =====================================================================


async def cb_adm_badges_root(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет прав", True)
    t, k = adm_badges_view(cb.from_user.id)
    await safe_edit(cb, t, k)
    await ans(cb)


# =====================================================================
#                        WEB APP: API-ЭНДПОИНТЫ
# =====================================================================
def api_trade_state(u, body):
    uid = u["user_id"]
    h = holding(uid)
    p = market_price()
    prev = price_at((int(time.time() / TICK) - 1) * TICK)
    k = int(time.time() / TICK)
    series = [{"t": (k - 59 + i) * TICK * 1000, "p": price_at((k - 59 + i) * TICK)} for i in range(60)]
    return {"ok": True, "price": p, "prev": prev, "series": series, "coins": round(h["coins"], 4),
            "value": int(h["coins"] * p), "invested": int(h["invested"]),
            "next_tick": int((k + 1) * TICK * 1000 - time.time() * 1000)}


def api_trade_buy(u, body):
    amount = int(float(body.get("amount", 0) or 0))
    msg = buy(u["user_id"], amount)
    return {"ok": msg.startswith("🟢"), "msg": msg, "state": api_trade_state(u, body)}


def api_trade_sell(u, body):
    h = holding(u["user_id"])
    try:
        coins = float(body.get("coins", 0) or 0)
    except (TypeError, ValueError):
        coins = 0.0
    if body.get("all"):
        coins = h["coins"]
    msg = sell(u["user_id"], coins)
    return {"ok": msg.startswith("🔴"), "msg": msg, "state": api_trade_state(u, body)}


def api_it_state(u, body):
    r = it_row(u["user_id"])
    return {"ok": True, "level": r["level"], "stage": it_stage(r["level"]), "xp": r["xp"],
            "coins": r["coins"], "tasks": r["tasks_done"], "cooldown": max(0, 60 - (now() - r["last_task"]))}



def api_it_task(u, body):
    uid = u["user_id"]
    r = it_row(uid)
    left = 60 - (now() - r["last_task"])
    if left > 0:
        return w_err(f"Следующее задание через {dur(left)}")
    title, desc, chance, base = random.choice(IT_TASKS)
    ok = random.random() < min(0.95, chance + 0.02 * r["level"])
    x("UPDATE it_progress SET last_task=? WHERE user_id=?", (now(), uid))
    if ok:
        amount = int(base * (1 + 0.15 * r["level"]) * (1.5 if is_premium(uid) else 1.0))
        xp = random.randint(10, 25)
        add_coin(uid, amount)
        x("UPDATE it_progress SET coins=coins+?, xp=xp+?, tasks_done=tasks_done+1, level=level+1 WHERE user_id=?", (amount, xp, uid))
        quest_inc(uid, "it")
        msg = f"✅ {title}: +{fmt(amount)} RCOIN · +{xp} XP"
    else:
        x("UPDATE it_progress SET tasks_done=tasks_done+1 WHERE user_id=?", (uid,))
        msg = f"↻ {title}: задача отправлена на доработку. Попробуй позже."
    return {"ok": True, "msg": msg}


def api_nft_state(u, body):
    uid = u["user_id"]
    uu = get_user(uid)
    bid = int(uu.get("balance_nft_id") or 0)
    pid = int(uu.get("profile_nft_id") or 0)
    rows = q("SELECT * FROM nft_items WHERE owner_id=? ORDER BY id DESC LIMIT 60", (uid,))
    items = []
    for r in rows:
        it = nft_public(r)
        it["in_balance"] = r["id"] == bid
        it["in_profile"] = r["id"] == pid
        it["emoji_id"] = nft_emoji_id(r["id"])
        items.append(it)
    return {"ok": True, "balance_id": bid, "profile_id": pid, "items": items,
            "is_admin": is_admin(uid), "balance": uu["balance_coin"]}


def api_nft_upgrade(u, body):
    try:
        nid = int(body.get("id", 0))
    except (TypeError, ValueError):
        return w_err("Неверный NFT")
    ok, msg, n = nft_upgrade(u["user_id"], nid)
    if not ok:
        return {"ok": False, "err": msg}
    return {"ok": True, "msg": msg, "item": nft_public(n), "balance": get_user(u["user_id"])["balance_coin"]}


def api_cases_state(u, body):
    return {"ok": True, "cases": [{"key": c["key"], "name": c["name"], "price": c["price"],
                                    "icon": c["icon"], "tag": c["tag"], "accent": c["accent"],
                                    "names": c["names"][:4]} for c in CASES],
            "balance": get_user(u["user_id"])["balance_coin"]}


def api_case_open(u, body):
    res = case_open(u["user_id"], str(body.get("key", "")))
    if res.get("ok"):
        res["balance"] = get_user(u["user_id"])["balance_coin"]
    return res


def api_admin_nft_create(u, body):
    uid = u["user_id"]
    if not is_admin(uid):
        return w_err("Только для администрации")
    name = (str(body.get("name") or "").strip() or "Кастомный NFT")[:30]
    try:
        number = int(body.get("number", 0) or 0)
    except (TypeError, ValueError):
        number = 0
    rarity = str(body.get("rarity") or "none").lower()
    if rarity in ("none", "нет", "-", "без", ""):
        rarity = "common"
    if rarity not in ("rare", "epic", "common"):
        return w_err("Редкость: none, rare или epic")
    model = str(body.get("model") or "")
    model = model if model in [m[0] for m in MODELS] else None
    bg = str(body.get("background") or "")
    bg = bg if bg in [b[0] for b in BGS] else None
    if number > 0 and q("SELECT 1 FROM nft_items WHERE id=?", (number,), one=True):
        return w_err(f"NFT #{number} уже существует")
    nid = make_nft(uid, name, rarity, "blank", "Кастомный NFT администратора",
                   RARITY_BASE.get(rarity, 50_000), model=model, background=bg, nft_id=number or None)
    raw = str(body.get("image") or "")
    if raw.startswith("data:image"):
        try:
            data = base64.b64decode(raw.split(",", 1)[1])
            if 0 < len(data) <= 8 * 1024 * 1024:
                NFT_DIR.mkdir(parents=True, exist_ok=True)
                (NFT_DIR / f"photo_{nid}.png").write_bytes(data)
                card = _nft_photo_card(data, name, rarity, nid)
                (NFT_DIR / f"photo_{nid}_card.png").write_bytes(card)
                kv_set(f"nftimg:{nid}", f"photo_{nid}_card.png")
                kv_set(f"nftpng:{nid}", base64.b64encode(card).decode("ascii"))
                x("UPDATE nft_items SET photo='photo' WHERE id=?", (nid,))
        except Exception:
            log.exception("admin nft image")
    if rarity in UPGRADE_RARITIES:
        x("UPDATE nft_items SET level=2 WHERE id=?", (nid,))
    if not kv_get(f"nftpng:{nid}"):
        make_nft_image(nid)
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    return {"ok": True, "msg": f"NFT #{nid} создан", "item": nft_public(n)}


def api_admin_ui(u, body):
    uid = u["user_id"]
    if not is_admin(uid):
        return w_err("Только для администрации")
    action = str(body.get("action") or "")
    if action == "ticker":
        text = str(body.get("text") or "").strip()[:300]
        if not text:
            return w_err("Пустой текст")
        kv_set(UI_TICKER_KEY, text)
        return {"ok": True, "ticker": text, "msg": "Тикер обновлён"}
    if action == "theme":
        theme = str(body.get("theme") or "").strip()[:24] or UI_THEME_DEFAULT
        kv_set(UI_THEME_KEY, theme)
        return {"ok": True, "theme": theme, "msg": "Тема по умолчанию обновлена"}
    if action == "redraw":
        n = redraw_nft_art()
        return {"ok": True, "count": n, "msg": f"Сброшено {n} превью"}
    if action == "reset":
        if uid != OWNER_ID:
            return w_err("Новая коллекция доступна только владельцу")
        if str(body.get("confirm") or "").strip().upper() != "RESET":
            return w_err("Введи RESET для подтверждения")
        res = reset_nft_collection()
        return {"ok": True, **res, "msg": "Коллекция пересоздана"}
    if action == "arena_bonus":
        try:
            amount = int(body.get("amount") or 0)
        except (TypeError, ValueError):
            return w_err("Неверная сумма")
        return ar_admin_bonus(uid, amount)
    return w_err("Неизвестное действие")


def api_nft_set(u, body):
    uid = u["user_id"]
    try:
        nid = int(body.get("id", 0))
    except (TypeError, ValueError):
        return w_err("Неверный NFT")
    target = str(body.get("target", ""))
    if target not in ("balance", "profile"):
        return w_err("Неверная цель")
    if not q("SELECT 1 FROM nft_items WHERE id=? AND owner_id=?", (nid, uid), one=True):
        return w_err("NFT не найден")
    col = "balance_nft_id" if target == "balance" else "profile_nft_id"
    current = int(get_user(uid).get(col) or 0)
    new_value = 0 if current == nid else nid
    update_user(uid, **{col: new_value})
    return {"ok": True, "msg": "Откреплено" if new_value == 0 else "Фото закреплено", "pinned": new_value}


def api_nft_photo(u, body):
    uid = u["user_id"]
    if not is_admin(uid):
        return w_err("NFT из фото создаёт только владелец")
    raw = str(body.get("image") or "")
    if not raw.startswith("data:image"):
        return w_err("Нужно фото")
    try:
        data = base64.b64decode(raw.split(",", 1)[1])
    except Exception:
        return w_err("Битое изображение")
    if not data or len(data) > 8 * 1024 * 1024:
        return w_err("Фото до 6 МБ")
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
    except Exception:
        return w_err("Это не картинка")
    title = (str(body.get("name") or "").strip() or "Фото NFT")[:30]
    try:
        number = int(body.get("number", 0) or 0)
    except (TypeError, ValueError):
        number = 0
    if number > 0 and q("SELECT 1 FROM nft_items WHERE id=?", (number,), one=True):
        return w_err(f"NFT #{number} уже существует")
    rarity = str(body.get("rarity") or "rare").lower()
    if rarity not in UPGRADE_RARITIES:
        rarity = "rare"
    nid = make_nft(uid, title, rarity, "photo", "NFT из личного фото",
                   RARITY_BASE[rarity], model="Призрачный", background="Галактика",
                   nft_id=number or None)
    try:
        NFT_DIR.mkdir(parents=True, exist_ok=True)
        (NFT_DIR / f"photo_{nid}.png").write_bytes(data)
        card = _nft_photo_card(data, title, rarity, nid)
        (NFT_DIR / f"photo_{nid}_card.png").write_bytes(card)
        kv_set(f"nftimg:{nid}", f"photo_{nid}_card.png")
        kv_set(f"nftpng:{nid}", base64.b64encode(card).decode("ascii"))
        x("UPDATE nft_items SET level=2 WHERE id=?", (nid,))
    except Exception:
        log.exception("api_nft_photo save")
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    return {"ok": True, "msg": f"NFT #{nid} создан", "id": nid, "item": nft_public(n)}


def api_nft_to_archive(u, body):
    try:
        nid = int(body.get("id", 0))
    except (TypeError, ValueError):
        return w_err("Неверный NFT")
    if not archive_take_nft(nid, u["user_id"]):
        return w_err("NFT не найден или стоит на продаже")
    return {"ok": True, "msg": "NFT пополнил архив"}


def api_nft_mint(u, body):
    try:
        ok, msg = mint_nft(u["user_id"])
    except Exception as e:
        log.exception("nft_mint")
        return {"ok": False, "err": f"Не удалось создать NFT: {e}"}
    return {"ok": ok, "msg": re.sub(r"<[^>]+>", "", msg)}


EMOJI_CACHE: Dict[str, Tuple[bytes, str]] = {}
_emoji_lock: Optional[asyncio.Lock] = None


async def emoji_asset(request: web.Request):
    """Отдаёт статичную картинку кастомного эмодзи для веб-приложения."""
    eid = re.sub(r"\D", "", request.match_info["eid"].split(".")[0])
    if not eid:
        raise web.HTTPNotFound()
    hit = EMOJI_CACHE.get(eid)
    if hit:
        return web.Response(body=hit[0], content_type=hit[1], headers={"Cache-Control": "public, max-age=604800"})
    global _emoji_lock
    if _emoji_lock is None:
        _emoji_lock = asyncio.Lock()
    async with _emoji_lock:
        hit = EMOJI_CACHE.get(eid)
        if hit:
            return web.Response(body=hit[0], content_type=hit[1], headers={"Cache-Control": "public, max-age=604800"})
        try:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=[eid])
        except Exception as e:
            log.debug("emoji fetch %s: %s", eid, e)
            stickers = []
        if not stickers:
            raise web.HTTPNotFound()
        sticker = stickers[0]
        thumb = getattr(sticker, "thumbnail", None)
        file_id = thumb.file_id if thumb else sticker.file_id
        try:
            f = await bot.get_file(file_id)
            buf = await bot.download_file(f.file_path)
            raw = buf.getvalue()
            mime = "image/webp"
            if raw[:8] == b"\x89PNG\r\n\x1a\n":
                mime = "image/png"
            elif raw[:4] == b"GIF8":
                mime = "image/gif"
            elif raw[:2] == b"\xff\xd8":
                mime = "image/jpeg"
            EMOJI_CACHE[eid] = (raw, mime)
            return web.Response(body=raw, content_type=mime, headers={"Cache-Control": "public, max-age=604800"})
        except Exception as e:
            log.warning("emoji download %s: %s", eid, e)
            raise web.HTTPNotFound()


def _emoji_mime(raw: bytes) -> str:
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:4] == b"GIF8":
        return "image/gif"
    if raw[:2] == b"\xff\xd8":
        return "image/jpeg"
    return "image/webp"


async def warm_nft_emojis():
    """Прогревает картинки NFT-эмодзи, чтобы они попадали в PNG-карточки."""
    await asyncio.sleep(3)
    ids = []
    for i in range(len(NFT_EMOJI_KEYS)):
        eid = nft_emoji_id(i)
        if eid and eid not in ids:
            ids.append(eid)
    for eid in ids:
        if eid in EMOJI_CACHE:
            continue
        try:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=[eid])
            if not stickers:
                continue
            st = stickers[0]
            thumb = getattr(st, "thumbnail", None)
            f = await bot.get_file(thumb.file_id if thumb else st.file_id)
            buf = await bot.download_file(f.file_path)
            raw = buf.getvalue()
            EMOJI_CACHE[eid] = (raw, _emoji_mime(raw))
        except Exception as e:
            log.debug("warm emoji %s: %s", eid, e)
        await asyncio.sleep(0.05)
    log.info("NFT-эмодзи прогреты: %s", len(ids))


MINING_FAN = Path(__file__).with_name("mining_art") / "fan.jpg"


_FAN_PNG = {}


def _draw_fan() -> bytes:
    """Кулер, нарисованный кодом — работает без файлов."""
    size = 640
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6, 6, size - 6, size - 6), fill=(24, 18, 42, 255), outline=(96, 64, 178, 255), width=12)
    for i in range(9):
        a0 = i * 40 + 6
        d.pieslice((74, 74, size - 74, size - 74), a0, a0 + 30, fill=(128, 84, 244, 255))
        d.pieslice((86, 86, size - 86, size - 86), a0 + 2, a0 + 26, fill=(162, 118, 255, 255))
    d.ellipse((size // 2 - 96, size // 2 - 96, size // 2 + 96, size // 2 + 96),
              fill=(16, 11, 30, 255), outline=(200, 74, 107, 255), width=8)
    d.ellipse((size // 2 - 58, size // 2 - 58, size // 2 + 58, size // 2 + 58),
              fill=(224, 40, 79, 255))
    d.ellipse((size // 2 - 30, size // 2 - 40, size // 2 + 4, size // 2 - 4),
              fill=(255, 160, 180, 200))
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


async def mining_fan_asset(request: web.Request):
    if MINING_FAN.is_file():
        return web.FileResponse(MINING_FAN, headers={"Cache-Control": "public, max-age=604800"})
    if "png" not in _FAN_PNG:
        _FAN_PNG["png"] = _draw_fan()
    return web.Response(body=_FAN_PNG["png"], content_type="image/png",
                        headers={"Cache-Control": "public, max-age=604800"})


async def logo_asset(request: web.Request):
    """Логотип для шапки веб-приложения: свой файл или нарисованный ромб."""
    if BALANCE_BANNER.exists():
        return web.FileResponse(BALANCE_BANNER, headers={"Cache-Control": "public, max-age=86400"})
    if "png" not in _LOGO_PNG:
        im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, 127, 127), 30, fill=(24, 16, 48, 255))
        d.polygon([(64, 18), (110, 64), (64, 110), (18, 64)], fill=(199, 182, 255, 255))
        d.polygon([(64, 34), (94, 64), (64, 94), (34, 64)], fill=(109, 40, 217, 255))
        out = io.BytesIO()
        im.save(out, format="PNG")
        _LOGO_PNG["png"] = out.getvalue()
    return web.Response(body=_LOGO_PNG["png"], content_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


_LOGO_PNG = {}


async def wall_asset(request: web.Request):
    """Обои интерфейса: размытый арт из code-art, внешних файлов не требует."""
    if "png" not in _LOGO_PNG:
        bright = Image.new("RGB", (720, 1200), (10, 6, 24))
        ov = Image.new("RGBA", bright.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for x, y, r, col in ((120, 120, 330, (124, 58, 237, 120)), (620, 420, 380, (219, 39, 119, 80)),
                             (300, 1080, 420, (37, 99, 235, 90))):
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        bright = Image.alpha_composite(bright.convert("RGBA"), ov).filter(ImageFilter.GaussianBlur(60)).convert("RGB")
        out = io.BytesIO()
        bright.save(out, format="JPEG", quality=72)
        _LOGO_PNG["wall"] = out.getvalue()
    return web.Response(body=_LOGO_PNG["wall"], content_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


async def banner_asset(request: web.Request):
    if BALANCE_BANNER.exists():
        return web.FileResponse(BALANCE_BANNER, headers={"Cache-Control": "public, max-age=86400"})
    raise web.HTTPNotFound()


async def nft_asset(request: web.Request):
    try:
        nid = int(request.match_info["nid"])
        row = q("SELECT id,photo,name,model,background,rarity,level FROM nft_items WHERE id=?", (nid,), one=True)
        if not row:
            raise web.HTTPNotFound()
        png_data = kv_get(f"nftpng:{nid}")
        if png_data:
            try:
                raw_png = base64.b64decode(png_data, validate=True)
                return web.Response(body=raw_png, content_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
            except Exception:
                log.warning("NFT PNG повреждён: %s", nid)
        svg = kv_get(f"nftsvg:{nid}")
        if svg:
            return web.Response(text=svg, content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
        filename = (kv_get(f"nftimg:{nid}") or row["photo"] or "").strip()
        path = Path(filename)
        if not path.is_absolute():
            path = NFT_DIR / path.name
        if path.exists() and path.parent.resolve() == NFT_DIR.resolve():
            return web.FileResponse(path, headers={"Cache-Control": "public, max-age=3600"})
        try:
            raw = png_nft(nid, row["name"], row.get("photo", ""), row.get("model", ""), row.get("background", ""), row.get("rarity", "common"), int(row.get("level", 1)))
            kv_set(f"nftpng:{nid}", base64.b64encode(raw).decode("ascii"))
            return web.Response(body=raw, content_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            log.warning("NFT regen png %s: %s", nid, e)
        try:
            svg = svg_nft(nid, row["name"])
            kv_set(f"nftsvg:{nid}", svg)
            return web.Response(text=svg, content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            log.warning("NFT regen svg %s: %s", nid, e)
            raise web.HTTPNotFound()
    except (ValueError, TypeError):
        raise web.HTTPNotFound()

async def archive_asset(request: web.Request):
    """Превью лота NFT-архива: рисуется кодом, файлов не требует."""
    try:
        aid = int(request.match_info["aid"])
        row = q("SELECT * FROM nft_archive WHERE id=?", (aid,), one=True)
        if not row:
            raise web.HTTPNotFound()
        raw = png_nft(aid * 31 + 7, row["name"], row.get("photo") or "✨",
                      row.get("model") or "", row.get("background") or "",
                      row.get("rarity") or "common", 2)
        return web.Response(body=raw, content_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
    except (ValueError, TypeError):
        raise web.HTTPNotFound()


def api_prices():
    """Публичный курс для live-графика (без авторизации)."""
    k = int(time.time() / TICK)
    return {"price": market_price(), "tick": TICK,
            "series": [{"t": (k - 119 + i) * TICK * 1000, "p": price_at((k - 119 + i) * TICK)} for i in range(120)]}



# =====================================================================
#                        УСТОЙЧИВОСТЬ (Render)
# =====================================================================

async def price_broadcast():
    """Держит кэш цены свежим, чтобы Web App отвечал мгновенно."""
    while True:
        try:
            market_price()
        except Exception:
            pass
        await asyncio.sleep(30)


async def watchdog():
    """Сторож: перенастраивает меню и держит процесс живым на Render."""
    await asyncio.sleep(20)
    while True:
        try:
            if WEBAPP_URL and bot:
                from aiogram.types import MenuButtonWebApp
                await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
                    text="Treyding", web_app=WebAppInfo(url=WEBAPP_URL)))
        except Exception as e:
            log.debug("watchdog menu: %s", e)
        await asyncio.sleep(3600)



# =====================================================================
#            ПРЕДНОВОГОДНЕЕ ОБНОВЛЕНИЕ: АРХИВ / МАЙНИНГ / АПГРЕЙДЕР
# =====================================================================
ARCHIVE_TG = "@rubinarxiv"


# ---------------------------- АРХИВ БАЛАНСА ----------------------------
def archive_view(uid: int) -> str:
    u = get_user(uid)
    arch = int(u.get("archive_coin") or 0)
    bal = int(u.get("balance_coin") or 0)
    room = max(0, MAX_BALANCE - bal)
    return box(f"{E('treasury')} <b>АРХИВ</b>",
               f"💰 Баланс: <b>{fmt(bal)}</b> / лимит {fmt(MAX_BALANCE)}",
               f"🏛 В Архиве: <b>{fmt(arch)}</b>",
               f"📥 Доступно к снятию: {fmt(min(arch, room))}",
               "Всё, что приходит сверх лимита, автоматически падает в Архив.")


def archive_kb(uid: int) -> InlineKeyboardMarkup:
    return kb([btn("Снять 100кк", "arch:w:100000000", "treasury")],
              [btn("Снять всё", "arch:w:0", "balance")],
              [btn("Назад", "menu:main", "door")])


def archive_withdraw(uid: int, amount: int = 0) -> tuple:
    """Архив → баланс, не выше MAX_BALANCE. Возвращает (переведено, остаток архива)."""
    u = get_user(uid)
    arch = int(u.get("archive_coin") or 0)
    room = max(0, MAX_BALANCE - int(u.get("balance_coin") or 0))
    if arch <= 0 or room <= 0:
        return 0, arch
    take = min(arch, room if amount <= 0 else min(amount, room))
    if take <= 0:
        return 0, arch
    if x("UPDATE users SET archive_coin=archive_coin-?, balance_coin=balance_coin+? "
         "WHERE user_id=? AND archive_coin>=?", (take, take, uid, take))[0] != 1:
        return 0, arch
    return take, arch - take


@dp.message(P("архив", "archive"))
async def cmd_archive(message: Message):
    uid = message.from_user.id
    get_user(uid)
    await message.reply(archive_view(uid), reply_markup=archive_kb(uid))


@dp.callback_query(F.data.startswith("arch:w:"))
async def cb_archive_withdraw(cb: CallbackQuery):
    uid = cb.from_user.id
    amount = int(cb.data.split(":")[2])
    got, left = archive_withdraw(uid, amount)
    if got <= 0:
        return await ans(cb, "Снимать нечего или баланс уже на лимите", True)
    await safe_edit(cb, archive_view(uid), archive_kb(uid))
    await ans(cb, f"+{fmt(got)} RCOIN из Архива", True)


# ---------------------------- МАЙНИНГ ----------------------------
MINING_TERM = 30 * 86400
MINING_SERVERS = [
    (5, "Мини", 10_000_000, 250_000),
    (0, "Старт", 150_000_000, 3_000_000),
    (1, "Про", 500_000_000, 12_000_000),
    (2, "Бизнес", 1_000_000_000, 30_000_000),
    (3, "Дата-центр", 2_500_000_000, 90_000_000),
    (4, "Квант", 5_000_000_000, 200_000_000),
]
SERVER_BY_TIER = {v[0]: v for v in MINING_SERVERS}


def grant_server(uid: int, tier: int) -> bool:
    sv = SERVER_BY_TIER.get(int(tier))
    if not sv:
        return False
    mining_sync(uid)
    x("INSERT INTO mining_servers(user_id,tier,bought_at,expires_at) VALUES(?,?,?,?) "
      "ON CONFLICT(user_id,tier) DO UPDATE SET expires_at=excluded.expires_at, bought_at=excluded.bought_at",
      (uid, int(tier), now(), now() + MINING_TERM))
    return True


def mining_servers(uid: int) -> List[dict]:
    return q("SELECT * FROM mining_servers WHERE user_id=? AND expires_at>?", (uid, now()))


def mining_rate(uid: int) -> int:
    active = {r["tier"] for r in mining_servers(uid)}
    return sum(v[3] for v in MINING_SERVERS if v[0] in active)


def mining_sync(uid: int) -> int:
    u = get_user(uid)
    last = int(u.get("mine_last") or 0)
    if not last:
        update_user(uid, mine_last=now())
        return int(u.get("mine_pending") or 0)
    rate = mining_rate(uid)
    dt = max(0, now() - last)
    pending = int(u.get("mine_pending") or 0)
    if rate and dt:
        pending = min(MAX_BALANCE * 2, pending + rate * dt // 86400)
    update_user(uid, mine_pending=pending, mine_last=now())
    return pending


def mining_view(uid: int) -> str:
    pending = mining_sync(uid)
    rate = mining_rate(uid)
    owned = {r["tier"]: r for r in mining_servers(uid)}
    lines = [f"{E('miner')} <b>МАЙНИНГ</b>", ""]
    for tier, name, cost, per_day in MINING_SERVERS:
        if tier in owned:
            left = dur(owned[tier]["expires_at"] - now())
            lines.append(f"🟢 <b>{name}</b> — {fmt(per_day)}/сутки, осталось {left}")
        else:
            lines.append(f"⚪ <b>{name}</b> — {fmt(cost)} RCOIN · {fmt(per_day)}/сутки · 30 дней")
    rows = []
    for tier, name, cost, _ in MINING_SERVERS:
        if tier not in owned:
            rows.append([btn(f"{name} · {fmt(cost)}", f"mng:b:{tier}", "miner"),
                         btn("50 ⭐", f"mng:s:{tier}", "star")])
    rows.append([btn(f"Снять {fmt(pending)}", "mng:c", "balance")])
    rows.append([btn("Назад", "menu:main", "door")])
    lines += ["", f"⛏ Добыча: <b>{fmt(rate)}</b>/сутки", f"📦 Накоплено: <b>{fmt(pending)}</b> RCOIN"]
    return "\n".join(lines), kb(*rows)


@dp.message(P("майнинг", "mining"))
async def cmd_mining(message: Message):
    text, markup = mining_view(message.from_user.id)
    await message.reply(text, reply_markup=markup)


@dp.callback_query(F.data.startswith("mng:"))
async def cb_mining(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split(":")
    if parts[1] == "b":
        tier = int(parts[2])
        sv = SERVER_BY_TIER.get(tier)
        if not sv:
            return await ans(cb, "Нет такого сервера", True)
        if q("SELECT 1 FROM mining_servers WHERE user_id=? AND tier=? AND expires_at>?", (uid, tier, now()), one=True):
            return await ans(cb, "Уже куплен", True)
        if not spend(uid, sv[2]):
            return await ans(cb, f"Нужно {fmt(sv[2])} RCOIN", True)
        mining_sync(uid)
        x("INSERT INTO mining_servers(user_id,tier,bought_at,expires_at) VALUES(?,?,?,?) "
          "ON CONFLICT(user_id,tier) DO UPDATE SET expires_at=excluded.expires_at, bought_at=excluded.bought_at",
          (uid, tier, now(), now() + MINING_TERM))
        text, markup = mining_view(uid)
        await safe_edit(cb, text, markup)
        return await ans(cb, f"Сервер «{sv[1]}» куплен!", True)
    if parts[1] == "s":
        tier = int(parts[2])
        sv = SERVER_BY_TIER.get(tier)
        if not sv:
            return await ans(cb, "Нет такого сервера", True)
        if q("SELECT 1 FROM mining_servers WHERE user_id=? AND tier=? AND expires_at>?", (uid, tier, now()), one=True):
            return await ans(cb, "Уже куплен", True)
        await stars_invoice(uid, 50, f"Сервер «{sv[1]}»", "Сервер на 30 дней за 50 ⭐", f"server:{tier}")
        return await ans(cb, "Счёт на 50 ⭐ выставлен")
    if parts[1] == "c":
        pending = mining_sync(uid)
        if pending <= 0:
            return await ans(cb, "Пока нечего снимать", True)
        if x("UPDATE users SET mine_pending=0 WHERE user_id=? AND mine_pending=?", (uid, pending))[0] != 1:
            return await ans(cb, "Попробуй ещё раз", True)
        over = add_coin(uid, pending)
        text, markup = mining_view(uid)
        await safe_edit(cb, text, markup)
        note = f" (+{fmt(over)} в Архив)" if over else ""
        return await ans(cb, f"+{fmt(pending - over)} RCOIN{note}", True)


# ---------------------------- NFT-АРХИВ / АПГРЕЙДЕР ----------------------------
UPG_CHANCE = {"common": 30, "rare": 45, "epic": 60, "uncommon": 45, "legendary": 60}
RARITY_IDX = {r: i for i, r in enumerate(RARITIES)}


def archive_count() -> int:
    return int(q("SELECT COUNT(*) c FROM nft_archive", one=True)["c"])


PREMIUM_LOTS = [
    ("Дух Нового года", "🎆", "epic", 1_000_000_000),
    ("Ёлка-мультивселенная", "🌌", "epic", 850_000_000),
    ("Золотой Дед Мороз", "👑", "epic", 700_000_000),
    ("Северное сияние Prime", "🌠", "epic", 500_000_000),
    ("Кибер-снеговик 2077", "🤖", "epic", 500_000_000),
    ("Хрустальная ёлка", "🎄", "rare", 250_000_000),
]


def archive_add(nft: dict, price: int = 0) -> None:
    x("INSERT INTO nft_archive(rarity,name,photo,model,background,price,created_at) VALUES(?,?,?,?,?,?,?)",
      (nft["rarity"], nft["name"], nft.get("photo") or "🎁", nft.get("model") or "Стандартный",
       nft.get("background") or "Обычный", int(price), now()))


def archive_seed(n: int = 40) -> int:
    """Наполняет NFT-архив, чтобы апгрейдер работал с первого дня."""
    have = archive_count()
    if have >= n:
        return 0
    made = 0
    per = max(2, n // len(RARITIES))
    for rar in RARITIES:
        for _ in range(per):
            name, photo = random.choice(NFT_POOL[rar])
            archive_add({"rarity": rar, "name": name, "photo": photo,
                         "model": random.choice([m[0] for m in MODELS]),
                         "background": random.choice([b[0] for b in BGS])})
            made += 1
    if not q("SELECT 1 FROM nft_archive WHERE price>=500000000", one=True):
        for name, photo, rar, price in PREMIUM_LOTS:
            archive_add({"rarity": rar, "name": name, "photo": photo,
                         "model": "Космический", "background": "Галактика"}, price)
            made += 1
    return made


def seed_nft_archive():
    try:
        ensure_cols("nft_archive", {"price": "INTEGER DEFAULT 0"})
        archive_seed()
    except Exception:
        log.exception("seed_nft_archive")


def archive_take_nft(nid: int, uid: int) -> bool:
    """Переносит NFT игрока в архив (для @rubinarxiv и проигрыша в апгрейдере)."""
    n = q("SELECT * FROM nft_items WHERE id=? AND owner_id=?", (nid, uid), one=True)
    if not n or nft_is_infinite(n) or n["for_sale"]:
        return False
    if x("DELETE FROM nft_items WHERE id=? AND owner_id=? AND for_sale=0", (nid, uid))[0] != 1:
        return False
    archive_add(n)
    return True


UPG_COIN_CHANCE = {2.0: 40, 4.0: 20, 8.0: 8}


def upg_pool() -> int:
    try:
        return max(0, int(kv_get("upg:pool") or 0))
    except Exception:
        return 0


def upg_pool_add(n: int):
    kv_set("upg:pool", str(upg_pool() + int(n)))


def upg_pool_take(n: int) -> bool:
    pool = upg_pool()
    if n <= 0 or pool < n:
        return False
    kv_set("upg:pool", str(pool - n))
    return True


def upg_coins(uid: int, bet: int, mult: float) -> dict:
    """Апгрейд RCOIN: ставка уходит в пул, при победе выплата ставка×множитель из пула."""
    bet = int(bet)
    mult = float(mult)
    if bet < 10_000:
        return {"ok": False, "err": "Минимум 10 000 RCOIN"}
    if bet > MAX_BALANCE:
        return {"ok": False, "err": f"Максимум {fmt(MAX_BALANCE)}"}
    if mult not in UPG_COIN_CHANCE:
        return {"ok": False, "err": "Неверный множитель"}
    chance = UPG_COIN_CHANCE[mult]
    if not spend(uid, bet):
        return {"ok": False, "err": "Недостаточно RCOIN"}
    upg_pool_add(bet)
    win = random.randint(1, 100) <= chance
    payout = int(bet * mult)
    if win:
        if not upg_pool_take(payout):
            upg_pool_take(bet)
            add_coin(uid, bet)
            return {"ok": False, "err": "В архиве апгрейдера не хватает RCOIN — пополни его"}
        over = add_coin(uid, payout)
        return {"ok": True, "win": True, "chance": chance, "payout": payout - over,
                "archived": over, "pool": upg_pool()}
    return {"ok": True, "win": False, "chance": chance, "pool": upg_pool()}


def upg_chance(n: dict, bet: int = 0) -> int:
    return min(88, UPG_CHANCE.get(n["rarity"], 30) + min(10, max(0, int(bet)) // 100_000_000))


def upg_spin(uid: int, ids, bet: int = 0, target: str = "", mode: str = "") -> dict:
    """Крутит апгрейдер. ids — до 5 NFT игрока, bet — донат RCOIN.
    mode: "nft" — выиграть можно только NFT; "coins" — только RCOIN;
    по умолчанию архивный лот, а при пустом архиве — коины."""
    if isinstance(ids, int):
        ids = [ids]
    ids = [int(x) for x in (ids or [])][:5]
    mode = str(mode or "")
    bet = max(0, min(int(bet or 0), MAX_BET))
    if mode == "coins" and not ids:
        return {"ok": False, "err": "Для режима RCOIN выбери NFT-залог"}
    if not ids:
        return {"ok": False, "err": "Выбери NFT"}
    rows = [r for r in (q("SELECT * FROM nft_items WHERE id=? AND owner_id=?", (i, uid), one=True) for i in ids) if r]
    if len(rows) != len(ids):
        return {"ok": False, "err": "NFT не найден"}
    if any(nft_is_infinite(r) or r["for_sale"] for r in rows):
        return {"ok": False, "err": "Эти NFT нельзя ставить"}
    target = str(target or "")
    lot = None
    if target.startswith("a:") and target[2:].isdigit():
        lot = q("SELECT * FROM nft_archive WHERE id=?", (int(target[2:]),), one=True)
    best = max(rows, key=lambda r: RARITY_IDX.get(r["rarity"], 0))
    stake = sum(nft_value(r) for r in rows) + bet
    chance = min(88, upg_chance(best, bet) + 5 * (len(rows) - 1))
    if bet and not spend(uid, bet):
        return {"ok": False, "err": "Недостаточно RCOIN для бонуса"}
    for r in rows:
        x("DELETE FROM nft_items WHERE id=? AND owner_id=? AND for_sale=0", (r["id"], uid))
    if mode == "coins":
        coins = max(int(stake * 1.6), RARITY_BASE.get(best["rarity"], 50_000))
        if random.randint(1, 100) <= chance:
            over = add_coin(uid, coins)
            x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
              (uid, ids[0], best["rarity"], "coins", chance, now()))
            return {"ok": True, "win": True, "chance": chance, "coins": coins - over, "archived": over,
                    "name": f"{fmt(coins - over)} RCOIN", "rarity": "coins"}
        for r in rows:
            archive_add(r)
        x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
          (uid, ids[0], best["rarity"], "lose", chance, now()))
        return {"ok": True, "win": False, "chance": chance, "msg": "NFT ушли в архив"}
    if random.randint(1, 100) <= chance:
        all_rows = q("SELECT * FROM nft_archive")
        if lot:
            pool = [lot]
        elif target in RARITY_IDX:
            pool = [r for r in all_rows if r["rarity"] == target]
            if not pool:
                pool = [r for r in all_rows if RARITY_IDX.get(r["rarity"], 0) >= RARITY_IDX[target]]
        else:
            pool = [r for r in all_rows if RARITY_IDX.get(r["rarity"], 0) >= RARITY_IDX.get(best["rarity"], 0)]
        if not pool:
            pool = sorted(all_rows, key=lambda r: -int(r.get("price") or 0))[:12]
        if mode == "nft" and not lot and target in ("", "auto"):
            # Режим «только NFT»: при пустом архиве рисуем свежую модель,
            # чтобы победа никогда не превращалась в коины.
            rarity = random.choice(UPGRADE_RARITIES)
            name, photo = random.choice(nft_pool(rarity))
            v = nft_variant(random.randint(1, 10_000_000))
            new_id = make_nft(uid, name, rarity, photo, "Выиграно в апгрейдере",
                              model=v["model"], background=v["background"])
            make_nft_image(new_id)
            x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
              (uid, ids[0], best["rarity"], "win", chance, now()))
            return {"ok": True, "win": True, "chance": chance, "nft_id": new_id,
                    "name": name, "rarity": RARITY_NAME.get(rarity, rarity), "url": f"/nft/{new_id}?v=2"}
        if pool:
            pick = random.choice(pool)
            x("DELETE FROM nft_archive WHERE id=?", (pick["id"],))
            new_id = make_nft(uid, pick["name"], pick["rarity"], pick["photo"], "Выиграно в апгрейдере",
                              model=pick["model"], background=pick["background"])
            make_nft_image(new_id)
            x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
              (uid, ids[0], best["rarity"], "win", chance, now()))
            return {"ok": True, "win": True, "chance": chance, "nft_id": new_id,
                    "name": pick["name"], "rarity": RARITY_NAME.get(pick["rarity"], pick["rarity"]),
                    "url": f"/nft/{new_id}"}
        # Архив пуст — улучшение выплачивается коинами.
        coins = max(int(stake * 1.5), RARITY_BASE.get(best["rarity"], 50_000))
        over = add_coin(uid, coins)
        x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
          (uid, ids[0], best["rarity"], "coins", chance, now()))
        return {"ok": True, "win": True, "coins": coins - over, "archived": over,
                "chance": chance, "name": f"{fmt(coins - over)} RCOIN", "rarity": "coins"}
    for r in rows:
        archive_add(r)
    x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(?,?,?,?,?,?)",
      (uid, ids[0], best["rarity"], "lose", chance, now()))
    return {"ok": True, "win": False, "chance": chance, "msg": "NFT ушли в архив"}


def upg_stuck() -> int:
    return int(q("SELECT COUNT(*) c FROM upg_log WHERE result='lose'", one=True)["c"])


def api_archive_state(u, body):
    uid = u["user_id"]
    rows = q("SELECT * FROM nft_items WHERE owner_id=? AND for_sale=0 AND price>=0 ORDER BY id DESC LIMIT 40", (uid,))
    items = []
    for r in rows:
        items.append({"id": r["id"], "name": r["name"], "rarity": RARITY_NAME.get(r["rarity"], r["rarity"]),
                      "rt": r["rarity"], "value": nft_value(r), "level": r["level"],
                      "model": r.get("model") or "", "url": f"/nft/{r['id']}?v={r['level']}"})
    return {"ok": True, "archive": archive_count(), "stuck": upg_stuck(),
            "chance": UPG_CHANCE, "coin_chance": UPG_COIN_CHANCE, "pool": upg_pool(),
            "items": items,
            "gifts": [{"id": r["id"], "name": r["name"], "rarity": RARITY_NAME.get(r["rarity"], r["rarity"]),
                       "rt": r["rarity"], "price": int(r.get("price") or 0),
                       "url": f"/archive/{r['id']}"}
                      for r in q("SELECT * FROM nft_archive ORDER BY price DESC, id DESC LIMIT 12")]}


def api_archive_spin_coins(u, body):
    try:
        bet = int(body.get("bet", 0))
        mult = float(body.get("mult", 0))
    except (TypeError, ValueError):
        return w_err("Неверные данные")
    return upg_coins(u["user_id"], bet, mult)


def api_archive_spin(u, body):
    try:
        raw = body.get("ids")
        ids = raw if isinstance(raw, list) else [body.get("id", 0)]
        ids = [int(i) for i in ids if str(i).isdigit()]
        bet = int(body.get("bet", 0) or 0)
        target = str(body.get("target", "") or "")
        mode = str(body.get("mode", "") or "")
    except (TypeError, ValueError):
        return w_err("Неверные данные")
    return upg_spin(u["user_id"], ids, bet, target, mode)


def api_mining_state(u, body):
    uid = u["user_id"]
    pending = mining_sync(uid)
    owned = {r["tier"]: r for r in mining_servers(uid)}
    rate = mining_rate(uid)
    return {"ok": True, "pending": pending, "rate": rate, "cap": rate * 30,
            "servers": [{"tier": t, "name": n, "cost": c, "per_day": p,
                         "owned": t in owned,
                         "left": max(0, owned[t]["expires_at"] - now()) if t in owned else 0}
                        for t, n, c, p in MINING_SERVERS]}


def api_mining_buy(u, body):
    uid = u["user_id"]
    try:
        tier = int(body.get("tier", -1))
    except (TypeError, ValueError):
        return w_err("Неверный сервер")
    sv = SERVER_BY_TIER.get(tier)
    if not sv:
        return w_err("Нет такого сервера")
    if q("SELECT 1 FROM mining_servers WHERE user_id=? AND tier=? AND expires_at>?", (uid, tier, now()), one=True):
        return w_err("Уже куплен")
    if not spend(uid, sv[2]):
        return w_err(f"Нужно {fmt(sv[2])} RCOIN")
    mining_sync(uid)
    x("INSERT INTO mining_servers(user_id,tier,bought_at,expires_at) VALUES(?,?,?,?) "
      "ON CONFLICT(user_id,tier) DO UPDATE SET expires_at=excluded.expires_at, bought_at=excluded.bought_at",
      (uid, tier, now(), now() + MINING_TERM))
    return {"ok": True, "msg": f"Сервер «{sv[1]}» куплен"}


def api_mining_collect(u, body):
    uid = u["user_id"]
    pending = mining_sync(uid)
    if pending <= 0:
        return w_err("Пока нечего снимать")
    if x("UPDATE users SET mine_pending=0 WHERE user_id=? AND mine_pending=?", (uid, pending))[0] != 1:
        return w_err("Попробуй ещё раз")
    over = add_coin(uid, pending)
    return {"ok": True, "got": pending - over, "archived": over, "msg": f"+{fmt(pending - over)} RCOIN"}


# ---------------------------- NFT ИЗ ФОТО (владелец) ----------------------------
def _nft_photo_card(raw: bytes, title: str, rarity: str, seed: int = 0, level: int = 2) -> bytes:
    """Карточка NFT из загруженного фото: размытый фон + фото по центру + рамка."""
    w, h = 1280, 720
    accent = NFT_RARITY_COLOR.get(rarity, (200, 190, 255))
    src = Image.open(io.BytesIO(raw)).convert("RGB")
    cover = src.copy()
    scale = max(w / cover.width, h / cover.height)
    cover = cover.resize((int(cover.width * scale) + 1, int(cover.height * scale) + 1), Image.LANCZOS)
    cover = cover.crop(((cover.width - w) // 2, (cover.height - h) // 2,
                        (cover.width - w) // 2 + w, (cover.height - h) // 2 + h))
    im = cover.filter(ImageFilter.GaussianBlur(26))
    im = ImageEnhance.Brightness(im).enhance(0.45)
    im = im.convert("RGBA")
    inner = min(h - 220, w - 260)
    photo = src.copy()
    scale = inner / max(photo.width, photo.height)
    photo = photo.resize((max(1, int(photo.width * scale)), max(1, int(photo.height * scale))), Image.LANCZOS)
    px, py = (w - photo.width) // 2, (h - photo.height) // 2 - 20
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle((px - 10, py - 10, px + photo.width + 10, py + photo.height + 10), 26,
                        fill=(0, 0, 0, 120), outline=accent + (200,), width=3)
    im.paste(photo, (px, py))
    _nft_top_pills(im, int(seed) or int.from_bytes(hashlib.md5(raw[:4096]).digest()[:4], "big"))
    _nft_bottom_labels(im, title, rarity, "Фото владельца", accent, level=level)
    _nft_frame(im, rarity)
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


async def _create_photo_nft(target_uid: int, photo, caption: str) -> Optional[int]:
    """Скачивает фото и создаёт NFT. Возвращает id или None."""
    tokens = [t.strip() for t in (caption or "").split()][1:]
    custom_id = 0
    if tokens and tokens[-1].isdigit():
        custom_id = int(tokens.pop())
    elif tokens and tokens[0].isdigit():
        custom_id = int(tokens.pop(0))
    rarity = "rare"
    for t in tokens:
        if t.lower() in RARITY_BASE:
            rarity = t.lower()
            tokens.remove(t)
            break
    title = (tokens[0][:30] if tokens else "Фото NFT")
    try:
        f = await bot.get_file(photo.file_id)
        buf = await bot.download_file(f.file_path)
        raw = buf.read() if hasattr(buf, "read") else bytes(buf)
    except Exception:
        log.exception("nft photo download")
        return None
    nid = make_nft(target_uid, title, rarity, "photo", "NFT из личного фото",
                   RARITY_BASE[rarity], model="Призрачный", background="Галактика",
                   nft_id=(custom_id or None))
    if rarity in UPGRADE_RARITIES:
        x("UPDATE nft_items SET level=2 WHERE id=?", (nid,))
    try:
        NFT_DIR.mkdir(parents=True, exist_ok=True)
        (NFT_DIR / f"photo_{nid}.png").write_bytes(raw)
        card = _nft_photo_card(raw, title, rarity, nid)
        (NFT_DIR / f"photo_{nid}_card.png").write_bytes(card)
        kv_set(f"nftimg:{nid}", f"photo_{nid}_card.png")
        kv_set(f"nftpng:{nid}", base64.b64encode(card).decode("ascii"))
    except Exception:
        log.exception("nft photo save")
    return nid


def _is_nft_photo(message: Message) -> bool:
    cap = (message.caption or "").strip().lower()
    has_photo = bool(message.photo) or bool(message.reply_to_message and message.reply_to_message.photo)
    return has_photo and cap.startswith(("нфт", "nft", "фото"))


@dp.message(_is_nft_photo)
async def cmd_nft_from_photo(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply(f"{E('lock')} Только для администрации.")
    photo = message.photo[-1] if message.photo else message.reply_to_message.photo[-1]
    nid = await _create_photo_nft(message.from_user.id, photo, message.caption or "")
    if not nid:
        return await message.reply("Не удалось скачать фото.")
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    caption = box("🎨 <b>NFT ИЗ ФОТО ГОТОВ</b>", nft_card(n),
                  f"Номер: <code>#{nid}</code>",
                  "Передать игроку: склад → NFT → «Передать».")
    try:
        raw = png_nft(nid, n["name"], n["photo"], n["model"], n["background"], n["rarity"], n["level"])
        await message.reply_photo(BufferedInputFile(raw, filename=f"nft_{nid}.png"), caption=caption)
    except Exception:
        await message.reply(caption)


@dp.message(Command("нфтфото"))
async def cmd_nft_photo_reply(message: Message):
    if not is_admin(message.from_user.id):
        return
    srcm = message.reply_to_message
    if not srcm or not srcm.photo:
        return await message.reply("Ответь этой командой на фото или отправь фото с подписью «нфтфото Название редкость».")
    nid = await _create_photo_nft(message.from_user.id, srcm.photo[-1], message.text or "")
    if not nid:
        return await message.reply("Не удалось скачать фото.")
    n = q("SELECT * FROM nft_items WHERE id=?", (nid,), one=True)
    caption = box("🎨 <b>NFT ИЗ ФОТО ГОТОВ</b>", nft_card(n), f"Номер: <code>#{nid}</code>")
    try:
        raw = png_nft(nid, n["name"], n["photo"], n["model"], n["background"], n["rarity"], n["level"])
        await message.reply_photo(BufferedInputFile(raw, filename=f"nft_{nid}.png"), caption=caption)
    except Exception:
        await message.reply(caption)


@dp.message(P("в архив", "вархив"))
async def cmd_nft_to_archive(message: Message):
    """Отправляет NFT в веб-архив: «в архив #12» или ответом на сообщение с номером."""
    uid = message.from_user.id
    p = message.text.split()
    nid = 0
    for token in p:
        if token.startswith("#") and token[1:].isdigit():
            nid = int(token[1:])
    if not nid and len(p) >= 3 and p[2].lstrip("#").isdigit():
        nid = int(p[2].lstrip("#"))
    if not nid:
        rows = q("SELECT id,name FROM nft_items WHERE owner_id=? ORDER BY id DESC LIMIT 8", (uid,))
        if not rows:
            return await message.reply("У тебя нет NFT.")
        listing = "\n".join(f"• #{r['id']} — {esc(r['name'])}" for r in rows)
        return await message.reply(box("🏛 <b>В NFT-АРХИВ</b>", listing,
                                       "Напиши: <code>в архив #12</code>"),
                                   reply_markup=kb(*[[btn(f"#{r['id']} → архив", f"arx2:{r['id']}")] for r in rows[:6]]))
    if archive_take_nft(nid, uid):
        return await message.reply(box("🏛 <b>NFT В АРХИВЕ</b>",
                                       f"#{nid} теперь можно выиграть в апгрейдере на сайте."))
    await message.reply("NFT не найден, не твой или стоит на продаже.")


@dp.callback_query(F.data.startswith("arx2:"))
async def cb_nft_to_archive(cb: CallbackQuery):
    nid = int(cb.data.split(":")[1])
    if archive_take_nft(nid, cb.from_user.id):
        await safe_edit(cb, box("🏛 <b>NFT В АРХИВЕ</b>", f"#{nid} добавлен в веб-архив."))
        return await ans(cb, "В архиве", True)
    await ans(cb, "Не получилось", True)


@dp.message(P("нфт архив", "nft архив", "нфтархив"))
async def cmd_nft_archive_view(message: Message):
    lots = q("SELECT * FROM nft_archive ORDER BY price DESC, id DESC LIMIT 8")
    lines = [f"🏛 <b>NFT-АРХИВ</b>", f"Всего NFT: <b>{archive_count()}</b>",
             f"Пул выплат: <b>{fmt(upg_pool())}</b> RCOIN", ""]
    for r in lots:
        lines.append(f"• {RARITY_NAME.get(r['rarity'], r['rarity'])} · {esc(r['name'])}"
                     + (f" · ≈{fmt(r['price'])}" if int(r.get('price') or 0) else ""))
    rows = []
    if is_admin(message.from_user.id):
        rows = [[btn("Пополнить NFT (+25)", "arx:fill", "treasury")],
                [btn("Пополнить пул на 100кк", "arx:pool:100000000", "balance")],
                [btn("Пополнить пул на 1ккк", "arx:pool:1000000000", "balance")]]
    await message.reply("\n".join(lines), reply_markup=kb(*rows) if rows else None)


@dp.message(P("апгрейд архив"))
async def cmd_upg_archive(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply(f"{E('lock')} Только для владельца.")
    parts = message.text.split()
    rest = parts[2:] if len(parts) > 2 else []
    if rest and rest[0].lower() in ("купить", "buy"):
        try:
            n = int(rest[1]) if len(rest) > 1 else 10
        except ValueError:
            n = 10
        n = max(1, min(n, 200))
        cost = n * 10_000_000
        if not spend(message.from_user.id, cost):
            return await message.reply(f"Нужно {fmt(cost)} RCOIN (по 10кк за NFT).")
        made = archive_seed(archive_count() + n)
        return await message.reply(f"🏛 Куплено {made} NFT за {fmt(cost)}. В архиве: {archive_count()}")
    if rest and rest[0].lower() in ("нфт", "nft"):
        try:
            n = int(rest[1]) if len(rest) > 1 else 25
        except ValueError:
            n = 25
        made = archive_seed(archive_count() + max(1, min(n, 200)))
        return await message.reply(f"🏛 Архив пополнен на {made} NFT. Всего: {archive_count()}")
    if rest:
        amount = parse_amount(rest[0])
        if amount <= 0:
            return await message.reply("Формат: <code>апгрейд архив 100ккк</code> или <code>апгрейд архив нфт 25</code>")
        upg_pool_add(amount)
        return await message.reply(f"💰 Пул выплат пополнен на {fmt(amount)}. Сейчас: {fmt(upg_pool())}")
    await message.reply(
        box("🛠 <b>АРХИВ АПГРЕЙДЕРА</b>",
            f"NFT в архиве: <b>{archive_count()}</b>",
            f"Пул выплат: <b>{fmt(upg_pool())}</b> RCOIN",
            "Пополнить: <code>апгрейд архив 100ккк</code>",
            "NFT: <code>апгрейд архив нфт 25</code>"),
        reply_markup=kb([btn("+25 NFT", "arx:fill", "treasury")],
                        [btn("+100кк в пул", "arx:pool:100000000", "balance")]))


@dp.callback_query(F.data.startswith("arx:pool:"))
async def cb_pool_add(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет доступа", True)
    amount = int(cb.data.split(":")[2])
    upg_pool_add(amount)
    await ans(cb, f"Пул: {fmt(upg_pool())} RCOIN", True)


# =====================================================================
#                    ИСТОРИЯ / НЕЗАВЕРШЁННЫЕ ИГРЫ
# =====================================================================
SESSION_TITLES = {"mines": "💣 Мины", "climb": "🗼 Башня", "labyrinth": "🌿 Лабиринт",
                  "hilo": "🎴 Хай-Лоу", "sun": "☀️ Солнце", "bj": "🃏 Очко",
                  "ttt": "❌ Крестики", "webcrash": "🚀 Краш"}


def history_view(uid: int):
    act = q("SELECT * FROM sessions WHERE user_id=? AND status IN ('active','pending') ORDER BY id DESC LIMIT 8", (uid,))
    done = q("SELECT game,bet,status,created_at FROM sessions WHERE user_id=? AND status NOT IN ('active','pending') ORDER BY id DESC LIMIT 6", (uid,))
    lines = [f"📜 <b>ИСТОРИЯ</b>", ""]
    rows = []
    if act:
        lines.append("<b>Незавершённые игры:</b>")
        for s in act:
            name = SESSION_TITLES.get(s["game"], s["game"])
            lines.append(f"• {name} · ставка {fmt(s['bet'])} · <code>#{s['id']}</code>")
            rows.append([btn(f"{name} · {fmt(s['bet'])}", f"res:{s['id']}", "games")])
    else:
        lines.append("<i>Незавершённых игр нет.</i>")
    if done:
        lines.append("")
        lines.append("<b>Последние игры:</b>")
        for s in done:
            name = SESSION_TITLES.get(s["game"], s["game"])
            ts = datetime.fromtimestamp(s["created_at"], MSK).strftime("%d.%m %H:%M") if s["created_at"] else "—"
            lines.append(f"• {name} · {fmt(s['bet'])} · {ts}")
    lines.append("")
    lines.append("Открыть незавершённую игру можно из любого чата.")
    return "\n".join(lines), (kb(*rows) if rows else None)


@dp.message(P("история", "history"))
async def cmd_history(message: Message):
    text, markup = history_view(message.from_user.id)
    await message.reply(text, reply_markup=markup)


@dp.callback_query(F.data.startswith("res:"))
async def cb_resume(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        sid = int(cb.data.split(":")[1])
    except (IndexError, ValueError):
        return await ans(cb, "Неверная игра", True)
    s = sess_get(sid)
    if not s or s["user_id"] != uid or s["status"] not in ("active", "pending"):
        return await ans(cb, "Игра уже завершена", True)
    u = get_user(uid)
    g, st, bet = s["game"], s["state"], int(s["bet"])
    try:
        if g == "mines":
            text, markup = mines_text(u, bet, st), mines_kb(sid, st)
        elif g == "climb":
            text, markup = climb_text(u, bet, st), climb_kb(sid, st)
        elif g == "labyrinth":
            text, markup = lab_text(sid, st), lab_kb(sid, st)
        elif g == "hilo":
            text, markup = hl_text(u, bet, st), hl_kb(sid, st)
        elif g == "ttt":
            text, markup = tt_text(st, bet), tt_kb(sid, st.get("board", ""))
        else:
            return await ans(cb, "Эту игру продолжи командой в чате", True)
    except Exception:
        log.exception("resume %s", g)
        return await ans(cb, "Не удалось открыть игру", True)
    await cb.message.answer(text, reply_markup=markup)
    await ans(cb, "Игра открыта")


BADGE_ALIASES = {
    "владелец": "dev", "owner": "dev", "dev": "dev",
    "модер": "moder", "moder": "moder", "модератор": "moder",
    "саппорт": "support", "support": "support", "поддержка": "support",
    "тестер": "tester", "tester": "tester",
    "премиум": "rubin", "premium": "rubin", "рубин": "rubin", "rubin": "rubin",
    "премиум2": "premium2", "premium2": "premium2",
    "черная": "black", "чёрная": "black", "black": "black",
    "синяя": "blue", "голубая": "blue", "blue": "blue", "лудоман": "blue",
    "новогодняя": "ny", "ny": "ny",
}


def _badge_key(token: str) -> Optional[str]:
    t = (token or "").strip().lower().lstrip("@")
    return BADGE_ALIASES.get(t) or (t if t in BADGES else None)


@dp.message(P("выдать галочку", "выдатьгалочку", "галочка"))
async def cmd_give_badge(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    args = [p for p in parts[1:] if p.lower() not in ("галочку", "галочка")]
    if not args:
        rows = [[btn(f"{b['fallback']} {b['title']}", f"gb:{k}")] for k, b in BADGES.items() if k != "dev"]
        return await message.reply("🎖 <b>Выдача галочки</b>\nВыбери галочку, затем игрока (ID или @ник).",
                                   reply_markup=kb(*rows))
    key = _badge_key(args[0])
    if not key:
        return await message.reply("Неизвестная галочка. Пример: <code>выдать галочку синяя @user</code>")
    target = resolve_target(message, args[1] if len(args) > 1 else None)
    if not target:
        return await message.reply("Игрок не найден (пусть запустит бота).")
    okb = give_badge(target["user_id"], key)
    if not okb:
        return await message.reply("У игрока уже есть эта галочка.")
    u = get_user(target["user_id"])
    await message.reply(box("🎖 <b>ГАЛОЧКА ВЫДАНА</b>", f"{badge(key)} {BADGES[key]['title']}",
                            f"Игрок: {uname(u, False)}", f"Ранг: {esc(u['rank_title'])}"))
    try:
        await bot.send_message(target["user_id"], f"🎖 Тебе выдали галочку {badge(key)} <b>{BADGES[key]['title']}</b>")
    except Exception:
        pass


@dp.callback_query(F.data.startswith("gb:"))
async def cb_give_badge_pick(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет доступа", True)
    key = cb.data.split(":")[1]
    if key not in BADGES:
        return await ans(cb, "Нет такой", True)
    await state.update_data(badge_key=key)
    await ask(cb, state, "badge_target", f"Кому выдать «{BADGES[key]['title']}»? ID или @ник:")


@flow("badge_target")
async def f_badge_target(m: Message, state: FSMContext, d, txt):
    key = (d or {}).get("badge_key")
    if not key:
        return await m.reply("Начни заново: <code>выдать галочку</code>")
    target = find_user(txt.strip())
    if not target:
        return await m.reply("Игрок не найден.")
    if not give_badge(target["user_id"], key):
        return await m.reply("Уже есть.")
    await state.clear()
    await m.reply(f"🎖 Выдано: {BADGES[key]['title']} → {uname(target, False)}")


# ---------------------------- АДМИН: NFT-АРХИВ ----------------------------
@dp.message(P("архивнфт", "nftarchive"))
async def cmd_admin_archive(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        box("🏛 <b>NFT-АРХИВ</b>",
            f"В архиве: <b>{archive_count()}</b> NFT",
            f"Застряло в апгрейдере: <b>{upg_stuck()}</b>",
            "Пополнение: «передать» NFT боту @rubinarxiv."),
        reply_markup=kb([btn("Пополнить на 20", "arx:fill", "treasury")],
                        [btn("Сбросить счётчик", "arx:reset", "settings")]))


@dp.callback_query(F.data.startswith("arx:"))
async def cb_admin_archive(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет доступа", True)
    if cb.data == "arx:fill":
        made = archive_seed(archive_count() + 20)
        return await ans(cb, f"Архив +{made} NFT", True)
    if cb.data == "arx:reset":
        x("INSERT INTO upg_log(user_id,nft_id,rarity,result,chance,created_at) VALUES(0,0,'','reset',0,?)", (now(),))
        return await ans(cb, "Счётчик обнулён", True)


# =====================================================================
#                  ПРИВАТНЫЕ КОМНАТЫ С КОДОМ
# =====================================================================
ROOM_MAX = 6


def room_get(code: str) -> Optional[Dict[str, Any]]:
    r = q("SELECT * FROM rooms WHERE code=?", (code.upper().strip(),), one=True)
    if r:
        try:
            r["players"] = json.loads(r["players"] or "[]")
        except Exception:
            r["players"] = []
    return r


def room_save(code: str, players: list, status: str):
    x("UPDATE rooms SET players=?, status=? WHERE code=?", (json.dumps(players), status, code))


def room_create(uid: int, bet: int) -> str:
    """Создаёт комнату и сразу списывает ставку. Возвращает код или "" при нехватке денег."""
    bet = int(bet)
    if bet <= 0 or not spend(uid, bet):
        return ""
    code = gen_code(6, string.digits)
    x("INSERT INTO rooms(code,owner_id,bet,players,status,created_at) VALUES(?,?,?,?,?,?)",
      (code, uid, bet, json.dumps([{"id": uid, "bet": bet}]), "wait", now()))
    return code


def room_join(uid: int, code: str) -> tuple:
    r = room_get(code)
    if not r:
        return False, "Комната не найдена."
    if r["status"] != "wait":
        return False, "Игра в этой комнате уже началась."
    players = r["players"]
    if any(p["id"] == uid for p in players):
        return False, "Ты уже в комнате."
    if len(players) >= ROOM_MAX:
        return False, "Комната заполнена."
    if not spend(uid, int(r["bet"])):
        return False, f"Нужно {fmt(r['bet'])} RCOIN — ставка комнаты."
    players.append({"id": uid, "bet": int(r["bet"])})
    room_save(code, players, "wait")
    r["players"] = players
    return True, r


async def room_play(code: str):
    r = room_get(code)
    if not r or r["status"] != "wait":
        return
    players = r["players"]
    if len(players) < 2:
        return
    room_save(code, players, "play")
    ids = [p["id"] for p in players]
    bets = {p["id"]: int(p["bet"]) for p in players}
    pot = sum(bets.values())
    rake = pot // 10
    prize = pot - rake
    winner = random.choices(ids, weights=[bets[i] for i in ids])[0]
    await asyncio.sleep(1.2)
    treasury_add(rake)
    for uid in ids:
        settle(uid, "room", bets[uid], prize if uid == winner else 0, "room " + code)
    wu = get_user(winner)
    txt = box("🎉 <b>ПРИВАТНАЯ КОМНАТА</b>",
              f"🔑 Код: <code>{code}</code>",
              f"🏆 Победитель: {uname(wu, False)}",
              f"💰 Банк: {fmt(pot)} · выигрыш: <b>{fmt(prize)}</b> RCOIN")
    for uid in ids:
        try:
            await bot.send_message(uid, txt, reply_markup=kb([btn("Создать свою", "room:new", "arena")]))
            await asyncio.sleep(0.05)
        except Exception:
            pass


def room_view(uid: int) -> str:
    mine = q("SELECT * FROM rooms WHERE owner_id=? AND status='wait' ORDER BY created_at DESC LIMIT 1", (uid,), one=True)
    text = box("🔐 <b>ПРИВАТНАЯ КОМНАТА</b>",
               "Создай комнату, скинь другу код — и играйте на равных.",
               "До 6 игроков · ставка одинаковая · 10% в казну.",
               f"Твоя открытая комната: <code>{mine['code']}</code> · {fmt(mine['bet'])}" if mine else "Открытых комнат нет.")
    return text


@dp.message(P("комната", "приват", "room"))
async def cmd_room(message: Message):
    uid = message.from_user.id
    p = message.text.split()
    if len(p) >= 2 and p[1].lower() in ("создать", "create"):
        bet = parse_amount(p[2], get_user(uid)["balance_coin"]) if len(p) >= 3 else 0
        if bet <= 0 or bet > MAX_BET:
            return await message.reply(f"Ставка от 1 до {fmt(MAX_BET)}. Пример: <code>комната создать 100к</code>")
        code = room_create(uid, bet)
        if not code:
            return await message.reply(f"{E('lock')} Недостаточно RCOIN.")
        return await message.reply(
            box("🔐 <b>КОМНАТА СОЗДАНА</b>", f"Код: <code>{code}</code>",
                f"Ставка: {fmt(bet)} RCOIN", "Отправь код другу: <code>комната войти " + code + "</code>"),
            reply_markup=kb([btn("Позвать друга", url=deeplink("room_" + code))]))
    if len(p) >= 3 and p[1].lower() in ("войти", "join"):
        code = re.sub(r"\D", "", p[2])[:6]
        okj, res = room_join(uid, code)
        if not okj:
            return await message.reply(f"{E('lock')} {res}")
        players = res["players"]
        await message.reply(box("✅ <b>ТЫ В КОМНАТЕ</b>", f"Код: <code>{code}</code>",
                                f"Игроков: {len(players)}/{ROOM_MAX}", f"Ставка: {fmt(res['bet'])}"))
        if len(players) >= 2:
            asyncio.create_task(room_play(code))
        return
    await message.reply(room_view(uid), reply_markup=kb(
        [btn("Создать комнату", "room:new", "arena")],
        [btn("Войти по коду", "room:join", "door")]))


@dp.callback_query(F.data == "room:new")
async def cb_room_new(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "room_bet", "Ставка комнаты? Например <code>100к</code>.")


@dp.callback_query(F.data == "room:join")
async def cb_room_join(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "room_code", "Введи код комнаты (6 цифр).")


@flow("room_bet")
async def f_room_bet(m: Message, state: FSMContext, d, txt):
    bet = parse_amount(txt, get_user(m.from_user.id)["balance_coin"])
    if bet <= 0 or bet > MAX_BET:
        return await m.reply(f"Ставка от 1 до {fmt(MAX_BET)}.")
    uid = m.from_user.id
    code = room_create(uid, bet)
    if not code:
        return await m.reply(f"{E('lock')} Недостаточно RCOIN.")
    await state.clear()
    await m.reply(box("🔐 <b>КОМНАТА СОЗДАНА</b>", f"Код: <code>{code}</code>", f"Ставка: {fmt(bet)}",
                      "Друг входит: <code>комната войти " + code + "</code>"))


@flow("room_code")
async def f_room_code(m: Message, state: FSMContext, d, txt):
    code = re.sub(r"\D", "", txt)[:6]
    if len(code) != 6:
        return await m.reply("Код — 6 цифр.")
    okj, res = room_join(m.from_user.id, code)
    if not okj:
        return await m.reply(res)
    await state.clear()
    await m.reply(box("✅ <b>ТЫ В КОМНАТЕ</b>", f"Код: <code>{code}</code>",
                      f"Игроков: {len(res['players'])}/{ROOM_MAX}"))
    if len(res["players"]) >= 2:
        asyncio.create_task(room_play(code))


def backup_db() -> str:
    """Копия SQLite-базы в backups/ — чтобы база не потерялась при рестарте."""
    if DATABASE_URL:
        return ""
    src = Path(DB_FILE)
    if not src.exists():
        return ""
    try:
        dst_dir = Path("backups")
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{src.stem}-{datetime.now(MSK):%Y%m%d-%H%M%S}.db"
        with src.open("rb") as f, dst.open("wb") as g:
            g.write(f.read())
        log.info("Бэкап БД: %s", dst)
        return str(dst)
    except Exception:
        log.exception("backup_db")
        return ""


atexit.register(backup_db)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен")
    finally:
        backup_db()
