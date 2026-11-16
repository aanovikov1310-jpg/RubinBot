# -*- coding: utf-8 -*-
# ============================================================================
#   РУБИН БОТ — ВСЁ В ОДНОМ ФАЙЛЕ (rCoin)
#   Запуск: pip install aiogram aiosqlite aiohttp Pillow
#           python rubin_single.py
# ============================================================================

import asyncio
import datetime
import logging
import math
import os
import random
import re
import string
import sys
import time
from dataclasses import dataclass, field

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MenuButtonWebApp,
    WebAppInfo,
)
from PIL import Image, ImageDraw, ImageFont


# =============================== CONFIG =====================================



BOT_TOKEN = (os.getenv("BOT_TOKEN") or os.getenv("9153206613:AAH6yeSZv2lYd-FT1sc3cjyK47rcLoO1uik") or "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "RubinCoinBot")
BOT_NAME = "Рубин Бот"
CUR = "rCoin"
CUSTOM_EMOJI = True

OWNER_ID = int(os.getenv("OWNER_ID", "5251635454041675257"))
# Render: переменные ADMIN_IDS, WEBAPP_URL, BOT_USERNAME

ADMIN_IDS = {OWNER_ID, *{
    int(x) for x in os.getenv("ADMIN_IDS", "5257618084").replace(";", ",").split(",") if x.strip().isdigit()
}}

STATUSES = {
    "owner": ("5251635454041675257", "OWNER"),
    "creator": ("5343677436418609379", "Content Creator"),
    "moderator": ("5766894601709296405", "Moderator"),
    "elite": ("5794158469988753026", "Elite"),
    "newyear": ("5954111328493771983", "New Year's Verify"),
    "black_verify": (None, "Black Donate Verify"),
    "blue_verify": (None, "Blue Donate Verify"),
}

STATUS_TITLES = {k: v[1] for k, v in STATUSES.items()}

STATUS_PRICES = {
    "black_verify": (250, 1_000_000_000),
    "blue_verify": (150, 500_000_000),
    "elite": (0, 2_500_000_000),
}

STAR_RATE = {"stars": 150, "coin": 500_000_000}   # 150 звёзд = 500кк rCoin
NEW_YEAR_STAR_RATE = {"stars": 150, "coin": 750_000_000}  # новогодний курс с бонусом

START_BALANCE = 100_000
MIN_BET = 1_000
MAX_BET = 5_000_000_000
DAILY_BASE = 100_000

BANK_INTEREST_HOURLY = 0.02
CHECK_FEE_PERCENT = 3
REF_PERCENT = 20

DEFAULT_TICKET_PRICE = 50_000
LOTTERY_PICK = 6
LOTTERY_MAX = 45
LOTTERY_JACKPOT = 5_000_000_000

WAREHOUSE_CELLS = 3
WAREHOUSE_MIN = 15_000
WAREHOUSE_MAX = 1_000_000
SANTA_HP = 10_000_000
SANTA_HP_FINAL = 100_000_000

UPGRADE_CHANCE = [0.45, 0.32, 0.20, 0.10, 0.0]
UPGRADE_FEE = {"common": 250_000, "rare": 2_500_000, "epic": 25_000_000,
               "legendary": 250_000_000, "mythic": 0}

RARITY_ORDER = ["common", "rare", "epic", "legendary", "mythic"]
RARITY_NAMES = {"common": "обычная", "rare": "редкая", "epic": "эпическая",
                "legendary": "легендарная", "mythic": "мифическая"}
RARITY_ICONS = {"common": "⚪️", "rare": "🔵", "epic": "🟣", "legendary": "🟡", "mythic": "🔴"}

DEFAULT_NFT_TEMPLATES = [
    {"slug": "porky", "title": "Porky", "model": "🐷", "rarity": "common",
     "floor": 500_000, "bg": "#2a1b1f"},
    {"slug": "buddy", "title": "Buddy", "model": "🐶", "rarity": "common",
     "floor": 650_000, "bg": "#1f2733"},
    {"slug": "walter", "title": "Walter", "model": "🐈", "rarity": "rare",
     "floor": 2_500_000, "bg": "#2b1d12"},
    {"slug": "cheremsha", "title": "Cheremsha", "model": "🦝", "rarity": "rare",
     "floor": 3_000_000, "bg": "#1c2b1c"},
    {"slug": "duckwave", "title": "Duckwave", "model": "🦆", "rarity": "epic",
     "floor": 15_000_000, "bg": "#12212b"},
    {"slug": "rubin_heart", "title": "Рубиновое сердце", "model": "❤️‍🔥", "rarity": "epic",
     "floor": 25_000_000, "bg": "#3a0d12"},
    {"slug": "ruby_crown", "title": "Корона Рубина", "model": "👑", "rarity": "legendary",
     "floor": 200_000_000, "bg": "#3c2a06"},
    {"slug": "mystic_orb", "title": "Мистическая сфера", "model": "🔮", "rarity": "mythic",
     "floor": 1_000_000_000, "bg": "#1b1140"},
]

DEFAULT_CASES = [
    ("Бронзовый кейс", 100_000, "50000:45,120000:30,300000:18,1000000:5,5000000:2"),
    ("Серебряный кейс", 1_000_000, "300000:40,800000:30,2500000:20,10000000:8,50000000:2"),
    ("Рубиновый кейс", 10_000_000, "2000000:45,6000000:30,20000000:18,100000000:5,500000000:2"),
]

DICE_GAMES = {
    "basket": {"emoji": "🏀", "title": "Баскетбол", "win_at": {4, 5}, "mult": 1.9},
    "football": {"emoji": "⚽️", "title": "Футбол", "win_at": {3, 4, 5}, "mult": 1.7},
    "darts": {"emoji": "🎯", "title": "Дартс", "win_at": {6}, "mult": 3.2},
    "bowling": {"emoji": "🎳", "title": "Боулинг", "win_at": {6}, "mult": 3.2},
    "dice": {"emoji": "🎲", "title": "Кости", "win_at": {6}, "mult": 3.2},
    "slots": {"emoji": "🎰", "title": "Слоты", "win_at": {1, 22, 43, 64}, "mult": 4.0},
}

RU_COMMANDS = {
    "б": "balance", "бал": "balance", "баланс": "balance",
    "профиль": "profile",
    "банк": "bank", "депозит": "bank",
    "бонус": "bonus",
    "дейли": "daily", "ежедневный": "daily",
    "лотерея": "lottery",
    "кейс": "cases", "кейсы": "cases",
    "билет": "tickets", "билеты": "tickets",
    "топ": "top",
    "топчат": "topchat",
    "пик": "topimg",
    "дать": "give",
    "маркет": "market", "маркетплейс": "market",
    "инвентарь": "inventory", "инв": "inventory",
    "донат": "donate",
    "заработок": "earn",
    "реф": "referral",
    "игры": "games",
    "история": "history",
    "чек": "checks",
    "обменник": "exchange",
    "витрина": "gifts",
    "склад": "warehouse", "зимний склад": "warehouse",
    "санта": "santa",
}

MSG_NO_TOKEN = "⚠️ Токен бота не настроен. Впиши BOT_TOKEN в config.py или .env."
MSG_UNKNOWN_CMD = "🤔 Не понял команду. Нажми /start и «📜 Команды»."


DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rubin.db'))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_URL = os.getenv('WEBAPP_URL', '').strip()


# =============================== КОМПАТ-СЛОЙ ===============================
config = sys.modules[__name__]

# =============================== ALIASES (до первого использования) ========
E = sys.modules[__name__]
M = sys.modules[__name__]
G = sys.modules[__name__]
K = sys.modules[__name__]
nft_image = sys.modules[__name__]
config = sys.modules[__name__]

# =============================== database/emoji.py ================
# file: database/emoji.py
"""Все Premium-эмодзи «Рубина»: id + fallback. Используются в кнопках и текстах."""


# (emoji, custom_emoji_id)
PREMIUM: dict[str, tuple[str, str | None]] = {
    "champagne": ("🍾", "5451814216031809603"),
    "disco": ("🪩", "5257960214291823402"),
    "heel": ("👠", "5224294190451538499"),
    "pinata": ("🪅", "5314589624377554054"),
    "bag": ("🛍", "5451937962629544243"),
    "heart": ("💖", "5470080737711502911"),
    "cake": ("🍰", "5406864011729843560"),
    "icecream": ("🍨", "5258378333653056711"),
    "bow": ("🎀", "5375203677487248777"),
    "balloon": ("🎈", "5407064810040864883"),
    "bday": ("🎂", "5452055425690123301"),
    "gift_heart": ("💝", "5192879906295397710"),
    "gift": ("🎁", "5449800250032143374"),
    "tophat": ("🎩", "5406905406624642546"),
    "sparkler": ("🎇", "5449816553727998023"),
    "black_cat": ("🐈‍⬛", "5211047317309767043"),
    "fireworks": ("🎆", "5195100606250889609"),
    "dog": ("🐶", "5226506532400674396"),
    "candy": ("🍬", "5404573776253825754"),
    "kiss": ("💋", "5474525960143385880"),
    "bouquet": ("💐", "5192959294470895031"),
    "ring": ("💍", "5458839914944672851"),
    "cupcake": ("🧁", "5413546967957516771"),
    "love_letter": ("💌", "5257980374868311346"),
    "calendar": ("🗓", "5472026645659401564"),
    "sparkles": ("✨", "5451636889717062286"),
    "flag": ("🚩", "5305570244595561790"),
    "note": ("🎶", "5470135030393090150"),
    "festival": ("🎏", "5210817072702964322"),
    "bulb": ("💡", "5224596414415256150"),
    "pin": ("📌", "5397782960512444700"),
    "cash": ("💵", "5409048419211682843"),
    "money_tear": ("💸", "5233326571099534068"),
    "money_wind": ("💸", "5231449120635370684"),
    "money_eyes": ("💸", "5278751923338490157"),
    "money_launch": ("💸", "5290017777174722330"),
    "money_rain": ("💸", "5231005931550030290"),
    "exchange": ("💱", "5402186569006210455"),
    "play": ("▶️", "5264919878082509254"),
    "red": ("🔴", "5411225014148014586"),
    "green": ("🟢", "5416081784641168838"),
    "arrow": ("➡️", "5416117059207572332"),
    "fire": ("🔥", "5424972470023104089"),
    "boom": ("💥", "5276032951342088188"),
    "mic": ("🎙", "5294339927318739359"),
    "mic2": ("🎤", "5224736245665511429"),
    "megaphone": ("📣", "5424818078833715060"),
    "hush": ("🤫", "5431609822288033666"),
    "thumb_down": ("👎", "5449875686837726134"),
    "speak": ("🗣️", "5460795800101594035"),
    "candle": ("🕯", "5451882707875276247"),
    "up": ("📈", "5244837092042750681"),
    "down": ("📉", "5246762912428603768"),
    "check": ("✔️", "5206607081334906820"),
    "cross": ("❌", "5210952531676504517"),
    "cool": ("🆒", "5222079954421818267"),
    "bell": ("🔔", "5458603043203327669"),
    "incognito": ("🥸", "5391112412445288650"),
    "clown": ("🤡", "5269531045165816230"),
    "lips": ("🫦", "5395444514028529554"),
    "eyes": ("👀", "5210956306952758910"),
    "smile": ("🙂", "5461117441612462242"),
    "bolt": ("⚡️", "5456140674028019486"),
    "comet": ("☄️", "5224607267797606837"),
    "bag2": ("🛍", "5229064374403998351"),
    "no_entry": ("⛔️", "5260293700088511294"),
    "banned": ("🚫", "5240241223632954241"),
    "excl": ("❗️", "5274099962655816924"),
    "excl2": ("‼️", "5440660757194744323"),
    "quest": ("⁉️", "5314504236132747481"),
    # --- мем-эмодзи со скриншотов ---
    "blue": ("🔵", "5359543311897998264"),
    "hundred": ("💯", "5341498088408234504"),
    "upd": ("UPD", "5375338737028841420"),
    "ai": ("AI", "5415655814079723871"),
    "new": ("NEW", "5382357040008021292"),
    "sony": ("Sony", "5440621591387980068"),
    "blue2": ("🔵", "5391032818111363540"),
    "sq_green": ("🟩", "5397916757333654639"),
    "gem": ("💎", "5427168083074628963"),
    "star_glow": ("🌟", "5438496463044752972"),
    "sparkles2": ("✨", "5325547803936572038"),
    "crown": ("👑", "5217822164362739968"),
    "building": ("🏢", "5445267414562389170"),
    "red_packet": ("🧧", "5222444124698853913"),
    "envelope": ("✉️", "5253742260054409879"),
    "lock": ("🔒", "5296369303661067030"),
    "wt": ("WT", "5303479226882603449"),
    "infinity": ("♾", "5305265301917549162"),
    "gear": ("⚙️", "5341715473882955310"),
    "stop": ("🛑", "5361741454685256344"),
    "crystal": ("🔮", "5388632425314140043"),
    "disc": ("💿", "5386367538735104399"),
    "download": ("⏬", "5406745015365943482"),
    "sun": ("☀️", "5402477260982731644"),
    "skull": ("💀", "5399913388845322366"),
    "ghost": ("👻", "5449569374065152798"),
    "skate": ("🛹", "5449449325434266744"),
    "rainbow": ("🌈", "5409109841538994759"),
    "rain": ("🌧", "5393512611968995988"),
    "calendar2": ("🗓", "5413879192267805083"),
    "bulb2": ("💡", "5422439311196834318"),
    "fire2": ("🔥", "5440539497383087970"),
    "silver": ("🥈", "5447203607294265305"),
    "bronze": ("🥉", "5453902265922376865"),
    "cap": ("🧢", "5816632586444741290"),
    "ninja": ("🥷", "5816751149016946075"),
    "tophat2": ("🎩", "5814674455019919008"),
    "frog": ("🐸", "5816435194042783541"),
    "sq_green2": ("🟩", "5816942708853315496"),
    "frog2": ("🐸", "5816600301175576093"),
    "frog3": ("🐸", "5814622958362039804"),
    "frog4": ("🐸", "5814299856562295924"),
    "frog5": ("🐸", "5814459710950086158"),
    "frog6": ("🐸", "5814656450517015834"),
    "alien": ("👽", "5816736035027031642"),
    "frog7": ("🐸", "5814255390765880388"),
    "amphora": ("🧿", "5951914611635655535"),
    "eyes2": ("👀", "5974354660411053888"),
    "crown2": ("👑", "5974150099708679853"),
    "frog8": ("🐸", "5902326491194070477"),
    "frog9": ("🐸", "5899923899373590126"),
    "frog10": ("🐸", "5902128514676561593"),
    "skull2": ("💀", "6015083577580984153"),
    "frog11": ("🐸", "6014856322271418329"),
    "ufo": ("👾", "5854766299690835045"),
    "frog12": ("🐸", "5854822452093261454"),
    "frog13": ("🐸", "5854887138595708373"),
    "frog14": ("🐸", "5960612835238091357"),
    "skull3": ("💀", "6005979548288556136"),
    "frog15": ("🐸", "6006015857942076349"),
    "frog16": ("🐸", "6005654887415684732"),
    "frog17": ("🐸", "6003790339033275600"),
    "fire3": ("🔥", "6003496095118792994"),
    "frog18": ("🐸", "6003443443114712006"),
    "frog19": ("🐸", "6003810254796627212"),
    "frog20": ("🐸", "6003832502727219886"),
    "frog21": ("🐸", "6005688023088372140"),
    "frog22": ("🐸", "6005761110546847909"),
    "frog23": ("🐸", "6006030246082517830"),
}

# Ключи конкретных ячеек Мины/Лесенки
CELL_CLOSED = ('❓', '5436113877181941026')
CELL_GEM = ('💎', '5305699699204837855')
CELL_BOMB = ("💥", "5276032951342088188")


def td(*parts: str) -> str:
    """Собирает tg-emoji тег: td('gift') -> <tg-emoji ...>🎁</tg-emoji>."""
    out = []
    for key in parts:
        item = PREMIUM.get(key)
        if not item:
            out.append(key)
            continue
        emoji, cid = item
        out.append(te(emoji, cid))
    return "".join(out)


def te(char: str, custom_id: str | None) -> str:
    if not custom_id or not config.CUSTOM_EMOJI:
        return char
    return f'<tg-emoji emoji-id="{custom_id}">{char}</tg-emoji>'


def plain(key: str) -> str:
    """Эмодзи без кастомного id — для мест, где HTML запрещён (кнопки dice)."""
    item = PREMIUM.get(key)
    return item[0] if item else key


def keys(starts: str) -> list[str]:
    """Все ключи, начинающиеся с префикса (например 'frog')."""
    return [k for k in PREMIUM if k.startswith(starts)]


# Группы для распределения по разделам
GROUPS = {
    "money": ["cash", "money_tear", "money_wind", "money_eyes", "money_launch",
              "money_rain", "exchange", "up", "down"],
    "party": ["champagne", "disco", "pinata", "balloon", "cake", "bday", "sparkler",
              "fireworks", "festival", "note"],
    "gifts": ["gift", "gift_heart", "bow", "bouquet", "love_letter", "ring", "candy",
              "cupcake", "icecream", "kiss"],
    "status": ["crown", "crown2", "gem", "star_glow", "infinity", "cool", "hundred",
               "ai", "new", "upd", "sony"],
    "warn": ["no_entry", "banned", "excl", "excl2", "quest", "stop", "hush"],
}

# =============================== database/models.py ================
# file: database/models.py
"""Модели и доступ к данным «Рубин Бот» (rCoin). Async, aiosqlite.

Слой совместим с database/db.py: обе схемы живут в одной базе,
модели используют свои таблицы с префиксом rc_*.
"""

import os
import random
import string
import time
from dataclasses import dataclass
from typing import Any

import aiosqlite


SCHEMA_RC = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS rc_users (
    id              INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    balance         INTEGER NOT NULL DEFAULT 0,
    bank            INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'none',
    status_until    INTEGER NOT NULL DEFAULT 0,
    played          INTEGER NOT NULL DEFAULT 0,
    duels_won       INTEGER NOT NULL DEFAULT 0,
    lost            INTEGER NOT NULL DEFAULT 0,
    won             INTEGER NOT NULL DEFAULT 0,
    best_win        INTEGER NOT NULL DEFAULT 0,
    last_daily      INTEGER NOT NULL DEFAULT 0,
    streak          INTEGER NOT NULL DEFAULT 0,
    referrer_id     INTEGER,
    referrals       INTEGER NOT NULL DEFAULT 0,
    invited_by_link TEXT,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    game      TEXT NOT NULL,
    bet       INTEGER NOT NULL,
    payout    INTEGER NOT NULL,
    payload   TEXT,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rc_history_user ON rc_history(user_id, id DESC);

CREATE TABLE IF NOT EXISTS rc_nft_templates (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    slug      TEXT UNIQUE NOT NULL,
    title     TEXT NOT NULL,
    model     TEXT NOT NULL,
    rarity    TEXT NOT NULL DEFAULT 'common',
    floor     INTEGER NOT NULL,
    supply    INTEGER NOT NULL DEFAULT 0,
    minted    INTEGER NOT NULL DEFAULT 0,
    bg        TEXT NOT NULL DEFAULT '#22131a',
    active    INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_nft_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    serial      INTEGER NOT NULL,
    owner_id    INTEGER,
    price       INTEGER NOT NULL,
    image_path  TEXT,
    created_at  INTEGER NOT NULL,
    UNIQUE(template_id, serial)
);
CREATE INDEX IF NOT EXISTS idx_rc_nft_owner ON rc_nft_items(owner_id);

CREATE TABLE IF NOT EXISTS rc_nft_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    event     TEXT NOT NULL,
    detail    TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_checks (
    code       TEXT PRIMARY KEY,
    owner_id   INTEGER NOT NULL,
    amount     INTEGER NOT NULL,
    claims     INTEGER NOT NULL DEFAULT 1,
    used       INTEGER NOT NULL DEFAULT 0,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_check_claims (
    code    TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (code, user_id)
);

CREATE TABLE IF NOT EXISTS rc_cases (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL,
    price   INTEGER NOT NULL,
    content TEXT NOT NULL,
    active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rc_case_opens (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    case_id   INTEGER NOT NULL,
    win       INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_lottery_draws (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    drawn_at   INTEGER NOT NULL,
    numbers    TEXT NOT NULL,
    prize_pool INTEGER NOT NULL,
    winners    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rc_lottery_tickets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    numbers  TEXT NOT NULL,
    draw_id  INTEGER,
    sold_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rc_event_claims (
    user_id  INTEGER NOT NULL,
    kind     TEXT NOT NULL,
    day      TEXT NOT NULL,
    payload  TEXT,
    PRIMARY KEY (user_id, kind, day)
);

CREATE TABLE IF NOT EXISTS rc_santa (
    user_id INTEGER NOT NULL,
    day     TEXT NOT NULL,
    damage  INTEGER NOT NULL,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS rc_promo (
    code     TEXT PRIMARY KEY,
    amount   INTEGER NOT NULL,
    uses     INTEGER NOT NULL DEFAULT 0,
    max_uses INTEGER NOT NULL DEFAULT 1000,
    active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rc_promo_uses (
    code    TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (code, user_id)
);
"""


# ---------------------------------------------------------------------------
# Соединение
# ---------------------------------------------------------------------------
async def connect() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(config.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA_RC)
    await db.commit()
    await seed_cases(db)
    return db


# ---------------------------------------------------------------------------
# Форматирование чисел: 10.47kkk
# ---------------------------------------------------------------------------
def short_num(n: float) -> str:
    """123456789 -> '123.46kk' , 10_470_000 -> '10.47kk' , 1_234_567_890_123 -> '1.23kkk'"""
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n < 1000:
        return f"{sign}{int(n)}"
    if n < 1_000_000:
        return f"{sign}{n / 1000:.2f}k"
    if n < 1_000_000_000:
        return f"{sign}{n / 1_000_000:.2f}kk"
    if n < 1_000_000_000_000:
        return f"{sign}{n / 1_000_000_000:.2f}kkk"
    return f"{sign}{n / 1_000_000_000_000:.2f}kkkk"


def full_num(n: float) -> str:
    return f"{int(round(n or 0)):,}".replace(",", " ")


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------
@dataclass
class RCUser:
    id: int
    username: str | None
    first_name: str | None
    balance: int
    bank: int
    status: str
    status_until: int
    played: int
    duels_won: int
    lost: int
    won: int
    best_win: int
    last_daily: int
    streak: int
    referrer_id: int | None
    referrals: int

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "RCUser":
        return cls(
            id=row["id"], username=row["username"], first_name=row["first_name"],
            balance=row["balance"], bank=row["bank"], status=row["status"],
            status_until=row["status_until"], played=row["played"],
            duels_won=row["duels_won"], lost=row["lost"], won=row["won"],
            best_win=row["best_win"], last_daily=row["last_daily"],
            streak=row["streak"], referrer_id=row["referrer_id"],
            referrals=row["referrals"],
        )

    @property
    def name(self) -> str:
        return self.first_name or self.username or str(self.id)

    @property
    def mention(self) -> str:
        if self.username:
            return f'<a href="https://t.me/{self.username}">@{self.username}</a>'
        return f'<a href="tg://user?id={self.id}">{self.name}</a>'

    @property
    def active_status(self) -> str:
        if self.status == "none":
            return "Нет"
        if self.status_until and self.status_until < int(time.time()):
            return "Нет"
        return config.STATUS_TITLES.get(self.status, self.status)


async def get_user(db: aiosqlite.Connection, user_id: int) -> RCUser | None:
    async with db.execute("SELECT * FROM rc_users WHERE id=?", (user_id,)) as cur:
        row = await cur.fetchone()
    return RCUser.from_row(row) if row else None


async def ensure_user(db: aiosqlite.Connection, tg_user, referrer_id: int | None = None) -> RCUser:
    now = int(time.time())
    user = await get_user(db, tg_user.id)
    if user:
        await db.execute(
            "UPDATE rc_users SET username=?, first_name=?, updated_at=? WHERE id=?",
            (tg_user.username, tg_user.first_name, now, tg_user.id),
        )
        await db.commit()
        return await get_user(db, tg_user.id)  # type: ignore
    start = config.START_BALANCE
    await db.execute(
        """INSERT INTO rc_users (id, username, first_name, balance, created_at, updated_at, referrer_id)
           VALUES (?,?,?,?,?,?,?)""",
        (tg_user.id, tg_user.username, tg_user.first_name, start, now, now,
         referrer_id if referrer_id and referrer_id != tg_user.id else None),
    )
    await db.execute(
        "INSERT INTO rc_history (user_id, game, bet, payout, payload, created_at) "
        "VALUES (?, 'welcome', 0, ?, 'старт', ?)",
        (tg_user.id, start, now),
    )
    if referrer_id and referrer_id != tg_user.id:
        bonus = start // 5
        await db.execute(
            "UPDATE rc_users SET balance = balance + ?, referrals = referrals + 1 WHERE id=?",
            (bonus, referrer_id),
        )
    await db.commit()
    return await get_user(db, tg_user.id)  # type: ignore


async def add_balance(db, user_id: int, amount: int, game: str = "manual",
                      payload: str = "") -> int:
    await db.execute(
        "UPDATE rc_users SET balance = MAX(0, balance + ?), updated_at=? WHERE id=?",
        (amount, int(time.time()), user_id),
    )
    await db.execute(
        "INSERT INTO rc_history (user_id, game, bet, payout, payload, created_at) "
        "VALUES (?, ?, 0, ?, ?, ?)",
        (user_id, game, amount, payload, int(time.time())),
    )
    await db.commit()
    async with db.execute("SELECT balance FROM rc_users WHERE id=?", (user_id,)) as cur:
        row = await cur.fetchone()
    return row[0] if row else 0


async def debit(db, user_id: int, amount: int) -> bool:
    cur = await db.execute(
        "UPDATE rc_users SET balance = balance - ? WHERE id=? AND balance >= ?",
        (amount, user_id, amount),
    )
    await db.commit()
    return cur.rowcount > 0


async def credit_game(db, user_id: int, game: str, bet: int, payout: int,
                      payload: str = "") -> int:
    """Записывает раунд и начисляет выигрыш. Возвращает чистый профит."""
    now = int(time.time())
    profit = payout - bet
    await db.execute(
        """UPDATE rc_users SET
             balance = balance + ?,
             played = played + 1,
             won = won + ?,
             lost = lost + ?,
             best_win = MAX(best_win, ?),
             updated_at = ?
           WHERE id=?""",
        (payout, max(0, profit), max(0, -profit), max(0, payout), now, user_id),
    )
    await db.execute(
        "INSERT INTO rc_history (user_id, game, bet, payout, payload, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (user_id, game, bet, payout, payload[:120], now),
    )
    await db.commit()
    return profit


async def history(db, user_id: int, limit: int = 10, offset: int = 0) -> list:
    async with db.execute(
        "SELECT * FROM rc_history WHERE user_id=? AND game != 'welcome' "
        "ORDER BY id DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ) as cur:
        return list(await cur.fetchall())


async def leaderboard(db, limit: int = 10) -> list:
    async with db.execute(
        "SELECT id, first_name, username, balance FROM rc_users ORDER BY balance DESC LIMIT ?",
        (limit,),
    ) as cur:
        return list(await cur.fetchall())


async def chat_leaderboard(db, chat_ids: list[int], limit: int = 10) -> list:
    if not chat_ids:
        return []
    placeholders = ",".join("?" * len(chat_ids))
    async with db.execute(
        f"SELECT id, first_name, username, balance FROM rc_users "
        f"WHERE id IN ({placeholders}) ORDER BY balance DESC LIMIT ?",
        (*chat_ids, limit),
    ) as cur:
        return list(await cur.fetchall())


# ---------------------------------------------------------------------------
# Статусы
# ---------------------------------------------------------------------------
async def set_status(db, user_id: int, status: str, days: int = 0) -> None:
    until = int(time.time()) + days * 86400 if days else 0
    await db.execute("UPDATE rc_users SET status=?, status_until=? WHERE id=?",
                     (status, until, user_id))
    await db.commit()


async def transfer(db, from_id: int, to_id: int, amount: int) -> bool:
    if amount <= 0 or from_id == to_id:
        return False
    if not await debit(db, from_id, amount):
        return False
    await add_balance(db, to_id, amount, "transfer", f"от {from_id}")
    return True


# ---------------------------------------------------------------------------
# Ежедневный бонус
# ---------------------------------------------------------------------------
async def claim_daily(db, user_id: int) -> tuple[bool, int, int]:
    user = await get_user(db, user_id)
    if not user:
        return False, 0, 0
    now = int(time.time())
    if now - user.last_daily < 86400:
        return False, 0, 86400 - (now - user.last_daily)
    streak = user.streak + 1 if now - user.last_daily < 172800 else 1
    reward = config.DAILY_BASE * min(streak, 7)
    await db.execute(
        "UPDATE rc_users SET last_daily=?, streak=?, balance=balance+? WHERE id=?",
        (now, streak, reward, user_id),
    )
    await db.execute(
        "INSERT INTO rc_history (user_id, game, bet, payout, payload, created_at) "
        "VALUES (?, 'daily', 0, ?, ?, ?)",
        (user_id, reward, f"streak={streak}", now),
    )
    await db.commit()
    return True, reward, streak


# ---------------------------------------------------------------------------
# NFT
# ---------------------------------------------------------------------------
async def seed_cases(db) -> None:
    async with db.execute("SELECT COUNT(*) FROM rc_cases") as cur:
        (cnt,) = await cur.fetchone()
    if cnt:
        return
    for title, price, content in config.DEFAULT_CASES:
        await db.execute(
            "INSERT INTO rc_cases (title, price, content) VALUES (?,?,?)",
            (title, price, content),
        )
    # базовые шаблоны подарков
    for t in config.DEFAULT_NFT_TEMPLATES:
        await db.execute(
            """INSERT OR IGNORE INTO rc_nft_templates
               (slug, title, model, rarity, floor, bg, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (t["slug"], t["title"], t["model"], t["rarity"], t["floor"], t["bg"], int(time.time())),
        )
    await db.commit()


async def templates(db, only_active: bool = True) -> list:
    q = "SELECT * FROM rc_nft_templates"
    if only_active:
        q += " WHERE active=1"
    q += " ORDER BY floor"
    async with db.execute(q) as cur:
        return list(await cur.fetchall())


async def template_by_slug(db, slug: str):
    async with db.execute("SELECT * FROM rc_nft_templates WHERE slug=?", (slug,)) as cur:
        return await cur.fetchone()


async def mint(db, template_id: int, owner_id: int, price: int) -> int:
    async with db.execute(
        "SELECT COALESCE(MAX(serial),0) FROM rc_nft_items WHERE template_id=?", (template_id,)
    ) as cur:
        (last,) = await cur.fetchone()
    serial = last + 1
    cur = await db.execute(
        "INSERT INTO rc_nft_items (template_id, serial, owner_id, price, created_at) "
        "VALUES (?,?,?,?,?)",
        (template_id, serial, owner_id, price, int(time.time())),
    )
    await db.execute("UPDATE rc_nft_templates SET minted = minted + 1 WHERE id=?", (template_id,))
    await db.execute(
        "INSERT INTO rc_nft_events (item_id, user_id, event, detail, created_at) "
        "VALUES (?,?,'mint',?,?)",
        (cur.lastrowid, owner_id, f"price={price}", int(time.time())),
    )
    await db.commit()
    return cur.lastrowid


async def inventory(db, owner_id: int, limit: int = 12) -> list:
    async with db.execute(
        """SELECT i.*, t.title, t.model, t.rarity, t.bg
           FROM rc_nft_items i JOIN rc_nft_templates t ON t.id = i.template_id
           WHERE i.owner_id=? ORDER BY t.floor DESC LIMIT ?""",
        (owner_id, limit),
    ) as cur:
        return list(await cur.fetchall())


async def inventory_value(db, owner_id: int) -> int:
    async with db.execute(
        "SELECT COALESCE(SUM(price),0) FROM rc_nft_items WHERE owner_id=?", (owner_id,)
    ) as cur:
        (total,) = await cur.fetchone()
    return int(total)


async def nft_item(db, item_id: int):
    async with db.execute(
        """SELECT i.*, t.title, t.model, t.rarity, t.bg, t.floor
           FROM rc_nft_items i JOIN rc_nft_templates t ON t.id = i.template_id
           WHERE i.id=?""",
        (item_id,),
    ) as cur:
        return await cur.fetchone()


async def nft_transfer(db, item_id: int, from_id: int, to_id: int) -> bool:
    cur = await db.execute(
        "UPDATE rc_nft_items SET owner_id=? WHERE id=? AND owner_id=?",
        (to_id, item_id, from_id),
    )
    if cur.rowcount:
        await db.execute(
            "INSERT INTO rc_nft_events (item_id, user_id, event, detail, created_at) "
            "VALUES (?,?,'transfer',?,?)",
            (item_id, to_id, f"from={from_id}", int(time.time())),
        )
        await db.commit()
    return cur.rowcount > 0


async def burn_nft(db, item_id: int, user_id: int) -> None:
    await db.execute("UPDATE rc_nft_items SET owner_id=NULL WHERE id=? AND owner_id=?",
                     (item_id, user_id))
    await db.execute(
        "INSERT INTO rc_nft_events (item_id, user_id, event, detail, created_at) "
        "VALUES (?,?,'burn','upgrade fail',?)",
        (item_id, user_id, int(time.time())),
    )
    await db.commit()


async def upgrade_nft(db, item_id: int, user_id: int, fee: int) -> dict:
    """Улучшение: шанс перейти на следующую редкость или сгорание."""
    item = await nft_item(db, item_id)
    if not item or item["owner_id"] != user_id:
        return {"ok": False, "reason": "no_item"}
    if not await debit(db, user_id, fee):
        return {"ok": False, "reason": "no_money"}
    order = ["common", "rare", "epic", "legendary", "mythic"]
    idx = order.index(item["rarity"]) if item["rarity"] in order else 0
    chance = config.UPGRADE_CHANCE[idx]
    if random.random() < chance:
        async with db.execute(
            "SELECT * FROM rc_nft_templates WHERE rarity=? AND active=1 AND id != ? "
            "ORDER BY RANDOM() LIMIT 1",
            (order[min(idx + 1, len(order) - 1)], item["template_id"]),
        ) as cur:
            tmpl = await cur.fetchone()
        await db.execute("UPDATE rc_nft_items SET owner_id=NULL WHERE id=?", (item_id,))
        await db.execute(
            "INSERT INTO rc_nft_events (item_id, user_id, event, detail, created_at) "
            "VALUES (?,?,'upgrade_ok',?,?)",
            (item_id, user_id, f"fee={fee}", int(time.time())),
        )
        await db.commit()
        if tmpl:
            new_id = await mint(db, tmpl["id"], user_id, tmpl["floor"])
            return {"ok": True, "item_id": new_id, "title": tmpl["title"],
                    "rarity": tmpl["rarity"], "model": tmpl["model"]}
        return {"ok": True, "item_id": None, "title": item["title"], "rarity": item["rarity"],
                "model": item["model"]}
    await burn_nft(db, item_id, user_id)
    return {"ok": False, "reason": "burned"}


# ---------------------------------------------------------------------------
# Чеки
# ---------------------------------------------------------------------------
CODE_ALPHABET = string.ascii_uppercase + string.digits


def new_code(prefix: str = "RB") -> str:
    return prefix + "".join(random.choice(CODE_ALPHABET) for _ in range(10))


async def create_check(db, owner_id: int, amount: int, claims: int, hours: int = 24) -> str:
    code = new_code()
    now = int(time.time())
    await db.execute(
        "INSERT INTO rc_checks (code, owner_id, amount, claims, expires_at, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (code, owner_id, amount, claims, now + hours * 3600, now),
    )
    await db.commit()
    return code


async def redeem_check(db, code: str, user_id: int) -> tuple[bool, str, int]:
    code = code.upper().strip()
    async with db.execute("SELECT * FROM rc_checks WHERE code=?", (code,)) as cur:
        row = await cur.fetchone()
    if not row:
        return False, "чек не найден", 0
    if row["expires_at"] < time.time():
        return False, "срок действия истёк", 0
    if row["used"] >= row["claims"]:
        return False, "чек уже полностью активирован", 0
    if row["owner_id"] == user_id:
        return False, "нельзя снять собственный чек", 0
    try:
        await db.execute("INSERT INTO rc_check_claims (code, user_id) VALUES (?,?)",
                         (code, user_id))
    except aiosqlite.IntegrityError:
        return False, "ты уже активировал этот чек", 0
    await db.execute("UPDATE rc_checks SET used = used + 1 WHERE code=?", (code,))
    await add_balance(db, user_id, row["amount"], "check", code)
    return True, "ok", row["amount"]


# ---------------------------------------------------------------------------
# Кейсы
# ---------------------------------------------------------------------------
async def case_list(db) -> list:
    async with db.execute("SELECT * FROM rc_cases WHERE active=1 ORDER BY price") as cur:
        return list(await cur.fetchall())


async def open_case(db, user_id: int, case_id: int) -> dict | None:
    async with db.execute("SELECT * FROM rc_cases WHERE id=? AND active=1", (case_id,)) as cur:
        case = await cur.fetchone()
    if not case:
        return None
    if not await debit(db, user_id, case["price"]):
        return {"error": "no_money"}
    # content: "1500:40,5000:35,15000:18,50000:5,250000:2"
    entries = []
    for part in case["content"].split(","):
        amount, weight = part.split(":")
        entries.append((int(amount), int(weight)))
    total = sum(w for _, w in entries)
    roll = random.uniform(0, total)
    acc = 0
    prize = entries[-1][0]
    for amount, weight in entries:
        acc += weight
        if roll <= acc:
            prize = amount
            break
    await credit_game(db, user_id, f"case:{case_id}", case["price"], prize, case["title"])
    await db.execute(
        "INSERT INTO rc_case_opens (user_id, case_id, win, created_at) VALUES (?,?,?,?)",
        (user_id, case_id, prize, int(time.time())),
    )
    await db.commit()
    return {"prize": prize, "title": case["title"]}


# ---------------------------------------------------------------------------
# Лотерея
# ---------------------------------------------------------------------------
async def buy_ticket(db, user_id: int, numbers: list[int], price: int) -> bool:
    if not await debit(db, user_id, price):
        return False
    await db.execute(
        "INSERT INTO rc_lottery_tickets (user_id, numbers, sold_at) VALUES (?,?,?)",
        (user_id, ",".join(map(str, numbers)), int(time.time())),
    )
    await db.commit()
    return True


async def draw_lottery(db, pool_share: float = 0.85) -> dict:
    async with db.execute(
        "SELECT * FROM rc_lottery_tickets WHERE draw_id IS NULL ORDER BY RANDOM() LIMIT 500"
    ) as cur:
        tickets = list(await cur.fetchall())
    if not tickets:
        return {"ok": False, "reason": "no_tickets"}
    numbers = sorted(random.sample(range(1, config.LOTTERY_MAX + 1), config.LOTTERY_PICK))
    cur = await db.execute(
        "INSERT INTO rc_lottery_draws (drawn_at, numbers, prize_pool) VALUES (?,?,0)",
        (int(time.time()), ",".join(map(str, numbers))),
    )
    draw_id = cur.lastrowid
    winners = 0
    prize_pool = 0
    for t in tickets:
        user_numbers = {int(x) for x in t["numbers"].split(",")}
        hits = len(user_numbers & set(numbers))
        payout = 0
        if hits == config.LOTTERY_PICK:
            payout = config.LOTTERY_JACKPOT
        elif hits == config.LOTTERY_PICK - 1:
            payout = config.DEFAULT_TICKET_PRICE * 20
        elif hits == config.LOTTERY_PICK - 2:
            payout = config.DEFAULT_TICKET_PRICE * 4
        if payout:
            winners += 1
            prize_pool += payout
            await add_balance(db, t["user_id"], payout, "lottery", f"draw={draw_id}")
        await db.execute("UPDATE rc_lottery_tickets SET draw_id=? WHERE id=?", (draw_id, t["id"]))
    await db.execute("UPDATE rc_lottery_draws SET prize_pool=?, winners=? WHERE id=?",
                     (prize_pool, winners, draw_id))
    await db.commit()
    return {"ok": True, "numbers": numbers, "winners": winners, "payout": prize_pool,
            "tickets": len(tickets)}


# ---------------------------------------------------------------------------
# Зимний ивент: склад + Санта
# ---------------------------------------------------------------------------
def today_key() -> str:
    return time.strftime("%Y-%m-%d")


async def warehouse_claim(db, user_id: int) -> dict:
    day = today_key()
    async with db.execute(
        "SELECT * FROM rc_event_claims WHERE user_id=? AND kind='warehouse' AND day=?",
        (user_id, day),
    ) as cur:
        if await cur.fetchone():
            return {"ok": False, "reason": "already"}
    prizes = []
    for _ in range(config.WAREHOUSE_CELLS):
        prizes.append(random.randint(config.WAREHOUSE_MIN, config.WAREHOUSE_MAX))
    total = sum(prizes)
    await add_balance(db, user_id, total, "warehouse", f"{prizes}")
    await db.execute(
        "INSERT OR REPLACE INTO rc_event_claims (user_id, kind, day, payload) VALUES (?,?,?,?)",
        (user_id, "warehouse", day, ",".join(map(str, prizes))),
    )
    await db.commit()
    return {"ok": True, "prizes": prizes, "total": total}


async def santa_state(db) -> dict:
    import datetime

    now = datetime.datetime.now()
    is_final = now.month == 12 and now.day == 31
    total_hp = config.SANTA_HP_FINAL if is_final else config.SANTA_HP
    async with db.execute("SELECT COALESCE(SUM(damage),0) FROM rc_santa WHERE day >= ?",
                          (f"{now.year}-12-01",)) as cur:
        (dealt,) = await cur.fetchone()
    return {
        "is_final": is_final,
        "hp": total_hp,
        "dealt": int(dealt),
        "left": max(0, total_hp - int(dealt)),
        "boss": "Главный босс" if is_final else "Санта",
    }


async def santa_hit(db, user_id: int) -> dict:
    day = today_key()
    async with db.execute("SELECT 1 FROM rc_santa WHERE user_id=? AND day=?", (user_id, day)) as cur:
        if await cur.fetchone():
            return {"ok": False, "reason": "already"}
    damage = random.randint(10_000, 120_000)
    await db.execute("INSERT INTO rc_santa (user_id, day, damage) VALUES (?,?,?)",
                     (user_id, day, damage))
    await db.commit()
    state = await santa_state(db)
    reward = damage * 2
    await add_balance(db, user_id, reward, "santa", f"dmg={damage}")
    return {"ok": True, "damage": damage, "reward": reward, "state": state}


# ---------------------------------------------------------------------------
# Промо
# ---------------------------------------------------------------------------
async def redeem_promo(db, code: str, user_id: int) -> tuple[bool, str, int]:
    code = code.upper().strip()
    async with db.execute("SELECT * FROM rc_promo WHERE code=? AND active=1", (code,)) as cur:
        row = await cur.fetchone()
    if not row:
        return False, "промокод не найден", 0
    if row["uses"] >= row["max_uses"]:
        return False, "лимит исчерпан", 0
    try:
        await db.execute("INSERT INTO rc_promo_uses (code, user_id) VALUES (?,?)",
                         (code, user_id))
    except aiosqlite.IntegrityError:
        return False, "уже активирован", 0
    await db.execute("UPDATE rc_promo SET uses = uses + 1 WHERE code=?", (code,))
    await add_balance(db, user_id, row["amount"], "promo", code)
    return True, "ok", row["amount"]

# =============================== services/rc_engine.py ================
# file: services/rc_engine.py
"""Чистые движки игр rCoin: без Telegram и записи в базу."""

import math
import random
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Мины
# ---------------------------------------------------------------------------
SIZE = 25


def mines_multiplier(opened: int, mines: int) -> float:
    if opened <= 0:
        return 1.0
    size = SIZE
    safe = size - mines
    p = 1.0
    for i in range(opened):
        p *= (safe - i) / (size - i)
    return round(0.96 / p, 3)


def mines_next(opened: int, mines: int) -> float:
    return mines_multiplier(opened + 1, mines)


@dataclass
class MinesRound:
    bet: int
    mines: int
    bombs: set[int] = field(default_factory=set)
    opened: set[int] = field(default_factory=set)
    dead: bool = False
    cashed: bool = False

    @classmethod
    def new(cls, bet: int, mines: int) -> "MinesRound":
        mines = max(1, min(mines, SIZE - 1))
        return cls(bet=bet, mines=mines, bombs=set(random.sample(range(SIZE), mines)))

    def open(self, idx: int) -> str:
        if self.dead or self.cashed or idx in self.opened:
            return "noop"
        self.opened.add(idx)
        if idx in self.bombs:
            self.dead = True
            return "boom"
        if len(self.opened) == SIZE - self.mines:
            self.cashed = True
            return "all"
        return "safe"

    def multiplier(self) -> float:
        return mines_multiplier(len(self.opened), self.mines)

    def payout(self) -> int:
        return int(self.bet * self.multiplier())

    def view(self) -> list[str]:

        cells = []
        for i in range(SIZE):
            if i in self.opened:
                cells.append(CELL_GEM)
            elif self.dead and i in self.bombs:
                cells.append(CELL_BOMB)
            elif self.cashed and i in self.bombs:
                cells.append(CELL_BOMB)
            else:
                cells.append(CELL_CLOSED)
        return cells


# ---------------------------------------------------------------------------
# Лесенка
# ---------------------------------------------------------------------------
LADDER_LEVELS = 6


def ladder_safe_prob(level: int) -> float:
    return max(0.35, 0.85 - level * 0.08)


def ladder_multiplier(level: int) -> float:
    mult = 1.0
    for i in range(level):
        mult /= ladder_safe_prob(i)
    return round(mult * 0.95, 3)


@dataclass
class LadderRound:
    bet: int
    level: int = 0
    dead: bool = False
    cashed: bool = False
    trail: list[str] = field(default_factory=list)

    @classmethod
    def new(cls, bet: int) -> "LadderRound":
        return cls(bet=bet)

    def step(self) -> str:
        if self.dead or self.cashed:
            return "noop"
        if random.random() > ladder_safe_prob(self.level):
            self.dead = True
            self.trail.append("💥")
            return "fall"
        self.level += 1
        self.trail.append("🪜")
        if self.level >= LADDER_LEVELS:
            self.cashed = True
            return "top"
        return "ok"

    def multiplier(self) -> float:
        return ladder_multiplier(self.level)

    def payout(self) -> int:
        return int(self.bet * self.multiplier())


# ---------------------------------------------------------------------------
# Краш
# ---------------------------------------------------------------------------
def crash_peak() -> float:
    r = random.random()
    return round(min(0.97 / max(r, 1e-4), 100.0), 2)


def crash_value(t: float) -> float:
    return round(math.exp(0.11 * t), 2)


# ---------------------------------------------------------------------------
# Текстовые игры
# ---------------------------------------------------------------------------
def coin(bet: int, side: str) -> tuple[bool, int, str]:
    result = random.choice(["heads", "tails"])
    win = result == side
    jackpot = win and random.random() < 0.05
    mult = 3.0 if jackpot else 2.0
    label = "орёл" if result == "heads" else "решка"
    return win, int(bet * mult) if win else 0, f"🪙 {label}" + (" · джекпот ×3" if jackpot else "")


def roulette(bet: int, color: str) -> tuple[bool, int, str]:
    number = random.randint(0, 36)
    reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    actual = "green" if number == 0 else ("red" if number in reds else "black")
    mult = {"red": 2.0, "black": 2.0, "green": 14.0}.get(color, 2.0)
    win = actual == color
    icon = {"red": "🔴", "black": "⚫️", "green": "🟢"}[actual]
    return win, int(bet * mult) if win else 0, f"{icon} {number}"


def rroulette(bet: int, chamber: int) -> tuple[bool, int, str]:
    bullet = random.randint(1, 6)
    win = bullet != chamber
    return win, int(bet * 4.5) if win else 0, f"🔫 выстрел в {bullet}"


def fortune(bet: int, slot: int) -> tuple[bool, int, str]:
    lucky = random.randint(0, 2)
    win = lucky == slot
    return win, int(bet * 2.5) if win else 0, f"🌠 приз в {lucky + 1}"


def chest(bet: int, box: int) -> tuple[bool, int, str]:
    lucky = random.randint(0, 4)
    win = lucky == box
    return win, int(bet * 4.0) if win else 0, f"🎁 приз в {lucky + 1}"


def ball(bet: int, slot: int) -> tuple[bool, int, str]:
    lucky = random.randint(0, 11)
    win = lucky == slot
    return win, int(bet * 6.0) if win else 0, f"🔮 шар в лунке {lucky + 1}"


def fishing(bet: int, spot: int) -> tuple[bool, int, str]:
    catch = random.random()
    if catch < 0.08:
        return False, 0, "🎣 сорвалась"
    mult = {0: 1.4, 1: 1.9, 2: 2.6}[max(0, min(2, spot))]
    if catch < 0.25:
        mult *= 2.5
    return True, int(bet * mult), f"🎣 улов ×{mult:g}"


def sketch(bet: int, guess: int) -> tuple[bool, int, str]:
    number = random.randint(1, 6)
    win = number == guess
    return win, int(bet * 5.2) if win else 0, f"🎨 выпало {number}"


def diamonds(bet: int, pick: int) -> tuple[bool, int, str]:
    hidden = random.randint(0, 3)
    win = hidden == pick
    return win, int(bet * 3.4) if win else 0, f"💎 алмаз в {hidden + 1}"


def tower(bet: int, floor: int) -> tuple[bool, int, str]:
    collapse_at = random.randint(1, 8)
    win = floor < collapse_at
    return win, int(bet * (1 + floor * 0.55)) if win else 0, f"🏗 обрушился {collapse_at}"


def gold(bet: int, vein: int) -> tuple[bool, int, str]:
    rich = random.randint(0, 2)
    win = rich == vein
    return win, int(bet * 2.8) if win else 0, f"🪙 жила {rich + 1}"


def quack(bet: int, lily: int) -> tuple[bool, int, str]:
    correct = random.randint(0, 4)
    win = lily == correct
    return win, int(bet * 4.6) if win else 0, f"🐸 жаба на кувшинке {correct + 1}"


def hilo(bet: int, guess: str) -> tuple[bool, int, str]:
    card = random.randint(2, 14)
    threshold = 8
    win = (card < threshold) if guess == "low" else (card > threshold)
    label = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(card, str(card))
    return win, int(bet * 2.0) if win else 0, f"↕️ выпало {label}"

# =============================== services/nft_image.py ================
# file: services/nft_image.py
"""Генерация картинок NFT через Pillow: фото/градиент + имя + номер."""

import os
import re
import time

from PIL import Image, ImageDraw, ImageFont


CARD_W, CARD_H = 900, 1100
PADDING = 48


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _hex(color: str) -> tuple[int, int, int]:
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    try:
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore
    except ValueError:
        return (34, 19, 26)


def _gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    w, h = size
    top_rgb, bot_rgb = _hex(top), _hex(bottom)
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        k = y / max(1, h - 1)
        grad.putpixel((0, y), tuple(int(top_rgb[i] + (bot_rgb[i] - top_rgb[i]) * k)
                                    for i in range(3)))
    return grad.resize((w, h))


def _fit_emoji(model: str) -> str:
    found = re.findall(r"[^\w\s]", model or "")
    return found[0] if found else "🎁"


def _font_for_emoji(size: int) -> ImageFont.FreeTypeFont | None:
    for path in ("C:/Windows/Fonts/seguiemj.ttf",
                 "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return None


def render_gift(*, title: str, serial: int, rarity: str, model: str,
                bg: str = "#22131a", source_image: str | None = None,
                out_dir: str | None = None) -> str:
    """Собирает PNG: фон/фото, карточка, имя коллекции, номер #N, редкость."""
    out_dir = out_dir or os.path.join(config.BASE_DIR, "gen")
    os.makedirs(out_dir, exist_ok=True)

    if source_image and os.path.exists(source_image):
        base = Image.open(source_image).convert("RGB")
        w, h = base.size
        scale = max(CARD_W / w, CARD_H / h)
        base = base.resize((int(w * scale) + 1, int(h * scale) + 1))
        x = (base.width - CARD_W) // 2
        y = (base.height - CARD_H) // 2
        card = base.crop((x, y, x + CARD_W, y + CARD_H))
        card = Image.blend(card, Image.new("RGB", card.size, (0, 0, 0)), 0.25)
    else:
        card = _gradient((CARD_W, CARD_H), bg, "#0a0709")
        emoji_font = _font_for_emoji(360)
        draw = ImageDraw.Draw(card)
        glyph = _fit_emoji(model)
        if emoji_font:
            box = draw.textbbox((0, 0), glyph, font=emoji_font)
            tw, th = box[2] - box[0], box[3] - box[1]
            draw.text(((CARD_W - tw) / 2 - box[0], (CARD_H - th) / 2 - box[1] - 120),
                      glyph, font=emoji_font, embedded_color=True)
        else:
            draw.text((CARD_W / 2 - 40, CARD_H / 2 - 220), model[:2], font=_font(160),
                      fill=(255, 255, 255))

    overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((24, 24, CARD_W - 24, CARD_H - 24), radius=40,
                         outline=(255, 255, 255, 70), width=3)
    od.rounded_rectangle((24, CARD_H - 230, CARD_W - 24, CARD_H - 24), radius=40,
                         fill=(10, 7, 9, 190))
    card = Image.alpha_composite(card.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(card)
    rarity_icon = config.RARITY_ICONS.get(rarity, "⚪️")
    draw.text((PADDING + 8, CARD_H - 200), f"{rarity_icon} {config.RARITY_NAMES.get(rarity, rarity).upper()}",
              font=_font(30, bold=True), fill=(255, 220, 220))
    draw.text((PADDING + 8, CARD_H - 155), title[:26], font=_font(52, bold=True),
              fill=(255, 255, 255))
    num_text = f"#{serial}"
    w_num = draw.textlength(num_text, font=_font(46, bold=True))
    draw.text((CARD_W - PADDING - w_num - 8, CARD_H - 150), num_text,
              font=_font(46, bold=True), fill=(255, 120, 140))
    draw.text((PADDING + 8, CARD_H - 90), "РУБИН · коллекция",
              font=_font(24), fill=(200, 190, 195))

    safe = re.sub(r"[^\w\-]+", "_", title, flags=re.UNICODE)[:40] or "gift"
    path = os.path.join(out_dir, f"{safe}_{serial}_{int(time.time() * 1000)}.png")
    card.convert("RGB").save(path, "PNG", optimize=True)
    return path


def render_transfer(amount: int, frm: str, to: str, out_dir: str | None = None) -> str:
    """Картинка перевода rCoin."""
    out_dir = out_dir or os.path.join(config.BASE_DIR, "gen")
    os.makedirs(out_dir, exist_ok=True)
    w, h = 900, 480
    img = _gradient((w, h), "#3a0d14", "#14080b").convert("RGBA")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((24, 24, w - 24, h - 24), radius=36,
                           outline=(255, 120, 140, 90), width=3)
    draw.text((60, 70), "ПЕРЕВОД rCoin", font=_font(34, bold=True), fill=(255, 190, 200))
    amount_text = f"+{amount:,}".replace(",", " ")
    draw.text((60, 150), amount_text, font=_font(96, bold=True), fill=(255, 255, 255))
    draw.text((60, 285), f"от: {frm[:28]}", font=_font(30), fill=(220, 220, 230))
    draw.text((60, 330), f"кому: {to[:28]}", font=_font(30), fill=(220, 220, 230))
    draw.text((60, h - 90), "РУБИН БОТ · rCoin", font=_font(24), fill=(180, 170, 180))
    path = os.path.join(out_dir, f"transfer_{int(time.time() * 1000)}.png")
    img.convert("RGB").save(path, "PNG", optimize=True)
    return path


def render_leaderboard(rows: list, title: str = "МИРОВОЙ РЕЙТИНГ",
                       out_dir: str | None = None) -> str:
    """Картинка рейтинга («Пик»)."""
    out_dir = out_dir or os.path.join(config.BASE_DIR, "gen")
    os.makedirs(out_dir, exist_ok=True)
    w = 1000
    h = 220 + max(1, len(rows)) * 86
    img = _gradient((w, h), "#1a0d12", "#0a0608").convert("RGBA")
    draw = ImageDraw.Draw(img)
    draw.text((50, 44), title, font=_font(52, bold=True), fill=(255, 255, 255))
    draw.text((50, 118), "Рубин Бот · рейтинг по балансу rCoin",
              font=_font(26), fill=(190, 175, 180))
    medals = {1: "1", 2: "2", 3: "3"}
    y = 190
    for i, row in enumerate(rows, start=1):
        draw.rounded_rectangle((40, y, w - 40, y + 72), radius=24, fill=(255, 255, 255, 18))
        place = medals.get(i, str(i))
        draw.text((62, y + 16), place, font=_font(38, bold=True), fill=(255, 140, 160))
        name = (row["first_name"] or row["username"] or str(row["id"]))[:24]
        draw.text((130, y + 18), name, font=_font(32, bold=True), fill=(255, 255, 255))
        money = f"{int(row['balance']):,}".replace(",", " ")
        tw = draw.textlength(money, font=_font(32, bold=True))
        draw.text((w - 70 - tw, y + 18), money, font=_font(32, bold=True),
                  fill=(150, 240, 180))
        y += 86
    path = os.path.join(out_dir, f"top_{int(time.time() * 1000)}.png")
    img.convert("RGB").save(path, "PNG", optimize=True)
    return path

# =============================== keyboards_rc.py ================
# file: keyboards_rc.py
"""Инлайн-клавиатуры «Рубин Бот» с Premium-эмодзи внутри кнопок."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo



def _btn(text: str, data: str | None = None, url: str | None = None,
         web: str | None = None, style: str | None = None) -> InlineKeyboardButton:
    kw: dict = {"text": text}
    if data:
        kw["callback_data"] = data
    if url:
        kw["url"] = url
    if web:
        kw["web_app"] = WebAppInfo(url=web)
    if style:
        kw["style"] = style
    try:
        return InlineKeyboardButton(**kw)
    except Exception:
        kw.pop("style", None)
        return InlineKeyboardButton(**kw)


def kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in rows if r])


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [_btn(f"{E.td('gem')} Баланс", "m:balance", style="success"),
         _btn(f"{E.td('crown')} Профиль", "m:profile")],
        [_btn(f"{E.td('bag')} Маркетплейс", "m:market"),
         _btn(f"{E.td('gift')} Инвентарь", "m:inventory")],
        [_btn(f"{E.td('money_tear')} Банк", "m:bank"),
         _btn(f"{E.td('exchange')} Обменник", "m:exchange")],
        [_btn(f"{E.td('play')} Игры", "m:games"),
         _btn(f"{E.td('cool')} Кейсы", "m:cases")],
        [_btn(f"{E.td('calendar')} Бонус", "m:daily"),
         _btn(f"{E.td('balloon')} Лотерея", "m:lottery")],
        [_btn(f"{E.td('champagne')} Донат", "m:donate"),
         _btn(f"{E.td('money_launch')} Заработок", "m:earn")],
        [_btn(f"{E.td('note')} История", "m:history"),
         _btn(f"{E.td('hundred')} Топ", "m:top")],
        [_btn(f"{E.td('bulb')} Команды", "m:commands"),
         _btn(f"{E.td('new')} Зимний склад", "m:warehouse")],
    ]
    if config.WEBAPP_URL:
        rows.append([_btn(f"{E.td('bolt')} Открыть приложение", web=config.WEBAPP_URL,
                          style="success")])
    if is_admin:
        rows.append([_btn(f"{E.td('gear')} Админка", "adm:menu")])
    return kb(*rows)


def back(to: str = "m:back") -> InlineKeyboardMarkup:
    return kb([_btn("◀️ Назад", to)])


def confirm(yes: str, no: str = "m:back") -> InlineKeyboardMarkup:
    return kb([_btn(f"{E.td('check')} Да", yes, style="success"),
               _btn(f"{E.td('cross')} Нет", no)])


# --- Баланс -----------------------------------------------------------------
def balance_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('money_tear')} Пополнить", "m:donate", style="success"),
         _btn(f"{E.td('exchange')} Обменник", "m:exchange")],
        [_btn(f"{E.td('bulb')} Заработок", "m:earn"),
         _btn(f"{E.td('note')} История", "m:history")],
        [_btn("🏠 В меню", "m:back")],
    )


# --- Банк -------------------------------------------------------------------
def bank_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn("25% в банк", "b:put25", style="success"), _btn("Всё в банк", "b:putall")],
        [_btn("Снять 25%", "b:take25"), _btn("Снять всё", "b:takeall")],
        [_btn(f"{E.td('up')} Проценты", "b:interest")],
        [_btn("🏠 В меню", "m:back")],
    )


# --- Каталог игр ------------------------------------------------------------
GAME_ROWS = [
    [("🏀 Баскетбол", "g:dice:basket", "success"), ("⚽️ Футбол", "g:dice:football", None)],
    [("🎯 Дартс", "g:dice:darts", None), ("🎳 Боулинг", "g:dice:bowling", None)],
    [("🎲 Кости (dice)", "g:dice:dice", None), ("🎰 Слоты", "g:dice:slots", "success")],
    [("💣 Мины", "g:mines", "success"), ("🪜 Лесенка", "g:ladder", None)],
    [("🚀 Краш", "g:crash", None), ("🪙 Монетка", "g:coin", None)],
    [("🔫 Рус. рулетка", "g:rroulette", None), ("🎡 Рулетка", "g:roulette", None)],
    [("🌠 Фортуна", "g:fortune", None), ("🎁 Сундук", "g:chest", None)],
    [("🔮 Шар", "g:ball", None), ("🎣 Рыбалка", "g:fishing", None)],
    [("🎨 Скетч", "g:sketch", None), ("💎 Алмазы", "g:diamonds", None)],
    [("🏗 Башня", "g:tower", None), ("🪙 Золото", "g:gold", None)],
    [("🐸 Квак", "g:quack", None), ("↕️ HiLo", "g:hilo", "success")],
    [_btn("🏠 В меню", "m:back")],
]


def games_kb() -> InlineKeyboardMarkup:
    return kb(*[
        [_btn(label, data, style=style) for label, data, style in row]
        for row in GAME_ROWS
    ])


BET_STEPS = [1_000, 10_000, 100_000, 1_000_000]


def bet_kb(game: str) -> InlineKeyboardMarkup:
    rows = [[_btn(f"{v // 1000}k", f"bet:{game}:{v}") for v in BET_STEPS]]
    rows.append([_btn("✍️ Своя ставка", f"betcustom:{game}", style="success")])
    rows.append([_btn("◀️ Игры", "m:games")])
    return kb(*rows)


# --- Мины (5x5) -------------------------------------------------------------
CELL_CLOSED = E.te(*E.CELL_CLOSED)
CELL_GEM = E.te(*E.CELL_GEM)
CELL_BOMB = E.te(*E.CELL_BOMB)


def mines_kb(view: list[str], sid: str, can_cash: bool) -> InlineKeyboardMarkup:
    rows = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            row.append(_btn(view[idx], f"mn:{sid}:{idx}"))
        rows.append(row)
    if can_cash:
        rows.append([_btn(f"{E.td('money_tear')} Забрать", f"mnc:{sid}", style="success")])
    rows.append([_btn("🔄 Новая", "g:mines"), _btn("🏠 Меню", "m:back")])
    return kb(*rows)


# --- Лесенка -----------------------------------------------------------------
LADDER_LEVELS = 6


def ladder_kb(level: int, sid: str, alive: bool) -> InlineKeyboardMarkup:
    rows = []
    if alive:
        row = []
        for cell in range(level + 3):
            row.append(_btn("❓", f"ld:{sid}:{cell}"))
        rows.append(row)
        rows.append([_btn(f"{E.td('money_tear')} Забрать", f"ldc:{sid}", style="success")])
    rows.append([_btn("🔄 Новая", "g:ladder"), _btn("🏠 Меню", "m:back")])
    return kb(*rows)


# --- Краш -------------------------------------------------------------------
def crash_kb(sid: str) -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('money_tear')} Забрать", f"cr:cash:{sid}", style="success")],
        [_btn("📈 Расти", f"cr:tick:{sid}")],
        [_btn("🔄 Новая", "g:crash")],
    )


# --- Общие текстовые игры ---------------------------------------------------
def choices_kb(game: str, choices: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = []
    chunk: list = []
    for label, value in choices:
        chunk.append(_btn(label, f"s:{game}:{value}"))
        if len(chunk) == 3:
            rows.append(chunk)
            chunk = []
    if chunk:
        rows.append(chunk)
    rows.append([_btn("◀️ Игры", "m:games")])
    return kb(*rows)


# --- Маркет / инвентарь ------------------------------------------------------
def market_kb(templates: list) -> InlineKeyboardMarkup:
    rows = []
    for t in templates:
        icon = config.RARITY_ICONS.get(t["rarity"], "⚪️")
        label = f"{t['model']} {t['title']} {icon} {E.plain('gem')} {short(t['floor'])}"
        rows.append([_btn(label, f"mk:view:{t['slug']}")])
    rows.append([_btn("📦 Инвентарь", "m:inventory"), _btn("🏠 Меню", "m:back")])
    return kb(*rows)


def market_item_kb(slug: str, price: int, balance: int) -> InlineKeyboardMarkup:
    can = balance >= price
    return kb(
        [_btn(f"{E.td('bag')} Купить за {short(price)}",
              f"mk:buy:{slug}", style="success" if can else None)],
        [_btn("◀️ Маркет", "m:market")],
    )


def inventory_kb(items: list) -> InlineKeyboardMarkup:
    rows = []
    for it in items:
        icon = config.RARITY_ICONS.get(it["rarity"], "⚪️")
        rows.append([_btn(f"{it['model']} {it['title']} #{it['serial']} {icon}",
                          f"inv:open:{it['id']}")])
    rows.append([_btn(f"{E.td('money_tear')} Привязать к балансу", "inv:bind", style="success")])
    rows.append([_btn("🛍 Маркет", "m:market"), _btn("🏠 Меню", "m:back")])
    return kb(*rows)


def nft_item_kb(item_id: int, rarity: str, fee: int) -> InlineKeyboardMarkup:
    rows = [
        [_btn(f"{E.td('money_tear')} Улучшить ({short(fee)})",
              f"inv:upgrade:{item_id}", style="success")],
        [_btn(f"{E.td('gift')} Подарить", f"inv:give:{item_id}")],
        [_btn("🖼 Картинка", f"inv:image:{item_id}")],
        [_btn("◀️ Инвентарь", "m:inventory")],
    ]
    return kb(*rows)


# --- Лотерея / кейсы / чеки ---------------------------------------------------
def lottery_kb(ticket_price: int) -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('balloon')} Купить билет ({short(ticket_price)})", "lot:buy", style="success")],
        [_btn("🎲 Розыгрыш", "lot:draw"), _btn("🎟 Мои билеты", "lot:mine")],
        [_btn("🏠 В меню", "m:back")],
    )


def cases_kb(cases: list) -> InlineKeyboardMarkup:
    rows = [[_btn(f"📦 {c['title']} — {short(c['price'])}", f"case:open:{c['id']}", style="success")]
            for c in cases]
    rows.append([_btn("🏠 В меню", "m:back")])
    return kb(*rows)


def checks_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('gift')} Создать чек", "chk:create", style="success")],
        [_btn("🎁 Активировать чек", "chk:redeem")],
        [_btn("🏠 В меню", "m:back")],
    )


# --- Донат / статусы ---------------------------------------------------------
def donate_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn("🔵 Blue Verify — 150⭐ / 500кк", "don:blue", style="success")],
        [_btn("⚫️ Black Verify — 250⭐ / 1ккк", "don:black")],
        [_btn(f"{E.td('crown')} Elite — 2.5ккк", "don:elite")],
        [_btn(f"{E.td('exchange')} Обменник", "m:exchange")],
        [_btn("🏠 В меню", "m:back")],
    )


# --- Ивент -------------------------------------------------------------------
def warehouse_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('gift')} Открыть 3 ячейки", "ev:warehouse", style="success")],
        [_btn(f"{E.td('skull')} Санта", "ev:santa"), _btn("🏠 Меню", "m:back")],
    )


def santa_kb() -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('fire')} Атаковать", "ev:santa:hit", style="success")],
        [_btn(f"{E.td('gift')} Склад", "m:warehouse"), _btn("🏠 Меню", "m:back")],
    )


# --- Админка -----------------------------------------------------------------
def admin_menu() -> InlineKeyboardMarkup:
    return kb(
        [_btn(f"{E.td('hundred')} Статистика", "adm:stats", style="success"),
         _btn(f"{E.td('money_tear')} Выдать", "adm:give")],
        [_btn(f"{E.td('gift')} Создать NFT", "adm:nft", style="success"),
         _btn(f"{E.td('bag')} Список NFT", "adm:nftlist")],
        [_btn(f"{E.td('crown')} Статус", "adm:status"),
         _btn(f"{E.td('no_entry')} Бан", "adm:ban")],
        [_btn(f"{E.td('megaphone')} Рассылка", "adm:broadcast"),
         _btn(f"{E.td('disc')} Промо", "adm:promo")],
        [_btn("🏠 В меню", "m:back")],
    )


def admin_back() -> InlineKeyboardMarkup:
    return kb([_btn("◀️ Админка", "adm:menu")])


def short(n: float) -> str:

    return short_num(n)

# =============================== handlers/core.py ================
# file: handlers/core.py
"""Ядро «Рубин Бот»: меню, профиль, баланс, банк, чеки, история, топ, рефералка."""

import time

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


router_rc_core = Router(name="rc_core")


class CoreFSM(StatesGroup):
    give_amount = State()
    give_target = State()
    check_amount = State()
    check_claims = State()
    check_redeem = State()
    custom_bet = State()


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDs


def status_line(user: M.RCUser) -> str:
    status = user.active_status
    item = config.STATUSES.get(user.status)
    if item and item[0] and status != "Нет":
        return f'{E.te(item[0], item[0])} {status}' if False else f'<tg-emoji emoji-id="{item[0]}">{item[1]}</tg-emoji>'
    return status


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
@router_rc_core.message(CommandStart())
async def start(message: Message, db, command: CommandObject, state: FSMContext):
    await state.clear()
    ref = None
    args = command.args or ""
    if args.startswith("ref_"):
        ref = args[4:]
        ref = int(ref) if ref.isdigit() else None
    user = await M.ensure_user(db, message.from_user, ref)
    if ref and user.referrer_id != message.from_user.id:
        try:
            await message.bot.send_message(
                ref, f"{E.td('money_launch')} По твоей ссылке пришёл новый игрок! Баланс пополнен."
            )
        except Exception:
            pass
    text = (
        f"{E.td('crown')} <b>{config.BOT_NAME}</b> — игровой клуб\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Привет, <b>{user.name}</b>!\n\n"
        "<blockquote>"
        f"{E.td('gem')} Валюта клуба — <b>rCoin</b>\n"
        f"{E.td('play')} 23 игры, кейсы, лотерея и маркет NFT\n"
        f"{E.td('gift')} Собирай коллекцию и улучшай редкость\n"
        "</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Баланс: <b>{M.full_num(user.balance)} rC</b>\n"
        f"{E.td('bulb')} Команды — обычным текстом: <code>Б</code>, <code>Игры</code>, <code>Маркет</code>"
    )
    await message.answer(text, reply_markup=K.main_menu(is_admin(message.from_user.id)))


# ---------------------------------------------------------------------------
# Главное меню
# ---------------------------------------------------------------------------
@router_rc_core.callback_query(F.data == "m:back")
async def menu_back(call: CallbackQuery, db):
    user = await M.get_user(db, call.from_user.id)
    text = (
        f"{E.td('crown')} <b>{config.BOT_NAME}</b> — меню\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Баланс: <b>{M.full_num(user.balance)} rC</b>\n"
        f"{E.td('up')} Статус: {status_line(user)}"
    )
    try:
        await call.message.edit_text(text, reply_markup=K.main_menu(is_admin(call.from_user.id)))
    except Exception:
        await call.message.answer(text, reply_markup=K.main_menu(is_admin(call.from_user.id)))
    await call.answer()


# ---------------------------------------------------------------------------
# Баланс
# ---------------------------------------------------------------------------
async def render_balance(db, uid: int) -> str:
    user = await M.get_user(db, uid)
    if not user:
        return "Нажми /start"
    return (
        f"{E.td('cash')} <b>БАЛАНС</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('gem')} На руках: <b>{M.full_num(user.balance)}</b> rC\n"
        f"{E.td('money_wind')} В банке: <b>{M.full_num(user.bank)}</b> rC\n"
        f"{E.td('infinity')} Всего: <b>{M.short_num(user.balance + user.bank)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('up')} Заработано: <b>{M.short_num(user.won)}</b>\n"
        f"{E.td('down')} Проиграно: <b>{M.short_num(user.lost)}</b>"
    )


@router_rc_core.callback_query(F.data == "m:balance")
async def cb_balance(call: CallbackQuery, db):
    await call.message.edit_text(await render_balance(db, call.from_user.id),
                                 reply_markup=K.balance_kb())
    await call.answer()


# ---------------------------------------------------------------------------
# Профиль
# ---------------------------------------------------------------------------
async def render_profile(db, uid: int) -> str:
    user = await M.get_user(db, uid)
    winners = user.duels_won
    return (
        f"{E.td('crown')} <b>ПРОФИЛЬ</b> — {user.mention}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('cool')} Статус: {status_line(user)}\n"
        f"{E.td('money_tear')} Баланс: <b>{M.short_num(user.balance)}</b>\n"
        f"{E.td('money_wind')} Банк: <b>{M.short_num(user.bank)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('play')} Сыграно игр: <b>{M.full_num(user.played)}</b>\n"
        f"{E.td('hundred')} Выиграно дуэлей: <b>{M.full_num(winners)}</b>\n"
        f"{E.td('down')} Проиграно rCoin: <b>{M.short_num(user.lost)}</b>\n"
        f"{E.td('up')} Крупнейший выигрыш: <b>{M.short_num(user.best_win)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('calendar')} Серия входов: <b>{user.streak}</b> дн.\n"
        f"{E.td('hundred')} Приглашено: <b>{user.referrals}</b>\n"
        f"🆔 <code>{user.id}</code>"
    )


@router_rc_core.callback_query(F.data == "m:profile")
async def cb_profile(call: CallbackQuery, db):
    await call.message.edit_text(await render_profile(db, call.from_user.id),
                                 reply_markup=K.back())
    await call.answer()


# ---------------------------------------------------------------------------
# Банк
# ---------------------------------------------------------------------------
async def render_bank(db, uid: int, note: str = "") -> tuple[str, object]:
    user = await M.get_user(db, uid)
    text = (
        f"{E.td('building')} <b>БАНК rCoin</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} На руках: <b>{M.full_num(user.balance)}</b>\n"
        f"{E.td('money_wind')} В банке: <b>{M.full_num(user.bank)}</b>\n"
        f"{E.td('up')} Ставка: <b>{config.BANK_INTEREST_HOURLY * 100:.0f}% в час</b>\n"
        f"{E.td('money_eyes')} Прогноз за час: <b>+{M.short_num(int(user.bank * config.BANK_INTEREST_HOURLY))}</b>\n"
    )
    if note:
        text += f"\n{note}"
    return text, K.bank_kb()


@router_rc_core.callback_query(F.data == "m:bank")
async def cb_bank(call: CallbackQuery, db):
    text, markup = await render_bank(db, call.from_user.id)
    await call.message.edit_text(text, reply_markup=markup)
    await call.answer()


@router_rc_core.callback_query(F.data.startswith("b:"))
async def bank_action(call: CallbackQuery, db):
    action = call.data.split(":")[1]
    uid = call.from_user.id
    user = await M.get_user(db, uid)
    note = ""
    if action == "interest":
        hours = max(0, int((time.time() - 0) // 3600))
        profit = int(user.bank * config.BANK_INTEREST_HOURLY * max(1, hours)) if user.bank else 0
        if profit:
            await M.add_balance(db, uid, profit, "bank_interest")
            note = f"{E.td('check')} Начислено <b>{M.short_num(profit)}</b> rC"
        else:
            note = f"{E.td('bell')} Проценты появятся, когда на счёте есть деньги"
    else:
        amount = {
            "put25": user.balance // 4,
            "putall": user.balance,
            "take25": user.bank // 4,
            "takeall": user.bank,
        }.get(action, 0)
        if amount <= 0:
            await call.answer("Нечего переводить", show_alert=True)
            return
        if action.startswith("put"):
            await M.debit(db, uid, amount)
            await db.execute("UPDATE rc_users SET bank = bank + ? WHERE id=?", (amount, uid))
            await db.commit()
            note = f"{E.td('money_wind')} Внесено: <b>{M.short_num(amount)}</b> rC"
        else:
            await db.execute(
                "UPDATE rc_users SET bank = bank - ?, balance = balance + ? WHERE id=? AND bank >= ?",
                (amount, amount, uid, amount),
            )
            await db.commit()
            note = f"{E.td('money_tear')} Снято: <b>{M.short_num(amount)}</b> rC"
    text, markup = await render_bank(db, uid, note)
    await call.message.edit_text(text, reply_markup=markup)
    await call.answer()


# ---------------------------------------------------------------------------
# История
# ---------------------------------------------------------------------------
EMOJI_BY_GAME = {
    "mines": "💣", "ladder": "🪜", "crash": "🚀", "dice:basket": "🏀",
    "dice:football": "⚽️", "dice:darts": "🎯", "dice:bowling": "🎳",
    "dice:dice": "🎲", "dice:slots": "🎰", "coin": "🪙", "roulette": "🎡",
    "rroulette": "🔫", "fortune": "🌠", "chest": "🎁", "ball": "🔮",
    "fishing": "🎣", "sketch": "🎨", "diamonds": "💎", "tower": "🏗",
    "gold": "🪙", "quack": "🐸", "hilo": "↕️", "transfer": "💸",
    "check": "🎁", "case": "📦", "lottery": "🎈", "daily": "🗓",
    "santa": "💀", "warehouse": "🎇", "market": "🛍",
}


@router_rc_core.callback_query(F.data == "m:history")
async def cb_history(call: CallbackQuery, db):
    await show_history(call.message, db, call.from_user.id)
    await call.answer()


async def show_history(message: Message, db, uid: int, offset: int = 0):
    rows = await M.history(db, uid, limit=10, offset=offset)
    if not rows:
        return await message.edit_text(
            f"{E.td('note')} <b>ИСТОРИЯ</b>\n\nПока пусто — сыграй первую игру!",
            reply_markup=K.back(),
        )
    lines = [f"{E.td('note')} <b>ИСТОРИЯ ИГР</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for r in rows:
        icon = EMOJI_BY_GAME.get(r["game"].split(":")[0], "🎲")
        profit = r["payout"] - r["bet"] if r["bet"] else r["payout"]
        sign = "+" if profit > 0 else ""
        color = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
        when = time.strftime("%d.%m %H:%M", time.localtime(r["created_at"]))
        lines.append(
            f"{color} {icon} <code>{r['game']}</code> — <b>{sign}{M.short_num(profit)}</b> "
            f"<i>{when}</i>"
        )
    await message.edit_text("\n".join(lines), reply_markup=K.back())


# ---------------------------------------------------------------------------
# Топ / Пик / Топчат
# ---------------------------------------------------------------------------
async def render_top(rows: list, title: str = "МИРОВОЙ РЕЙТИНГ") -> str:
    medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
    lines = [f"{E.td('hundred')} <b>{title}</b>", "━━━━━━━━━━━━━━━━━━━━"]
    if not rows:
        lines.append("Пока пусто")
    for i, r in enumerate(rows[:10]):
        name = (r["first_name"] or r["username"] or str(r["id"]))[:18]
        lines.append(f"{medals[i]} <b>{i + 1}.</b> {name} — <b>{M.short_num(r['balance'])}</b>")
    return "\n".join(lines)


@router_rc_core.callback_query(F.data == "m:top")
async def cb_top(call: CallbackQuery, db):
    rows = await M.leaderboard(db)
    await call.message.edit_text(await render_top(rows), reply_markup=K.back())
    await call.answer()


async def top_image_answer(message: Message, db, rows: list) -> None:
    path = nft_image.render_leaderboard(rows)
    await message.answer_photo(path, caption=f"{E.td('hundred')} Рейтинг rCoin")


async def chat_top(message: Message, db) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("Топчат работает только в группах.")
    rows = await M.leaderboard(db, limit=200)
    chat_ids = set()
    try:
        async for member in message.bot.get_chat_administrators(message.chat.id):
            chat_ids.add(member.user.id)
    except Exception:
        pass
    rows = await M.chat_leaderboard(db, list(chat_ids)) or rows[:10]
    await message.answer(await render_top(rows, "РЕЙТИНГ ЧАТА"), reply_markup=K.back())


# ---------------------------------------------------------------------------
# Ежедневный бонус
# ---------------------------------------------------------------------------
async def daily_answer(message_or_call, db, uid: int) -> str:
    ok, reward, streak = await M.claim_daily(db, uid)
    if not ok:
        hours = streak // 3600 if streak > 3600 else 1
        return (f"{E.td('calendar')} <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n"
                f"Ещё не готов — попробуй через <b>{hours} ч</b>.")
    user = await M.get_user(db, uid)
    return (
        f"{E.td('calendar')} <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('fire')} Серия: <b>{streak}</b> дн.\n"
        f"{E.td('money_tear')} Получено: <b>{M.short_num(reward)}</b> rC\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>"
    )


@router_rc_core.callback_query(F.data == "m:daily")
async def cb_daily(call: CallbackQuery, db):
    text = await daily_answer(call, db, call.from_user.id)
    await call.message.edit_text(text, reply_markup=K.back())
    await call.answer()


# ---------------------------------------------------------------------------
# Рефералка
# ---------------------------------------------------------------------------
async def ref_answer(message: Message) -> None:
    link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{message.from_user.id}"
    await message.answer(
        f"{E.td('money_launch')} <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"За каждого друга: <b>{config.REF_PERCENT}% с его входов + {M.short_num(config.START_BALANCE // 5)} rC</b>\n\n"
        f"Твоя ссылка:\n<code>{link}</code>",
        reply_markup=K.back(),
    )


# ---------------------------------------------------------------------------
# Команды
# ---------------------------------------------------------------------------
@router_rc_core.callback_query(F.data == "m:commands")
async def cb_commands(call: CallbackQuery):
    lines = [f"{E.td('bulb')} <b>КОМАНДЫ</b> (пиши без слэша)", "━━━━━━━━━━━━━━━━━━━━"]
    for word in sorted(set(config.RU_COMMANDS)):
        lines.append(f"• <code>{word}</code>")
    await call.message.edit_text("\n".join(lines), reply_markup=K.back())
    await call.answer()


# ---------------------------------------------------------------------------
# Передача rCoin (Дать)
# ---------------------------------------------------------------------------
def parse_amount(text: str | None) -> int | None:
    if not text:
        return None
    t = text.strip().lower().replace(" ", "").replace("rc", "").replace("rcoin", "")
    mult = 1
    for suffix, m in (("kkk", 10**9), ("kk", 10**6), ("k", 10**3)):
        if t.endswith(suffix):
            t, mult = t[: -len(suffix)], m
            break
    try:
        value = float(t.replace(",", "."))
    except ValueError:
        return None
    if value <= 0:
        return None
    return int(value * mult)


async def parse_ru_command(message: Message, db, state: FSMContext) -> bool:
    """Единый разбор русских команд. True — если обработано."""
    text = (message.text or "").strip()
    low = text.lower()
    parts = low.split()
    if not parts:
        return False
    head = parts[0]
    tail = parts[1:]

    if head in ("дать", "передать"):
        await start_give(message, db, state, tail)
        return True
    if head in ("мины", "лесенка", "краш"):
        # "мины 10000 3" / "лесенка 50к"

        if head == "мины":
            await rc_games.start_mines_text(message, db, tail)
        elif head == "лесенка":
            await rc_games.start_ladder_text(message, db, tail)
        else:
            await rc_games.start_crash_text(message, db, tail)
        return True
    action = config.RU_COMMANDS.get(head)
    if not action:
        return False
    if action == "balance":
        await message.answer(await render_balance(db, message.from_user.id),
                             reply_markup=K.balance_kb())
    elif action == "profile":
        await message.answer(await render_profile(db, message.from_user.id), reply_markup=K.back())
    elif action == "bank":
        text_out, markup = await render_bank(db, message.from_user.id)
        await message.answer(text_out, reply_markup=markup)
    elif action == "daily":
        await message.answer(await daily_answer(message, db, message.from_user.id),
                             reply_markup=K.back())
    elif action == "lottery":

        await rc_lottery.lottery_screen(message, db)
    elif action == "cases":

        await rc_lottery.cases_screen(message, db)
    elif action == "tickets":

        await rc_lottery.tickets_screen(message, db)
    elif action == "top":
        await message.answer(await render_top(await M.leaderboard(db)), reply_markup=K.back())
    elif action == "topchat":
        await chat_top(message, db)
    elif action == "topimg":
        await top_image_answer(message, db, await M.leaderboard(db))
    elif action == "market":

        await rc_market.market_screen(message, db)
    elif action == "inventory":

        await rc_market.inventory_screen(message, db)
    elif action == "gifts":

        await rc_market.gifts_screen(message, db)
    elif action == "games":
        await message.answer(
            f"{E.td('play')} <b>КАТАЛОГ ИГР</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Выбери игру или пиши: <code>Мины 10000 3</code>, <code>Краш 50000</code>",
            reply_markup=K.games_kb(),
        )
    elif action == "history":
        rows = await M.history(db, message.from_user.id, 10)
        lines = [f"{E.td('note')} <b>ИСТОРИЯ</b>", "━━━━━━━━━━━━━━━━━━━━"]
        for r in rows:
            profit = (r["payout"] - r["bet"]) if r["bet"] else r["payout"]
            lines.append(f"{'🟢' if profit >= 0 else '🔴'} {r['game']} — {M.short_num(profit)}")
        await message.answer("\n".join(lines), reply_markup=K.back())
    elif action == "checks":
        await message.answer(
            f"{E.td('envelope')} <b>ЧЕКОВАЯ КНИЖКА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Комиссия {config.CHECK_FEE_PERCENT}%. Чек можно активировать по коду или ссылке.",
            reply_markup=K.checks_kb(),
        )
    elif action == "exchange":
        await message.answer(await render_exchange(), reply_markup=K.back())
    elif action == "donate":

        await rc_misc.donate_screen(message, db)
    elif action == "earn":

        await rc_misc.earn_screen(message, db)
    elif action == "referral":
        await ref_answer(message)
    elif action == "warehouse":

        await rc_misc.warehouse_screen(message, db)
    elif action == "santa":

        await rc_misc.santa_screen(message, db)
    elif action == "bonus":

        await rc_misc.bonus_screen(message, db)
    return True


async def render_exchange() -> str:
    return (
        f"{E.td('exchange')} <b>ОБМЕННИК</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Курс: <b>{config.STAR_RATE['stars']} звёзд = {M.short_num(config.STAR_RATE['coin'])} rC</b>\n"
        f"Новогодний курс: <b>{config.NEW_YEAR_STAR_RATE['stars']} звёзд = "
        f"{M.short_num(config.NEW_YEAR_STAR_RATE['coin'])} rC</b>\n\n"
        "Обмен выполняется в разделе «Донат»."
    )


# ---------------------------------------------------------------------------
# Дать: rCoin или NFT
# ---------------------------------------------------------------------------
async def start_give(message: Message, db, state: FSMContext, tail: list[str]) -> None:
    target_id = None
    amount = None
    reply = message.reply_to_message
    if reply and reply.from_user:
        target_id = reply.from_user.id
    for token in tail:
        if token.startswith("@") and target_id is None:
            row = await db.execute(
                "SELECT id FROM rc_users WHERE LOWER(username)=?", (token[1:].lower(),)
            )
            found = await row.fetchone()
            if found:
                target_id = found[0]
        elif token.isdigit() and amount is None:
            amount = int(token)
        elif parse_amount(token) and amount is None:
            amount = parse_amount(token)
    if amount is None or amount <= 0:
        await state.update_data(give_target=target_id)
        await state.set_state(CoreFSM.give_amount)
        return await message.answer(
            f"{E.td('money_tear')} <b>ПЕРЕДАЧА rCoin</b>\n\n"
            f"Кому: {'указан' if target_id else 'ответь на сообщение или укажи @username'}\n"
            "Напиши сумму (например <code>50000</code> или <code>1kk</code>)."
        )
    if not target_id:
        return await message.answer(
            f"{E.td('cross')} Ответь на сообщение получателя или укажи <code>@username</code>."
        )
    await do_give(message, db, target_id, amount, message)


@router_rc_core.message(CoreFSM.give_amount)
async def give_amount_step(message: Message, db, state: FSMContext):
    amount = parse_amount(message.text)
    data = await state.get_data()
    await state.clear()
    target_id = data.get("give_target") or (
        message.reply_to_message.from_user.id if message.reply_to_message else None
    )
    if not amount or not target_id:
        return await message.answer(f"{E.td('cross')} Не понял сумму или получателя.")
    await do_give(message, db, target_id, amount, message)


async def do_give(message: Message, db, target_id: int, amount: int, origin: Message) -> None:
    sender = await M.get_user(db, message.from_user.id)
    if sender.balance < amount:
        return await message.answer(f"{E.td('cross')} Недостаточно средств: у тебя {M.short_num(sender.balance)}")
    target = await M.get_user(db, target_id)
    if not target:
        return await message.answer(f"{E.td('cross')} Получатель не пользовался ботом.")
    ok = await M.transfer(db, message.from_user.id, target_id, amount)
    if not ok:
        return await message.answer(f"{E.td('cross')} Перевод не выполнен.")
    path = nft_image.render_transfer(amount, sender.name, target.name)
    caption = (
        f"{E.td('money_launch')} <b>ПЕРЕВОД rCoin</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Сумма: <b>{M.full_num(amount)}</b> rC\n"
        f"{E.td('arrow')} От: {sender.mention}\n"
        f"{E.td('heart')} Кому: {target.mention}"
    )
    await message.answer_photo(path, caption=caption, reply_to_message_id=origin.message_id)


def register_text_router(dp) -> None:
    """Эвристика русских команд: подключается в bot.py после остальных роутеров."""
    from aiogram import F as _F
    from aiogram.types import Message as _Msg

    @dp.message(_F.text)
    async def ru_commands(message: _Msg, db, state: FSMContext):
        # если пользователь в FSM-состоянии (ввод суммы, имени и т.п.) — не трогаем
        if await state.get_state() is not None:
            return
        try:
            handled = await parse_ru_command(message, db, state)
        except Exception:
            handled = False
        if not handled and message.chat.type == "private":
            await message.answer(config.MSG_UNKNOWN_CMD)

# =============================== handlers/rc_games.py ================
# file: handlers/rc_games.py
"""Все игры «Рубин Бот»: Dice-анимации, Мины, Лесенка, Краш и 17 текстовых."""

import asyncio
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


router_rc_games = Router(name="rc_games")


class GameFSM(StatesGroup):
    custom_bet = State()


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
def _edit(message: Message, text: str, markup=None) -> None:
    try:
        message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


async def _user(call: CallbackQuery, db) -> M.RCUser:
    return await M.get_user(db, call.from_user.id)


async def _check_bet(call: CallbackQuery, db, bet: int) -> bool:
    user = await _user(call, db)
    if bet < config.MIN_BET:
        await call.answer(f"Минимальная ставка — {M.short_num(config.MIN_BET)}", show_alert=True)
        return False
    if bet > config.MAX_BET:
        await call.answer(f"Максимум — {M.short_num(config.MAX_BET)}", show_alert=True)
        return False
    if user.balance < bet:
        await call.answer(f"Не хватает: на балансе {M.short_num(user.balance)}", show_alert=True)
        return False
    return True


def _result_block(title: str, detail: str, bet: int, payout: int, balance: int) -> str:
    profit = payout - bet
    icon = E.td("check") if payout > bet else (E.td("hundred") if payout == bet else E.td("cross"))
    lines = [
        f"{icon} <b>{title}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        detail,
        f"{E.td('money_tear')} Ставка: <b>{M.short_num(bet)}</b>",
    ]
    if payout:
        lines.append(f"{E.td('cash')} Выплата: <b>{M.short_num(payout)}</b>")
        lines.append(f"{E.td('up') if profit >= 0 else E.td('down')} "
                     f"Итог: <b>{'+' if profit >= 0 else ''}{M.short_num(profit)}</b>")
    else:
        lines.append(f"{E.td('skull')} Ставка сгорела")
    lines.append(f"{E.td('gem')} Баланс: <b>{M.short_num(balance)}</b>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Каталог
# ---------------------------------------------------------------------------
@router_rc_games.callback_query(F.data == "m:games")
async def games_menu(call: CallbackQuery, db):
    user = await _user(call, db)
    _edit(
        call.message,
        f"{E.td('play')} <b>КАТАЛОГ ИГР</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>\n\n"
        "<code>Мины 10000 3</code> · <code>Краш 50к</code> · <code>Лесенка 10к</code>",
        K.games_kb(),
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Dice-игры (Telegram-анимация)
# ---------------------------------------------------------------------------
@router_rc_games.callback_query(F.data.startswith("g:dice:"))
async def dice_choose(call: CallbackQuery, db):
    game = call.data.split(":")[2]
    conf = config.DICE_GAMES[game]
    _edit(
        call.message,
        f"{conf['emoji']} <b>{conf['title'].upper()}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Выигрыш при: <b>{', '.join(map(str, sorted(conf['win_at'])))}</b>\n"
        f"Множитель: <b>×{conf['mult']}</b>\n\n"
        "Выбери ставку 👇",
        K.bet_kb(f"dice_{game}"),
    )
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("bet:dice_"))
async def dice_play(call: CallbackQuery, db, bot):
    game = call.data.split("_", 1)[1]
    bet = int(call.data.split(":")[2])
    if not await _check_bet(call, db, bet):
        return
    if not await M.debit(db, call.from_user.id, bet):
        return await call.answer("Списание не удалось", show_alert=True)
    conf = config.DICE_GAMES[game]
    msg = await call.message.answer_dice(emoji=conf["emoji"])
    await asyncio.sleep(3.2)
    value = msg.dice.value if msg.dice else 0
    win = value in conf["win_at"]
    payout = int(bet * conf["mult"]) if win else 0
    await M.credit_game(db, call.from_user.id, f"dice:{game}", bet, payout, f"value={value}")
    user = await _user(call, db)
    detail = f"{conf['emoji']} Выпало: <b>{value}</b> · нужно {', '.join(map(str, sorted(conf['win_at'])))}"
    await call.message.answer(
        _result_block(conf["title"].upper(), detail, bet, payout, user.balance),
        reply_markup=K.kbd([K._btn("🔁 Ещё", f"g:dice:{game}", style="success")],
                           [K._btn("🏠 Меню", "m:back")]),
    )
    await call.answer("Победа!" if win else "Не повезло")


# ---------------------------------------------------------------------------
# Мины
# ---------------------------------------------------------------------------
@router_rc_games.callback_query(F.data == "g:mines")
async def mines_menu(call: CallbackQuery, db):
    _edit(
        call.message,
        f"{E.td('skull')} <b>МИНЫ 5×5</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Открывай безопасные клетки — множитель растёт.\n"
        "Наткнулся на мину — ставка сгорает.\n\n"
        "Выбери ставку, затем количество мин:",
        K.bet_kb("mines"),
    )
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("bet:mines"))
async def mines_bets(call: CallbackQuery, db):
    bet = int(call.data.split(":")[2])
    rows = []
    for mines_count in (1, 3, 5, 10, 15, 24):
        rows.append([K._btn(f"{mines_count} мин · ×{G.mines_multiplier(1, mines_count):.2f}",
                            f"mn:new:{bet}:{mines_count}",
                            style="success" if mines_count == 3 else None)])
    rows.append([K._btn("◀️ Назад", "g:mines")])
    _edit(call.message,
          f"{E.td('skull')} Ставка: <b>{M.short_num(bet)}</b>\nСколько мин спрятать?",
          K.kb(*rows))
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("mn:new:"))
async def mines_new(call: CallbackQuery, db):
    _, _, bet_s, mines_s = call.data.split(":")
    bet, mines_count = int(bet_s), int(mines_s)
    if not await _check_bet(call, db, bet):
        return
    if not await M.debit(db, call.from_user.id, bet):
        return await call.answer("Списание не удалось", show_alert=True)
    game = G.MinesRound.new(bet, mines_count)
    sid = f"{call.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": call.from_user.id, "game": game, "kind": "mines"})
    _edit(call.message, mines_text(game), K.mines_kb(game.view(), sid, bool(game.opened)))
    await call.answer("Поле готово")


def mines_text(game: G.MinesRound) -> str:
    return (
        f"{E.td('skull')} <b>МИНЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Ставка: <b>{M.short_num(game.bet)}</b>\n"
        f"💣 Мин: <b>{game.mines}</b> · Открыто: <b>{len(game.opened)}</b>\n"
        f"{E.td('up')} Множитель: <b>×{game.multiplier():.2f}</b>\n"
        f"{E.td('arrow')} Следующий: <b>×{G.mines_next(len(game.opened), game.mines):.2f}</b>\n"
        f"{E.td('cash')} Кэшаут: <b>{M.short_num(game.payout())}</b>"
    )


@router_rc_games.callback_query(F.data.startswith("mn:"))
async def mines_open(call: CallbackQuery, db):
    parts = call.data.split(":")
    if len(parts) < 3 or parts[1] == "new":
        return
    sid, idx = parts[1], int(parts[2])

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    game: G.MinesRound = data["game"]
    state = game.open(idx)
    if state == "noop":
        return await call.answer("Клетка уже открыта")
    if state == "boom":
        await M.credit_game(db, call.from_user.id, "mines", game.bet, 0, "мина")
        user = await _user(call, db)
        _edit(call.message,
              _result_block("МИНА 💥", f"Открыто клеток: <b>{len(game.opened) - 1}</b>",
                            game.bet, 0, user.balance),
              K.mines_kb(game.view(), sid, False))
        sessions.drop(sid)
        return await call.answer("Бум!")
    if state == "all":
        payout = game.payout()
        await M.credit_game(db, call.from_user.id, "mines", game.bet, payout, "все клетки")
        user = await _user(call, db)
        _edit(call.message,
              _result_block("ПОЛЕ ОЧИЩЕНО", f"×{game.multiplier():.2f}", game.bet, payout, user.balance),
              K.mines_kb(game.view(), sid, False))
        sessions.drop(sid)
        return await call.answer("Джекпот!")
    _edit(call.message, mines_text(game), K.mines_kb(game.view(), sid, True))
    await call.answer(f"Безопасно · ×{game.multiplier():.2f}")


@router_rc_games.callback_query(F.data.startswith("mnc:"))
async def mines_cash(call: CallbackQuery, db):
    sid = call.data.split(":")[1]

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    game: G.MinesRound = data["game"]
    if not game.opened:
        return await call.answer("Открой хотя бы одну клетку")
    game.cashed = True
    payout = game.payout()
    await M.credit_game(db, call.from_user.id, "mines", game.bet, payout, "кэшаут")
    user = await _user(call, db)
    _edit(call.message,
          _result_block("КЭШАУТ", f"×{game.multiplier():.2f} за {len(game.opened)} клеток",
                        game.bet, payout, user.balance),
          K.mines_kb(game.view(), sid, False))
    sessions.drop(sid)
    await call.answer("Забрано")


# ---------------------------------------------------------------------------
# Лесенка
# ---------------------------------------------------------------------------
@router_rc_games.callback_query(F.data == "g:ladder")
async def ladder_menu(call: CallbackQuery, db):
    _edit(call.message,
          f"🪜 <b>ЛЕСЕНКА</b>\n━━━━━━━━━━━━━━━━━━━━\n"
          f"Шесть уровней, на каждом есть шанс сорваться.\n"
          f"Множитель растёт с высотой. До финиша: <b>×{G.ladder_multiplier(6):.2f}</b>\n\n"
          "Выбери ставку:", K.bet_kb("ladder"))
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("bet:ladder"))
async def ladder_bets(call: CallbackQuery, db):
    bet = int(call.data.split(":")[2])
    if not await _check_bet(call, db, bet):
        return
    if not await M.debit(db, call.from_user.id, bet):
        return await call.answer("Списание не удалось", show_alert=True)
    game = G.LadderRound.new(bet)
    sid = f"{call.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": call.from_user.id, "game": game, "kind": "ladder"})
    _edit(call.message, ladder_text(game), K.ladder_kb(0, sid, True))
    await call.answer("Старт")


def ladder_text(game: G.LadderRound) -> str:
    return (
        f"🪜 <b>ЛЕСЕНКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Ставка: <b>{M.short_num(game.bet)}</b>\n"
        f"{E.td('up')} Уровень: <b>{game.level}</b> / {G.LADDER_LEVELS}\n"
        f"📈 Множитель: <b>×{game.multiplier():.2f}</b>\n"
        f"{E.td('cash')} Кэшаут: <b>{M.short_num(game.payout())}</b>\n\n"
        f"{''.join(game.trail) or '🪜 Готов к подъёму'}"
    )


@router_rc_games.callback_query(F.data.startswith("ld:"))
async def ladder_step(call: CallbackQuery, db):
    parts = call.data.split(":")
    if len(parts) < 3:
        return
    sid = parts[1]

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    game: G.LadderRound = data["game"]
    result = game.step()
    if result == "noop":
        return await call.answer("Игра окончена")
    if result == "fall":
        await M.credit_game(db, call.from_user.id, "ladder", game.bet, 0, "сорвался")
        user = await _user(call, db)
        _edit(call.message,
              _result_block("СОРВАЛСЯ", f"Уровень {game.level}", game.bet, 0, user.balance),
              K.ladder_kb(game.level, sid, False))
        sessions.drop(sid)
        return await call.answer("Сорвался!")
    if result == "top":
        payout = game.payout()
        await M.credit_game(db, call.from_user.id, "ladder", game.bet, payout, "финиш")
        user = await _user(call, db)
        _edit(call.message,
              _result_block("ФИНИШ", f"×{game.multiplier():.2f}", game.bet, payout, user.balance),
              K.ladder_kb(game.level, sid, False))
        sessions.drop(sid)
        return await call.answer("Дошёл до верха!")
    _edit(call.message, ladder_text(game), K.ladder_kb(game.level, sid, True))
    await call.answer(f"Уровень {game.level}")


@router_rc_games.callback_query(F.data.startswith("ldc:"))
async def ladder_cash(call: CallbackQuery, db):
    sid = call.data.split(":")[1]

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    game: G.LadderRound = data["game"]
    if game.level == 0:
        return await call.answer("Поднимись хотя бы на уровень")
    game.cashed = True
    payout = game.payout()
    await M.credit_game(db, call.from_user.id, "ladder", game.bet, payout, "кэшаут")
    user = await _user(call, db)
    _edit(call.message,
          _result_block("КЭШАУТ", f"×{game.multiplier():.2f}", game.bet, payout, user.balance),
          K.ladder_kb(game.level, sid, False))
    sessions.drop(sid)
    await call.answer("Забрано")


# ---------------------------------------------------------------------------
# Краш
# ---------------------------------------------------------------------------
@router_rc_games.callback_query(F.data == "g:crash")
async def crash_menu(call: CallbackQuery, db):
    _edit(call.message,
          f"{E.td('up')} <b>КРАШ</b>\n━━━━━━━━━━━━━━━━━━━━\n"
          "Множитель растёт, пока ракета не взорвётся.\n"
          "Жми «Забрать» вовремя.\n\nВыбери ставку:", K.bet_kb("crash"))
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("bet:crash"))
async def crash_bets(call: CallbackQuery, db):
    bet = int(call.data.split(":")[2])
    if not await _check_bet(call, db, bet):
        return
    if not await M.debit(db, call.from_user.id, bet):
        return await call.answer("Списание не удалось", show_alert=True)
    sid = f"{call.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": call.from_user.id, "kind": "crash", "bet": bet,
                       "peak": G.crash_peak(), "start": time.time()})
    _edit(call.message,
          f"{E.td('up')} <b>КРАШ</b>\n"
          "━━━━━━━━━━━━━━━━━━━━\n"
          f"{E.td('money_tear')} Ставка: <b>{M.short_num(bet)}</b>\n"
          "📈 ×<b>1.00</b> · жми «Расти» и забирай вовремя",
          K.crash_kb(sid))
    await call.answer("Взлёт!")


@router_rc_games.callback_query(F.data.startswith("cr:tick:"))
async def crash_tick(call: CallbackQuery, db):
    sid = call.data.split(":")[2]

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    elapsed = time.time() - data["start"]
    value = G.crash_value(elapsed)
    if value >= data["peak"]:
        await M.credit_game(db, call.from_user.id, "crash", data["bet"], 0, f"×{value}")
        user = await _user(call, db)
        sessions.drop(sid)
        _edit(call.message,
              _result_block("КРАШ", f"Взрыв на ×{data['peak']:.2f}", data["bet"], 0, user.balance),
              K.kbd([K._btn("🔄 Новая", "g:crash", style="success")],
                    [K._btn("🏠 Меню", "m:back")]))
        return await call.answer("Взрыв!")
    bar = "🟩" * min(int(value * 2), 20)
    _edit(call.message,
          f"{E.td('up')} <b>КРАШ</b>\n"
          "━━━━━━━━━━━━━━━━━━━━\n"
          f"{E.td('money_tear')} Ставка: <b>{M.short_num(data['bet'])}</b>\n"
          f"📈 Множитель: <b>×{value:.2f}</b>\n"
          f"{E.td('cash')} Потенциал: <b>{M.short_num(int(data['bet'] * value))}</b>\n"
          f"{bar}",
          K.crash_kb(sid))
    await call.answer(f"×{value:.2f}")


@router_rc_games.callback_query(F.data.startswith("cr:cash:"))
async def crash_cash(call: CallbackQuery, db):
    sid = call.data.split(":")[2]

    data = sessions.get(sid)
    if not data or data["uid"] != call.from_user.id:
        return await call.answer("Игра не активна", show_alert=True)
    elapsed = time.time() - data["start"]
    value = min(G.crash_value(elapsed), data["peak"])
    payout = int(data["bet"] * value)
    await M.credit_game(db, call.from_user.id, "crash", data["bet"], payout, f"кэшаут ×{value:.2f}")
    user = await _user(call, db)
    sessions.drop(sid)
    _edit(call.message,
          _result_block("ЗАБРАНО", f"Множитель <b>×{value:.2f}</b>", data["bet"], payout, user.balance),
          K.kbd([K._btn("🔄 Новая", "g:crash", style="success")],
                [K._btn("🏠 Меню", "m:back")]))
    await call.answer("Забрано")


# ---------------------------------------------------------------------------
# Текстовые игры
# ---------------------------------------------------------------------------
SIMPLE_GAMES = {
    "coin": ("🪙", "Монетка", [("Орёл", "heads"), ("Решка", "tails")]),
    "roulette": ("🎡", "Рулетка", [("🔴 Красное", "red"), ("⚫️ Чёрное", "black"),
                                   ("🟢 Зеро", "green")]),
    "rroulette": ("🔫", "Русская рулетка", [(f"{i}", str(i)) for i in range(1, 7)]),
    "fortune": ("🌠", "Фортуна", [("1", "0"), ("2", "1"), ("3", "2")]),
    "chest": ("🎁", "Сундук", [("1", "0"), ("2", "1"), ("3", "2"), ("4", "3"), ("5", "4")]),
    "ball": ("🔮", "Шар", [(str(i + 1), str(i)) for i in range(12)]),
    "fishing": ("🎣", "Рыбалка", [("Отмель", "0"), ("Глубина", "1"), ("Омут", "2")]),
    "sketch": ("🎨", "Скетч", [(str(i), str(i)) for i in range(1, 7)]),
    "diamonds": ("💎", "Алмазы", [("1", "0"), ("2", "1"), ("3", "2"), ("4", "3")]),
    "tower": ("🏗", "Башня", [(str(i), str(i)) for i in range(1, 9)]),
    "gold": ("🪙", "Золото", [("Жила 1", "0"), ("Жила 2", "1"), ("Жила 3", "2")]),
    "quack": ("🐸", "Квак", [("1", "0"), ("2", "1"), ("3", "2"), ("4", "3"), ("5", "4")]),
    "hilo": ("↕️", "HiLo", [("Меньше 8", "low"), ("Больше 8", "high")]),
}


@router_rc_games.callback_query(F.data.startswith("g:") & ~F.data.startswith("g:dice"))
async def simple_menu(call: CallbackQuery, db):
    key = call.data.split(":")[1]
    if key not in SIMPLE_GAMES:
        return await call.answer("Игра недоступна", show_alert=True)
    icon, title, choices = SIMPLE_GAMES[key]
    user = await _user(call, db)
    _edit(call.message,
          f"{icon} <b>{title.upper()}</b>\n"
          "━━━━━━━━━━━━━━━━━━━━\n"
          f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>\n\n"
          "Выбери ставку:", K.bet_kb(key))
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("bet:") & ~F.data.startswith("bet:dice_"))
async def simple_bets(call: CallbackQuery, db):
    key = call.data.split(":")[1]
    bet = int(call.data.split(":")[2])
    if key not in SIMPLE_GAMES:
        return await call.answer("Игра недоступна", show_alert=True)
    icon, title, choices = SIMPLE_GAMES[key]
    if not await _check_bet(call, db, bet):
        return
    _edit(call.message,
          f"{icon} <b>{title.upper()}</b> · ставка <b>{M.short_num(bet)}</b>\n"
          "━━━━━━━━━━━━━━━━━━━━\nВыбери исход:",
          K.choices_kb(key, choices))
    # запоминаем ставку в сессии callback-данных
    call.message.bot  # noqa: B018
    await call.answer()


@router_rc_games.callback_query(F.data.startswith("s:"))
async def simple_play(call: CallbackQuery, db, state: FSMContext):
    _, key, value = call.data.split(":")
    data = await state.get_data()
    bet = data.get("bet") or 0
    if not bet:
        return await call.answer("Сначала выбери ставку", show_alert=True)
    if not await M.debit(db, call.from_user.id, bet):
        return await call.answer("Недостаточно средств", show_alert=True)
    if key == "coin":
        win, payout, detail = G.coin(bet, value)
    elif key == "roulette":
        win, payout, detail = G.roulette(bet, value)
    elif key == "rroulette":
        win, payout, detail = G.rroulette(bet, int(value))
    elif key == "fortune":
        win, payout, detail = G.fortune(bet, int(value))
    elif key == "chest":
        win, payout, detail = G.chest(bet, int(value))
    elif key == "ball":
        win, payout, detail = G.ball(bet, int(value))
    elif key == "fishing":
        win, payout, detail = G.fishing(bet, int(value))
    elif key == "sketch":
        win, payout, detail = G.sketch(bet, int(value))
    elif key == "diamonds":
        win, payout, detail = G.diamonds(bet, int(value))
    elif key == "tower":
        win, payout, detail = G.tower(bet, int(value))
    elif key == "gold":
        win, payout, detail = G.gold(bet, int(value))
    elif key == "quack":
        win, payout, detail = G.quack(bet, int(value))
    elif key == "hilo":
        win, payout, detail = G.hilo(bet, value)
    else:
        return await call.answer("Неизвестная игра", show_alert=True)
    await M.credit_game(db, call.from_user.id, key, bet, payout, detail)
    user = await _user(call, db)
    icon, title, _ = SIMPLE_GAMES[key]
    _edit(call.message,
          _result_block(f"{icon} {title.upper()}", detail, bet, payout, user.balance),
          K.kbd([K._btn("🔁 Ещё", f"g:{key}", style="success")],
                [K._btn("🏠 Меню", "m:back")]))
    await call.answer("Победа!" if win else "Не повезло")


@router_rc_games.callback_query(F.data.startswith("betcustom:"))
async def custom_bet_start(call: CallbackQuery, state: FSMContext):
    game = call.data.split(":")[1]
    await state.update_data(game=game)
    await state.set_state(GameFSM.custom_bet)
    _edit(call.message,
          f"{E.td('bulb')} <b>СВОЯ СТАВКА</b>\n\n"
          f"Напиши сумму: <code>50000</code>, <code>1kk</code>, <code>2.5kkk</code>\n"
          f"Минимум: {M.short_num(config.MIN_BET)}")
    await call.answer()


@router_rc_games.message(GameFSM.custom_bet)
async def custom_bet_value(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    amount = parse_amount(message.text)
    if not amount:
        return await message.answer(f"{E.td('cross')} Не понял сумму.")
    amount = max(config.MIN_BET, min(amount, config.MAX_BET))
    await state.update_data(bet=amount)
    game = data.get("game", "coin")
    if game in SIMPLE_GAMES:
        icon, title, choices = SIMPLE_GAMES[game]
        return await message.answer(
            f"{icon} <b>{title.upper()}</b> · ставка <b>{M.short_num(amount)}</b>\nВыбери исход:",
            reply_markup=K.choices_kb(game, choices),
        )
    await message.answer(
        f"{E.td('check')} Ставка <b>{M.short_num(amount)}</b> принята. "
        "Для 𝘥𝘪𝘤𝘦-игр выбери игру снова.",
        reply_markup=K.games_kb(),
    )


# ---------------------------------------------------------------------------
# Текстовые команды: Мины / Лесенка / Краш
# ---------------------------------------------------------------------------
async def start_mines_text(message: Message, db, args: list[str]) -> None:
    bet = parse_amount(args[0]) if args else None
    mines_count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
    if not bet:
        return await message.answer(
            f"{E.td('skull')} <b>МИНЫ</b>\n"
            "Формат: <code>Мины [ставка] [мин]</code>\n"
            "Пример: <code>Мины 50000 5</code>",
            reply_markup=K.bet_kb("mines"),
        )
    user = await M.get_user(db, message.from_user.id)
    if bet < config.MIN_BET or bet > config.MAX_BET:
        return await message.answer(f"{E.td('cross')} Ставка вне лимитов.")
    if user.balance < bet:
        return await message.answer(f"{E.td('cross')} Не хватает: {M.short_num(user.balance)}")
    if not await M.debit(db, message.from_user.id, bet):
        return await message.answer(f"{E.td('cross')} Списание не удалось.")
    game = G.MinesRound.new(bet, mines_count)
    sid = f"{message.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": message.from_user.id, "game": game, "kind": "mines"})
    await message.answer(mines_text(game), reply_markup=K.mines_kb(game.view(), sid, False))


async def start_ladder_text(message: Message, db, args: list[str]) -> None:
    bet = parse_amount(args[0]) if args else None
    if not bet:
        return await message.answer(f"{E.td('cross')} Формат: <code>Лесенка 100000</code>",
                                    reply_markup=K.bet_kb("ladder"))
    user = await M.get_user(db, message.from_user.id)
    if user.balance < bet:
        return await message.answer(f"{E.td('cross')} Не хватает средств.")
    if not await M.debit(db, message.from_user.id, bet):
        return await message.answer(f"{E.td('cross')} Списание не удалось.")
    game = G.LadderRound.new(bet)
    sid = f"{message.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": message.from_user.id, "game": game, "kind": "ladder"})
    await message.answer(ladder_text(game), reply_markup=K.ladder_kb(0, sid, True))


async def start_crash_text(message: Message, db, args: list[str]) -> None:
    bet = parse_amount(args[0]) if args else None
    if not bet:
        return await message.answer(f"{E.td('cross')} Формат: <code>Краш 100000</code>",
                                    reply_markup=K.bet_kb("crash"))
    user = await M.get_user(db, message.from_user.id)
    if user.balance < bet:
        return await message.answer(f"{E.td('cross')} Не хватает средств.")
    if not await M.debit(db, message.from_user.id, bet):
        return await message.answer(f"{E.td('cross')} Списание не удалось.")
    sid = f"{message.from_user.id}{int(time.time() * 1000) % 100000}"

    sessions.set(sid, {"uid": message.from_user.id, "kind": "crash", "bet": bet,
                       "peak": G.crash_peak(), "start": time.time()})
    await message.answer(
        f"{E.td('up')} <b>КРАШ</b>\nСтавка: <b>{M.short_num(bet)}</b>\n"
        "Жми «Расти» и забирай вовремя",
        reply_markup=K.crash_kb(sid),
    )

# =============================== handlers/rc_market.py ================
# file: handlers/rc_market.py
"""Маркет NFT, инвентарь, улучшение, привязка к балансу и передача с фото."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


router_rc_market = Router(name="rc_market")


class SendFSM(StatesGroup):
    username = State()


def _edit(message: Message, text: str, markup=None) -> None:
    try:
        message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


# ---------------------------------------------------------------------------
# Маркет
# ---------------------------------------------------------------------------
async def market_text(db, uid: int) -> str:
    user = await M.get_user(db, uid)
    return (
        f"{E.td('bag')} <b>МАРКЕТПЛЕЙС</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<blockquote>"
        "Покупай подарки с уникальным номером.\n"
        "Каждый предмет можно улучшить до более редкой коллекции.\n"
        "</blockquote>\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>\n"
        f"{E.td('money_eyes')} Общий объём инвентаря: <b>{M.short_num(await M.inventory_value(db, uid))}</b>"
    )


async def market_screen(message: Message, db) -> None:
    templates = await M.templates(db)
    await message.answer(await market_text(db, message.from_user.id),
                         reply_markup=K.market_kb(templates))


@router_rc_market.callback_query(F.data == "m:market")
async def cb_market(call: CallbackQuery, db):
    templates = await M.templates(db)
    _edit(call.message, await market_text(db, call.from_user.id), K.market_kb(templates))
    await call.answer()


@router_rc_market.callback_query(F.data.startswith("mk:view:"))
async def view_template(call: CallbackQuery, db):
    slug = call.data.split(":")[2]
    t = await M.template_by_slug(db, slug)
    if not t:
        return await call.answer("Подарок не найден", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    icon = config.RARITY_ICONS.get(t["rarity"], "⚪️")
    _edit(
        call.message,
        f"{t['model']} <b>{t['title']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{icon} Редкость: <b>{config.RARITY_NAMES.get(t['rarity'], t['rarity'])}</b>\n"
        f"{E.td('gem')} Цена: <b>{M.short_num(t['floor'])}</b> rC\n"
        f"{E.td('hundred')} Выпущено: <b>{fmt_minted(t)}</b>\n"
        f"{E.td('lock')} Следующий номер: <b>#{fmt_next(t)}</b>",
        K.market_item_kb(slug, t["floor"], user.balance),
    )
    await call.answer()


def fmt_minted(t) -> str:
    supply = t["supply"]
    minted = t["minted"]
    if supply:
        return f"{minted} / {supply}"
    return f"{minted} (не ограничено)"


def fmt_next(t) -> str:
    return str(t["minted"] + 1)


@router_rc_market.callback_query(F.data.startswith("mk:buy:"))
async def buy_template(call: CallbackQuery, db):
    slug = call.data.split(":")[2]
    t = await M.template_by_slug(db, slug)
    if not t:
        return await call.answer("Подарок не найден", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    if t["supply"] and t["minted"] >= t["supply"]:
        return await call.answer("Тираж закончился", show_alert=True)
    if user.balance < t["floor"]:
        return await call.answer(f"Не хватает {M.short_num(t['floor'] - user.balance)}", show_alert=True)
    if not await M.debit(db, call.from_user.id, t["floor"]):
        return await call.answer("Списание не удалось", show_alert=True)
    item_id = await M.mint(db, t["id"], call.from_user.id, t["floor"])
    item = await M.nft_item(db, item_id)
    path = nft_image.render_gift(
        title=item["title"], serial=item["serial"], rarity=item["rarity"],
        model=item["model"], bg=item["bg"],
    )
    caption = (
        f"{E.td('gift')} <b>ПОДАРОК В ИНВЕНТАРЕ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{item['model']} <b>{item['title']}</b> #{item['serial']}\n"
        f"{config.RARITY_ICONS.get(item['rarity'])} {config.RARITY_NAMES.get(item['rarity'])}\n"
        f"{E.td('money_tear')} Оплачено: <b>{M.short_num(t['floor'])}</b>"
    )
    await call.message.answer_photo(
        path, caption=caption,
        reply_markup=K.kbd(
            [K._btn(f"{E.td('up')} Улучшить", f"inv:upgrade:{item_id}", style="success"),
             K._btn("📦 Инвентарь", "m:inventory")],
        ),
    )
    await call.message.answer("Куплено!")
    await call.answer(f"#{item['serial']} твой!")


# ---------------------------------------------------------------------------
# Инвентарь
# ---------------------------------------------------------------------------
async def inventory_text(db, uid: int) -> str:
    items = await M.inventory(db, uid)
    total = await M.inventory_value(db, uid)
    lines = [
        f"{E.td('gift')} <b>ИНВЕНТАРЬ</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{E.td('money_eyes')} Суммарная стоимость: <b>{M.short_num(total)}</b> rC",
        f"{E.td('hundred')} Предметов: <b>{len(items)}</b>",
        "",
    ]
    if not items:
        lines.append("Пока пусто. Начинай с маркета!")
    else:
        for it in items:
            lines.append(
                f"{it['model']} <b>{it['title']}</b> #{it['serial']} · "
                f"{config.RARITY_ICONS.get(it['rarity'])} {M.short_num(it['price'])}"
            )
    return "\n".join(lines)


@router_rc_market.callback_query(F.data == "m:inventory")
async def cb_inventory(call: CallbackQuery, db):
    items = await M.inventory(db, call.from_user.id)
    _edit(call.message, await inventory_text(db, call.from_user.id), K.inventory_kb(items))
    await call.answer()


@router_rc_market.callback_query(F.data == "inv:bind")
async def bind_value(call: CallbackQuery, db):
    total = await M.inventory_value(db, call.from_user.id)
    user = await M.get_user(db, call.from_user.id)
    await call.answer(
        f"Стоимость NFT: {M.short_num(total)} rC\nБаланс: {M.short_num(user.balance)} rC",
        show_alert=True,
    )


@router_rc_market.callback_query(F.data.startswith("inv:open:"))
async def open_item(call: CallbackQuery, db):
    item_id = int(call.data.split(":")[2])
    item = await M.nft_item(db, item_id)
    if not item or item["owner_id"] != call.from_user.id:
        return await call.answer("Предмет не найден", show_alert=True)
    fee = config.UPGRADE_FEE.get(item["rarity"], 0)
    _edit(
        call.message,
        f"{item['model']} <b>{item['title']}</b> #{item['serial']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{config.RARITY_ICONS.get(item['rarity'])} {config.RARITY_NAMES.get(item['rarity'])}\n"
        f"{E.td('gem')} Стоимость: <b>{M.short_num(item['price'])}</b>\n"
        f"{E.td('up')} Шанс улучшения: <b>{config.UPGRADE_CHANCE[config.RARITY_ORDER.index(item['rarity'])] * 100:.0f}%</b>\n"
        f"{E.td('money_wind')} Стоимость улучшения: <b>{M.short_num(fee)}</b>",
        K.nft_item_kb(item_id, item["rarity"], fee),
    )
    await call.answer()


@router_rc_market.callback_query(F.data.startswith("inv:image:"))
async def send_image(call: CallbackQuery, db):
    item_id = int(call.data.split(":")[2])
    item = await M.nft_item(db, item_id)
    if not item or item["owner_id"] != call.from_user.id:
        return await call.answer("Предмет не найден", show_alert=True)
    path = nft_image.render_gift(
        title=item["title"], serial=item["serial"], rarity=item["rarity"],
        model=item["model"], bg=item["bg"],
    )
    await call.message.answer_photo(
        path,
        caption=f"{item['model']} <b>{item['title']}</b> #{item['serial']}",
        reply_to_message_id=call.message.message_id,
    )
    await call.answer("Фото отправлено")


@router_rc_market.callback_query(F.data.startswith("inv:upgrade:"))
async def upgrade_item(call: CallbackQuery, db):
    item_id = int(call.data.split(":")[2])
    item = await M.nft_item(db, item_id)
    if not item or item["owner_id"] != call.from_user.id:
        return await call.answer("Предмет не найден", show_alert=True)
    if item["rarity"] == "mythic":
        return await call.answer("Мифическую редкость улучшить нельзя", show_alert=True)
    fee = config.UPGRADE_FEE.get(item["rarity"], 0)
    result = await M.upgrade_nft(db, item_id, call.from_user.id, fee)
    if not result["ok"] and result.get("reason") == "no_money":
        return await call.answer(f"Нужно {M.short_num(fee)} rC", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    if result["ok"]:
        new_item = await M.nft_item(db, result["item_id"]) if result.get("item_id") else None
        path = nft_image.render_gift(
            title=result["title"], serial=new_item["serial"] if new_item else 1,
            rarity=result["rarity"], model=result["model"],
        )
        await call.message.answer_photo(
            path,
            caption=(
                f"{E.td('champagne')} <b>УЛУЧШЕНИЕ УДАЛОСЬ!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"{result['model']} <b>{result['title']}</b>\n"
                f"{config.RARITY_ICONS.get(result['rarity'])} "
                f"{config.RARITY_NAMES.get(result['rarity'])}\n"
                f"{E.td('money_tear')} Потрачено: <b>{M.short_num(fee)}</b>\n"
                f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>"
            ),
            reply_to_message_id=call.message.message_id,
        )
        await call.answer("Улучшено!")
    else:
        await call.message.answer(
            f"{E.td('skull')} <b>УЛУЧШЕНИЕ НЕ УДАЛОСЬ</b>\n"
            f"{item['model']} {item['title']} #{item['serial']} сгорел.\n"
            f"{E.td('down')} Потрачено: <b>{M.short_num(fee)}</b> rC\n"
            f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>",
            reply_to_message_id=call.message.message_id,
        )
        await call.answer("Сгорел")
    items = await M.inventory(db, call.from_user.id)
    try:
        await call.message.edit_text(await inventory_text(db, call.from_user.id),
                                     reply_markup=K.inventory_kb(items))
    except TelegramBadRequest:
        pass


# ---------------------------------------------------------------------------
# Подарить NFT (с картинкой и цитатой)
# ---------------------------------------------------------------------------
@router_rc_market.callback_query(F.data.startswith("inv:give:"))
async def give_start(call: CallbackQuery, db, state: FSMContext):
    item_id = int(call.data.split(":")[2])
    item = await M.nft_item(db, item_id)
    if not item or item["owner_id"] != call.from_user.id:
        return await call.answer("Предмет не найден", show_alert=True)
    await state.update_data(item_id=item_id, msg_id=call.message.message_id)
    await state.set_state(SendFSM.username)
    _edit(call.message,
          f"{E.td('gift')} Кому подарить «{item['title']} #{item['serial']}»?\n\n"
          f"Отправь <code>@username</code> или ID. Или просто ответь на сообщение командой "
          f"<code>Дать @username</code>.")
    await call.answer()


@router_rc_market.message(SendFSM.username)
async def give_apply(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    raw = (message.text or "").strip().lstrip("@")
    target = None
    if raw.isdigit():
        target = await M.get_user(db, int(raw))
    else:
        async with db.execute("SELECT * FROM rc_users WHERE LOWER(username)=?", (raw.lower(),)) as cur:
            row = await cur.fetchone()
        target = M.RCUser.from_row(row) if row else None
    if not target:
        return await message.answer(f"{E.td('cross')} Получатель не найден.")
    item_id = data.get("item_id")
    ok = await M.nft_transfer(db, item_id, message.from_user.id, target.id)
    if not ok:
        return await message.answer(f"{E.td('cross')} Передача не удалась.")
    item = await M.nft_item(db, item_id)
    path = nft_image.render_gift(
        title=item["title"], serial=item["serial"], rarity=item["rarity"],
        model=item["model"], bg=item["bg"],
    )
    caption = (
        f"{E.td('gift')} <b>ПОДАРОК ПЕРЕДАН</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{item['model']} <b>{item['title']}</b> #{item['serial']}\n"
        f"{E.td('arrow')} Кому: {target.mention}"
    )
    await message.answer_photo(path, caption=caption,
                               reply_to_message_id=message.message_id)
    try:
        await message.bot.send_message(
            target.id,
            f"{E.td('gift')} Тебе подарок от {message.from_user.first_name}!\n"
            f"{item['model']} <b>{item['title']}</b> #{item['serial']}",
            reply_markup=K.kbd([K._btn("📦 Инвентарь", "m:inventory", style="success")]),
        )
    except Exception:
        pass


@router_rc_market.callback_query(F.data == "m:gifts")
async def gifts_screen(call: CallbackQuery, db):
    await cb_market(call, db)

# =============================== handlers/rc_lottery.py ================
# file: handlers/rc_lottery.py
"""Лотерея, билеты, кейсы и чековая книжка."""

import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


router_rc_lottery = Router(name="rc_lottery")


class CheckFSM(StatesGroup):
    amount = State()
    claims = State()
    redeem = State()


def _edit(message: Message, text: str, markup=None) -> None:
    try:
        message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


# ---------------------------------------------------------------------------
# Лотерея
# ---------------------------------------------------------------------------
def lottery_text(balance: int) -> str:
    return (
        f"{E.td('balloon')} <b>ЛОТЕРЕЯ «РУБИН-6/45»</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<blockquote>"
        f"6 чисел из 45. Билет — {M.short_num(config.DEFAULT_TICKET_PRICE)} rC.\n"
        f"6 совпадений — джекпот {M.short_num(config.LOTTERY_JACKPOT)}.\n"
        "5 совпадений — ×20 от билета, 4 — ×4."
        "</blockquote>\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(balance)}</b>"
    )


async def lottery_screen(message: Message, db) -> None:
    user = await M.get_user(db, message.from_user.id)
    await message.answer(lottery_text(user.balance), reply_markup=K.lottery_kb(config.DEFAULT_TICKET_PRICE))


@router_rc_lottery.callback_query(F.data == "m:lottery")
async def cb_lottery(call: CallbackQuery, db):
    user = await M.get_user(db, call.from_user.id)
    _edit(call.message, lottery_text(user.balance), K.lottery_kb(config.DEFAULT_TICKET_PRICE))
    await call.answer()


@router_rc_lottery.callback_query(F.data == "lot:buy")
async def buy_ticket(call: CallbackQuery, db):
    import random

    numbers = sorted(random.sample(range(1, config.LOTTERY_MAX + 1), config.LOTTERY_PICK))
    ok = await M.buy_ticket(db, call.from_user.id, numbers, config.DEFAULT_TICKET_PRICE)
    if not ok:
        return await call.answer("Недостаточно средств", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    _edit(
        call.message,
        f"{E.td('check')} <b>БИЛЕТ КУПЛЕН</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟 Числа: <code>{' · '.join(map(str, numbers))}</code>\n"
        f"{E.td('money_tear')} Стоимость: <b>{M.short_num(config.DEFAULT_TICKET_PRICE)}</b>\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>",
        K.kbd([K._btn("🎟 Ещё билет", "lot:buy", style="success")],
              [K._btn("◀️ Лотерея", "m:lottery")]),
    )
    await call.answer("Билет куплен!")


@router_rc_lottery.callback_query(F.data == "lot:draw")
async def draw(call: CallbackQuery, db):
    result = await M.draw_lottery(db)
    if not result.get("ok"):
        return await call.answer("Нет билетов для розыгрыша", show_alert=True)
    _edit(
        call.message,
        f"{E.td('balloon')} <b>РОЗЫГРЫШ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟 Числа: <code>{' · '.join(map(str, result['numbers']))}</code>\n"
        f"{E.td('check')} Победителей: <b>{result['winners']}</b>\n"
        f"{E.td('money_tear')} Выплачено: <b>{M.short_num(result['payout'])}</b>\n"
        f"{E.td('hundred')} Билетов: <b>{result['tickets']}</b>",
        K.back("m:lottery"),
    )
    await call.answer("Розыгрыш проведён")


@router_rc_lottery.callback_query(F.data == "lot:mine")
async def mine_tickets(call: CallbackQuery, db):
    async with db.execute(
        "SELECT numbers, draw_id FROM rc_lottery_tickets WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (call.from_user.id,),
    ) as cur:
        rows = list(await cur.fetchall())
    if not rows:
        return await call.answer("У тебя нет билетов", show_alert=True)
    lines = [f"🎟 <b>МОИ БИЛЕТЫ</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for r in rows:
        state = "участвует" if r["draw_id"] is None else f"тираж #{r['draw_id']}"
        lines.append(f"<code>{r['numbers']}</code> — {state}")
    _edit(call.message, "\n".join(lines), K.back("m:lottery"))
    await call.answer()


async def tickets_screen(message: Message, db) -> None:
    await message.answer(
        f"🎟 <b>БИЛЕТНАЯ ЛОТЕРЕЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Билет стоит <b>{M.short_num(config.DEFAULT_TICKET_PRICE)}</b> rC.\n"
        "Числа выбираются случайно, розыгрыш — общий на все билеты.",
        reply_markup=K.lottery_kb(config.DEFAULT_TICKET_PRICE),
    )


# ---------------------------------------------------------------------------
# Кейсы
# ---------------------------------------------------------------------------
async def cases_screen(message: Message, db) -> None:
    cases = await M.case_list(db)
    lines = [f"{E.td('cool')} <b>КЕЙСЫ</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for c in cases:
        lines.append(f"📦 <b>{c['title']}</b> — {M.short_num(c['price'])} rC")
    lines.append("\nОткрой кейс и забери случайный приз.")
    await message.answer("\n".join(lines), reply_markup=K.cases_kb(cases))


@router_rc_lottery.callback_query(F.data == "m:cases")
async def cb_cases(call: CallbackQuery, db):
    cases = await M.case_list(db)
    lines = [f"{E.td('cool')} <b>КЕЙСЫ</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for c in cases:
        lines.append(f"📦 <b>{c['title']}</b> — {M.short_num(c['price'])} rC")
    _edit(call.message, "\n".join(lines), K.cases_kb(cases))
    await call.answer()


@router_rc_lottery.callback_query(F.data.startswith("case:open:"))
async def open_case(call: CallbackQuery, db):
    case_id = int(call.data.split(":")[2])
    result = await M.open_case(db, call.from_user.id, case_id)
    if result is None:
        return await call.answer("Кейс не найден", show_alert=True)
    if result.get("error") == "no_money":
        return await call.answer("Недостаточно средств", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    _edit(
        call.message,
        f"📦 <b>{result['title']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('champagne')} Приз: <b>{M.short_num(result['prize'])}</b> rC\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>",
        K.kbd([K._btn("🔁 Ещё кейс", f"case:open:{case_id}", style="success")],
              [K._btn("◀️ Кейсы", "m:cases")]),
    )
    await call.answer(f"+{M.short_num(result['prize'])}")


# ---------------------------------------------------------------------------
# Чеки
# ---------------------------------------------------------------------------
@router_rc_lottery.callback_query(F.data == "chk:create")
async def check_create_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(CheckFSM.amount)
    _edit(call.message,
          f"{E.td('gift')} <b>СОЗДАНИЕ ЧЕКА</b>\n\n"
          f"Введи сумму rC (например <code>50000</code> или <code>1kk</code>):\n"
          f"Комиссия: {config.CHECK_FEE_PERCENT}%")
    await call.answer()


@router_rc_lottery.message(CheckFSM.amount)
async def check_amount(message: Message, db, state: FSMContext):
    amount = parse_amount(message.text)
    if not amount or amount < config.MIN_BET:
        return await message.answer(f"{E.td('cross')} Минимум {M.short_num(config.MIN_BET)} rC.")
    await state.update_data(amount=amount)
    await state.set_state(CheckFSM.claims)
    await message.answer("Сколько человек смогут активировать чек? (1–100)")


@router_rc_lottery.message(CheckFSM.claims)
async def check_claims(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    amount = data["amount"]
    raw = (message.text or "1").strip()
    claims = int(raw) if raw.isdigit() else 1
    claims = max(1, min(100, claims))
    fee = amount * claims * config.CHECK_FEE_PERCENT // 100
    total = amount * claims + fee
    if not await M.debit(db, message.from_user.id, total):
        return await message.answer(f"{E.td('cross')} Нужно {M.short_num(total)} rC с комиссией.")
    code = await M.create_check(db, message.from_user.id, amount, claims)
    link = f"https://t.me/{config.BOT_USERNAME}?start=check_{code}"
    await message.answer(
        f"{E.td('gift')} <b>ЧЕК СОЗДАН</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('money_tear')} Номинал: <b>{M.short_num(amount)}</b> rC\n"
        f"{E.td('hundred')} Активаций: <b>{claims}</b>\n"
        f"{E.td('money_eyes')} Комиссия: <b>{M.short_num(fee)}</b>\n\n"
        f"🔗 <code>{link}</code>",
        reply_markup=K.kbd([K._btn("📤 Поделиться", url=link, style="success")],
                           [K._btn("◀️ Назад", "m:back")]),
    )


@router_rc_lottery.callback_query(F.data == "chk:redeem")
async def redeem_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(CheckFSM.redeem)
    _edit(call.message, f"{E.td('gift')} Отправь код чека, например <code>RBABCD123456</code>")
    await call.answer()


@router_rc_lottery.message(CheckFSM.redeem)
async def redeem_apply(message: Message, db, state: FSMContext):
    await state.clear()
    ok, reason, amount = await M.redeem_check(db, message.text or "", message.from_user.id)
    if not ok:
        return await message.answer(f"{E.td('cross')} {reason}")
    user = await M.get_user(db, message.from_user.id)
    await message.answer(
        f"{E.td('champagne')} <b>ЧЕК АКТИВИРОВАН</b>\n"
        f"{E.td('money_tear')} Получено: <b>{M.short_num(amount)}</b> rC\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>",
        reply_markup=K.back(),
    )


@router_rc_lottery.callback_query(F.data.startswith("check:claim:"))
async def claim_from_link(call: CallbackQuery, db):
    code = call.data.split(":")[2]
    ok, reason, amount = await M.redeem_check(db, code, call.from_user.id)
    if not ok:
        return await call.answer(reason, show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    await call.message.answer(
        f"{E.td('champagne')} Чек на <b>{M.short_num(amount)}</b> rC активирован!\n"
        f"Баланс: <b>{M.short_num(user.balance)}</b>",
        reply_markup=K.back(),
    )
    await call.answer("Активировано")

# =============================== handlers/rc_misc.py ================
# file: handlers/rc_misc.py
"""Донат, статусы, заработок, обменник, зимний ивент (склад и Санта), бонусы."""

import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message


router_rc_misc = Router(name="rc_misc")


def _edit(message: Message, text: str, markup=None) -> None:
    try:
        message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


def status_badge(key: str) -> str:
    item = config.STATUSES.get(key)
    if not item:
        return ""
    cid, title = item
    if cid:
        return f'<tg-emoji emoji-id="{cid}">{title}</tg-emoji>'
    return title


# ---------------------------------------------------------------------------
# Донат
# ---------------------------------------------------------------------------
async def donate_screen(message: Message, db) -> None:
    user = await M.get_user(db, message.from_user.id)
    await message.answer(
        f"{E.td('champagne')} <b>ДОНАТ И ГАЛОЧКИ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<blockquote>"
        f"🔵 <b>Blue Donate Verify</b> — {config.STATUS_PRICES['blue_verify'][0]} ⭐ "
        f"или {M.short_num(config.STATUS_PRICES['blue_verify'][1])} rC\n"
        f"⚫️ <b>Black Donate Verify</b> — {config.STATUS_PRICES['black_verify'][0]} ⭐ "
        f"или {M.short_num(config.STATUS_PRICES['black_verify'][1])} rC\n"
        f"{E.td('crown')} <b>Elite</b> — {M.short_num(config.STATUS_PRICES['elite'][1])} rC\n"
        "</blockquote>\n"
        f"Курс: <b>{config.STAR_RATE['stars']} ⭐ = {M.short_num(config.STAR_RATE['coin'])} rC</b>\n"
        f"Новогодний курс: <b>{config.NEW_YEAR_STAR_RATE['stars']} ⭐ = "
        f"{M.short_num(config.NEW_YEAR_STAR_RATE['coin'])} rC</b>\n\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>\n"
        f"{E.td('up')} Текущий статус: <b>{user.active_status}</b>",
        reply_markup=K.donate_kb(),
    )


@router_rc_misc.callback_query(F.data == "m:donate")
async def cb_donate(call: CallbackQuery, db):
    user = await M.get_user(db, call.from_user.id)
    _edit(
        call.message,
        f"{E.td('champagne')} <b>ДОНАТ И ГАЛОЧКИ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 Blue Verify — {M.short_num(config.STATUS_PRICES['blue_verify'][1])} rC\n"
        f"⚫️ Black Verify — {M.short_num(config.STATUS_PRICES['black_verify'][1])} rC\n"
        f"{E.td('crown')} Elite — {M.short_num(config.STATUS_PRICES['elite'][1])} rC\n\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>\n"
        f"{E.td('up')} Статус: <b>{user.active_status}</b>",
        K.donate_kb(),
    )
    await call.answer()


@router_rc_misc.callback_query(F.data.startswith("don:"))
async def buy_status(call: CallbackQuery, db):
    key = call.data.split(":")[1]
    mapping = {"blue": "blue_verify", "black": "black_verify", "elite": "elite"}
    status = mapping.get(key)
    if not status:
        return await call.answer("Статус не найден", show_alert=True)
    price_rcoin = config.STATUS_PRICES[status][1]
    user = await M.get_user(db, call.from_user.id)
    if user.status == status:
        return await call.answer("Этот статус у тебя уже есть", show_alert=True)
    if user.balance < price_rcoin:
        need = price_rcoin - user.balance
        return await call.answer(
            f"Не хватает {M.short_num(need)} rC.\n"
            f"Звёздами: оплата через Telegram Stars (демо).",
            show_alert=True,
        )
    if not await M.debit(db, call.from_user.id, price_rcoin):
        return await call.answer("Списание не удалось", show_alert=True)
    days = 30 if status != "elite" else 90
    await M.set_status(db, call.from_user.id, status, days)
    fresh = await M.get_user(db, call.from_user.id)
    try:
        await call.message.bot.send_message(
            call.from_user.id,
            f"{E.td('crown')} <b>СТАТУС ПРИСВОЕН</b>\n"
            f"{status_badge(status)}\n"
            f"Действует {days} дней.\n"
            f"{E.td('gem')} Баланс: <b>{M.short_num(fresh.balance)}</b>",
        )
    except Exception:
        pass
    await call.answer("Статус активирован!", show_alert=True)
    await cb_donate(call, db)


# ---------------------------------------------------------------------------
# Заработок
# ---------------------------------------------------------------------------
EARN_TASKS = [
    ("Бонус за рекламу", "earn:ad", 150_000, "Посмотри ролик (демо) и получи rC"),
    ("Спонсорская подписка", "earn:sponsor", 500_000, "Подпишись на канал спонсора (демо)"),
    ("Пригласи друга", "earn:ref", 1_000_000, "Реферальная программа в боте"),
    ("Ежечасный бонус", "m:daily", 250_000, "Забирай раз в сутки"),
]


async def earn_screen(message: Message, db) -> None:
    lines = [f"{E.td('money_launch')} <b>ЗАРАБОТОК rCoin</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for title, code, reward, desc in EARN_TASKS:
        lines.append(f"{E.td('check')} <b>{title}</b> — до {M.short_num(reward)}\n   <i>{desc}</i>")
    rows = []
    for title, code, reward, _ in EARN_TASKS[:3]:
        rows.append([K._btn(f"{E.td('money_tear')} {title}", code, style="success")])
    rows.append([K._btn("◀️ Назад", "m:back")])
    await message.answer("\n".join(lines), reply_markup=K.kb(*rows))


@router_rc_misc.callback_query(F.data == "m:earn")
async def cb_earn(call: CallbackQuery, db):
    lines = [f"{E.td('money_launch')} <b>ЗАРАБОТОК rCoin</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for title, code, reward, desc in EARN_TASKS:
        lines.append(f"{E.td('check')} <b>{title}</b> — до {M.short_num(reward)}")
    rows = [[K._btn(f"{E.td('money_tear')} {title}", code, style="success")]
            for title, code, _, _ in EARN_TASKS[:3]]
    rows.append([K._btn("◀️ Назад", "m:back")])
    _edit(call.message, "\n".join(lines), K.kb(*rows))
    await call.answer()


@router_rc_misc.callback_query(F.data == "earn:ad")
async def earn_ad(call: CallbackQuery, db):
    day = M.today_key()
    async with db.execute(
        "SELECT 1 FROM rc_event_claims WHERE user_id=? AND kind='ad' AND day=?",
        (call.from_user.id, day),
    ) as cur:
        if await cur.fetchone():
            return await call.answer("Бонус уже получен сегодня", show_alert=True)
    await db.execute(
        "INSERT INTO rc_event_claims (user_id, kind, day, payload) VALUES (?,?,?,?)",
        (call.from_user.id, "ad", day, "150k"),
    )
    await M.add_balance(db, call.from_user.id, 150_000, "earn_ad")
    await call.answer("Получено 150к rC (демо-реклама)", show_alert=True)


@router_rc_misc.callback_query(F.data == "earn:sponsor")
async def earn_sponsor(call: CallbackQuery, db):
    day = M.today_key()
    async with db.execute(
        "SELECT 1 FROM rc_event_claims WHERE user_id=? AND kind='sponsor' AND day=?",
        (call.from_user.id, day),
    ) as cur:
        if await cur.fetchone():
            return await call.answer("Бонус уже получен сегодня", show_alert=True)
    await db.execute(
        "INSERT INTO rc_event_claims (user_id, kind, day, payload) VALUES (?,?,?,?)",
        (call.from_user.id, "sponsor", day, "500k"),
    )
    await M.add_balance(db, call.from_user.id, 500_000, "earn_sponsor")
    await call.answer("Подписка подтверждена (демо). +500к rC", show_alert=True)


@router_rc_misc.callback_query(F.data == "earn:ref")
async def earn_ref(call: CallbackQuery):
    link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{call.from_user.id}"
    await call.message.edit_text(
        f"{E.td('money_launch')} <b>РЕФЕРАЛЬНАЯ ССЫЛКА</b>\n"
        f"<code>{link}</code>\n"
        f"За каждого друга — {M.short_num(config.START_BALANCE // 5)} rC",
        reply_markup=K.back("m:earn"),
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Бонус-хаб
# ---------------------------------------------------------------------------
async def bonus_screen(message: Message, db) -> None:
    user = await M.get_user(db, message.from_user.id)
    now = int(time.time())
    daily_left = max(0, 86400 - (now - user.last_daily))
    hours = daily_left // 3600
    await message.answer(
        f"{E.td('gift')} <b>БОНУСЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('calendar')} Ежедневный: "
        f"{'<b>готов</b>' if not daily_left else f'через {hours} ч'}\n"
        f"{E.td('fire')} Серия входов: <b>{user.streak}</b> дн.\n"
        f"{E.td('champagne')} Реклама: +150к rC\n"
        f"{E.td('money_launch')} Спонсор: +500к rC\n"
        f"{E.td('gift')} Зимний склад: {config.WAREHOUSE_CELLS} ячейки в день",
        reply_markup=K.kb(
            [K._btn(f"{E.td('calendar')} Ежедневный", "m:daily", style="success")],
            [K._btn(f"{E.td('money_tear')} Реклама", "earn:ad"),
             K._btn("Спонсор", "earn:sponsor")],
            [K._btn("� comedу Зимний склад", "m:warehouse")],
            [K._btn("◀️ Назад", "m:back")],
        ),
    )


@router_rc_misc.callback_query(F.data == "m:bonus")
async def cb_bonus(call: CallbackQuery, db):
    user = await M.get_user(db, call.from_user.id)
    now = int(time.time())
    daily_left = max(0, 86400 - (now - user.last_daily))
    _edit(
        call.message,
        f"{E.td('gift')} <b>БОНУСЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('calendar')} Ежедневный: "
        f"{'<b>готов</b>' if not daily_left else f'через {daily_left // 3600} ч'}\n"
        f"{E.td('fire')} Серия: <b>{user.streak}</b> дн.",
        K.kb(
            [K._btn(f"{E.td('calendar')} Ежедневный", "m:daily", style="success")],
            [K._btn(f"{E.td('money_tear')} Реклама", "earn:ad"),
             K._btn("Спонсор", "earn:sponsor")],
            [K._btn(f"{E.td('gift')} Зимний склад", "m:warehouse")],
            [K._btn("◀️ Назад", "m:back")],
        ),
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Зимний склад
# ---------------------------------------------------------------------------
async def warehouse_screen(message: Message, db) -> None:
    day = M.today_key()
    async with db.execute(
        "SELECT payload FROM rc_event_claims WHERE user_id=? AND kind='warehouse' AND day=?",
        (message.from_user.id, day),
    ) as cur:
        row = await cur.fetchone()
    if row:
        prizes = [int(x) for x in row["payload"].split(",") if x]
        lines = [f"{E.td('gift')} <b>ЗИМНИЙ СКЛАД</b>", "━━━━━━━━━━━━━━━━━━━━",
                 "Сегодняшние ячейки уже открыты:"]
        for i, p in enumerate(prizes, start=1):
            lines.append(f"🎁 Ячейка {i}: <b>{M.short_num(p)}</b> rC")
        lines.append(f"\n{E.td('hundred')} Итого: <b>{M.short_num(sum(prizes))}</b>")
        lines.append("Возвращайся завтра!")
        await message.answer("\n".join(lines), reply_markup=K.back())
        return
    await message.answer(
        f"{E.td('gift')} <b>ЗИМНИЙ СКЛАД</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Раз в день доступно <b>{config.WAREHOUSE_CELLS}</b> ячейки.\n"
        f"Приз в каждой: от <b>{M.short_num(config.WAREHOUSE_MIN)}</b> до "
        f"<b>{M.short_num(config.WAREHOUSE_MAX)}</b> rC.\n\n"
        "Жми, чтобы открыть 👇",
        reply_markup=K.warehouse_kb(),
    )


@router_rc_misc.callback_query(F.data == "m:warehouse")
async def cb_warehouse(call: CallbackQuery, db):
    day = M.today_key()
    async with db.execute(
        "SELECT payload FROM rc_event_claims WHERE user_id=? AND kind='warehouse' AND day=?",
        (call.from_user.id, day),
    ) as cur:
        row = await cur.fetchone()
    if row:
        prizes = [int(x) for x in row["payload"].split(",") if x]
        _edit(call.message,
              f"{E.td('gift')} <b>ЗИМНИЙ СКЛАД</b>\n"
              "Ячейки на сегодня открыты: "
              + ", ".join(M.short_num(p) for p in prizes)
              + f"\n{E.td('hundred')} Итого: <b>{M.short_num(sum(prizes))}</b>",
              K.back())
        return await call.answer("Приходи завтра")
    await call.answer()


@router_rc_misc.callback_query(F.data == "ev:warehouse")
async def warehouse_claim(call: CallbackQuery, db):
    result = await M.warehouse_claim(db, call.from_user.id)
    if not result.get("ok"):
        return await call.answer("Сегодня уже открывал", show_alert=True)
    user = await M.get_user(db, call.from_user.id)
    prizes = result["prizes"]
    lines = [f"{E.td('fireworks')} <b>ЗИМНИЙ СКЛАД</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for i, p in enumerate(prizes, start=1):
        lines.append(f"🎁 Ячейка {i}: <b>{M.short_num(p)}</b> rC")
    lines.append(f"\n{E.td('money_tear')} Итого: <b>{M.short_num(result['total'])}</b>")
    lines.append(f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>")
    _edit(call.message, "\n".join(lines), K.warehouse_kb())
    await call.answer(f"+{M.short_num(result['total'])}")


# ---------------------------------------------------------------------------
# Санта
# ---------------------------------------------------------------------------
def santa_bar(dealt: int, hp: int) -> str:
    if hp <= 0:
        return "▱" * 12
    filled = int(12 * dealt / hp)
    return "▰" * filled + "▱" * (12 - filled)


async def santa_screen(message: Message, db) -> None:
    state = await M.santa_state(db)
    await message.answer(await santa_text(state), reply_markup=K.santa_kb())


async def santa_text(state: dict) -> str:
    return (
        f"{E.td('skull')} <b>БИТВА С САНТОЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('fire')} Босс: <b>{state['boss']}</b>\n"
        f"❤️ HP: <b>{M.short_num(max(0, state['left']))}</b> / {M.short_num(state['hp'])}\n"
        f"<code>{santa_bar(state['dealt'], state['hp'])}</code>\n"
        f"{E.td('money_tear')} Твой урон приносит rC по курсу ×2.\n\n"
        "<i>1–30 декабря — Санта 10 000 000 HP.\n31 декабря — Главный босс 100 000 000 HP "
        "и мега-дроп всем участникам.</i>"
    )


@router_rc_misc.callback_query(F.data == "m:santa")
async def cb_santa(call: CallbackQuery, db):
    state = await M.santa_state(db)
    _edit(call.message, await santa_text(state), K.santa_kb())
    await call.answer()


@router_rc_misc.callback_query(F.data == "ev:santa")
async def cb_santa2(call: CallbackQuery, db):
    await cb_santa(call, db)


@router_rc_misc.callback_query(F.data == "ev:santa:hit")
async def santa_hit(call: CallbackQuery, db):
    result = await M.santa_hit(db, call.from_user.id)
    if not result.get("ok"):
        return await call.answer("Ты уже бил Санту сегодня", show_alert=True)
    state = result["state"]
    user = await M.get_user(db, call.from_user.id)
    _edit(
        call.message,
        f"{E.td('fire')} <b>УДАР ПО БОССУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{E.td('boom')} Урон: <b>{M.short_num(result['damage'])}</b>\n"
        f"{E.td('money_tear')} Награда: <b>{M.short_num(result['reward'])}</b> rC\n"
        f"❤️ HP босса: <b>{M.short_num(max(0, state['left']))}</b>\n"
        f"<code>{santa_bar(state['dealt'], state['hp'])}</code>\n"
        f"{E.td('gem')} Баланс: <b>{M.short_num(user.balance)}</b>",
        K.santa_kb(),
    )
    await call.answer(f"−{M.short_num(result['damage'])} HP")

# =============================== handlers/rc_admin.py ================
# file: handlers/rc_admin.py
"""Админка «Рубин Бот»: выдача, статусы, бан, рассылка, промо и создание NFT через FSM."""

import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message


router_rc_admin = Router(name="rc_admin")


class NftFSM(StatesGroup):
    title = State()
    model = State()
    rarity = State()
    floor = State()
    supply = State()
    photo = State()
    photo_serial = State()


class AdminFSM(StatesGroup):
    give_target = State()
    give_amount = State()
    status_target = State()
    status_kind = State()
    ban_target = State()
    broadcast = State()
    promo_code = State()
    promo_amount = State()


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDs


def admin_only(func):
    async def wrapper(event, *args, **kwargs):
        user = getattr(event, "from_user", None)
        if not user or not is_admin(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа", show_alert=True)
            return None
        return await func(event, *args, **kwargs)

    wrapper.__name__ = getattr(func, "__name__", "handler")
    return wrapper


def _edit(message: Message, text: str, markup=None) -> None:
    try:
        message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


@router_rc_admin.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        f"{E.td('gear')} <b>АДМИН-ПАНЕЛЬ</b>\n━━━━━━━━━━━━━━━━━━━━",
        reply_markup=K.admin_menu(),
    )


@router_rc_admin.callback_query(F.data == "adm:menu")
@admin_only
async def admin_menu(call: CallbackQuery, db):
    stats = await admin_stats_text(db)
    _edit(call.message, f"{E.td('gear')} <b>АДМИН-ПАНЕЛЬ</b>\n━━━━━━━━━━━━━━━━━━━━\n{stats}",
          K.admin_menu())
    await call.answer()


async def admin_stats_text(db) -> str:
    async with db.execute(
        "SELECT COUNT(*), COALESCE(SUM(balance),0) FROM rc_users"
    ) as cur:
        users, total = await cur.fetchone()
    async with db.execute("SELECT COUNT(*), COALESCE(SUM(bet),0) FROM rc_history") as cur:
        rounds, bets = await cur.fetchone()
    async with db.execute(
        "SELECT COUNT(*), COALESCE(SUM(price),0) FROM rc_nft_items WHERE owner_id IS NOT NULL"
    ) as cur:
        nfts, nft_value = await cur.fetchone()
    return (
        f"{E.td('hundred')} Игроков: <b>{M.full_num(users)}</b>\n"
        f"{E.td('money_tear')} Балансы: <b>{M.short_num(total)}</b> rC\n"
        f"{E.td('play')} Раундов: <b>{M.full_num(rounds)}</b>\n"
        f"{E.td('up')} Ставок на: <b>{M.short_num(bets)}</b> rC\n"
        f"{E.td('gift')} NFT в обороте: <b>{M.full_num(nfts)}</b> на {M.short_num(nft_value)}"
    )


@router_rc_admin.callback_query(F.data == "adm:stats")
@admin_only
async def admin_stats(call: CallbackQuery, db):
    _edit(call.message, f"{E.td('hundred')} <b>СТАТИСТИКА</b>\n━━━━━━━━━━━━━━━━━━━━\n"
          + await admin_stats_text(db), K.admin_back())
    await call.answer()


# ---------------------------------------------------------------------------
# Выдача rCoin
# ---------------------------------------------------------------------------
@router_rc_admin.callback_query(F.data == "adm:give")
@admin_only
async def give_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.give_target)
    _edit(call.message, f"{E.td('money_tear')} <b>ВЫДАЧА</b>\n\nID или @username игрока:")
    await call.answer()


async def resolve_user(db, raw: str):
    raw = (raw or "").strip().lstrip("@")
    if raw.isdigit():
        return await M.get_user(db, int(raw))
    async with db.execute("SELECT * FROM rc_users WHERE LOWER(username)=?", (raw.lower(),)) as cur:
        row = await cur.fetchone()
    return M.RCUser.from_row(row) if row else None


@router_rc_admin.message(AdminFSM.give_target)
async def give_target(message: Message, db, state: FSMContext):
    target = await resolve_user(db, message.text or "")
    if not target:
        return await message.answer(f"{E.td('cross')} Игрок не найден")
    await state.update_data(target=target.id)
    await state.set_state(AdminFSM.give_amount)
    await message.answer(f"Игрок: <b>{target.name}</b>\nСумма rC (минус — списать):")


@router_rc_admin.message(AdminFSM.give_amount)
async def give_amount(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    amount = parse_amount(message.text)
    if not amount:
        return await message.answer(f"{E.td('cross')} Неверная сумма")
    await M.add_balance(db, data["target"], amount, "admin")
    fresh = await M.get_user(db, data["target"])
    await message.answer(
        f"{E.td('check')} Начислено <b>{M.short_num(amount)}</b> rC\n"
        f"Баланс: <b>{M.short_num(fresh.balance)}</b>",
        reply_markup=K.admin_back(),
    )


# ---------------------------------------------------------------------------
# Статусы и бан
# ---------------------------------------------------------------------------
@router_rc_admin.callback_query(F.data == "adm:status")
@admin_only
async def status_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.status_target)
    _edit(call.message, f"{E.td('crown')} <b>ВЫДАТЬ СТАТУС</b>\n\nID или @username:")
    await call.answer()


@router_rc_admin.message(AdminFSM.status_target)
async def status_target(message: Message, db, state: FSMContext):
    target = await resolve_user(db, message.text or "")
    if not target:
        return await message.answer(f"{E.td('cross')} Игрок не найден")
    await state.update_data(target=target.id)
    await state.set_state(AdminFSM.status_kind)
    lines = ["Выбери ключ статуса:"]
    for key in config.STATUSES:
        lines.append(f"<code>{key}</code> — {config.STATUS_TITLES[key]}")
    lines.append("<code>none</code> — снять статус")
    await message.answer("\n".join(lines))


@router_rc_admin.message(AdminFSM.status_kind)
async def status_kind(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    key = (message.text or "").strip().lower()
    status = "none" if key == "none" else (key if key in config.STATUSES else None)
    if status is None:
        return await message.answer(f"{E.td('cross')} Неизвестный статус")
    await M.set_status(db, data["target"], status, 0 if status == "none" else 365)
    await message.answer(f"{E.td('check')} Статус обновлён: <b>{config.STATUS_TITLES.get(status, 'нет')}</b>",
                         reply_markup=K.admin_back())


@router_rc_admin.callback_query(F.data == "adm:ban")
@admin_only
async def ban_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.ban_target)
    _edit(call.message, f"{E.td('no_entry')} <b>БАН</b>\n\nID или @username (повторно — разбан):")
    await call.answer()


@router_rc_admin.message(AdminFSM.ban_target)
async def ban_apply(message: Message, db, state: FSMContext):
    await state.clear()
    target = await resolve_user(db, message.text or "")
    if not target:
        return await message.answer(f"{E.td('cross')} Игрок не найден")
    current = await db.execute("SELECT 1 FROM rc_users WHERE id=? AND status='banned'",
                               (target.id,))
    banned = bool(await current.fetchone())
    if banned:
        await M.set_status(db, target.id, "none", 0)
        await message.answer(f"{E.td('check')} {target.name} разбанен", reply_markup=K.admin_back())
    else:
        await M.set_status(db, target.id, "banned", 0)
        await message.answer(f"{E.td('no_entry')} {target.name} забанен", reply_markup=K.admin_back())


# ---------------------------------------------------------------------------
# Рассылка и промо
# ---------------------------------------------------------------------------
@router_rc_admin.callback_query(F.data == "adm:broadcast")
@admin_only
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.broadcast)
    _edit(call.message, f"{E.td('megaphone')} <b>РАССЫЛКА</b>\n\nОтправь текст (HTML разрешён):")
    await call.answer()


@router_rc_admin.message(AdminFSM.broadcast)
async def broadcast_send(message: Message, db, state: FSMContext):
    await state.clear()
    text = message.html_text
    async with db.execute("SELECT id FROM rc_users WHERE status != 'banned'") as cur:
        ids = [r["id"] for r in await cur.fetchall()]
    ok = fail = 0
    for uid in ids:
        try:
            await message.bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1
    await message.answer(
        f"{E.td('megaphone')} Отправлено: <b>{ok}</b>\n{E.td('cross')} Ошибок: <b>{fail}</b>",
        reply_markup=K.admin_back(),
    )


@router_rc_admin.callback_query(F.data == "adm:promo")
@admin_only
async def promo_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.promo_code)
    _edit(call.message, f"{E.td('disc')} <b>ПРОМОКОД</b>\n\nКод (A-Z0-9):")
    await call.answer()


@router_rc_admin.message(AdminFSM.promo_code)
async def promo_code(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()
    if not code:
        return await message.answer(f"{E.td('cross')} Пустой код")
    await state.update_data(code=code)
    await state.set_state(AdminFSM.promo_amount)
    await message.answer("Сумма rC:")


@router_rc_admin.message(AdminFSM.promo_amount)
async def promo_amount(message: Message, db, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    amount = parse_amount(message.text)
    if not amount:
        return await message.answer(f"{E.td('cross')} Неверная сумма")
    await db.execute(
        "INSERT OR REPLACE INTO rc_promo (code, amount, uses, max_uses, active) VALUES (?,?,0,1000,1)",
        (data["code"], amount),
    )
    await db.commit()
    await message.answer(f"{E.td('check')} Промокод <code>{data['code']}</code> на {M.short_num(amount)}",
                         reply_markup=K.admin_back())


# ---------------------------------------------------------------------------
# Создание NFT через FSM: имя → модель → редкость → цена → тираж → фото
# ---------------------------------------------------------------------------
@router_rc_admin.callback_query(F.data == "adm:nft")
@admin_only
async def nft_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(NftFSM.title)
    _edit(
        call.message,
        f"{E.td('gift')} <b>СОЗДАНИЕ NFT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Шаг 1/6. Название коллекции (например <b>Frost Bear</b>):",
    )
    await call.answer()


@router_rc_admin.message(NftFSM.title)
async def nft_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()[:40]
    if not title:
        return await message.answer(f"{E.td('cross')} Введи название")
    await state.update_data(title=title)
    await state.set_state(NftFSM.model)
    await message.answer("Шаг 2/6. Эмодзи-модель (например 🐻‍❄️):")


@router_rc_admin.message(NftFSM.model)
async def nft_model(message: Message, state: FSMContext):
    model = (message.text or "🎁").strip()[:6]
    await state.update_data(model=model)
    await state.set_state(NftFSM.rarity)
    await message.answer(
        "Шаг 3/6. Редкость: " + " / ".join(config.RARITY_ORDER)
    )


@router_rc_admin.message(NftFSM.rarity)
async def nft_rarity(message: Message, state: FSMContext):
    rarity = (message.text or "").strip().lower()
    if rarity not in config.RARITY_ORDER:
        return await message.answer(f"{E.td('cross')} Только: {', '.join(config.RARITY_ORDER)}")
    await state.update_data(rarity=rarity)
    await state.set_state(NftFSM.floor)
    await message.answer("Шаг 4/6. Цена в rC (можно <code>5kk</code>):")


@router_rc_admin.message(NftFSM.floor)
async def nft_floor(message: Message, state: FSMContext):
    price = parse_amount(message.text)
    if not price:
        return await message.answer(f"{E.td('cross')} Неверная цена")
    await state.update_data(floor=price)
    await state.set_state(NftFSM.supply)
    await message.answer("Шаг 5/6. Тираж: число или <code>0</code> (без ограничения):")


@router_rc_admin.message(NftFSM.supply)
async def nft_supply(message: Message, state: FSMContext):
    raw = (message.text or "0").strip()
    supply = int(raw) if raw.isdigit() else 0
    await state.update_data(supply=supply)
    await state.set_state(NftFSM.photo)
    await message.answer(
        "Шаг 6/6. Загрузи фото подарка (или напиши <code>нет</code> — будет градиент с моделью):"
    )


@router_rc_admin.message(NftFSM.photo)
async def nft_create(message: Message, db, state: FSMContext, bot):
    data = await state.get_data()
    photo_path = None
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        target = f"uploads/nft_{int(time.time())}.jpg"
        import os

        os.makedirs("uploads", exist_ok=True)
        await bot.download_file(file.file_path, target)
        photo_path = target
    slug = "adm_" + str(int(time.time()))
    now = int(time.time())
    await db.execute(
        """INSERT INTO rc_nft_templates
           (slug, title, model, rarity, floor, supply, bg, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (slug, data["title"], data["model"], data["rarity"], data["floor"],
         data["supply"], "#1a1420", now),
    )
    await db.commit()
    async with db.execute("SELECT * FROM rc_nft_templates WHERE slug=?", (slug,)) as cur:
        tmpl = await cur.fetchone()
    await state.update_data(template_id=tmpl["id"], photo_path=photo_path)
    await state.set_state(NftFSM.photo_serial)
    preview = nft_image.render_gift(
        title=data["title"], serial=1, rarity=data["rarity"],
        model=data["model"], bg="#1a1420", source_image=photo_path,
    )
    await bot.send_photo(message.chat.id, preview,
                         caption=f"{E.td('check')} Превью #{1}: <b>{data['title']}</b>\n\n"
                                 "Сколько экземпляров выпустить сразу? (число, 0 — без минтинга)")
    await state.clear()


@router_rc_admin.message(NftFSM.photo_serial)
async def nft_mint_batch(message: Message, db, state: FSMContext, bot):
    data = await state.get_data()
    await state.clear()
    count = int(message.text) if (message.text or "").strip().isdigit() else 0
    count = max(0, min(count, 500))
    template_id = data["template_id"]
    async with db.execute(
        "SELECT * FROM rc_nft_templates WHERE id=?", (template_id,)
    ) as cur:
        tmpl = await cur.fetchone()
    for _ in range(count):
        item_id = await M.mint(db, tmpl["id"], None, tmpl["floor"])
        await db.execute("UPDATE rc_nft_items SET owner_id=NULL WHERE id=?", (item_id,))
        path = nft_image.render_gift(
            title=tmpl["title"], serial=await _serial(db, item_id), rarity=tmpl["rarity"],
            model=tmpl["model"], bg=tmpl["bg"], source_image=data.get("photo_path"),
        )
        await db.execute("UPDATE rc_nft_items SET image_path=? WHERE id=?", (path, item_id))
    await db.commit()
    await message.answer(
        f"{E.td('check')} <b>КОЛЛЕКЦИЯ СОЗДАНА</b>\n"
        f"{tmpl['model']} {tmpl['title']} · {config.RARITY_NAMES[tmpl['rarity']]}\n"
        f"{E.td('gift')} Выпущено: <b>{count}</b>",
        reply_markup=K.admin_back(),
    )


async def _serial(db, item_id: int) -> int:
    async with db.execute("SELECT serial FROM rc_nft_items WHERE id=?", (item_id,)) as cur:
        row = await cur.fetchone()
    return row[0] if row else 1


@router_rc_admin.callback_query(F.data == "adm:nftlist")
@admin_only
async def nft_list(call: CallbackQuery, db):
    rows = await M.templates(db, only_active=False)
    lines = [f"{E.td('bag')} <b>КОЛЛЕКЦИИ NFT</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for t in rows[:15]:
        lines.append(
            f"{t['model']} <b>{t['title']}</b> · {config.RARITY_NAMES[t['rarity']]} · "
            f"{M.short_num(t['floor'])} · выпущено {t['minted']}"
        )
    _edit(call.message, "\n".join(lines), K.admin_back())
    await call.answer()


# ---------------------------------------------------------------------------
# Быстрые команды
# ---------------------------------------------------------------------------
@router_rc_admin.message(Command("give"))
async def quick_give(message: Message, db, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split()
    if len(args) != 2:
        return await message.answer("Использование: /give <user_id> <сумма>")
    amount = parse_amount(args[1])
    if not amount:
        return await message.answer(f"{E.td('cross')} Неверная сумма")
    await M.add_balance(db, int(args[0]) if args[0].isdigit() else 0, amount, "admin")
    await message.answer(f"{E.td('check')} Выдано {M.short_num(amount)} пользователю {args[0]}")


@router_rc_admin.message(Command("promo"))
async def quick_promo(message: Message, db, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split()
    if len(args) != 2:
        return await message.answer("Использование: /promo <КОД> <сумма>")
    amount = parse_amount(args[1])
    if not amount:
        return await message.answer(f"{E.td('cross')} Неверная сумма")
    await db.execute(
        "INSERT OR REPLACE INTO rc_promo (code, amount, uses, max_uses, active) VALUES (?,?,0,1000,1)",
        (args[0].upper(), amount),
    )
    await db.commit()
    await message.answer(f"{E.td('check')} Промокод {args[0].upper()} на {M.short_num(amount)}")


@router_rc_admin.message(Command("promocode"))
async def redeem_promo_cmd(message: Message, db, command: CommandObject):
    code = (command.args or "").strip()
    if not code:
        return await message.answer("Формат: /promocode КОД")
    ok, reason, amount = await M.redeem_promo(db, code, message.from_user.id)
    if not ok:
        return await message.answer(f"{E.td('cross')} {reason}")
    await message.answer(f"{E.td('champagne')} Получено <b>{M.short_num(amount)}</b> rC")


# ---------------------------------------------------------------------------
# Обработчик ссылки chek_ и приглашения
# ---------------------------------------------------------------------------
@router_rc_admin.callback_query(F.data == "unused")
async def _noop(call: CallbackQuery):
    await call.answer()




# =============================== SESSION STORE ==============================
MAX_IDLE = 3600

class SessionStore:
    def __init__(self):
        self._data = {}
        self._last = {}

    def new(self):
        gid = 's' + str(int(time.time()*1000)) + str(random.randint(100,999))
        self._data[gid] = {}
        self._last[gid] = time.time()
        return gid

    def get(self, gid):
        s = self._data.get(gid)
        if s is not None:
            self._last[gid] = time.time()
        return s

    def set(self, gid, value):
        self._data[gid] = value
        self._last[gid] = time.time()

    def drop(self, gid):
        self._data.pop(gid, None)
        self._last.pop(gid, None)

    def gc(self):
        now = time.time()
        dead = [g for g, t in self._last.items() if now - t > MAX_IDLE]
        for g in dead:
            self.drop(g)
        return len(dead)


# =============================== bot_rc.py ================
# file: bot.py
"""«Рубин Бот» — точка входа: aiogram 3 + aiosqlite + aiohttp (mini app)."""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo


log = logging.getLogger("rubin")


class DbMiddleware:
    """Пробрасывает соединение с базой в каждый хендлер как аргумент db."""

    def __init__(self, db):
        self.db = db

    async def __call__(self, handler, event, data):
        data["db"] = self.db
        return await handler(event, data)


class BanMiddleware:
    """Отсекает забаненных (кроме админов)."""

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and user.id not in config.ADMIN_IDs:
            row = await M.get_user(data["db"], user.id)
            if row and row.status == "banned":
                return None
        return await handler(event, data)


def build_dispatcher(db) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    for observer in (dp.message, dp.callback_query):
        observer.middleware(DbMiddleware(db))
        observer.middleware(BanMiddleware())
    # Порядок важен: сначала админка и игры (конкретные callback_data),
    # затем маркет, лотерея, прочее и в конце общее меню.
    for r in (router_rc_admin, router_rc_games, router_rc_market,
              router_rc_lottery, router_rc_misc, router_rc_core):
        dp.include_router(r)
    register_text_router(dp)
    return dp


# =============================== MINI APP ===================================
WEBAPP_HTML = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Рубин · rCoin</title><style>
:root{--bg:#0e0a0d;--panel:#1a1218;--acc:#ff3b6b;--acc2:#ff8a3d;--txt:#f4eef1;--dim:#a08e96}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,
Roboto,sans-serif;background:
var(--wall,rgba(0,0,0,0)) fixed,radial-gradient(120% 80% at 15% -10%,#3a0d14,transparent 60%),
linear-gradient(180deg,#170d12,#0b0709 70%);color:var(--txt);min-height:100vh;padding-bottom:84px}
header{position:sticky;top:0;z-index:9;display:flex;gap:12px;align-items:center;
padding:14px 16px;background:rgba(14,10,13,.86);backdrop-filter:blur(14px);border-bottom:1px solid #2a1b22}
.ava{width:42px;height:42px;border-radius:14px;background:linear-gradient(140deg,var(--acc),var(--acc2));
display:grid;place-items:center;font-weight:800}
.bal{margin-left:auto;text-align:right;font-size:13px;color:var(--dim)}.bal b{display:block;font-size:19px;color:#fff}
main{padding:16px;max-width:640px;margin:0 auto}
.card{background:var(--panel);border:1px solid #2a1b22;border-radius:20px;padding:16px;margin-bottom:14px}
.card h3{margin:0 0 10px;font-size:15px;letter-spacing:.02em}
.btn{display:block;width:100%;padding:13px;border-radius:14px;border:0;margin:8px 0;
font:600 15px/1 system-ui;background:linear-gradient(140deg,var(--acc),var(--acc2));color:#fff;cursor:pointer}
.btn.ghost{background:#241821;color:var(--txt);border:1px solid #3a2731}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.tile{aspect-ratio:1;border-radius:14px;background:#241821;border:1px solid #3a2731;display:grid;
place-items:center;font-size:22px;cursor:pointer}
.tile.gem{background:linear-gradient(140deg,#2b1f45,#161021);border-color:#4d3a7a}
.tile.bomb{background:#3a0d14;border-color:#7a2530}
.row{display:flex;gap:8px}.row>*{flex:1}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;background:#120c10;
border-top:1px solid #2a1b22;padding:8px 4px calc(8px + env(safe-area-inset-bottom))}
nav button{flex:1;background:none;border:0;color:var(--dim);font:500 11px system-ui;padding:6px 0}
nav button.on{color:var(--acc)}
.toast{position:fixed;left:50%;top:18px;transform:translateX(-50%);background:#241821;
border:1px solid #4d2b38;padding:10px 18px;border-radius:999px;font-size:13px;opacity:0;
transition:.25s;pointer-events:none;z-index:99}
.toast.show{opacity:1}
input,select{width:100%;padding:11px;border-radius:12px;border:1px solid #3a2731;
background:#120c10;color:var(--txt);font:14px system-ui}
.sw{display:flex;gap:8px;flex-wrap:wrap}.sw span{width:30px;height:30px;border-radius:10px;cursor:pointer}
</style></head><body>
<header><div class="ava" id="ava">R</div><div><div id="name" style="font-weight:700">Гость</div>
<div id="st" style="font-size:12px;color:var(--dim)">rCoin</div></div>
<div class="bal">Баланс<b id="bal">0</b></div></header>
<main>
<div class="card"><h3>ИГРАТЬ</h3>
<button class="btn" id="play">Крутить рулетку (-10 000)</button>
<div class="row"><button class="btn ghost" id="coin">Монетка</button>
<button class="btn ghost" id="dice">Кости</button></div>
<div class="grid" id="field"></div>
<div class="row" style="margin-top:8px"><button class="btn ghost" id="reset">Новая игра</button>
<button class="btn" id="cash">Забрать</button></div>
<div id="mult" style="text-align:center;color:var(--dim);font-size:13px">Множитель ×1.00</div></div>
<div class="card"><h3>МАРКЕТ</h3><div id="market"></div></div>
<div class="card"><h3>ОФОРМЛЕНИЕ</h3>
<div class="sw" id="themes"></div>
<div style="margin-top:10px"><input type="color" id="acc" value="#ff3b6b"></div>
<div style="margin-top:10px"><input type="color" id="wall" value="#170d12"></div>
<div style="margin-top:10px"><input type="file" id="wallimg" accept="image/*"></div></div>
</main>
<nav><button class="on">Главная</button><button>Игры</button><button>Маркет</button>
<button>Задачи</button><button>Профиль</button></nav>
<div class="toast" id="toast"></div>
<script>
const TG = window.Telegram && window.Telegram.WebApp;
if (TG) { TG.ready(); TG.expand(); }
const $ = id => document.getElementById(id);
const LS = {get(k,d){try{const v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}},
  set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
let state = LS.get('rb', {bal:100000, bet:10000, mines:3, game:null, cd:[]});
const fmt = n => (n||0).toLocaleString('ru-RU');
const toast = m => {const t=$('toast');t.textContent=m;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),1600)};
function save(){LS.set('rb',state);render()}
function render(){
  $('bal').textContent = fmt(state.bal);
  $('name').textContent = (TG && TG.initDataUnsafe && TG.initDataUnsafe.user &&
    (TG.initDataUnsafe.user.first_name||TG.initDataUnsafe.user.username)) || 'Гость';
  $('mult').textContent = 'Множитель ×' + (state.game ? state.game.mult : 1).toFixed(2);
  const f = $('field'); f.innerHTML='';
  for(let i=0;i<25;i++){
    const d=document.createElement('div'); d.className='tile'; d.textContent='❓';
    if(state.cd.includes(i)){d.className='tile gem';d.textContent='💎'}
    d.onclick=()=>openCell(i); f.appendChild(d);
  }
}
function startGame(bet){
  if(!state.coins) state.coins = 0;
  if(state.bal<bet) return toast('Недостаточно rC');
  state.bal-=bet; state.game={bet,mult:1,dead:false}; state.cd=[];
  save(); toast('Ставка '+fmt(bet));
}
function openCell(i){
  if(!state.game||state.game.dead||state.cd.includes(i)) return toast('Игра не активна');
  if(Math.random()<0.12){state.game.dead=true;state.cd.push(i);save();return toast('💥 Мина!')}
  state.cd.push(i);
  const m=+(0.96/Math.pow((22-state.cd.length+1)/23,state.cd.length)).toFixed(2);
  state.game.mult=Math.max(state.game.mult,m); save();
}
$('play').onclick=()=>{const win=Math.random()<0.47;
  if(state.bal<10000) return toast('Недостаточно rC');
  state.bal-=10000; if(win){state.bal+=20000;toast('🔴 Красное +20 000')}
  else toast('⚫️ Чёрное −10 000'); save()};
$('coin').onclick=()=>{if(state.bal<10000)return toast('Мало rC');
  state.bal-=10000; if(Math.random()<0.5){state.bal+=20000;toast('Орёл +10 000')}
  else toast('Решка −10 000'); save()};
$('dice').onclick=()=>{if(state.bal<10000)return toast('Мало rC');
  state.bal-=10000; const r=Math.ceil(Math.random()*6);
  if(r===6){state.bal+=32000;toast('🎲 6! +32 000')}else toast('Выпало '+r); save()};
$('reset').onclick=()=>{state.game=null;state.cd=[];save();toast('Новая игра')};
$('cash').onclick=()=>{if(!state.game||state.game.dead)return toast('Нечего забирать');
  const pay=Math.floor(state.game.bet*state.game.mult); state.bal+=pay;
  state.game=null;state.cd=[];save();toast('Забрано '+fmt(pay))};
['mines','ladder','crash','bjack','quack'].forEach(g=>{});
const market=[['Porky','🐷',500000],['Buddy','🐶',650000],['Walter','🐈',2500000],
['Cheremsha','🦝',3000000],['Duckwave','🦆',15000000],['Корона','👑',200000000]];
$('market').innerHTML=market.map(([t,e,p])=>
`<button class="btn ghost" onclick="buy('${t}',${p})">${e} ${t} — ${fmt(p)}</button>`).join('');
window.buy=(t,p)=>{if(state.bal<p)return toast('Мало rC');
  state.bal-=p; save(); toast('Куплено '+t)};
const themes=[['#ff3b6b','рубин'],['#3b82f6','синий'],['#22c55e','зелёный'],
['#a855f7','фиолет'],['#f59e0b','золото'],['#06b6d4','бирюза']];
$('themes').innerHTML=themes.map(([c])=>`<span style="background:${c}" data-c="${c}"></span>`).join('');
$('themes').onclick=e=>{const c=e.target.dataset.c;if(!c)return;
  document.documentElement.style.setProperty('--acc',c); LS.set('acc',c)};
const savedAcc=LS.get('acc',null); if(savedAcc) document.documentElement.style.setProperty('--acc',savedAcc);
$('acc').oninput=e=>{document.documentElement.style.setProperty('--acc',e.target.value);
  LS.set('acc',e.target.value)};
$('wall').oninput=e=>{document.body.style.background=e.target.value; LS.set('wall',e.target.value)};
const savedWall=LS.get('wall',null); if(savedWall) document.body.style.background=savedWall;
$('wallimg').onchange=e=>{const f=e.target.files[0]; if(!f)return;
  const r=new FileReader(); r.onload=()=>{document.body.style.backgroundImage='url('+r.result+')';
  document.body.style.backgroundSize='cover'; LS.set('wallimg',r.result)}; r.readAsDataURL(f)};
const savedImg=LS.get('wallimg',null);
if(savedImg){document.body.style.backgroundImage='url('+savedImg+')';document.body.style.backgroundSize='cover'}
render();
</script></body></html>"""


async def webapp_handler(_request):
    from aiohttp import web
    return web.Response(text=WEBAPP_HTML, content_type="text/html")

async def web_server(db):
    """Мини-апп: статика webapp/ + API на rCoin."""
    try:
        from aiohttp import web
    except ImportError:
        log.warning("aiohttp не установлен — мини-апп недоступен")
        return None

    async def index(request):
        return await webapp_handler(request)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/app", index)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT") or "8080")
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Мини-апп слушает порт %s", port)
    return runner


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    db = await M.connect()
    if not BOT_TOKEN or "TEST_TOKEN" in BOT_TOKEN:
        log.error("BOT_TOKEN не задан в Environment Render")
        print(MSG_NO_TOKEN)
        return 1
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    log.info("Рубин запущен: @%s", me.username)
    if config.BOT_USERNAME in ("", "RubinCoinBot"):
        config.BOT_USERNAME = me.username or config.BOT_USERNAME
    if config.WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="🎰 Рубин",
                                             web_app=WebAppInfo(url=config.WEBAPP_URL))
            )
        except Exception as exc:
            log.warning("Кнопка меню: %s", exc)
    runner = await web_server(db)
    dp = build_dispatcher(db)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=True)
    finally:
        if runner is not None:
            await runner.cleanup()
        await db.close()
        await bot.session.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
