# -*- coding: utf-8 -*-
"""
RCOIN·BOT — игровой бот (aiogram 3.x) + веб-приложение (aiohttp) в одном файле.

Запуск:  pip install -U aiogram aiohttp  &&  BOT_TOKEN=... python rcoin_bot.py
Render:  Start Command `python rubinbot.py`, переменные окружения см. README в ответе.
Токен НЕ хранится в коде — только в переменной окружения BOT_TOKEN.
"""
import asyncio
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
import psycopg2
from psycopg2.extras import RealDictCursor
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape as esc
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
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
                           InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message,
                           PreCheckoutQuery, WebAppInfo)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rcoin")

# ============================ КОНФИГ ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9176453419:AAEXQzBO_7xUEXGTTYM6cYJHs-DoO-q_htI").strip()
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
REF_PERCENT = 2
BONUS_AMOUNT = 2500
IMAGE_PATH = "image.png"
# For Render persistent disk, set NFT_DIR=/var/data/nft_images.
NFT_DIR = Path(os.getenv("NFT_DIR", "/var/data/nft_images" if os.getenv("RENDER") else "nft_images"))

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
    "nft": "5262517101578443800", "referral": "5942877472163892475", "check": "5444856076954520455",
    "treasury": "5798678875823153004", "win": "5305747221996177787", "lose": "5305474786400690766",
    "settings": "5258096772776991776", "admin": "6129805886383723340", "donate": "5438496463044752972",
    "ad": "5213391561999526028", "market": "5278702045883292456", "question": "5436113877181941026",
    "item_1": "5332717942599618048", "item_2": "5404752966584394198", "item_3": "5280924618444514633",
    "item_4": "5368488358681000659", "item_5": "5398024200235529935", "item_6": "5449449325434266744",
    "item_7": "5201924046563852634", "item_8": "5199959030306456092", "item_9": "5316599316884766402",
}
FALLBACK = {
    "games": "🎮", "dice": "🎲", "roulette": "🎰", "fortune": "🎡", "mines": "💣", "crash": "🚀",
    "basket": "🏀", "darts": "🎯", "blackjack": "🃏", "sun": "☀️", "hunt": "🏹", "spin": "🎰",
    "football": "⚽", "pyramid": "🔺", "miner": "⛏", "hi_lo": "🎴", "ttt": "❌", "door": "🚪",
    "profile": "👤", "balance": "💰", "bank": "🏦", "diamond": "💎", "star": "⭐", "lock": "🔒",
    "nft": "🖼", "referral": "👥", "check": "✅", "treasury": "🏛", "win": "🏆", "lose": "💔",
    "settings": "⚙️", "admin": "👑", "donate": "🎁", "ad": "📢", "market": "🛒", "question": "❔",
    "item_1": "❄️", "item_2": "🍬", "item_3": "🧦", "item_4": "🧤", "item_5": "🍪", "item_6": "⭐",
    "item_7": "🔔", "item_8": "🧊", "item_9": "☕",
}
SOUVENIRS = {"item_1": "Снежный шар", "item_2": "Леденец-трость", "item_3": "Носок с подарками",
             "item_4": "Варежка Деда Мороза", "item_5": "Пряник-драчун", "item_6": "Ёлочная звезда",
             "item_7": "Колокольчик саней", "item_8": "Сосулька-сабля", "item_9": "Кружка какао"}


def E(key: str) -> str:
    fb = FALLBACK.get(key, "▫️")
    if PREMIUM_EMOJI and key in EMOJI_IDS:
        return f'<tg-emoji emoji-id="{EMOJI_IDS[key]}">{fb}</tg-emoji>'
    return fb


def btn(text: str, data: str = None, icon: str = None, url: str = None, web: str = None) -> InlineKeyboardButton:
    kw: Dict[str, Any] = {"text": text}
    if data:
        kw["callback_data"] = data
    if url:
        kw["url"] = url
    if web:
        kw["web_app"] = WebAppInfo(url=web)
    if icon and PREMIUM_ICONS:
        custom_id = EMOJI_IDS.get(icon)
        if not custom_id:
            custom_id = globals().get("BADGES", {}).get(icon, {}).get("id")
        if custom_id:
            kw["icon_custom_emoji_id"] = str(custom_id)
    return InlineKeyboardButton(**kw)


def qbtn(data: str) -> InlineKeyboardButton:
    """Кнопка-вопрос (мины, башня, бонус 5x5)."""
    if PREMIUM_ICONS:
        return btn("\u2800", data, icon="question")
    return btn("❔", data)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows if r])


def box(*lines) -> str:
    return "<blockquote>" + "\n".join(str(l) for l in lines) + "</blockquote>"


# ---------- защита от DOCUMENT_INVALID (битые/запрещённые кастомные эмодзи) ----------
TGE_RE = re.compile(r'<tg-emoji emoji-id="\d+">(.*?)</tg-emoji>', re.S)
_fb_hits = [0]


def _strip_method(method):
    """Копия запроса без кастомных эмодзи в тексте и без иконок на кнопках (или None, если нечего убирать)."""
    upd = {}
    for f in ("text", "caption"):
        v = getattr(method, f, None)
        if isinstance(v, str) and "<tg-emoji" in v:
            upd[f] = TGE_RE.sub(r"\1", v)
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
                    if d.get("text") == "\u2800":
                        d["text"] = "❔"
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
            if "document_invalid" in s_ or "emoji" in s_ or "icon" in s_:
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
    ids = sorted(set(EMOJI_IDS.values()))
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
    log.info("Рабочих премиум-эмодзи: %s из %s", len(EMOJI_IDS), len(EMOJI_IDS) + len(bad))


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
    "bank_limit": "INTEGER DEFAULT 500000000", "bonus_last_time": "INTEGER DEFAULT 0",
    "banned_until": "INTEGER DEFAULT 0", "muted_until": "INTEGER DEFAULT 0", "ban_reason": "TEXT DEFAULT ''",
    "mute_reason": "TEXT DEFAULT ''", "total_wins": "INTEGER DEFAULT 0", "total_losses": "INTEGER DEFAULT 0",
    "total_games": "INTEGER DEFAULT 0", "total_games_day": "INTEGER DEFAULT 0", "last_game_day": "INTEGER DEFAULT 0",
    "referral_code": "TEXT DEFAULT ''", "referred_by": "INTEGER DEFAULT 0", "referral_earnings": "INTEGER DEFAULT 0",
    "referral_percent": "INTEGER DEFAULT 2", "referral_withdrawn": "INTEGER DEFAULT 0",
    "created_at": "INTEGER DEFAULT 0", "is_anonymous": "INTEGER DEFAULT 0", "last_spin_time": "INTEGER DEFAULT 0",
    "about_text": "TEXT DEFAULT ''", "rank_title": "TEXT DEFAULT 'Новичок'", "custom_username": "TEXT DEFAULT ''",
    "is_scammer": "INTEGER DEFAULT 0", "is_admin_rank": "INTEGER DEFAULT 0", "is_donater": "INTEGER DEFAULT 0",
    "is_official": "INTEGER DEFAULT 0", "treasury_access": "INTEGER DEFAULT 0", "titles": "TEXT DEFAULT '[]'",
    "antiludo_until": "INTEGER DEFAULT 0", "shield_until": "INTEGER DEFAULT 0", "inventory": "TEXT DEFAULT '[]'",
    "ev_day": "TEXT DEFAULT ''", "ev_stash_used": "INTEGER DEFAULT 0", "ev_boss_day": "TEXT DEFAULT ''",
    "ev_wheel_last": "INTEGER DEFAULT 0", "ev_points": "INTEGER DEFAULT 0",
    "db5_streak": "INTEGER DEFAULT 0", "db5_last_day": "TEXT DEFAULT ''",
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
    "nft_items": {"photo": "TEXT DEFAULT '🎨'", "model": "TEXT DEFAULT 'Стандартный'",
                  "background": "TEXT DEFAULT 'Обычный'", "base_name": "TEXT DEFAULT ''"},
    "gifts": {"expires_at": "INTEGER DEFAULT 0"},
}


def ensure_cols(table: str, cols: Dict[str, str]):
    have = {r["name"] for r in q(f"PRAGMA table_info({table})")}
    for name, decl in cols.items():
        if name not in have:
            try:
                x(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            except (sqlite3.OperationalError, psycopg2.Error) as e:
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
    x("INSERT OR IGNORE INTO event_progress(id,boss_hp,boss_max,day,season) VALUES(1,0,0,'',1)")
    log.info("База данных готова: %s", "PostgreSQL" if DATABASE_URL else DB_FILE)
    init_tables()


def kv_get(key: str) -> Optional[str]:
    r = q("SELECT value FROM kv WHERE key=?", (key,), one=True)
    return r["value"] if r else None


def kv_set(key: str, value: str):
    x("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


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


def add_coin(uid: int, n: int):
    x("UPDATE users SET balance_coin=balance_coin+? WHERE user_id=?", (int(n), uid))


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
    rows = []
    for r in range(5):
        row = []
        for c in range(5):
            i = r * 5 + c
            if over:
                row.append(btn("💣" if i in mines else ("💎" if i in opened else "▫️"), "noop"))
            elif i in opened:
                row.append(btn("💎", "noop"))
            else:
                row.append(qbtn(f"mn:o:{sid}:{i}"))
        rows.append(row)
    if not over:
        if opened:
            rows.append([btn(f"💰 Забрать выигрыш ×{mines_mult(st['m'], len(opened)):.2f}", f"mn:c:{sid}")])
        else:
            rows.append([btn("↩️ Отменить игру", f"mn:x:{sid}")])
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
    cols, levels = (5, 9) if kind == "tower" else (4, 8)
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
                    cell = "💥" if bomb else "💎"
                elif over and bomb:
                    cell = "💣"
                else:
                    cell = "▫️"
                row.append(btn(cell, "noop"))
            rows.append(row)
    elif not over:
        ds = [btn(f"🚪 {c + 1}", f"cl:p:{sid}:{c}", "door") for c in range(cols)]
        rows = [ds[:2], ds[2:]]
    if not over:
        if lvl:
            rows.append([btn(f"💰 Забрать выигрыш ×{climb_mult(cols, st['b'], lvl):.2f}", f"cl:c:{sid}", "win")])
        else:
            rows.append([btn("💥 Отменить игру", f"cl:x:{sid}")])
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
        ex = "<code>башня 500</code> / <code>башня 500 2</code> (2 бомбы в ряду, 1-3)" if kind == "tower" else "<code>пирамида 500</code> — 4 двери, 1 ловушка"
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
    sym = {"-": "⬜", "X": "❌", "O": "⭕"}
    rows = [[btn(sym[board[r * 3 + c]], "noop" if over or board[r * 3 + c] != "-" else f"tt:m:{sid}:{r * 3 + c}") for c in range(3)] for r in range(3)]
    if not over:
        rows.append([btn("🏳️ Сдаться", f"tt:q:{sid}")])
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
ARENA_COLORS = ["🟥", "🟦", "🟩", "🟨", "🟪", "🟧"]
ARENA_RING = 20


def arena_pick(bets: Dict[int, int]) -> int:
    ids = list(bets)
    return random.choices(ids, weights=[bets[i] for i in ids])[0]


def arena_text(a: dict, extra: str = "") -> str:
    pl = a["players"]
    lines = [f"{ARENA_COLORS[i]} {esc(n)}" for i, (uid, n) in enumerate(pl.items())]
    pct = f" — шанс каждого {100 // max(1, len(pl))}%" if pl else ""
    return (f"{E('games')} <b>АРЕНА</b> · ставка <b>{fmt(a['bet'])}</b> RCOIN\n" + "\n".join(lines) +
            f"\n\n💰 Банк: <b>{fmt(a['bet'] * len(pl))}</b>{pct}\n{extra}")


def arena_kb(aid: int, a: dict) -> InlineKeyboardMarkup:
    rows = [[btn(f"⚔️ Вступить ({fmt(a['bet'])})", f"ar:j:{aid}")]]
    if len(a["players"]) == 1:
        rows.append([btn("↩️ Отменить арену", f"ar:x:{aid}")])
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
    a = {"bet": bet, "players": {u["user_id"]: re.sub(r"<[^>]+>", "", uname(u, False))}, "started": False, "chat": m.chat.id, "msg": None}
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
    if len(a["players"]) >= len(ARENA_COLORS):
        return await ans(cb, "Арена заполнена", True)
    if not spend(uid, a["bet"]):
        return await ans(cb, "Недостаточно RCOIN", True)
    a["players"][uid] = re.sub(r"<[^>]+>", "", uname(get_user(uid), False))
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
            ring += [ARENA_COLORS[i]] * (per + (1 if i < ARENA_RING - per * n else 0))
        wi = ids.index(winner)
        wcells = [i for i, c in enumerate(ring) if c == ARENA_COLORS[wi]]
        target = random.choice(wcells)
        start = random.randrange(ARENA_RING)
        total = ARENA_RING * 2 + (target - start) % ARENA_RING
        for k in range(1, 8):
            pos = (start + int(total * (1 - (1 - k / 7) ** 2.2))) % ARENA_RING if k < 7 else target
            line = "".join("⚪" if i == pos else c for i, c in enumerate(ring))
            await _arena_edit(a, f"{E('games')} <b>АРЕНА</b> — шарик катится...\n\n{line}")
            await asyncio.sleep(0.9 + k * 0.15)
        pool = a["bet"] * n
        rake = pool // 10
        treasury_add(rake)
        prize = pool - rake
        for uid in ids:
            settle(uid, "arena", a["bet"], prize if uid == winner else 0, "arena")
        line = "".join("⚪" if i == target else c for i, c in enumerate(ring))
        await _arena_edit(a, box(f"{E('win')} <b>АРЕНА — РЕЗУЛЬТАТ</b>", line,
                                 f"🏆 Победитель: <b>{esc(pl[winner])}</b> {ARENA_COLORS[wi]}",
                                 f"💰 Выигрыш: <b>+{fmt(prize - a['bet'])}</b> RCOIN (банк {fmt(pool)}, комиссия {fmt(rake)})"))
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
        [btn("Ежедневный 5×5", "menu:db5", "question"), btn("Заработать", "menu:earn", "balance")],
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
    t = (f"{E('profile')} <b>ПРОФИЛЬ</b>\n━━━━━━━━━━━━\n🆔 ID: <code>{uid}</code>\n👤 Имя: {uname(u, False)}\n"
         f"🏷 Юзернейм: {uname_line}\n🔒 Анонимность: {'вкл' if u['is_anonymous'] else 'выкл'}\n🎖 Ранг: {esc(u['rank_title'])}\n"
         f"💎 Титулы: {esc(titles)}\n📝 О себе: {esc(u['about_text'] or 'не указано')}\n━━━━━━━━━━━━\n"
         f"{E('balance')} RCOIN: <b>{fmt(u['balance_coin'])}</b>\n{E('diamond')} RBP: <b>{fmt(u['balance_point'])}</b>\n"
         f"{E('bank')} Банк: {fmt(u['bank_balance'])}\n⭐ Stars: {u['stars_balance']}\n━━━━━━━━━━━━\n"
         f"📊 Игр: {n} · побед: {w} · {round(w / max(n, 1) * 100, 1)}%\n{E('referral')} Рефералов: {refs}\n━━━━━━━━━━━━\n"
         f"<code>сменить ник Имя</code> (150 000) · <code>о себе Текст</code> · <code>+юзер @ник</code> (100 000 000)")
    return t, kb([btn("Склад", "menu:stash", "diamond"), btn("Рефералы", "menu:refs", "referral")],
                 [btn("Настройки", "menu:settings", "settings"), btn("История", "menu:history", "games")],
                 [btn("Назад", "menu:main", "door")])


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
         "<b>Ивенты:</b> <code>ивенты</code> · <code>помочь санте 100к</code> · <code>ежедневный</code> (бонус 5×5)\n\n"
         "<b>Прочее:</b> <code>/antiludo</code> (ответом, 100 000 RCOIN — блок игр на 5 мин) · <code>+юзер @ник</code> · "
         "<code>сменить ник Имя</code> · <code>о себе Текст</code>\n\n"
         "Суммы: 1к = 1 000 · 1кк = 1 000 000 · 1ккк = 1 000 000 000 · <code>все</code> = весь баланс\n"
         f"Статус бота: ответы идут реплаем на твоё сообщение.")
    return t, kb([btn("Назад", "menu:main", "door")])


def reg_view(name: str, *words: str):
    @dp.message(P(*words))
    async def _h(message: Message, state: FSMContext):
        await state.clear()
        t, k = await VIEWS[name](message.from_user.id, message.chat.type == "private")
        await message.reply(t, reply_markup=k)


reg_view("main", "меню", "menu", "старт")
reg_view("games", "игры", "games", "игра")
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


def games_page(page: int):
    per = 6
    pages = (len(GAMES) + per - 1) // per
    page = max(0, min(page, pages - 1))
    rows, row = [], []
    for i in range(page * per, min(len(GAMES), (page + 1) * per)):
        row.append(btn(GAMES[i][1], f"gm:i:{i}", GAMES[i][0]))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"gm:p:{page - 1}"))
    if page < pages - 1:
        nav.append(btn("▶️", f"gm:p:{page + 1}"))
    if nav:
        rows.append(nav)
    if WEBAPP_URL:
        rows.append([btn("🌐 Веб-апп: арена и игры", web=WEBAPP_URL)])
    rows.append([btn("Назад", "menu:main", "door")])
    return f"{E('games')} <b>ВЫБЕРИ ИГРУ</b>\nНажми на игру — увидишь правила и формат команды.", kb(*rows)


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
    t = f"{E('treasury')} <b>КАЗНА</b>\n\n💰 RCOIN: <b>{fmt(treasury_get())}</b>\n\nКазна — общий фонд: из неё идут авто-чеки и награды ивентов. Пополняется комиссиями."
    rows = []
    if u["treasury_access"] or is_admin(uid):
        rows.append([btn("Пополнить", "tr:d", "treasury"), btn("Снять", "tr:w", "treasury")])
    rows.append([btn("Назад", "menu:main", "door")])
    return t, kb(*rows)


@dp.callback_query(F.data.startswith("tr:"))
async def cb_treasury(cb: CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    if not (u["treasury_access"] or is_admin(u["user_id"])):
        return await ans(cb, "Нет доступа", True)
    await ask(cb, state, "tr_d" if cb.data.endswith("d") else "tr_w", "Введи сумму RCOIN (1к, 1кк):")


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


# ============================ ЧЕКИ ============================
@dp.message(P("чек"))
async def cmd_check_book(message: Message):
    t, k = await v_checks(message.from_user.id, True)
    await message.reply(t, reply_markup=k)


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
@dp.message(P("донат"))
async def cmd_donate(message: Message):
    u = get_user(message.from_user.id)
    await message.reply(f"{E('donate')} <b>Пополнение RBP</b>\n\n{E('diamond')} Твой баланс: {fmt(u['balance_point'])} RBP\n1 ⭐ Telegram Stars = 5 RBP",
                        reply_markup=kb([btn("Пополнить звёздами", "don:stars", "star")]))


@dp.callback_query(F.data == "don:stars")
async def cb_don(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "stars", "Сколько звёзд ⭐ потратить? (1 ⭐ = 5 RBP)")


@flow("stars")
async def f_stars(m: Message, state: FSMContext, d, txt):
    if not txt.isdigit() or not 1 <= int(txt) <= 100000:
        return await m.reply("Введи целое число звёзд.")
    n = int(txt)
    try:
        await bot.send_invoice(chat_id=m.from_user.id, title="Пополнение RBP", description=f"{n * 5} RBP за {n} ⭐",
                               payload=f"stars:{m.from_user.id}", provider_token="", currency="XTR",
                               prices=[LabeledPrice(label=f"{n * 5} RBP", amount=n)])
        await state.clear()
    except Exception as e:
        log.warning("invoice: %s", e)
        await m.reply("Не удалось создать счёт. Открой диалог с ботом и попробуй снова.")


@dp.pre_checkout_query()
async def on_pre_checkout(q_: PreCheckoutQuery):
    await q_.answer(ok=True)


@dp.message(F.successful_payment)
async def on_paid(message: Message):
    sp = message.successful_payment
    if kv_get("pay:" + sp.telegram_payment_charge_id):
        return
    kv_set("pay:" + sp.telegram_payment_charge_id, "1")
    rbp = sp.total_amount * 5
    x("UPDATE users SET balance_point=balance_point+? WHERE user_id=?", (rbp, message.from_user.id))
    await message.reply(box(f"{E('star')} <b>ПОПОЛНЕНИЕ УСПЕШНО!</b>", f"💎 +{fmt(rbp)} RBP", "Спасибо! 🎉"))


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
RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_EMOJI = {"common": "🟢", "uncommon": "🔵", "rare": "🟣", "epic": "🟠", "legendary": "🔴"}
RARITY_NAME = {"common": "Обычный", "uncommon": "Необычный", "rare": "Редкий", "epic": "Эпический", "legendary": "Легендарный"}
RARITY_BASE = {"common": 50_000, "uncommon": 120_000, "rare": 250_000, "epic": 600_000, "legendary": 1_500_000}
NFT_POOL = {
    "common": [("Снеговик-неудачник", "⛄"), ("Носок с дыркой", "🧦"), ("Мандаринка на удачу", "🍊"), ("Пельмень-талисман", "🥟"),
               ("Тапок Деда Мороза", "🥿"), ("Космический кот", "🐱"), ("Пузырчатая плёнка", "🫧")],
    "uncommon": [("Оливье в вакууме", "🥗"), ("Селёдка под шубой (NFT)", "🐟"), ("Олень Рудольф в отпуске", "🦌"),
                 ("Кот в гирлянде", "😼"), ("Бенгальский огонёк", "🎇"), ("Пиксельный дракон", "🐉")],
    "rare": [("Золотой мандарин", "🍊"), ("Снегурочка-хакер", "👩‍💻"), ("Шампанское 00:00", "🍾"), ("Хрустальная ёлка", "🎄"),
             ("Пингвин-диджей", "🐧"), ("Радужный единорог", "🦄")],
    "epic": [("Санта-майнер", "🎅"), ("Кибер-снеговик 2077", "🤖"), ("Мамонт под ёлкой", "🦣"), ("Звёздный олень", "✨"),
             ("Робот-бариста", "☕")],
    "legendary": [("Дух Нового года", "🎆"), ("Золотой Дед Мороз", "👑"), ("Часы курантов", "🕛"), ("Ёлка-мультивселенная", "🌌"),
                  ("Северное сияние Prime", "🌠")],
}
MODELS = [("Стандартный", 1.0, 30), ("Зимний", 1.2, 25), ("Снежный", 1.4, 18), ("Золотой", 2.0, 12),
          ("Неоновый", 2.5, 8), ("Призрачный", 3.5, 5), ("Космический", 5.0, 2)]
BGS = [("Обычный", 1.0, 30), ("Морозный", 1.2, 25), ("Праздничный", 1.5, 18), ("Звёздный", 2.0, 14),
       ("Северное сияние", 3.0, 8), ("Галактика", 4.0, 5)]
PHOTOS = ["🎄", "🎁", "⛄", "❄️", "🎅", "🤶", "🦌", "🎀", "✨", "🌲", "🔔", "🍊", "🥂", "🧸", "🐧", "🐲", "🦄", "🤖", "🌌", "👑"]


def make_nft(owner: int, name: str, rarity: str, photo: str = None, desc: str = "", price: int = None) -> int:
    if photo is None:
        photo = next((e for n, e in NFT_POOL.get(rarity, []) if n == name), random.choice(PHOTOS))
    price = price or RARITY_BASE.get(rarity, 50_000)
    return x("INSERT INTO nft_items(owner_id,name,base_name,level,rarity,price,created_at,description,photo,model,background) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
             (owner, name, name, 1, rarity, price, now(), desc, photo, "Стандартный", "Обычный"))[1]


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
    name, emoji = random.choice(NFT_POOL[g["rarity"]] if g["rarity"] in NFT_POOL else NFT_POOL["common"])
    return make_nft(uid, name, g["rarity"], emoji, "Открыто из коллекционного бокса")


def nft_value(n: dict) -> int:
    mm = next((m for nm, m, _ in MODELS if nm == n["model"]), 1.0)
    bm = next((m for nm, m, _ in BGS if nm == n["background"]), 1.0)
    return int(RARITY_BASE.get(n["rarity"], 50_000) * mm * bm * (1 + 0.1 * (n["level"] - 1)))


def nft_card(n: dict) -> str:
    sale = f"\n🛒 На продаже за <b>{fmt(n['sale_price'])}</b>" if n["for_sale"] else ""
    return (f"{n['photo']} {RARITY_EMOJI.get(n['rarity'], '🟢')} <b>{esc(n['name'])}</b> <code>#{n['id']}</code>\n"
            f"✨ Редкость: {RARITY_NAME.get(n['rarity'], '—')}\n📊 Уровень: {n['level']}\n🎭 Модель: {esc(n['model'])}\n"
            f"🖼 Фон: {esc(n['background'])}\n💰 Оценка: <b>{fmt(n['price'])}</b> RCOIN{sale}\n📝 {esc(n['description'] or '—')}")


def nft_upgrade_cost(n: dict) -> int:
    return max(20_000, int(RARITY_BASE.get(n["rarity"], 50_000) * 0.25 * n["level"]))


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
        ns = q("SELECT * FROM nft_items WHERE owner_id=? ORDER BY price DESC LIMIT 8 OFFSET ?", (uid, page * 8))
        if not ns and page == 0:
            await safe_edit(cb, "📭 У тебя нет NFT. Купи бокс в маркете и открой его!", kb([btn("Маркет", "menu:market", "market")], [btn("Назад", "menu:stash", "door")]))
            return await ans(cb)
        rows = [[btn(f"{n['photo']} {n['name']} · {fmt(n['price'])}" + (" 🛒" if n["for_sale"] else ""), f"nft:v:{n['id']}")] for n in ns]
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
        if n["for_sale"]:
            rows.append([btn("Снять с продажи", f"nft:us:{nid}")])
        else:
            rows.append([btn(f"⚡ Улучшить ({fmt(nft_upgrade_cost(n))})", f"nft:up:{nid}")])
            rows.append([btn("✏️ Название (50к)", f"nft:rn:{nid}"), btn("🖼 Фото (50к)", f"nft:ph:{nid}")])
            rows.append([btn("📤 Передать", f"nft:tr:{nid}"), btn("🛒 Продать", f"nft:sl:{nid}")])
        rows.append([btn("Назад", "inv:nfts:0", "door")])
        await safe_edit(cb, nft_card(n), kb(*rows))
        return await ans(cb)
    if n["for_sale"] and act != "us":
        return await ans(cb, "Сначала сними NFT с продажи", True)
    if act == "up":
        cost = nft_upgrade_cost(n)
        if not spend(uid, cost):
            return await ans(cb, f"Нужно {fmt(cost)} RCOIN", True)
        model = random.choices(MODELS, weights=[w for _, _, w in MODELS])[0][0]
        bg = random.choices(BGS, weights=[w for _, _, w in BGS])[0][0]
        n2 = {**n, "model": model, "background": bg, "level": n["level"] + 1}
        val = nft_value(n2)
        x("UPDATE nft_items SET model=?, background=?, level=?, price=?, photo=? WHERE id=?", (model, bg, n2["level"], val, random.choice(PHOTOS), n["id"]))
        n = q("SELECT * FROM nft_items WHERE id=?", (n["id"],), one=True)
        await safe_edit(cb, box("⚡ <b>NFT УЛУЧШЕН!</b>", nft_card(n)), kb([btn("Ещё раз", f"nft:v:{nid}")], [btn("К списку", "inv:nfts:0")]))
        return await ans(cb, "⚡ Улучшено!")
    if act == "us":
        x("UPDATE nft_items SET for_sale=0, sale_price=0 WHERE id=? AND owner_id=?", (n["id"], uid))
        n = q("SELECT * FROM nft_items WHERE id=?", (n["id"],), one=True)
        return await cb_nft(cb.model_copy(update={"data": f"nft:v:{nid}"}), state)
    prompts = {"rn": ("nft_rn", "Новое название NFT (до 30 символов). Стоимость 50 000 RCOIN:"),
               "ph": ("nft_ph", "Отправь один эмодзи для фото NFT. Стоимость 50 000 RCOIN:"),
               "tr": ("nft_tr", "Кому передать? Введи @юзернейм или ID игрока:"),
               "sl": ("nft_sl", f"За сколько RCOIN продать? (оценка {fmt(n['price'])}). Налог 5%:")}
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
    t = find_user(target_token)
    if not t:
        return "Игрок не найден (он должен запустить бота)."
    if t["user_id"] == uid:
        return "Нельзя передать самому себе."
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
    return t, kb([btn("Купить боксы", "mk:boxes", "donate"), btn("Маркет игроков", "mk:list:0", "market")],
                 [btn("Магазин штук", "mk:shop", "settings"), btn("Мой склад", "menu:stash", "diamond")],
                 [btn("Назад", "menu:main", "door")])


reg_view("market", "маркет", "market")


@dp.callback_query(F.data.startswith("mk:"))
async def cb_market(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    uid = cb.from_user.id
    act = parts[1]
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
            lines.append(f"{n['photo']} {RARITY_EMOJI[n['rarity']]} <b>{esc(n['name'])}</b> #{n['id']} · ур.{n['level']} · {esc(n['model'])}/{esc(n['background'])}\n   💰 {fmt(n['sale_price'])} · оценка {fmt(n['price'])}")
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
BOSS_HP, BOSS_HP_FINAL = 10_000_000, 100_000_000
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
    t = (f"{E('star')} <b>ЗИМНИЕ ИВЕНТЫ</b>\n\n{E('diamond')} <b>Зимний склад</b> — {STASH_CELLS} ячейки в день, приз {fmt(STASH_MIN)}–{fmt(STASH_MAX)} + сувениры\n"
         f"{E('crash')} <b>Санта-босс</b> — {fmt(b['hp'])}/{fmt(b['max'])} HP\n<code>{bar(b['max'] - b['hp'], b['max'])}</code>\n"
         f"{E('spin')} <b>Колесо удачи</b> — раз в 6 часов\n{E('treasury')} <b>Квесты</b> — ежедневные задания\n\n"
         "Помоги Санте монетами: <code>помочь санте 100к</code>")
    return t, kb([btn("Зимний склад", "ev:stash", "diamond"), btn("Санта-босс", "ev:boss", "crash")],
                 [btn("Колесо удачи", "ev:wheel", "spin"), btn("Квесты", "ev:quests", "treasury")],
                 [btn("🎮 Зимние игры", "ev:games!"), btn("🎨 Чеканить NFT", "ev:mint", "nft")],
                 [btn("⛄ Снежный марафон", "snowman:open", "item_1")],
                 [btn("🛡 Новогодняя галочка", "ev:nybadge"), btn("Мой склад", "menu:stash", "diamond")],
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
    1: {"key": "snow", "name": "Снежки", "bp": (1.5, 2.2), "max": 0, "min": 5_000,
        "desc": "Собери снежки в точку: 3 из 3 — победа"},
    2: {"key": "ice", "name": "Ледяная дорожка", "bp": (1.8, 2.0), "max": 0, "min": 10_000,
        "desc": "Перепрыгни в прорубь от 1 до 5"},
    3: {"key": "bear", "name": "Белый медведь", "bp": (2.0, 2.0), "max": 0, "min": 10_000,
        "desc": "Угадай лапу: из 3 лап одна с рыбой"},
    4: {"key": "santa", "name": "Сани Санты", "bp": (1.6, 2.5), "max": 0, "min": 25_000,
        "desc": "Доведи сани: 5 000 км"} ,
    5: {"key": "gift", "name": "Подарки", "bp": (1.7, 2.0), "max": 0, "min": 20_000,
        "desc": "Из трёх коробок одна с подарком"},
    6: {"key": "mint", "name": "Пряничный забег", "bp": (1.9, 2.0), "max": 0, "min": 15_000,
        "desc": "Добеги до дома: 5 шагов"},
}
EV_POT = "ev_pot"


def ev_pot(*_a) -> int:
    try:
        return int(kv_get(EV_POT) or 0)
    except Exception:
        return 0


def ev_add_pot(n: int):
    kv_set(EV_POT, str(ev_pot() + n))


def ev_games_view(uid: int) -> Tuple[str, InlineKeyboardMarkup]:
    u = get_user(uid)
    lines = [f"{E('item_6')} <b>ЗИМНИЕ ИГРЫ</b> {E('item_9')}",
             f"<i>У каждого раунда есть джекпот ивентов: {fmt(ev_pot())} RCOIN</i>", ""]
    for i, g in SNOW_GAMES.items():
        lines.append(f"{E('item_' + str(i))} <b>{g['name']}</b> — {g['desc']}\n   x{g['bp'][0]:.2f}–{g['bp'][1]:.2f} · от {fmt(g['min'])}")
    lines.append("\nВыбери игру и ставку: <code>снежки 10к</code>")
    rows = [[btn(f"{E('item_' + str(i))} {g['name']}", f"gm:{g['key']}")] for i, g in SNOW_GAMES.items()]
    rows.append([btn("Назад", "menu:events", "door")])
    return "\n".join(lines), kb(*rows)


@dp.callback_query(F.data.startswith("gm:"))
async def cb_game_hint(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    g = next((x for x in SNOW_GAMES.values() if x["key"] == key), None)
    if not g:
        return await ans(cb, "Игра не найдена", True)
    await ans(cb, f"{g['name']}: сделай ставку\n<code>{g['name'].lower()} 10000</code>", True)


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
        payout = int(bet * [0, 1.2, 2.0, 3.4][hits]) if hits == 3 else 0
        detail = f"Попаданий: <b>{hits}/3</b>"
    elif key == "ice":
        pick, hole = random.randint(1, 5), random.randint(1, 5)
        payout = bet * 5 if pick == hole else 0
        detail = f"Ты прыгнул в прорубь №{pick}, лёд был на №{hole}" if pick != hole else f"Промахнулся в прорубь №{hole}!"
    elif key == "bear":
        pick, fish = random.choice([1, 2, 3]), random.choice([1, 2, 3])
        payout = bet * 3 if pick == fish else 0
        detail = f"Лапа {pick}: {'🐟 есть рыба!' if pick == fish else 'пусто'}"
    elif key == "santa":
        step = random.choice([0, 1800, 2600, 5000, 5000, 5000])
        payout = int(bet * (1 + step / 1000)) if step >= 5000 else 0
        detail = f"Сани проехали <b>{step:,}</b> км".replace(",", " ")
    elif key == "gift":
        pick, gift = random.choice([1, 2, 3]), random.choice([1, 2, 3])
        payout = bet * 2 if pick == gift else 0
        detail = f"Ты открыл коробку №{pick}: {'подарок!' if pick == gift else 'мишура'}"
    else:
        step = random.randint(1, 5)
        payout = int(bet * (1 + 0.4 * step)) if step == 5 else 0
        detail = f"Пряничный человечек прошёл {step}/5 шагов"
    settle(uid, key, bet, payout, detail)
    if payout > bet:
        bonus = payout // 20
        ev_add_pot(bonus)
        detail += f"\n{E('item_7')} В джекпот ивентов ушло {fmt(bonus)}"
    bal = get_user(uid)["balance_coin"]
    head = f"{E('win')} <b>ПОБЕДА!</b> +{fmt(payout)} RCOIN" if payout > 0 else f"{E('lose')} <b>Провал.</b>"
    return f"{head}\n<blockquote>{detail}</blockquote>\n{E('balance')} Баланс: <b>{fmt(bal)}</b> RCOIN"


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
    "rank_clear": ("🗑 Снять ранги", True, []),
    "treasury": ("🏦 Доступ к казне (вкл/выкл)", True, []),
    "info": ("ℹ️ Инфо об игроке", True, []),
    "history": ("📜 История игр игрока", True, []),
    "nft_create": ("🎨 Создать NFT игроку", True, ["Название NFT", "Редкость: common / uncommon / rare / epic / legendary", "Оценка в RCOIN (или 0 — по редкости)", "Описание (или «-»)"]),
    "gift_give": ("💌 Выдать подарок-бокс игроку", True, ["Редкость: common / uncommon / rare / epic / legendary / random"]),
    "gift_gen": ("🎁 Сгенерировать подарок (код)", False, ["Редкость: common / uncommon / rare / epic / legendary / random"]),
    "mailing": ("📨 Рассылка", False, ["Текст рассылки (HTML разрешён)"]),
}


def admin_kb() -> InlineKeyboardMarkup:
    a = lambda k: btn(ADMIN_ACTIONS[k][0], f"adm:{k}")
    return kb([a("ban"), a("mute")], [a("unban")],
              [a("give_coin"), a("give_rbp")], [a("give_stars")],
              [a("take_coin"), a("take_rbp")], [a("take_stars")],
              [a("reset_coin"), a("reset_bank")], [a("reset_rbp"), a("reset_all")],
              [a("rank_scammer"), a("rank_admin")], [a("rank_donater"), a("rank_official")],
              [a("rank_clear"), a("treasury")],
              [btn("📊 Статистика", "adm:stats"), btn("👥 Игроки", "adm:users")],
              [a("mailing"), btn("💾 Выгрузка БД", "adm:export")],
              [a("info"), a("history")],
              [a("nft_create"), a("gift_gen")], [a("gift_give"), btn("📦 Список подарков", "adm:gift_list")])


@dp.message(P("адм1308", "admin", "админ"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ У вас нет прав администратора.")
    await state.clear()
    await message.reply(f"{E('admin')} <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=admin_kb())


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
    elif action == "nft_create":
        rar = a[1].lower()
        if rar not in RARITY_BASE:
            return "❌ Неверная редкость."
        price = parse_amount(a[2]) or RARITY_BASE[rar]
        nid = make_nft(tid, a[0][:30], rar, None, "" if a[3] == "-" else a[3][:200], price)
        return f"🎨 NFT создан и выдан {nm}:\n{nft_card(q('SELECT * FROM nft_items WHERE id=?', (nid,), one=True))}"
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


async def _dm(uid: int, text: str):
    try:
        await bot.send_message(uid, text)
    except Exception:
        pass


@dp.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет прав", True)
    action = cb.data.split(":")[1]
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
    await ask(cb, state, "adm_a", f"{title}\n{prompts[0]}", action=action, target=0, answers=[])


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
    answers = list(d.get("answers", [])) + [m.text.strip()]
    if len(answers) < len(prompts):
        return await step(m, state, "adm_a", f"{title}\n{prompts[len(answers)]}", answers=answers)
    await adm_finish(m, state, d["action"], d.get("target", 0), answers)


async def mailing(m: Message, text: str):
    ids = [r["user_id"] for r in q("SELECT user_id FROM users")]
    ok = fail = 0
    for uid in ids:
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
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
    amount = 1_000_000 if kind == "fri" else 500_000
    ids = [r["user_id"] for r in q("SELECT user_id FROM users WHERE banned_until<=?", (now(),))]
    if not ids:
        return False
    total = amount * len(ids)
    if not treasury_take(total):
        log.warning("Авто-чек %s: в казне не хватает %s", kind, fmt(total))
        await _dm(OWNER_ID, f"⚠️ Авто-чек не выдан: в казне {fmt(treasury_get())}, нужно {fmt(total)}. Пополни казну.")
        return False
    x("UPDATE users SET balance_coin=balance_coin+? WHERE banned_until<=?", (amount, now()))
    key = None
    if kind == "sat":
        for uid in ids:
            inv_add(uid, random.choice(list(SOUVENIRS)))
    title = "🎄 ПЯТНИЧНЫЙ АВТО-ЧЕК" if kind == "fri" else "❄️ СУББОТНИЙ ИВЕНТ-ЧЕК"
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
                kv_set("auto:fri:" + d, "1")
                await distribute_check("fri")
            if n.weekday() == 5 and n.hour >= 12 and not kv_get("auto:sat:" + d):
                kv_set("auto:sat:" + d, "1")
                await distribute_check("sat")
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
    return bet if bet >= lo else 0


def w_err(msg: str) -> dict:
    return {"ok": False, "err": msg}


def w_spend(u, bet: int, lo: int = 10) -> Optional[dict]:
    if bet < lo:
        return w_err(f"Минимальная ставка {lo}")
    if not spend(u["user_id"], bet):
        return w_err("Недостаточно RCOIN")
    return None


# ---------- арена: бесплатное соревнование без денежных ставок ----------
AR: Dict[str, Any] = {}
AR_HIST: List[dict] = []
AR_CD, AR_ROLL, AR_SHOW, AR_MAX = 15, 7, 9, 10
ARENA_COLORS = ["#ff8a3d", "#3d9bff", "#35d07f", "#b06bff", "#ffd23d", "#ff5c5c", "#2de2e6", "#c98bff", "#8dff6b", "#ff7ab8", "#111111"]


def ar_reset():
    AR.clear()
    AR.update(phase="idle", players={}, t_cd=0.0, t_roll=0.0, t_done=0.0,
              winner=None, land=0.5, created=time.time())


ar_reset()


def ar_tick():
    t = time.time()
    ph = AR["phase"]
    if ph == "countdown" and t >= AR["t_cd"] + AR_CD:
        ids = list(AR["players"])
        if not ids:
            ar_reset()
            return None
        AR["winner"] = random.choice(ids)
        AR["land"] = random.uniform(0.15, 0.85)
        AR["phase"], AR["t_roll"] = "rolling", t
    elif ph == "rolling" and t >= AR["t_roll"] + AR_ROLL:
        winner = AR["winner"]
        player = AR["players"].get(winner)
        if player:
            # Non-monetary participation reward: experience only.
            x("INSERT OR IGNORE INTO it_progress(user_id) VALUES(?)", (winner,))
            x("UPDATE it_progress SET xp=xp+25 WHERE user_id=?", (winner,))
            AR_HIST.insert(0, {"name": player["name"], "reward": "25 XP"})
            del AR_HIST[6:]
        AR["phase"], AR["t_done"] = "done", t
        return winner, 25
    elif ph == "done" and t >= AR["t_done"] + AR_SHOW:
        ar_reset()
    elif ph == "waiting" and t - AR["created"] > 600:
        ar_reset()
    return None


async def arena_loop():
    while True:
        try:
            res = ar_tick()
            if res:
                await _dm(res[0], "🏆 <b>Арена завершена!</b> Ты получил <b>25 XP</b> за победу.")
        except Exception:
            log.exception("arena_loop")
        await asyncio.sleep(0.5)


def ar_state(uid: int) -> dict:
    t = time.time()
    pl = AR["players"]
    ids = list(pl)
    count = len(ids)
    ph = AR["phase"]
    players = [{"id": i, "name": pl[i]["name"], "color": pl[i]["color"],
                "pct": round(100 / max(count, 1), 1), "avatar": pl[i].get("avatar", "")}
               for i in ids]
    winner_idx = ids.index(AR["winner"]) if AR.get("winner") in ids else -1
    return {"phase": ph, "players": players, "pool": 0, "you": uid in pl,
            "cd_left": max(0.0, AR["t_cd"] + AR_CD - t) if ph == "countdown" else 0,
            "roll_total": AR_ROLL, "roll_elapsed": min(AR_ROLL, t - AR["t_roll"]) if ph == "rolling" else (AR_ROLL if ph == "done" else 0),
            "winner_idx": winner_idx, "land": AR["land"], "history": AR_HIST,
            "max": AR_MAX, "min_bet": 0}


def a_arena(u, body):
    ar_tick()
    return {"ok": True, "state": ar_state(u["user_id"])}


def a_arena_join(u, body):
    ar_tick()
    uid = u["user_id"]
    if AR["phase"] not in ("idle", "waiting", "countdown"):
        return w_err("Раунд уже идёт — дождись следующего")
    if uid not in AR["players"] and len(AR["players"]) >= AR_MAX:
        return w_err("Арена заполнена")
    if uid not in AR["players"]:
        name = re.sub(r"<[^>]+>", "", uname(u, False))
        requested = str(body.get("color", "")).lower()
        if requested == "#111111" and not is_premium(uid):
            requested = ""
        color = requested if requested in ARENA_COLORS else ARENA_COLORS[len(AR["players"]) % 10]
        photo = str(body.get("photo_url", ""))[:500]
        if not (photo.startswith("https://t.me/i/userpic/") or photo.startswith("https://telegram.org/")):
            photo = ""
        AR["players"][uid] = {"name": name, "color": color, "avatar": photo}
    t = time.time()
    if len(AR["players"]) == 1:
        AR["phase"], AR["created"] = "waiting", t
    elif AR["phase"] != "countdown":
        AR["phase"], AR["t_cd"] = "countdown", t
    return {"ok": True, "state": ar_state(uid)}


def a_arena_leave(u, body):
    uid = u["user_id"]
    if AR["phase"] != "waiting" or uid not in AR["players"]:
        return w_err("Покинуть лобби можно до начала отсчёта")
    del AR["players"][uid]
    if not AR["players"]:
        ar_reset()
    return {"ok": True, "state": ar_state(uid)}


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
    return {"ok": True, "name": re.sub(r"<[^>]+>", "", uname(u, False)), "id": uid,
            "balance": u["balance_coin"], "rbp": u["balance_point"], "games": stats["n"] or 0,
            "wins": u["total_wins"] or stats["w"] or 0, "lost": int(stats["lost"] or 0),
            "rank": u["rank_title"] or "Новичок", "badges": [f"{BADGES[b]['fallback']} {BADGES[b]['role']}" for b in profile_badges(uid) if b in BADGES],
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
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover,user-scalable=no"><title>RCOIN · Игровой центр</title><script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{color-scheme:dark;--bg:#080b10;--panel:#111720;--panel2:#151e29;--line:#263443;--text:#f4f7fb;--muted:#8d9baa;--blue:#2798ff;--green:#27c982;--red:#ff5268;--gold:#ffc45d;--radius:22px}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}body{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(900px 500px at 100% -10%,#12304a 0%,transparent 60%),radial-gradient(700px 450px at -20% 40%,#172433 0%,transparent 60%),var(--bg);color:var(--text);min-height:100vh;padding:calc(14px + env(safe-area-inset-top)) 14px calc(100px + env(safe-area-inset-bottom));overflow-x:hidden}.wrap{max-width:760px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.brand{font-size:19px;font-weight:950;letter-spacing:.08em}.brand span{color:var(--blue)}.wallet{background:#111b26;border:1px solid #263b50;padding:9px 13px;border-radius:999px;font-weight:850}.wallet small{color:var(--muted);font-size:10px;margin-right:6px}.hero{background:linear-gradient(135deg,#142638,#101720 65%);border:1px solid #2b4054;border-radius:28px;padding:20px;margin-bottom:14px;position:relative;overflow:hidden}.hero:after{content:"";position:absolute;width:190px;height:190px;right:-65px;top:-85px;border-radius:50%;background:#178cf2;filter:blur(75px);opacity:.28}.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#91a7bb;font-weight:800}.balance{font-size:clamp(27px,7vw,38px);font-weight:950;margin:7px 0 4px;letter-spacing:-1px}.balance small{font-size:15px;color:#8dbde7}.subline{color:var(--muted);font-size:12px}.copy{margin-top:12px;border:1px dashed #52677b;background:#0c141d;color:#c7d8e8;padding:9px 12px;border-radius:12px;width:100%;text-align:left;font:600 13px ui-monospace,monospace}.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin:12px 0}.stat{background:var(--panel);border:1px solid var(--line);border-radius:17px;padding:13px}.stat span{display:block;color:var(--muted);font-size:11px;margin-bottom:5px}.stat b{font-size:16px}.panel{background:linear-gradient(155deg,#141d27,#0f151d);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin:12px 0;box-shadow:0 12px 32px #0003}.panel h2{font-size:16px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}.muted{color:var(--muted);font-size:12px;line-height:1.5}.nav{position:fixed;z-index:10;bottom:calc(10px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);width:min(720px,calc(100% - 24px));display:grid;grid-template-columns:repeat(5,1fr);gap:5px;padding:7px;background:#111923ed;border:1px solid #304153;border-radius:22px;backdrop-filter:blur(18px);box-shadow:0 12px 40px #0009}.nav button{border:0;background:transparent;color:#8191a1;padding:10px 3px;border-radius:15px;font-size:10px;font-weight:800}.nav button i{display:block;font-style:normal;font-size:18px;margin-bottom:4px}.nav button.active{background:#173a59;color:#eaf6ff;box-shadow:inset 0 0 0 1px #2d77b2}.page{display:none}.page.active{display:block;animation:fade .22s ease}@keyframes fade{from{opacity:.3;transform:translateY(5px)}to{opacity:1;transform:none}}.actions{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.action{border:1px solid #304255;background:#172431;color:#eaf4ff;padding:12px 6px;border-radius:15px;font-size:12px;font-weight:800}.action:active,.btn:active{transform:scale(.98)}.btn{width:100%;border:0;border-radius:15px;padding:14px 16px;font-weight:900;font-size:14px;color:white;background:linear-gradient(135deg,#1687ed,#2864d9);margin-top:9px}.btn.green{background:linear-gradient(135deg,#21c981,#149c72);color:#061b13}.btn.red{background:linear-gradient(135deg,#ff536b,#cf294a)}.btn.ghost{background:#1a2632;border:1px solid #35485b;color:#dce8f4}.row{display:flex;gap:9px;align-items:center}.row>*{min-width:0;flex:1}input{width:100%;padding:13px;border-radius:13px;border:1px solid #34495e;background:#0a1119;color:white;font-size:15px;font-weight:800;outline:none}input:focus{border-color:var(--blue)}.profile-head{display:flex;align-items:center;gap:13px;margin:4px 0 12px}.profile-photo{width:58px;height:58px;border-radius:50%;object-fit:cover;border:2px solid #4b91c9;background:#22384b}.profile-photo.fallback{display:grid;place-items:center;color:#fff;font-weight:900;font-size:22px}.color-picks{display:flex;gap:9px;flex-wrap:wrap;margin:10px 0}.color-pick{width:30px;height:30px;border-radius:50%;border:2px solid #ffffff33;cursor:pointer}.color-pick.selected{outline:2px solid white;outline-offset:3px}.snowman-score{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid #253747}.players{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.player{display:flex;align-items:center;gap:9px;background:#0c141d;border:1px solid #263849;border-radius:14px;padding:10px}.avatar{width:35px;height:35px;border-radius:50%;display:grid;place-items:center;font-weight:900;color:#07111a;flex:none}.player b{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.player small{display:block;color:var(--muted);font-size:10px;margin-top:2px}.arena{display:grid;place-items:center;min-height:250px;background:radial-gradient(circle at 50% 50%,#1b3448,#0b121b 70%);border:1px solid #2a4155;border-radius:22px;overflow:hidden}.arena canvas{width:min(100%,340px);height:auto}.status{text-align:center;font-size:18px;font-weight:900;margin:12px 0 4px}.progress{height:7px;background:#243241;border-radius:20px;overflow:hidden;margin-top:12px}.progress span{height:100%;display:block;width:0;background:linear-gradient(90deg,#259aff,#55d4ff);transition:width .25s}.chart{width:100%;height:190px;display:block;background:#0b131c;border-radius:16px}.price{font-size:28px;font-weight:950}.up{color:var(--green)}.down{color:var(--red)}.trade-buttons{display:grid;grid-template-columns:1fr 1fr;gap:9px}.trade-buttons .btn{margin-top:0}.gridcards{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.tile{border:1px solid #2b3b4b;border-radius:17px;background:#101923;padding:14px;min-height:105px}.tile .ico{font-size:25px;margin-bottom:9px}.tile b{display:block;font-size:13px}.tile small{color:var(--muted);font-size:11px}.badge{display:inline-flex;align-items:center;padding:5px 9px;border:1px solid #31516a;background:#142b3e;border-radius:999px;color:#b9ddfa;font-size:10px;font-weight:900;margin:3px}.nft{border:1px solid #33475a;background:#0b131c;border-radius:16px;padding:10px}.nft img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:12px;background:#182432}.nft b{display:block;font-size:12px;margin-top:8px}.toast{position:fixed;left:50%;bottom:95px;transform:translate(-50%,15px);opacity:0;pointer-events:none;background:#1b2b3a;border:1px solid #42617b;padding:11px 16px;border-radius:13px;font-size:13px;font-weight:800;transition:.2s;z-index:20;max-width:90%;text-align:center}.toast.show{opacity:1;transform:translate(-50%,0)}.hide{display:none!important}@media(min-width:600px){.stats{grid-template-columns:repeat(4,1fr)}.gridcards{grid-template-columns:repeat(3,1fr)}}
</style></head><body><main class="wrap">
<header class="top"><div class="brand">RCOIN<span>·</span>BOT</div><div class="wallet"><small>RCOIN</small><span id="topBal">—</span></div></header>
<section class="hero"><div class="eyebrow">ТВОЙ ИГРОВОЙ СЧЁТ</div><div class="balance" id="heroBal">— <small>RCOIN</small></div><div class="subline">Нажми на моно-строку ниже, чтобы скопировать баланс</div><button class="copy" id="copyBal" onclick="copyBalance()">·····················</button><div class="actions"><button class="action" onclick="sendBotAction('bonus')">🎁 Бонус</button><button class="action" onclick="sendBotAction('daily')">📅 Ежедневный</button><button class="action" onclick="go('career')">💼 Заработать</button></div></section>
<div class="stats"><div class="stat"><span>🎮 Сыграно игр</span><b id="games">—</b></div><div class="stat"><span>🏅 Ранг</span><b id="rank">—</b></div><div class="stat"><span>⚔️ Победы в дуэлях</span><b id="wins">—</b></div><div class="stat"><span>📉 Проиграно RCOIN</span><b id="lost">—</b></div></div>
<section id="home" class="page active"><div class="panel"><div class="profile-head"><img id="profilePhoto" class="profile-photo" src="" alt="Аватар"><div><h2 id="playerName">Игрок</h2><div class="muted" id="profileRank">Профиль RCOIN</div></div></div><div id="badges"></div><p class="muted" style="margin-top:10px">Твои достижения и статус отображаются здесь. Управление галочками — команда «Галочки» в боте.</p></div><div class="gridcards"><div class="tile" onclick="go('arena')"><div class="ico">🎯</div><b>Арена</b><small>Соревнование до 10 игроков</small></div><div class="tile" onclick="go('career')"><div class="ico">💻</div><b>IT-карьера</b><small>Задания и опыт</small></div><div class="tile" onclick="go('trade')"><div class="ico">📈</div><b>Трейдинг</b><small>Курс и портфель</small></div><div class="tile" onclick="go('events')"><div class="ico">🎄</div><b>Ивенты</b><small>Сезонные активности</small></div><div class="tile" onclick="go('nft')"><div class="ico">🖼️</div><b>NFT-коллекция</b><small>Твои цифровые предметы</small></div><div class="tile" onclick="toast('Команды: /зп · /работа · /трейдинг · Галочки')"><div class="ico">📚</div><b>Команды</b><small>Все возможности бота</small></div></div></section>
<section id="arena" class="page"><div class="panel"><h2>🎯 ARENA <span class="muted" id="arenaCount">0/10</span></h2><div class="arena"><canvas id="arenaCanvas" width="340" height="260"></canvas></div><div class="status" id="arenaStatus">Подключаем арену…</div><p class="muted" id="arenaHint" style="text-align:center">Вход бесплатный. При двух игроках начинается отсчёт 15 секунд.</p><div class="color-picks"><button class="color-pick selected" data-color="#ff8a3d" style="background:#ff8a3d" onclick="setArenaColor('#ff8a3d')"></button><button class="color-pick" data-color="#3d9bff" style="background:#3d9bff" onclick="setArenaColor('#3d9bff')"></button><button class="color-pick" data-color="#35d07f" style="background:#35d07f" onclick="setArenaColor('#35d07f')"></button><button class="color-pick" data-color="#b06bff" style="background:#b06bff" onclick="setArenaColor('#b06bff')"></button><button class="color-pick" data-color="#111111" style="background:#111111" onclick="setArenaColor('#111111')" title="Premium"></button></div><div class="progress"><span id="arenaProgress"></span></div><button class="btn" id="joinBtn" onclick="arenaJoin()">Войти в лобби</button><button class="btn ghost hide" id="leaveBtn" onclick="arenaLeave()">Покинуть лобби</button></div><div class="panel"><h2>👥 Участники</h2><div class="players" id="players"><p class="muted">Пока никого нет.</p></div></div><div class="panel"><h2>🏆 Последние победители</h2><div id="arenaHistory" class="muted">Пока нет завершённых раундов.</div></div></section>
<section id="career" class="page"><div class="panel"><h2>💻 IT-карьера <span class="badge" id="jobStage">Стажёр</span></h2><div class="stats"><div class="stat"><span>Уровень</span><b id="jobLevel">1</b></div><div class="stat"><span>Опыт</span><b id="jobXp">0 XP</b></div><div class="stat"><span>Заработано</span><b id="jobCoins">0</b></div><div class="stat"><span>Заданий</span><b id="jobTasks">0</b></div></div><p class="muted" id="jobCooldown">Выполняй задания, повышай уровень и открывай новые должности.</p><button class="btn green" id="taskBtn" onclick="doTask()">🚀 Получить IT-задание</button></div><div class="panel"><h2>💼 Зарплата за активность</h2><p class="muted">Пиши сообщения в групповых чатах. Команда /зп покажет начисление и позволит забрать ежедневную зарплату.</p><button class="btn ghost" onclick="toast('Открой чат с ботом и отправь /зп')">Как получить зарплату</button></div></section>
<section id="trade" class="page"><div class="panel"><h2>📈 RCOIN MARKET <span class="badge">LIVE</span></h2><div class="row"><div><div class="muted">Текущий курс v-RCOIN</div><div class="price" id="price">—</div></div><div style="text-align:right"><div class="muted">Изменение</div><b id="change">—</b></div></div><canvas id="chart" class="chart" width="640" height="190"></canvas><p class="muted" style="margin-top:8px">Внутриигровой симулятор курса. Это не реальные деньги и не финансовый инструмент.</p></div><div class="panel"><h2>💼 Портфель</h2><div class="stats"><div class="stat"><span>v-RCOIN</span><b id="holding">0</b></div><div class="stat"><span>Стоимость</span><b id="value">0</b></div><div class="stat"><span>Вложено</span><b id="invested">0</b></div><div class="stat"><span>Результат</span><b id="profit">0</b></div></div></div><div class="panel"><h2>Обмен</h2><input id="amount" type="number" min="1000" step="1000" value="100000" placeholder="Сумма RCOIN"><div class="trade-buttons" style="margin-top:10px"><button class="btn green" onclick="buy()">🟢 Купить</button><button class="btn red" onclick="sell()">🔴 Продать всё</button></div></div></section>
<section id="events" class="page"><div class="panel"><h2>⛄ СНЕЖНЫЙ МАРАФОН <span class="badge">DAILY TOP 3</span></h2><div class="stats"><div class="stat"><span>Снежки</span><b id="snowballs">0</b></div><div class="stat"><span>Снеговики сегодня</span><b id="snowmen">0</b></div></div><p class="muted">Собирай снежки каждые 20 секунд. Из 20 снежков можно слепить снеговика. Топ-3 дня получают случайную награду из казны от 1 до 10 млрд RCOIN, если средств достаточно.</p><div class="row"><button class="btn" onclick="snowCollect()">❄️ Собрать снежки</button><button class="btn green" onclick="snowBuild()">☃️ Слепить</button></div><div class="panel"><h2>🏆 Рейтинг дня</h2><div id="snowTop" class="muted">Загрузка рейтинга…</div></div></div><div class="panel"><h2>🎄 СЕЗОННЫЕ ИВЕНТЫ</h2><p class="muted">Собирай коллекционные предметы, выполняй задания и открывай награды. Новогодние эмодзи доступны в сообщениях бота при поддержке Telegram Premium Emoji.</p><div class="gridcards" style="margin-top:12px"><div class="tile"><div class="ico">❄️</div><b>Снежный марафон</b><small>Ежедневные задания</small></div><div class="tile"><div class="ico">🎅</div><b>Помощь Санте</b><small>Сезонная цепочка</small></div><div class="tile"><div class="ico">🐻‍❄️</div><b>Полярная коллекция</b><small>Собери предметы</small></div><div class="tile"><div class="ico">🎁</div><b>NFT-чеканка</b><small>Создай предмет в коллекцию</small></div></div><button class="btn" onclick="toast('Открой в боте команду «ивенты» для полного списка заданий')">Открыть задания в боте</button></div></section>
<section id="nft" class="page"><div class="panel"><h2>🖼️ NFT-коллекция <span class="muted" id="nftCount">0 предметов</span></h2><p class="muted">Твои сгенерированные цифровые предметы и коллекционные изображения.</p><div class="gridcards" id="nftGrid" style="margin-top:12px"><p class="muted">Загружаем коллекцию…</p></div><button class="btn" onclick="mintNft()">✨ Создать NFT · 50 000 RCOIN</button></div></section>
</main><nav class="nav"><button class="active" data-page="home" onclick="go('home')"><i>⌂</i>Главная</button><button data-page="arena" onclick="go('arena')"><i>◉</i>Арена</button><button data-page="career" onclick="go('career')"><i>⌘</i>Работа</button><button data-page="trade" onclick="go('trade')"><i>↗</i>Трейдинг</button><button data-page="events" onclick="go('events')"><i>✧</i>Ивенты</button></nav><div class="toast" id="toast"></div>
<script>
const tg=window.Telegram&&Telegram.WebApp;if(tg){try{tg.ready();tg.expand();tg.setHeaderColor('#080b10');tg.setBackgroundColor('#080b10')}catch(e){}}
const INIT=tg?tg.initData:"",TU=tg?.initDataUnsafe?.user||{},$=id=>document.getElementById(id),fmt=n=>Math.floor(Number(n)||0).toLocaleString('en-US').replace(/,/g,"'");let ME=null,AS=null,AT=0,TS=null,tradeTimer=null,arenaTimer=null,arenaColor='#ff8a3d';
async function api(p,b={}){try{const r=await fetch('/api/'+p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({init:INIT,photo_url:TU.photo_url||'',display_name:[TU.first_name,TU.last_name].filter(Boolean).join(' '),...b})});return await r.json()}catch(e){return{ok:false,err:'Нет соединения с сервером'}}}
function toast(t){const e=$('toast');e.textContent=t;e.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>e.classList.remove('show'),2600)}function haptic(){try{tg.HapticFeedback.impactOccurred('light')}catch(e){}}
function go(p){document.querySelectorAll('.page').forEach(e=>e.classList.toggle('active',e.id===p));document.querySelectorAll('.nav button').forEach(e=>e.classList.toggle('active',e.dataset.page===p));if(p==='arena')startArena();if(p==='trade')startTrade();if(p==='career')loadCareer();if(p==='nft')loadNft();if(p==='events')loadSnowman()}
function setBalance(v){const x=fmt(v);$('topBal').textContent=x;$('heroBal').innerHTML=x+' <small>RCOIN</small>';$('copyBal').textContent=x}
async function copyBalance(){const value=ME?Number(ME.balance||0).toLocaleString('en-US').replace(/,/g,"'"):'0';try{await navigator.clipboard.writeText(value);toast('Баланс '+value+' скопирован')}catch(e){toast('Баланс: '+value)}}
function sendBotAction(action){if(!tg||typeof tg.sendData!=='function'){toast('Открой приложение через кнопку бота в Telegram');return}try{tg.sendData(action)}catch(e){toast('Не удалось передать действие боту')}}
async function loadMe(){if(!INIT){$('arenaStatus').textContent='Открой веб-приложение через меню бота в Telegram';return}const j=await api('me');if(!j.ok)return toast(j.err||'Не удалось загрузить профиль');ME=j;setBalance(j.balance);$('playerName').textContent=j.name||'Игрок';$('profileRank').textContent=j.rank||'Новичок';const ph=$('profilePhoto');if(j.photo_url){ph.src=j.photo_url;ph.style.display='block'}else{ph.style.display='none'}$('games').textContent=fmt(j.games);$('rank').textContent=j.rank||'Новичок';$('wins').textContent=fmt(j.wins);$('lost').textContent=fmt(j.lost);$('badges').innerHTML=(j.badges||[]).map(x=>'<span class="badge">'+safe(x)+'</span>').join('')||'<span class="muted">Пока нет выбранных галочек</span>'}
function safe(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
/* Free arena */
const ac=$('arenaCanvas'),ax=ac.getContext('2d');let ball=0;
function drawArena(){const w=340,h=260;ax.clearRect(0,0,w,h);ax.save();ax.translate(w/2,h/2);ax.beginPath();ax.arc(0,0,92,0,Math.PI*2);ax.strokeStyle='#29465d';ax.lineWidth=18;ax.stroke();const n=AS?.players?.length||0;for(let i=0;i<n;i++){const a=(i/n)*Math.PI*2-Math.PI/2;ax.beginPath();ax.arc(0,0,92,a,a+Math.PI*2/n);ax.strokeStyle=AS.players[i].color;ax.lineWidth=17;ax.stroke()}const rolling=AS?.phase==='rolling'||AS?.phase==='done';const a=rolling?ball:(performance.now()/1600);const x=Math.cos(a)*65,y=Math.sin(a)*65;ax.beginPath();ax.arc(x,y,9,0,Math.PI*2);ax.fillStyle='#fff';ax.shadowColor='#65caff';ax.shadowBlur=20;ax.fill();ax.shadowBlur=0;ax.fillStyle='#eaf5ff';ax.textAlign='center';ax.font='800 18px sans-serif';ax.fillText(AS?.phase==='countdown'?String(Math.ceil(Math.max(0,AS.cd_left-(performance.now()-AT)/1000))):rolling?'●':'ARENA',0,5);ax.restore();requestAnimationFrame(drawArena)}requestAnimationFrame(drawArena);
function renderArena(){if(!AS)return;const n=AS.players.length,ph=AS.phase;const left=Math.max(0,AS.cd_left-(performance.now()-AT)/1000);$('arenaCount').textContent=n+'/10';let title=ph==='idle'?'Лобби свободно':ph==='waiting'?'Ожидаем второго игрока':ph==='countdown'?'Старт через '+Math.ceil(left)+' сек.':ph==='rolling'?'Шарик выбирает победителя…':'Раунд завершён';if(ph==='done'&&AS.winner_idx>=0)title='🏆 Победитель: '+AS.players[AS.winner_idx].name;$('arenaStatus').textContent=title;$('arenaHint').textContent=ph==='idle'?'Вход бесплатный. Собери до 10 участников.':ph==='waiting'?'Нужен ещё один игрок — затем начнётся отсчёт 15 секунд.':'У каждого участника равные шансы. Победитель получает 25 XP.';$('arenaProgress').style.width=ph==='countdown'?((15-left)/15*100)+'%':ph==='rolling'?((AS.roll_elapsed||0)/7*100)+'%':ph==='done'?'100%':'0%';$('joinBtn').classList.toggle('hide',AS.you||!['idle','waiting','countdown'].includes(ph));$('joinBtn').disabled=!['idle','waiting','countdown'].includes(ph);$('leaveBtn').classList.toggle('hide',!(AS.you&&ph==='waiting'));const box=$('players');box.innerHTML='';if(!n)box.innerHTML='<p class="muted">Пока никого нет.</p>';AS.players.forEach(p=>{const d=document.createElement('div');d.className='player';const a=document.createElement('div');a.className='avatar';a.style.background=p.color;if(p.avatar){const im=document.createElement('img');im.src=p.avatar;im.alt='';im.style.cssText='width:35px;height:35px;border-radius:50%;object-fit:cover';a.append(im)}else{a.textContent=(p.name||'?').slice(0,1).toUpperCase()}const t=document.createElement('div');t.innerHTML='<b>'+safe(p.name)+'</b><small>'+safe(String(p.pct||0))+'% шанс · '+(p.color||'')+'</small>';d.append(a,t);box.append(d)});$('arenaHistory').textContent=AS.history?.length?AS.history.map(x=>x.name+' · '+x.reward).join('  •  '):'Пока нет завершённых раундов'}
async function pollArena(){if(!INIT)return;const j=await api('arena');if(j.ok){AS=j.state;AT=performance.now();renderArena()}arenaTimer=setTimeout(pollArena,AS&&['countdown','rolling'].includes(AS.phase)?450:1300)}function startArena(){if(!arenaTimer)pollArena()}
async function arenaJoin(){const j=await api('arena_join',{color:arenaColor});if(!j.ok)return toast(j.err);AS=j.state;AT=performance.now();renderArena();haptic();toast('Ты в лобби!')}async function arenaLeave(){const j=await api('arena_leave');if(!j.ok)return toast(j.err);AS=j.state;AT=performance.now();renderArena();toast('Ты покинул лобби')}
/* IT career */
async function loadCareer(){const j=await api('it_state');if(!j.ok)return;$('jobStage').textContent=j.stage;$('jobLevel').textContent=j.level;$('jobXp').textContent=fmt(j.xp)+' XP';$('jobCoins').textContent=fmt(j.coins);$('jobTasks').textContent=fmt(j.tasks);$('jobCooldown').textContent=j.cooldown>0?'Следующее задание через '+Math.ceil(j.cooldown)+' сек.':'Можно брать новое задание.';$('taskBtn').disabled=j.cooldown>0}
async function doTask(){const j=await api('it_task');if(!j.ok)return toast(j.err||'Не удалось выполнить задание');toast(j.msg||'Задание завершено');setBalance(j.balance);loadCareer()}
/* NFT inventory */
async function loadNft(){const j=await api('nft_state');if(!j.ok)return;const g=$('nftGrid');g.innerHTML='';$('nftCount').textContent=j.items.length+' предметов';if(!j.items.length){g.innerHTML='<p class="muted">Коллекция пока пуста. Создай первый NFT.</p>';return}j.items.forEach(x=>{const d=document.createElement('div');d.className='nft';const im=document.createElement('img');im.src=x.url;im.alt=x.name;const b=document.createElement('b');b.textContent=x.name+' #'+x.id;const sm=document.createElement('small');sm.className='muted';sm.textContent=x.rarity;d.append(im,b,sm);g.append(d)})}
async function mintNft(){const j=await api('nft_mint');if(!j.ok)return toast(j.err||'Не удалось создать NFT');setBalance(j.balance);toast(j.msg||'NFT создан');loadNft()}
/* Live simulated market */
const cc=$('chart'),cx=cc.getContext('2d');function drawChart(){if(!TS?.series?.length)return;const w=cc.width,h=cc.height,ps=TS.series.map(x=>x.p),lo=Math.min(...ps),hi=Math.max(...ps),rg=hi-lo||1;cx.clearRect(0,0,w,h);const up=ps.at(-1)>=ps[0];const gr=cx.createLinearGradient(0,0,0,h);gr.addColorStop(0,up?'rgba(39,201,130,.28)':'rgba(255,82,104,.28)');gr.addColorStop(1,'rgba(0,0,0,0)');cx.beginPath();ps.forEach((v,i)=>{const x=i/(ps.length-1)*w,y=h-12-(v-lo)/rg*(h-28);i?cx.lineTo(x,y):cx.moveTo(x,y)});cx.lineTo(w,h);cx.lineTo(0,h);cx.closePath();cx.fillStyle=gr;cx.fill();cx.beginPath();ps.forEach((v,i)=>{const x=i/(ps.length-1)*w,y=h-12-(v-lo)/rg*(h-28);i?cx.lineTo(x,y):cx.moveTo(x,y)});cx.strokeStyle=up?'#27c982':'#ff5268';cx.lineWidth=3;cx.stroke()}
function renderTrade(){if(!TS)return;$('price').textContent=Number(TS.price).toFixed(2);const ch=(TS.price-TS.prev)/TS.prev*100;$('change').textContent=(ch>=0?'+':'')+ch.toFixed(2)+'%';$('change').className=ch>=0?'up':'down';$('holding').textContent=Number(TS.coins||0).toFixed(2);$('value').textContent=fmt(TS.value);$('invested').textContent=fmt(TS.invested);const pl=(TS.value||0)-(TS.invested||0);$('profit').textContent=(pl>=0?'+':'')+fmt(pl);$('profit').className=pl>=0?'up':'down';drawChart()}
async function loadTrade(){const j=await api('trade_state');if(j.ok){TS=j;renderTrade()}}function startTrade(){if(!tradeTimer){loadTrade();tradeTimer=setInterval(loadTrade,5000)}else loadTrade()}async function buy(){const j=await api('trade_buy',{amount:$('amount').value});if(!j.ok)return toast(j.msg||j.err);TS=j.state;setBalance(j.balance);renderTrade();toast(j.msg||'Покупка выполнена')}async function sell(){const j=await api('trade_sell',{all:true});if(!j.ok)return toast(j.msg||j.err);TS=j.state;setBalance(j.balance);renderTrade();toast(j.msg||'Продажа выполнена')}
async function loadSnowman(){const j=await api('snowman_state');if(!j.ok)return;$('snowballs').textContent=fmt(j.snowballs);$('snowmen').textContent=fmt(j.snowmen);const box=$('snowTop');box.innerHTML='';if(!j.leaderboard.length){box.textContent='Пока нет участников — начни первым!';return}j.leaderboard.forEach((p,i)=>{const d=document.createElement('div');d.className='snowman-score';const medals=['🥇','🥈','🥉'];const a=document.createElement('b');a.textContent=(medals[i]||('#'+(i+1)))+' '+p.name;const b=document.createElement('span');b.textContent=fmt(p.snowmen)+' ☃️ · '+fmt(p.snowballs)+' ❄️';d.append(a,b);box.append(d)})}
async function snowCollect(){const j=await api('snowman_collect');if(!j.ok)return toast(j.err||'Не удалось собрать снежки');toast('+'+j.gained+' снежков!');loadSnowman();haptic()}
async function snowBuild(){const j=await api('snowman_build');if(!j.ok)return toast(j.err||'Не удалось слепить снеговика');toast('Слеплено снеговиков: '+j.built+' ☃️');loadSnowman();haptic()}
function setArenaColor(c){arenaColor=c;document.querySelectorAll('.color-pick').forEach(x=>x.classList.toggle('selected',x.dataset.color===c))}
loadMe();setInterval(()=>{if(AS?.phase==='rolling')ball+=.28;},80);
</script></body></html>"""


async def page(request: web.Request):
    return web.Response(text=WEBAPP_HTML, content_type="text/html", charset="utf-8")


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
    app = web.Application()
    app.router.add_get("/", page)
    app.router.add_get("/webapp", page)
    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)
    app.router.add_get("/nft/{nid}", nft_asset)
    # The Web App exposes only non-wagering activities, the free arena, career and simulated market.
    routes = {"me": a_me, "arena": a_arena, "arena_join": a_arena_join, "arena_leave": a_arena_leave,
              "snowman_state": a_snowman_state, "snowman_collect": a_snowman_collect, "snowman_build": a_snowman_build}
    routes.update({"trade_state": api_trade_state, "trade_buy": api_trade_buy,
                   "trade_sell": api_trade_sell, "it_state": api_it_state,
                   "it_task": api_it_task, "nft_state": api_nft_state, "nft_mint": api_nft_mint})
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
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
                                   BotCommand(command="help", description="Помощь")])
        if WEBAPP_URL:
            from aiogram.types import MenuButtonWebApp
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Арена", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e:
        log.warning("set_my_commands/menu: %s", e)
    await start_web()
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(arena_loop())
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
    "dev": {"id": "5251635454041675257", "fallback": "👨‍💻", "title": "Developer", "role": "Developer",
            "price_coin": 0, "price_stars": 0, "buyable": False},
    "moder": {"id": "5766894601709296405", "fallback": "🛡", "title": "Moder", "role": "Moder",
              "price_coin": 0, "price_stars": 0, "buyable": False},
    "support": {"id": "5888937609253623352", "fallback": "🎧", "title": "Support", "role": "Support",
                "price_coin": 0, "price_stars": 0, "buyable": False},
    "tester": {"id": "5888937609253623352", "fallback": "🧪", "title": "Tester", "role": "Tester",
                "price_coin": 0, "price_stars": 0, "buyable": False},
    "premium2": {"id": "5789568614533176726", "fallback": "💎", "title": "Premium", "role": "Premium",
                 "price_coin": 0, "price_stars": 0, "buyable": False},
    "rubin": {"id": "5341454906807034418", "fallback": "💠", "title": "Rubin Premium", "role": "Premium",
              "price_coin": 0, "price_stars": 299, "buyable": True, "premium": True},
    "black": {"id": "5789386473560088107", "fallback": "☑️", "title": "Чёрная галочка", "role": "Donate",
              "price_coin": 5_000_000_000, "price_stars": 500, "buyable": True},
    "blue": {"id": "5444856076954520455", "fallback": "✔️", "title": "Синяя галочка", "role": "Donate",
             "price_coin": 2_500_000_000, "price_stars": 250, "buyable": True},
    "ny": {"id": "5954111328493771983", "fallback": "🎄", "title": "Новогодняя", "role": "Event",
           "price_coin": 5_000_000_000, "price_stars": 0, "buyable": True},
}
BADGE_ORDER = ["dev", "moder", "support", "tester", "premium2", "rubin", "black", "blue", "ny"]
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
    ):
        x(sql)


# ---------------- операции ----------------
def has_badge(uid: int, key: str) -> bool:
    return q("SELECT 1 FROM user_badges WHERE user_id=? AND badge=?", (uid, key), one=True) is not None


def give_badge(uid: int, key: str) -> bool:
    if key not in BADGES:
        return False
    created = x("INSERT OR IGNORE INTO user_badges(user_id,badge,got_at,slot) VALUES(?,?,?,0)", (uid, key, now()))[0]
    if created and BADGES[key].get("premium"):
        set_premium(uid, 30 * 86400)
    return bool(created)


def take_badge(uid: int, key: str) -> bool:
    if key not in BADGES:
        return False
    removed = x("DELETE FROM user_badges WHERE user_id=? AND badge=?", (uid, key))[0]
    if removed and BADGES[key].get("premium"):
        x("UPDATE user_premium SET until=0 WHERE user_id=?", (uid,))
    return bool(removed)


def my_badges(uid: int):
    have = {r["badge"] for r in q("SELECT badge FROM user_badges WHERE user_id=?", (uid,))}
    return [b for b in BADGE_ORDER if b in have]


def profile_badges(uid: int):
    pinned = [r["badge"] for r in q("SELECT badge FROM user_badges WHERE user_id=? AND slot=1", (uid,)) if r["badge"] in BADGES]
    if not pinned:
        pinned = my_badges(uid)
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
    parts = [f"<b>{esc(u['rank_title'] or 'Новичок')}</b>"]
    parts += [badge(b) for b in profile_badges(uid)]
    return " ".join(parts)


# =====================================================================
#                        НОВЫЙ ФОРМАТ БАЛАНСА
# =====================================================================
def mono(n: int) -> str:
    return f"{int(n):,}".replace(",", "'")


def nft_photo(uid: int):
    """Последняя NFT-картинка игрока; db:<id> означает изображение, сохранённое в БД."""
    r = q("SELECT id,name,photo FROM nft_items WHERE owner_id=? ORDER BY id DESC LIMIT 1", (uid,), one=True)
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
    return "", cap


def png_nft(seed: int, title: str) -> bytes:
    """Генерирует оригинальную NFT-карточку в PNG без внешних API."""
    rnd = random.Random(seed)
    w, h = 640, 420
    a = tuple(rnd.randint(15, 75) for _ in range(3))
    b = tuple(rnd.randint(80, 220) for _ in range(3))
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        for x0 in range(w):
            px[x0, y] = c
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(28):
        x0, y0 = rnd.randint(-40, w), rnd.randint(-40, h)
        rr = rnd.randint(12, 90)
        col = (rnd.randint(100,255), rnd.randint(100,255), rnd.randint(100,255), rnd.randint(18,65))
        d.ellipse((x0-rr, y0-rr, x0+rr, y0+rr), fill=col)
    # Central original geometric emblem.
    cx, cy = w // 2, 185
    col1 = tuple(rnd.randint(150,255) for _ in range(3)) + (235,)
    d.rounded_rectangle((cx-105, cy-105, cx+105, cy+105), radius=42, fill=(8,12,20,105), outline=col1, width=5)
    d.polygon([(cx,cy-75),(cx+67,cy),(cx,cy+75),(cx-67,cy)], fill=col1)
    d.ellipse((cx-26,cy-26,cx+26,cy+26), fill=(10,15,24,255))
    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 17)
    except Exception:
        font_big = ImageFont.load_default(); font_small = ImageFont.load_default()
    title = str(title)[:28]
    box = d.textbbox((0,0), title, font=font_big)
    d.text(((w-(box[2]-box[0]))/2, 330), title, font=font_big, fill=(255,255,255,245), stroke_width=1, stroke_fill=(0,0,0,120))
    d.text((24, 385), f"RCOIN NFT  /  #{seed}", font=font_small, fill=(255,255,255,190))
    out = io.BytesIO(); im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def balance_text(uid: int) -> str:
    u = get_user(uid)
    lost = q("SELECT SUM(CASE WHEN bet_amount>win_amount THEN bet_amount-win_amount ELSE 0 END) v "
             "FROM bet_history WHERE user_id=?", (uid,), one=True)["v"] or 0
    games = u["total_games"] or q("SELECT COUNT(*) n FROM bet_history WHERE user_id=?", (uid,), one=True)["n"] or 0
    prem = premium_left(uid)
    text = (f"{E('balance')} <b>Баланс: {fmt(u['balance_coin'])} RCOIN</b>\n"
            f"<code>{mono(u['balance_coin'])}</code>\n"
            f"<code>·····················</code>\n\n"
            f"{E('games')} Сыграно игр: <b>{fmt(games)}</b>\n"
            f"{E('profile')} Ранг: {rank_line(uid)}\n"
            f"{E('win')} Выиграно дуэлей: <b>{fmt(u['total_wins'])}</b>\n"
            f"{E('lose')} Проиграно RCOIN: <b>{fmt(int(lost))}</b>")
    if prem:
        text += f"\n💠 Premium: <b>{dur(prem)}</b> · шанс ×1.5 · бонус ×2"
    return text


def balance_kb(uid: int) -> InlineKeyboardMarkup:
    """На экране баланса оставляем только три основные кнопки."""
    return kb(
        [btn("🎁 Бонус", "bal:bonus", "donate"),
         btn("📅 Ежедневный бонус", "bal:daily", "star")],
        [btn("💼 Заработать", "bal:earn", "balance")],
    )


async def send_balance(message: Message, uid: int):
    url, cap = nft_photo(uid)
    text = balance_text(uid)
    markup = balance_kb(uid)
    if url.startswith("db:"):
        try:
            image_id = int(url.split(":", 1)[1])
            raw = base64.b64decode(kv_get(f"nftpng:{image_id}"), validate=True)
            await message.answer_photo(BufferedInputFile(raw, filename=f"rcoin_nft_{image_id}.png"),
                                       caption=text[:1000], reply_markup=markup)
            return
        except Exception as e:
            log.warning("Не удалось отправить NFT из БД: %s", e)
    if url and not url.startswith("http"):
        try:
            from aiogram.types import FSInputFile
            await message.answer_photo(FSInputFile(url), caption=text[:1000], reply_markup=markup)
            return
        except Exception:
            pass
    if url.startswith("http"):
        try:
            await message.answer_photo(url, caption=text[:1000], reply_markup=markup)
            return
        except Exception:
            pass
    await message.reply(text, reply_markup=markup)


@dp.callback_query(F.data == "bal:main")
async def cb_balance(cb: CallbackQuery):
    await safe_edit(cb, balance_text(cb.from_user.id), balance_kb(cb.from_user.id))
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
SALARY_BASE, SALARY_PER_MSG, SALARY_MAX, SALARY_ACTIVE_BONUS = 75_000, 2_500, 150_000, 100_000


async def track_activity(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    tu = message.from_user
    if not tu or tu.is_bot or not (message.text or message.caption):
        return
    x("INSERT INTO chat_activity(user_id,day,msg_count) VALUES(?,?,1) "
      "ON CONFLICT(user_id,day) DO UPDATE SET msg_count=msg_count+1", (tu.id, today()))


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
    amount = min(SALARY_MAX, SALARY_BASE + msgs * SALARY_PER_MSG)
    if msgs >= 30:
        amount += SALARY_ACTIVE_BONUS
    return amount * bonus_mult(uid), msgs


def salary_view(uid: int):
    amount, msgs = salary_amount(uid)
    paid = q("SELECT 1 FROM salary_log WHERE user_id=? AND day=?", (uid, today()), one=True)
    prem = premium_left(uid)
    text = (f"💼 <b>ЗАРПЛАТА ЗА АКТИВНОСТЬ</b>\n\n"
            f"💬 Сообщений в чате сегодня: <b>{fmt(msgs)}</b>\n"
            f"💰 Начислено: <b>{fmt(amount)}</b> RCOIN"
            + (" <i>(×2 Premium)</i>" if prem else "") + "\n"
            + (f"🔥 Бонус за активность: +{fmt(SALARY_ACTIVE_BONUS)}\n" if msgs >= 30
               else f"📈 Каждое сообщение в чате +{fmt(SALARY_PER_MSG)} RCOIN\n")
            + ("\n✅ <b>Зарплата за сегодня получена.</b>" if paid else "\n🎁 Доступна — нажми «Забрать»!"))
    rows = [[btn("Уже получено", "noop")] if paid else [btn(f"Забрать {fmt(amount)} RCOIN", "zp:get")]]
    return text, kb(*rows)


@dp.message(P("зп", "зарплата", "zp", "salary"))
async def cmd_salary(message: Message):
    t, k = salary_view(message.from_user.id)
    await message.reply(t, reply_markup=k)


@dp.callback_query(F.data == "zp:get")
async def cb_salary(cb: CallbackQuery):
    uid = cb.from_user.id
    amount, _ = salary_amount(uid)
    try:
        x("INSERT INTO salary_log(user_id,day,amount) VALUES(?,?,?)", (uid, today(), amount))
    except Exception:
        return await ans(cb, "Зарплата уже получена сегодня", True)
    add_coin(uid, amount)
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
    lines = ["🛡 <b>ГАЛОЧКИ</b>\n"]
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
        mark = "✅" if is_in else "▫️"
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
            await ans(cb, f"Куплено: {BADGES[b]['title']}!", True)
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
    rows = [[btn(f"Выдать {badge_text(b)}", f"adm:bg:{b}")] for b in BADGE_ORDER]
    rows.append([btn("Снять галочку", "adm:bgrm")])
    rows.append([btn("💠 Premium 30 дней", "adm:bgprem")])
    rows.append([btn("Себе Premium", "adm:bgself")])
    return text, kb(*rows)


@dp.callback_query(F.data.startswith("adm:bg"))
async def cb_adm_badges(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await ans(cb, "Нет прав", True)
    parts = cb.data.split(":")
    act = parts[1]
    if act == "bg":
        return await ask(cb, state, "adm_badge", f"Выдать {BADGES[parts[2]]['title']}\nВведи ID игрока:", badge=parts[2])
    if act == "bgrm":
        rows = [[btn(f"Снять {badge_text(b)}", f"adm:bgd:{b}")] for b in BADGE_ORDER]
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
    t = find_user((m.text or "").strip())
    if not t:
        return await m.reply("❌ Игрок не найден. Введи ID или @ник.")
    await state.clear()
    if remove:
        take_badge(t["user_id"], key)
        await m.reply(f"✅ Снята {BADGES[key]['title']} у {esc(t['display_name'] or str(t['user_id']))}")
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
    if not spend(uid, 50_000):
        return False, "❌ Отчеканить NFT стоит 50 000 RCOIN"
    rar = random.choices(RARITIES, weights=[50, 27, 14, 7, 2])[0]
    name = random.choice([n for n, _ in NFT_POOL[rar]])[0]
    name = " ".join([n for n, _ in NFT_POOL[rar] if True][:0]) or name
    pick = random.choice(NFT_POOL[rar])
    name = pick[0]
    nid = make_nft(uid, name, rar)
    path = NFT_DIR / f"nft_{nid}.svg"
    try:
        NFT_DIR.mkdir(parents=True, exist_ok=True)
        svg = svg_nft(nid, name)
        path.write_text(svg, encoding="utf-8")
        # Store both SVG and PNG in the DB: artwork survives Render Free restarts.
        kv_set(f"nftsvg:{nid}", svg)
        kv_set(f"nftpng:{nid}", base64.b64encode(png_nft(nid, name)).decode("ascii"))
        kv_set(f"nftimg:{nid}", path.name)
        x("UPDATE nft_items SET photo=? WHERE id=?", (path.name, nid))
    except Exception as e:
        log.warning("nft image: %s", e)
    return True, (f"🎨 <b>NFT отчеканен!</b>\n{RARITY_EMOJI[rar]} <b>{esc(name)}</b> <code>#{nid}</code>\n"
                  f"Редкость: {RARITY_NAME[rar]}\n\n<i>Картинка теперь показывается в балансе.</i>")


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
    rows = q("SELECT id,name,rarity FROM nft_items WHERE owner_id=? ORDER BY id DESC LIMIT 30", (u["user_id"],))
    return {"ok": True, "items": [{"id": r["id"], "name": r["name"], "rarity": RARITY_NAME.get(r["rarity"], r["rarity"]), "url": f"/nft/{r['id']}"} for r in rows]}


def api_nft_mint(u, body):
    ok, msg = mint_nft(u["user_id"])
    return {"ok": ok, "msg": re.sub(r"<[^>]+>", "", msg)}


async def nft_asset(request: web.Request):
    try:
        nid = int(request.match_info["nid"])
        row = q("SELECT id,photo FROM nft_items WHERE id=?", (nid,), one=True)
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
        if not path.exists() or path.parent.resolve() != NFT_DIR.resolve():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "public, max-age=3600"})
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен")
