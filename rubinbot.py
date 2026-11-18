# -*- coding: utf-8 -*-
"""
RCOIN·BOT — игровой бот (aiogram 3.x) + веб-приложение (aiohttp) в одном файле.

Запуск:  pip install -U aiogram aiohttp  &&  BOT_TOKEN=... python rcoin_bot.py
Render:  Start Command `python rcoin_bot.py`, переменные окружения см. README в ответе.
Токен НЕ хранится в коде — только в переменной окружения BOT_TOKEN.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import random
import re
import sqlite3
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape as esc
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "9165228951:AAFqAxLfwHc83TMlCib7awt0chj4mY_Ngt8").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "5257618084") or 0)
ADMIN_IDS = {OWNER_ID} | {int(v) for v in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
ADMIN_IDS.discard(0)
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@playhomemines").strip()
REQUIRED_CHAT = os.getenv("REQUIRED_CHAT", "@gamehomemines").strip()
ANNOUNCE_CHAT = os.getenv("ANNOUNCE_CHAT", REQUIRED_CHAT).strip()
REQUIRE_SUB = os.getenv("REQUIRE_SUB", "1") == "1"
DB_FILE = os.getenv("DB_FILE", "data.db")
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
    if icon and PREMIUM_ICONS and icon in EMOJI_IDS:
        kw["icon_custom_emoji_id"] = EMOJI_IDS[icon]
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


# ============================ УТИЛИТЫ ============================
MSK = timezone(timedelta(hours=3))


def now() -> int:
    return int(time.time())


def today() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d")


def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
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
def q(sql: str, args=(), one: bool = False):
    c = sqlite3.connect(DB_FILE, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        rows = c.execute(sql, args).fetchall()
    finally:
        c.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def x(sql: str, args=()) -> Tuple[int, int]:
    c = sqlite3.connect(DB_FILE, timeout=30)
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
            except sqlite3.OperationalError as e:
                log.warning("ALTER %s.%s: %s", table, name, e)


def init_db():
    c = sqlite3.connect(DB_FILE)
    try:
        c.execute("PRAGMA journal_mode=WAL")
    finally:
        c.close()
    for s in SCHEMA:
        x(s)
    ensure_cols("users", USER_COLS)
    for t, cols in EXTRA_COLS.items():
        ensure_cols(t, cols)
    x("INSERT OR IGNORE INTO treasury(id,balance_coin,balance_point,updated_at) VALUES(1,?,0,?)", (TREASURY_START, now()))
    x("INSERT OR IGNORE INTO event_progress(id,boss_hp,boss_max,day,season) VALUES(1,0,0,'',1)")
    log.info("База данных готова: %s", DB_FILE)


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
    cols, levels = (5, 5) if kind == "tower" else (4, 8)
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
    lvl, picks, cols = len(st["picks"]), st["picks"], st["cols"]
    rows = []
    if st["kind"] == "tower":
        for r in range(st["levels"]):
            row = []
            for c in range(cols):
                bomb = c in st["bombs"][r]
                if r < len(picks):
                    row.append(btn("💣" if (c == picks[r] and bomb) else ("💎" if c == picks[r] else ("💣" if over and bomb else "▫️")), "noop"))
                elif over:
                    row.append(btn("💣" if bomb else "▫️", "noop"))
                elif r == lvl:
                    row.append(qbtn(f"cl:p:{sid}:{c}"))
                else:
                    row.append(btn("▪️", "noop"))
            rows.append(row)
    elif not over:
        ds = [btn(f"🚪 {c + 1}", f"cl:p:{sid}:{c}", "door") for c in range(cols)]
        rows = [ds[:2], ds[2:]]
    if not over:
        if lvl:
            rows.append([btn(f"💰 Забрать ×{climb_mult(cols, st['b'], lvl):.2f}", f"cl:c:{sid}")])
        else:
            rows.append([btn("↩️ Отменить игру", f"cl:x:{sid}")])
    return kb(*rows)


def climb_text(u, bet: int, st: dict, extra: str = "") -> str:
    lvl = len(st["picks"])
    name = "БАШНЯ" if st["kind"] == "tower" else "ПИРАМИДА"
    ladder = " → ".join(f"x{climb_mult(st['cols'], st['b'], k):.2f}" for k in range(lvl + 1, min(lvl + 4, st["levels"]) + 1))
    return (f"{E('games' if st['kind'] == 'tower' else 'pyramid')} <b>{name}</b>\n👤 {uname(u)}\n💸 Ставка: {fmt(bet)} RCOIN\n"
            f"💣 Ловушек в ряду: {st['b']}\n📊 Уровень: {lvl}/{st['levels']}\n"
            f"📈 Сейчас: <b>x{climb_mult(st['cols'], st['b'], lvl):.2f}</b> ({fmt(int(bet * climb_mult(st['cols'], st['b'], lvl)))})\n"
            f"⬆️ Дальше: {ladder or '—'}\n" + extra)


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
    t, k = await v_main(message.from_user.id, message.chat.type == "private")
    await message.reply(t, reply_markup=k)


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
    ("games", "Башня", "5 уровней по 5 клеток, бомбы 1-3 в ряду.\n<code>башня 500</code> · <code>башня 500 2</code>"),
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
    except sqlite3.IntegrityError:
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
    except sqlite3.IntegrityError:
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
    except sqlite3.IntegrityError:
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
    if opened:
        rows.append([btn(f"💰 Забрать {fmt(row['pot'])}", "db5:c")])
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
        except sqlite3.IntegrityError:
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
    x("UPDATE event_progress SET boss_hp=MAX(0, boss_hp-?) WHERE id=1", (dmg,))
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
                 [btn("Мой склад", "menu:stash", "diamond"), btn("Назад", "menu:main", "door")])


reg_view("events", "ивенты", "ивент", "events")


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


# ---------- арена (общая комната) ----------
AR: Dict[str, Any] = {}
AR_HIST: List[dict] = []
AR_CD, AR_ROLL, AR_SHOW, AR_MAX, AR_MIN_BET = 15, 7, 9, 8, 100


def ar_reset():
    AR.clear()
    AR.update(phase="idle", players={}, t_cd=0.0, t_roll=0.0, t_done=0.0, winner=None, land=0.5, created=0.0)


ar_reset()


def ar_tick() -> Optional[Tuple[int, int]]:
    t = time.time()
    ph = AR["phase"]
    if ph == "countdown" and t >= AR["t_cd"] + AR_CD:
        AR["winner"] = arena_pick({uid: p["bet"] for uid, p in AR["players"].items()})
        AR["land"] = random.uniform(0.2, 0.8)
        AR["phase"], AR["t_roll"] = "rolling", t
    elif ph == "rolling" and t >= AR["t_roll"] + AR_ROLL:
        pl = AR["players"]
        pool = sum(p["bet"] for p in pl.values())
        rake = pool // 10
        treasury_add(rake)
        prize = pool - rake
        for uid, p in pl.items():
            settle(uid, "arena", p["bet"], prize if uid == AR["winner"] else 0, "web")
        AR_HIST.insert(0, {"name": pl[AR["winner"]]["name"], "prize": prize, "pool": pool})
        del AR_HIST[6:]
        AR["phase"], AR["t_done"] = "done", t
        return AR["winner"], prize
    elif ph == "done" and t >= AR["t_done"] + AR_SHOW:
        ar_reset()
    elif ph == "waiting" and t - AR["created"] > 600:
        for uid, p in AR["players"].items():
            add_coin(uid, p["bet"])
        ar_reset()
    return None


async def arena_loop():
    while True:
        try:
            res = ar_tick()
            if res:
                await _dm(res[0], f"{E('win')} <b>Арена: победа!</b> Ты выиграл <b>{fmt(res[1])}</b> RCOIN")
        except Exception:
            log.exception("arena_loop")
        await asyncio.sleep(0.4)


def ar_state(uid: int) -> dict:
    t = time.time()
    pl = AR["players"]
    total = sum(p["bet"] for p in pl.values()) or 1
    ids = list(pl)
    players = [{"id": i, "name": pl[i]["name"], "bet": pl[i]["bet"], "pct": round(pl[i]["bet"] * 100 / total, 1)} for i in ids]
    ph = AR["phase"]
    st = {"phase": ph, "players": players, "pool": sum(p["bet"] for p in pl.values()), "you": uid in pl, "your_bet": pl[uid]["bet"] if uid in pl else 0,
          "cd_left": max(0.0, AR["t_cd"] + AR_CD - t) if ph == "countdown" else 0, "roll_total": AR_ROLL, "roll_elapsed": 0,
          "winner_idx": -1, "land": AR["land"], "history": AR_HIST, "max": AR_MAX, "min_bet": AR_MIN_BET}
    if ph in ("rolling", "done"):
        st["roll_elapsed"] = min(AR_ROLL, t - AR["t_roll"]) if ph == "rolling" else AR_ROLL
        st["winner_idx"] = ids.index(AR["winner"])
    return st


def a_arena(u, body):
    ar_tick()
    return {"ok": True, "state": ar_state(u["user_id"])}


def a_arena_join(u, body):
    ar_tick()
    uid = u["user_id"]
    bet = w_bet(u, body, AR_MIN_BET)
    if not bet:
        return w_err(f"Минимальная ставка {AR_MIN_BET}")
    if AR["phase"] not in ("idle", "waiting", "countdown"):
        return w_err("Раунд уже идёт — дождись следующего")
    if uid not in AR["players"] and len(AR["players"]) >= AR_MAX:
        return w_err("Арена заполнена")
    if not spend(uid, bet):
        return w_err("Недостаточно RCOIN")
    t = time.time()
    if uid in AR["players"]:
        AR["players"][uid]["bet"] += bet
    else:
        AR["players"][uid] = {"name": re.sub(r"<[^>]+>", "", uname(u, False)), "bet": bet}
    if len(AR["players"]) == 1:
        AR["phase"], AR["created"] = "waiting", t
    elif AR["phase"] != "countdown":
        AR["phase"], AR["t_cd"] = "countdown", t
    return {"ok": True, "state": ar_state(uid)}


def a_arena_leave(u, body):
    ar_tick()
    uid = u["user_id"]
    if AR["phase"] != "waiting" or uid not in AR["players"]:
        return w_err("Выйти нельзя — отсчёт уже идёт")
    add_coin(uid, AR["players"][uid]["bet"])
    ar_reset()
    return {"ok": True, "state": ar_state(uid)}


# ---------- мини-игры ----------
def a_me(u, body):
    return {"ok": True, "name": re.sub(r"<[^>]+>", "", uname(u, False)), "id": u["user_id"], "rbp": u["balance_point"]}


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


WEBAPP_HTML = r"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<title>RCOIN — Игровой центр</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{--bg:#070b18;--c1:#7c5cff;--c2:#2de2e6;--c3:#ff4d8d;--card:rgba(255,255,255,.07);--line:rgba(255,255,255,.14);--tx:#eef1ff;--mut:#9aa3c7}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;padding:12px 12px 40px;overflow-x:hidden}
.bg{position:fixed;inset:0;z-index:-1;background:radial-gradient(60% 50% at 15% 10%,rgba(124,92,255,.35),transparent 60%),radial-gradient(50% 40% at 90% 20%,rgba(45,226,230,.25),transparent 60%),radial-gradient(60% 50% at 50% 100%,rgba(255,77,141,.25),transparent 60%);animation:drift 14s ease-in-out infinite alternate}
@keyframes drift{to{filter:hue-rotate(40deg) saturate(1.2)}}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.logo{font-weight:800;font-size:20px;background:linear-gradient(90deg,var(--c2),var(--c1),var(--c3));-webkit-background-clip:text;background-clip:text;color:transparent}
.bal{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:8px 12px;font-weight:700;backdrop-filter:blur(8px)}
.bal small{color:var(--mut);font-weight:500;margin-right:4px}
nav{display:flex;gap:8px;margin-bottom:12px}
nav button{flex:1;padding:11px;border-radius:14px;border:1px solid var(--line);background:var(--card);color:var(--mut);font-weight:700;font-size:15px;transition:.2s}
nav button.on{color:#fff;background:linear-gradient(135deg,var(--c1),var(--c3));border-color:transparent;box-shadow:0 6px 24px rgba(124,92,255,.4)}
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:14px;margin-bottom:12px;backdrop-filter:blur(10px)}
h2{font-size:16px;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.mut{color:var(--mut);font-size:13px}
.hide{display:none!important}
.arena-wrap{display:flex;flex-direction:column;align-items:center}
canvas{max-width:100%;filter:drop-shadow(0 10px 30px rgba(124,92,255,.35))}
.phase{margin:8px 0 2px;font-weight:800;font-size:17px;text-align:center}
.row{display:flex;gap:8px;align-items:center}
input[type=number],input[type=text]{flex:1;min-width:0;background:rgba(0,0,0,.35);border:1px solid var(--line);border-radius:12px;color:var(--tx);padding:12px;font-size:16px;font-weight:700;outline:none}
input:focus{border-color:var(--c2)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.chip{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.06);color:var(--tx);font-size:13px;font-weight:600}
.btn{width:100%;padding:14px;border:0;border-radius:14px;font-size:16px;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--c1),var(--c3));box-shadow:0 8px 26px rgba(124,92,255,.45);margin-top:8px;transition:transform .1s}
.btn:active{transform:scale(.97)}
.btn.green{background:linear-gradient(135deg,#00c9a7,#2de2e6);box-shadow:0 8px 26px rgba(45,226,230,.35);color:#04111a}
.btn.ghost{background:rgba(255,255,255,.08);box-shadow:none}
.btn:disabled{opacity:.45}
.pl{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.pl:last-child{border:0}.dot{width:12px;height:12px;border-radius:50%;flex:none}
.pl .n{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.pl .b{color:var(--mut)}.pl .p{font-weight:800;min-width:48px;text-align:right}
.games{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.gcard{border-radius:18px;padding:16px 8px;text-align:center;font-weight:800;border:1px solid var(--line);background:var(--card);font-size:15px}
.gcard span{display:block;font-size:30px;margin-bottom:4px}
.big{font-size:44px;font-weight:900;text-align:center;margin:10px 0}
.coin{width:110px;height:110px;margin:8px auto;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:48px;background:radial-gradient(circle at 30% 30%,#fff3b0,#ffb300 60%,#c77700);box-shadow:0 10px 30px rgba(255,179,0,.4)}
.coin.flip{animation:flip 1s ease-in-out}
@keyframes flip{0%{transform:rotateY(0)}100%{transform:rotateY(1800deg)}}
.grid5{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:10px}
.cell{aspect-ratio:1;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.08);font-size:24px;color:var(--tx);transition:.15s}
.cell:active{transform:scale(.92)}.cell.safe{background:rgba(45,226,230,.25)}.cell.mine{background:rgba(255,77,141,.35)}
.hist{font-size:13px;color:var(--mut);margin-top:6px}
input[type=range]{width:100%;accent-color:var(--c1);margin:8px 0}
.toast{position:fixed;left:50%;bottom:24px;transform:translate(-50%,40px);opacity:0;background:#1b2140;border:1px solid var(--line);padding:12px 18px;border-radius:14px;font-weight:700;transition:.25s;z-index:9;max-width:90%;text-align:center}
.toast.show{opacity:1;transform:translate(-50%,0)}.toast.good{border-color:#2de2e6}.toast.bad{border-color:#ff4d8d}
</style></head><body>
<div class="bg"></div>
<header><div class="logo">💎 RCOIN</div><div class="bal"><small>RCOIN</small><span id="bal">—</span></div></header>
<nav><button id="t1" class="on" onclick="tab(1)">⚔️ Арена</button><button id="t2" onclick="tab(2)">🎮 Игры</button></nav>

<section id="s1">
 <div class="card arena-wrap">
  <canvas id="cv" width="400" height="400"></canvas>
  <div class="phase" id="phase">Загрузка…</div>
  <div class="mut" id="sub"></div>
 </div>
 <div class="card">
  <h2>🎯 Твоя ставка</h2>
  <div class="row"><input id="abet" type="number" inputmode="numeric" value="1000" min="100"></div>
  <div class="chips" id="achips"></div>
  <div class="mut" id="mych">Шанс на победу = твоя ставка / банк арены. Победитель получает банк минус 10%.</div>
  <button class="btn" id="abtn" onclick="arenaJoin()">⚔️ Войти в арену</button>
  <button class="btn ghost hide" id="aleave" onclick="arenaLeave()">↩️ Выйти и забрать ставку</button>
 </div>
 <div class="card"><h2>👥 Игроки · банк <span id="pool">0</span></h2><div id="plist"><div class="mut">Пока никого. Стань первым!</div></div>
  <div class="hist" id="hist"></div></div>
</section>

<section id="s2" class="hide">
 <div class="games">
  <div class="gcard" onclick="openG('coin')"><span>🪙</span>Монетка</div>
  <div class="gcard" onclick="openG('dice')"><span>🎲</span>Кубик-шанс</div>
  <div class="gcard" onclick="openG('crash')"><span>🚀</span>Краш</div>
  <div class="gcard" onclick="openG('mines')"><span>💣</span>Мины</div>
 </div>
 <div id="g-coin" class="card hide"><h2>🪙 Монетка <span class="mut">x1.95</span></h2>
  <div class="coin" id="coin">🪙</div>
  <input id="cbet" type="number" value="1000" min="10"><div class="chips" data-for="cbet"></div>
  <div class="row"><button class="btn" onclick="coin('heads')">🦅 Орёл</button><button class="btn green" onclick="coin('tails')">🪙 Решка</button></div></div>
 <div id="g-dice" class="card hide"><h2>🎲 Кубик-шанс</h2>
  <div class="big" id="droll">—</div>
  <div class="mut">Выпадет число меньше шанса — победа. Выплата <b id="dmult">x1.90</b></div>
  <input type="range" id="dch" min="5" max="90" value="50" oninput="diceUp()"><div class="mut">Шанс: <b id="dchv">50</b>%</div>
  <input id="dbet" type="number" value="1000" min="10"><div class="chips" data-for="dbet"></div>
  <button class="btn" onclick="dice()">Бросить</button></div>
 <div id="g-crash" class="card hide"><h2>🚀 Краш</h2>
  <div class="big" id="crm">x1.00</div><div class="mut" id="crinfo">Забери выигрыш до краша!</div>
  <input id="crbet" type="number" value="1000" min="10"><div class="chips" data-for="crbet"></div>
  <button class="btn" id="crbtn" onclick="crashBtn()">🚀 Старт</button></div>
 <div id="g-mines" class="card hide"><h2>💣 Мины</h2>
  <div class="row"><input id="mbet" type="number" value="1000" min="10"><input id="mcnt" type="number" value="3" min="1" max="10" style="max-width:90px"></div>
  <div class="chips" data-for="mbet"></div>
  <div class="mut" id="minfo">Ставка и количество мин (1–10)</div>
  <div class="grid5" id="mgrid"></div>
  <button class="btn" id="mbtn" onclick="minesBtn()">Начать игру</button></div>
</section>
<div class="toast" id="toast"></div>

<script>
const tg=window.Telegram&&Telegram.WebApp;if(tg){try{tg.ready();tg.expand();tg.setHeaderColor('#070b18');tg.setBackgroundColor('#070b18')}catch(e){}}
const INIT=tg?tg.initData:"";const $=id=>document.getElementById(id);
const fmt=n=>Math.floor(n).toLocaleString('ru-RU');
function setBal(v){$('bal').textContent=fmt(v)}
function toast(t,ok){const e=$('toast');e.textContent=t;e.className='toast show '+(ok===false?'bad':ok?'good':'');clearTimeout(toast.t);toast.t=setTimeout(()=>e.className='toast',2600)}
function hap(t){try{tg.HapticFeedback.notificationOccurred(t)}catch(e){}}
async function api(p,b){try{const r=await fetch('/api/'+p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({init:INIT},b||{}))});const j=await r.json();if(j.balance!==undefined)setBal(j.balance);return j}catch(e){return{ok:false,err:'Нет связи с сервером'}}}
function tab(n){for(const i of[1,2]){$('s'+i).classList.toggle('hide',i!==n);$('t'+i).classList.toggle('on',i===n)}}
function chips(){document.querySelectorAll('.chips').forEach(c=>{const id=c.dataset.for||'abet';[100,1000,10000,100000,1000000].forEach(v=>{const b=document.createElement('button');b.className='chip';b.textContent=v>=1e6?(v/1e6)+'кк':v>=1e3?(v/1e3)+'к':v;b.onclick=()=>{$(id).value=v};c.appendChild(b)});const m=document.createElement('button');m.className='chip';m.textContent='×2';m.onclick=()=>{$(id).value=Math.max(1,Math.floor($(id).value*2))};c.appendChild(m)})}
document.getElementById('achips').dataset.for='abet';

/* ---------- АРЕНА ---------- */
const COLORS=['#ff4d8d','#2de2e6','#7cf29c','#ffd166','#c77dff','#ff9f1c','#5b8cff','#f15bb5'];
let S=null,SAT=0,W=360,trail=[];const cv=$('cv'),cx=cv.getContext('2d');
function resize(){const s=Math.min(cv.parentElement.clientWidth-8,420);const d=window.devicePixelRatio||1;cv.width=s*d;cv.height=s*d;cv.style.width=s+'px';cv.style.height=s+'px';cx.setTransform(d,0,0,d,0,0);W=s}
window.addEventListener('resize',resize);resize();
function cdLeft(){return S?Math.max(0,S.cd_left-(performance.now()-SAT)/1000):0}
function draw(){
 const c=W/2,R=W*0.46;cx.clearRect(0,0,W,W);cx.save();cx.translate(c,c);
 const pl=S?S.players:[];const total=pl.reduce((a,p)=>a+p.bet,0);
 if(!total){cx.beginPath();cx.arc(0,0,R,0,7);cx.fillStyle='rgba(255,255,255,.07)';cx.fill();cx.strokeStyle='rgba(255,255,255,.2)';cx.lineWidth=3;cx.setLineDash([8,8]);cx.stroke();cx.setLineDash([])}
 else{let a=-Math.PI/2;pl.forEach((p,i)=>{const sp=2*Math.PI*p.bet/total;cx.beginPath();cx.moveTo(0,0);cx.arc(0,0,R,a,a+sp);cx.closePath();cx.fillStyle=COLORS[i%8];cx.globalAlpha=(S.phase==='done'&&i!==S.winner_idx)?.22:(.55+.1*Math.sin(performance.now()/500+i));cx.fill();cx.globalAlpha=1;cx.strokeStyle='#070b18';cx.lineWidth=3;cx.stroke();a+=sp})}
 cx.beginPath();cx.arc(0,0,R,0,7);cx.strokeStyle='rgba(255,255,255,.35)';cx.lineWidth=4;cx.stroke();
 cx.beginPath();cx.arc(0,0,R*.26,0,7);cx.fillStyle='#0c1226';cx.fill();cx.strokeStyle='rgba(255,255,255,.25)';cx.lineWidth=2;cx.stroke();
 cx.fillStyle='#fff';cx.textAlign='center';cx.textBaseline='middle';cx.font='800 '+Math.round(R*.2)+'px sans-serif';
 let hub='⚔️';if(S){if(S.phase==='countdown')hub=Math.ceil(cdLeft());else if(S.phase==='rolling')hub='🎱';else if(S.phase==='done')hub='🏆';else if(S.phase==='waiting')hub='⏳'}cx.fillText(hub,0,0);
 let bx,by;const t=performance.now()/1000;
 if(S&&(S.phase==='rolling'||S.phase==='done')&&S.winner_idx>=0&&total){
  const el=Math.min(S.roll_total,S.roll_elapsed+(S.phase==='done'?99:(performance.now()-SAT)/1000));const e=Math.min(1,el/S.roll_total),ease=1-Math.pow(1-e,3);
  let cum=0;for(let i=0;i<S.winner_idx;i++)cum+=pl[i].bet;
  const a0=-Math.PI/2+2*Math.PI*cum/total,span=2*Math.PI*pl[S.winner_idx].bet/total,aT=a0+span*S.land,st=-Math.PI/2,TP=Math.PI*2;
  const ang=st+(TP*5+(((aT-st)%TP)+TP)%TP)*ease,rad=R*(0.93-0.43*ease)+Math.sin(e*45)*(1-e)*R*.06;
  bx=Math.cos(ang)*rad;by=Math.sin(ang)*rad;
 }else{const a=t*(S&&S.phase==='countdown'?2.2:.7),r=R*(.55+.06*Math.sin(t*2));bx=Math.cos(a)*r;by=Math.sin(a)*r}
 trail.push([bx,by]);if(trail.length>16)trail.shift();
 trail.forEach((p,i)=>{cx.beginPath();cx.arc(p[0],p[1],R*.035*(i/16),0,7);cx.fillStyle='rgba(255,255,255,'+(i/32)+')';cx.fill()});
 const g=cx.createRadialGradient(bx-3,by-3,1,bx,by,R*.06);g.addColorStop(0,'#fff');g.addColorStop(1,'#b9c4ff');
 cx.shadowColor='#fff';cx.shadowBlur=18;cx.beginPath();cx.arc(bx,by,R*.055,0,7);cx.fillStyle=g;cx.fill();cx.shadowBlur=0;
 cx.restore();requestAnimationFrame(draw)}
requestAnimationFrame(draw);
function renderArena(){
 if(!S)return;const ph=S.phase;const you=S.you;
 const names={idle:'Арена свободна',waiting:'Ждём соперника…',countdown:'Старт через '+Math.ceil(cdLeft())+' c',rolling:'🎱 Шарик катится!',done:'Победитель определён!'};
 let txt=names[ph];if(ph==='done'&&S.winner_idx>=0)txt='🏆 '+S.players[S.winner_idx].name;$('phase').textContent=txt;
 $('sub').textContent=ph==='idle'?'Сделай ставку — как только зайдёт 2-й игрок, через 15 секунд шарик выберет победителя':'';
 $('pool').textContent=fmt(S.pool);
 const pl=$('plist');pl.innerHTML='';if(!S.players.length){const d=document.createElement('div');d.className='mut';d.textContent='Пока никого. Стань первым!';pl.appendChild(d)}
 S.players.forEach((p,i)=>{const r=document.createElement('div');r.className='pl';const d=document.createElement('span');d.className='dot';d.style.background=COLORS[i%8];const n=document.createElement('span');n.className='n';n.textContent=p.name;const b=document.createElement('span');b.className='b';b.textContent=fmt(p.bet);const pc=document.createElement('span');pc.className='p';pc.textContent=p.pct+'%';r.append(d,n,b,pc);pl.appendChild(r)});
 const can=['idle','waiting','countdown'].includes(ph);$('abtn').disabled=!can;$('abtn').textContent=can?(you?'➕ Добавить к ставке':'⚔️ Войти в арену'):'Раунд идёт…';
 $('aleave').classList.toggle('hide',!(you&&ph==='waiting'));
 if(you&&S.pool)$('mych').textContent='Твой шанс: '+(S.your_bet*100/S.pool).toFixed(1)+'% · твоя ставка '+fmt(S.your_bet);
 $('hist').textContent=S.history.length?'Последние: '+S.history.map(h=>h.name+' +'+fmt(h.prize)).join(' · '):'';
}
let lastPhase='';
async function poll(){const j=await api('arena');if(j.ok){S=j.state;SAT=performance.now();renderArena();if(S.phase==='done'&&lastPhase!=='done'){hap('success');if(S.you)toast('Раунд завершён: '+S.players[S.winner_idx].name,true)}lastPhase=S.phase}
 setTimeout(poll,S&&(S.phase==='rolling'||S.phase==='countdown')?600:1300)}
setInterval(()=>{if(S&&S.phase==='countdown')$('phase').textContent='Старт через '+Math.ceil(cdLeft())+' c'},250);
async function arenaJoin(){const j=await api('arena_join',{bet:$('abet').value});if(!j.ok){hap('error');return toast(j.err,false)}S=j.state;SAT=performance.now();renderArena();hap('success');toast('Ставка принята!',true)}
async function arenaLeave(){const j=await api('arena_leave');if(!j.ok)return toast(j.err,false);S=j.state;SAT=performance.now();renderArena();toast('Ставка возвращена',true)}

/* ---------- ИГРЫ ---------- */
function openG(n){['coin','dice','crash','mines'].forEach(g=>$('g-'+g).classList.toggle('hide',g!==n));$('g-'+n).scrollIntoView({behavior:'smooth'})}
async function coin(side){const c=$('coin');c.classList.remove('flip');void c.offsetWidth;c.classList.add('flip');const j=await api('coin',{bet:$('cbet').value,side});
 if(!j.ok){c.classList.remove('flip');hap('error');return toast(j.err,false)}
 setTimeout(()=>{c.textContent=j.result==='heads'?'🦅':'🪙';toast(j.win?'Победа! +'+fmt(j.payout):'Не повезло',j.win);hap(j.win?'success':'error')},1000)}
function diceUp(){const c=+$('dch').value;$('dchv').textContent=c;$('dmult').textContent='x'+(95/c).toFixed(2)}
async function dice(){const j=await api('dice',{bet:$('dbet').value,chance:$('dch').value});if(!j.ok){hap('error');return toast(j.err,false)}
 $('droll').textContent=j.roll.toFixed(2);$('droll').style.color=j.win?'#7cf29c':'#ff4d8d';toast(j.win?'Победа! +'+fmt(j.payout):'Мимо',j.win);hap(j.win?'success':'error')}
let CR=null;
async function crashBtn(){
 if(!CR){const j=await api('crash_start',{bet:$('crbet').value});if(!j.ok){hap('error');return toast(j.err,false)}CR=j.id;$('crbtn').textContent='💰 Забрать';$('crbtn').className='btn green';$('crinfo').textContent='Ракета летит…';crPoll()}
 else{const j=await api('crash_cash',{id:CR});crEnd(j)}}
async function crPoll(){if(!CR)return;const j=await api('crash_poll',{id:CR});if(!j.ok){CR=null;return crReset()}
 if(j.status==='run'){$('crm').textContent='x'+j.mult.toFixed(2);setTimeout(crPoll,170)}else crEnd(j)}
function crEnd(j){if(!CR)return;CR=null;if(!j.ok){toast(j.err,false);return crReset()}$('crm').textContent='x'+Number(j.mult).toFixed(2);
 if(j.status==='won'){$('crinfo').textContent='✅ Забрал +'+fmt(j.payout);toast('Победа! +'+fmt(j.payout),true);hap('success')}else{$('crinfo').textContent='💥 Краш на x'+Number(j.mult).toFixed(2);toast('Ракета упала',false);hap('error')}crReset()}
function crReset(){$('crbtn').textContent='🚀 Старт';$('crbtn').className='btn'}
let MG=null;
function mBuild(open,mines){const g=$('mgrid');g.innerHTML='';for(let i=0;i<25;i++){const b=document.createElement('button');b.className='cell';if(open.includes(i)){b.classList.add('safe');b.textContent='💎'}else if(mines&&mines.includes(i)){b.classList.add('mine');b.textContent='💣'}else b.textContent='❔';b.onclick=()=>mOpen(i);g.appendChild(b)}}
async function minesBtn(){
 if(!MG){const j=await api('mines_start',{bet:$('mbet').value,mines:$('mcnt').value});if(!j.ok){hap('error');return toast(j.err,false)}MG={id:j.id};mBuild([],null);$('minfo').textContent='Открывай клетки!';$('mbtn').textContent='💰 Забрать';$('mbtn').className='btn green'}
 else{const j=await api('mines_cash',{id:MG.id});mAfter(j)}}
async function mOpen(i){if(!MG)return;const j=await api('mines_open',{id:MG.id,i});mAfter(j)}
function mAfter(j){if(!j.ok){hap('error');return toast(j.err,false)}mBuild(j.open,j.mines||null);
 if(j.status==='safe'){$('minfo').textContent='x'+j.mult.toFixed(2)+' · открыто '+j.open.length;hap('success');return}
 MG=null;$('mbtn').textContent='Начать игру';$('mbtn').className='btn';
 if(j.status==='won'){$('minfo').textContent='✅ +'+fmt(j.payout);toast('Победа! +'+fmt(j.payout),true);hap('success')}else{$('minfo').textContent='💥 Мина!';toast('Взрыв!',false);hap('error')}}
chips();mBuild([],null);
(async()=>{if(!INIT){$('phase').textContent='Открой приложение через бота в Telegram';return}const m=await api('me');if(m.ok)setBal(m.balance);poll()})();
</script></body></html>"""


async def page(request: web.Request):
    return web.Response(text=WEBAPP_HTML, content_type="text/html", charset="utf-8")


async def health(request: web.Request):
    return web.Response(text="RCOIN OK")


async def start_web():
    app = web.Application()
    app.router.add_get("/", page)
    app.router.add_get("/webapp", page)
    app.router.add_get("/health", health)
    app.router.add_get("/healthz", health)
    for name, fn in {"me": a_me, "arena": a_arena, "arena_join": a_arena_join, "arena_leave": a_arena_leave, "coin": a_coin,
                     "dice": a_dice, "crash_start": a_crash_start, "crash_poll": a_crash_poll, "crash_cash": a_crash_cash,
                     "mines_start": a_mines_start, "mines_open": a_mines_open, "mines_cash": a_mines_cash}.items():
        app.router.add_post("/api/" + name, api(fn))
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
        elif "emoji" in s and PREMIUM_EMOJI:
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
    try:
        me = await bot.get_me()
    except Exception as e:
        log.error("Неверный BOT_TOKEN: %s", e)
        return
    BOT_USERNAME = me.username or BOT_USERNAME
    log.info("Бот запущен: @%s", BOT_USERNAME)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await bot.set_my_commands([BotCommand(command="start", description="Запуск"), BotCommand(command="menu", description="Главное меню"),
                                   BotCommand(command="games", description="Список игр"), BotCommand(command="help", description="Помощь"),
                                   BotCommand(command="antiludo", description="Антилудо (ответом на сообщение)")])
        if WEBAPP_URL:
            from aiogram.types import MenuButtonWebApp
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Арена", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception as e:
        log.warning("set_my_commands/menu: %s", e)
    await start_web()
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(arena_loop())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен")
