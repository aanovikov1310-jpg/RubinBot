import asyncio
import random
import sqlite3
import time
import re
import hashlib
import string
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import aiohttp

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    Message, CallbackQuery, FSInputFile,
    InputFile, BufferedInputFile,
    LabeledPrice, PreCheckoutQuery,
    WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.formatting import Text, Bold, Code, Italic
from aiogram.enums import ParseMode


# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
class FixedLogger:
    @staticmethod
    def setup():
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


FixedLogger.setup()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
# Never store a live Telegram token in source control. Set BOT_TOKEN in the host environment.
BOT_TOKEN = os.getenv("BOT_TOKEN", "9153206613:AAH6yeSZv2lYd-FT1sc3cjyK47rcLoO1uik").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "5257618084"))
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "5257618084").replace(" ", "").split(",") if x.isdigit()}
if OWNER_ID > 0:
    ADMIN_IDS.add(OWNER_ID)
REQUIRED_CHANNEL = "@playhomemines"
REQUIRED_CHAT = "@gamehomemines"
BOT_USERNAME = "rubinupbot"
DB_FILE = "data.db"
IMAGE_PATH = "image.png"
WIN_IMAGE = "win.png"
LOSE_IMAGE = "lose.png"
# URL веб-аппа (health-сервер на Render). Замените на реальный домен вида https://rubinbot.onrender.com
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://rubinbot.onrender.com")

# Crypto Pay API
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "")
CRYPTO_PAY_URL = "https://pay.crypt.bot/api"
CRYPTO_WALLET = os.getenv("CRYPTO_WALLET", "")

CRYPTO_PRICES = {
    "BTC": 0.000001,
    "ETH": 0.000015,
    "USDT": 1.0,
    "TON": 0.5
}

# A deliberately invalid placeholder lets the module load so main() can print a clear setup error.
_bot_token_for_init = BOT_TOKEN or "000000000:INVALID_TOKEN"
bot = Bot(token=_bot_token_for_init, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ==================== TELEGRAM PREMIUM ЭМОДЗИ ====================

def get_emoji(emoji_id: str, fallback: str = "⬛") -> str:
    """Для текста: возвращает <tg-emoji> тег"""
    try:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    except:
        return fallback


# ====== ID ДЛЯ ТГП ЭМОДЗИ ======
EMOJI_IDS = {
    # ИГРЫ
    "games": "5841551282321497604",
    "dice": "5312533460324199794",
    "roulette": "6228608791529656524",
    "fortune": "5434093331292377553",
    "mines": "5370692462882857093",
    "crash": "5283080528818360566",
    "basket": "5384327463629233871",
    "darts": "5310278924616356636",
    "blackjack": "5285420684699260907",
    "sun": "5391270767889497941",
    "hunt": "5370553185683394181",
    "spin": "5915833712368424979",
    "football": "5413474404485061402",
    "pyramid": "5224257782013769471",
    "miner": "5370692462882857093",
    "hi_lo": "5926783847453692661",
    "ttt": "5222158908805632010",
    "door": "5259067694396474462",

    # ОСНОВНЫЕ
    "profile": "5202216593966244027",
    "balance": "5197491391206281629",
    "bank": "5881948563591666817",
    "diamond": "5438496463044752972",
    "star": "5438496463044752972",
    "lock": "5305621469134857194",
    "nft": "5262517101578443800",
    "username_emoji": "5262517101578443800",
    "referral": "5942877472163892475",
    "check": "5444856076954520455",
    "treasury": "5798678875823153004",
    "win": "5305747221996177787",
    "lose": "5305474786400690766",
    "settings": "5258096772776991776",
    "admin": "6129805886383723340",
    "donate": "5438496463044752972",
    "ad": "5213391561999526028",
    "market": "5278702045883292456",

    # ДОБАВЛЕННЫЕ ДЛЯ АДМИН-ПАНЕЛИ
    "scammer": "5305621469134857194",
    "admin_rank": "6129805886383723340",
    "donater": "5438496463044752972",
    "verified": "5444856076954520455",
    "mine": "5370692462882857093",
    "business": "5384327463629233871",
    "villa": "5278702045883292456",
    "collect": "5197491391206281629",
    "question": "5436113877181941026",
    # --- НОВЫЕ ТГП ЭМОДЗИ ДЛЯ ЗИМНЕГО ИВЕНТА ---
    "item_1": "5332717942599618048",
    "item_2": "5404752966584394198",
    "item_3": "5280924618444514633",
    "item_4": "5368488358681000659",
    "item_5": "5398024200235529935",
    "item_6": "5449449325434266744",
    "item_7": "5201924046563852634",
    "item_8": "5199959030306456092",
    "item_9": "5316599316884766402"
}
PREMIUM_EMOJI_TEXT = {key: get_emoji(val) for key, val in EMOJI_IDS.items()}

# ==================== МНОЖИТЕЛИ ДЛЯ МИН ====================
MULTIPLIERS = {
    1: {0: 1.0, 1: 1.04, 2: 1.08, 3: 1.12, 4: 1.16, 5: 1.21, 6: 1.26, 7: 1.31, 8: 1.36, 9: 1.42, 10: 1.48, 11: 1.54,
        12: 1.60, 13: 1.67, 14: 1.74, 15: 1.81, 16: 1.89, 17: 1.97, 18: 2.05, 19: 2.14, 20: 2.23, 21: 2.32, 22: 2.42,
        23: 2.52, 24: 2.63},
    2: {0: 1.0, 1: 1.10, 2: 1.20, 3: 1.32, 4: 1.45, 5: 1.59, 6: 1.75, 7: 1.93, 8: 2.13, 9: 2.35, 10: 2.59, 11: 2.86,
        12: 3.16, 13: 3.50, 14: 3.88, 15: 4.30, 16: 4.78, 17: 5.33, 18: 5.95, 19: 6.66, 20: 7.48, 21: 8.42, 22: 9.50,
        23: 10.75, 24: 12.20},
    3: {0: 1.0, 1: 1.16, 2: 1.35, 3: 1.57, 4: 1.83, 5: 2.14, 6: 2.50, 7: 2.93, 8: 3.44, 9: 4.05, 10: 4.78, 11: 5.65,
        12: 6.70, 13: 7.98, 14: 9.53, 15: 11.42, 16: 13.74, 17: 16.59, 18: 20.09, 19: 24.40, 20: 29.75, 21: 36.40,
        22: 44.70, 23: 55.10, 24: 68.20},
    4: {0: 1.0, 1: 1.22, 2: 1.48, 3: 1.81, 4: 2.20, 5: 2.68, 6: 3.27, 7: 4.00, 8: 4.90, 9: 6.03, 10: 7.45, 11: 9.23,
        12: 11.48, 13: 14.33, 14: 17.95, 15: 22.55, 16: 28.44, 17: 36.00, 18: 45.75, 19: 58.40, 20: 74.90, 21: 96.50,
        22: 124.80, 23: 162.00, 24: 211.40},
    5: {0: 1.0, 1: 1.27, 2: 1.61, 3: 2.05, 4: 2.60, 5: 3.30, 6: 4.20, 7: 5.35, 8: 6.85, 9: 8.80, 10: 11.35, 11: 14.70,
        12: 19.10, 13: 24.90, 14: 32.60, 15: 42.80, 16: 56.40, 17: 74.60, 18: 99.00, 19: 132.00, 20: 176.50, 21: 237.00,
        22: 319.50, 23: 432.50, 24: 588.00},
    6: {0: 1.0, 1: 1.33, 2: 1.76, 3: 2.33, 4: 3.08, 5: 4.07, 6: 5.38, 7: 7.12, 8: 9.44, 9: 12.55, 10: 16.75, 11: 22.40,
        12: 30.05, 13: 40.45, 14: 54.65, 15: 74.10, 16: 100.80, 17: 137.60, 18: 188.50, 19: 259.00, 20: 357.00,
        21: 494.00, 22: 686.00, 23: 956.00, 24: 1338.00},
    7: {0: 1.0, 1: 1.38, 2: 1.91, 3: 2.63, 4: 3.63, 5: 5.00, 6: 6.88, 7: 9.50, 8: 13.10, 9: 18.15, 10: 25.20,
        11: 35.10, 12: 49.00, 13: 68.60, 14: 96.40, 15: 136.00, 16: 192.50, 17: 273.50, 18: 390.00, 19: 558.00,
        20: 801.00, 21: 1155.00, 22: 1672.00, 23: 2430.00, 24: 3545.00},
    8: {0: 1.0, 1: 1.45, 2: 2.08, 3: 3.00, 4: 4.33, 5: 6.25, 6: 9.00, 7: 13.00, 8: 18.85, 9: 27.40, 10: 40.00,
        11: 58.50, 12: 85.80, 13: 126.40, 14: 187.00, 15: 277.50, 16: 413.00, 17: 617.00, 18: 925.00, 19: 1392.00,
        20: 2102.00, 21: 3185.00, 22: 4845.00, 23: 7390.00, 24: 11320.00},
    9: {0: 1.0, 1: 1.52, 2: 2.28, 3: 3.43, 4: 5.14, 5: 7.72, 6: 11.60, 7: 17.45, 8: 26.30, 9: 39.80, 10: 60.40,
        11: 92.00, 12: 140.50, 13: 215.40, 14: 331.50, 15: 512.00, 16: 793.50, 17: 1235.00, 18: 1928.00, 19: 3022.00,
        20: 4755.00, 21: 7510.00, 22: 11910.00, 23: 18950.00, 24: 30250.00},
    10: {0: 1.0, 1: 1.60, 2: 2.50, 3: 3.90, 4: 6.10, 5: 9.50, 6: 14.80, 7: 23.10, 8: 36.10, 9: 56.50, 10: 88.50,
         11: 139.00, 12: 219.00, 13: 346.00, 14: 548.00, 15: 870.00, 16: 1385.00, 17: 2210.00, 18: 3540.00, 19: 5680.00,
         20: 9140.00, 21: 14750.00, 22: 23880.00, 23: 38800.00, 24: 63280.00}
}

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                balance_coin INTEGER DEFAULT 0,
                balance_point INTEGER DEFAULT 0,
                bonus_last_time INTEGER DEFAULT 0,
                banned_until INTEGER DEFAULT 0,
                muted_until INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT '',
                mute_reason TEXT DEFAULT '',
                registered INTEGER DEFAULT 1,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                referral_code TEXT DEFAULT '',
                referred_by INTEGER DEFAULT 0,
                referral_earnings INTEGER DEFAULT 0,
                referral_percent INTEGER DEFAULT 5,
                referral_withdrawn INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT 0,
                is_anonymous INTEGER DEFAULT 0,
                stars_balance INTEGER DEFAULT 0,
                last_roulette_time INTEGER DEFAULT 0,
                last_fortune_time INTEGER DEFAULT 0,
                bank_balance INTEGER DEFAULT 0,
                last_spin_time INTEGER DEFAULT 0,
                about_text TEXT DEFAULT '',
                rank_title TEXT DEFAULT 'Новичок',
                custom_username TEXT DEFAULT '',
                is_scammer INTEGER DEFAULT 0,
                is_admin_rank INTEGER DEFAULT 0,
                is_donater INTEGER DEFAULT 0,
                is_official INTEGER DEFAULT 0,
                last_game_time INTEGER DEFAULT 0,
                daily_bonus_last INTEGER DEFAULT 0,
                daily_bonus_streak INTEGER DEFAULT 0,
                total_games_day INTEGER DEFAULT 0,
                last_game_day INTEGER DEFAULT 0,
                titles TEXT DEFAULT '[]',
                treasury_access INTEGER DEFAULT 0
            )
        ''')

        cur.execute("""
            CREATE TABLE IF NOT EXISTS event_progress (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                boss_hp INTEGER DEFAULT 0,
                boss_max INTEGER DEFAULT 0,
                day TEXT DEFAULT '',
                season INTEGER DEFAULT 1
            )
        """)
        cur.execute("INSERT OR IGNORE INTO event_progress (id, boss_hp, boss_max, day, season) "
                    "VALUES (1, 0, 0, '', 1)")

        columns_to_add = [
            ('rank_title', 'TEXT DEFAULT "Новичок"'),
            ('custom_username', 'TEXT DEFAULT ""'),
            ('is_scammer', 'INTEGER DEFAULT 0'),
            ('is_admin_rank', 'INTEGER DEFAULT 0'),
            ('is_donater', 'INTEGER DEFAULT 0'),
            ('is_official', 'INTEGER DEFAULT 0'),
            ('last_game_time', 'INTEGER DEFAULT 0'),
            ('bank_balance', 'INTEGER DEFAULT 0'),
            ('stars_balance', 'INTEGER DEFAULT 0'),
            ('about_text', 'TEXT DEFAULT ""'),
            ('referral_withdrawn', 'INTEGER DEFAULT 0'),
            ('daily_bonus_last', 'INTEGER DEFAULT 0'),
            ('daily_bonus_streak', 'INTEGER DEFAULT 0'),
            ('total_games_day', 'INTEGER DEFAULT 0'),
            ('last_game_day', 'INTEGER DEFAULT 0'),
            ('titles', 'TEXT DEFAULT "[]"'),
            ('treasury_access', 'INTEGER DEFAULT 0'),
            # --- ИВЕНТЫ ---
            ('event_day', 'TEXT DEFAULT ""'),
            ('event_stash_last', 'INTEGER DEFAULT 0'),
            ('event_boss_dmg', 'INTEGER DEFAULT 0'),
            ('event_boss_last', 'INTEGER DEFAULT 0'),
            ('event_wheel_last', 'INTEGER DEFAULT 0'),
            ('event_points', 'INTEGER DEFAULT 0'),
            # --- КВЕСТЫ (статусы завершения) ---
            ('quest_q_games', 'INTEGER DEFAULT 0'),
            ('quest_q_wins', 'INTEGER DEFAULT 0'),
            ('quest_q_stash', 'INTEGER DEFAULT 0'),
            ('quest_q_boss', 'INTEGER DEFAULT 0'),
            # --- ЕЖЕДНЕВНЫЙ БОНУС 5x5 ---
            ('db5_checked', 'INTEGER DEFAULT 0'),
            ('db5_last', 'INTEGER DEFAULT 0'),
            ('db5_streak', 'INTEGER DEFAULT 0'),
            ('db5_opened', 'INTEGER DEFAULT 0'),
            ('db5_grid', 'TEXT DEFAULT "[]"'),
            ('db5_won', 'INTEGER DEFAULT 0'),
            # --- ЛИЧНЫЙ СКЛАД ---
            ('inventory', 'TEXT DEFAULT "[]"'),
        ]

        for col_name, col_type in columns_to_add:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                logger.info(f"✅ Добавлена колонка {col_name}")
            except sqlite3.OperationalError:
                pass

        cur.execute('''
            CREATE TABLE IF NOT EXISTS checks (
                check_id TEXT PRIMARY KEY,
                owner_id INTEGER,
                amount INTEGER,
                activations INTEGER DEFAULT 0,
                max_activations INTEGER,
                description TEXT DEFAULT '',
                password TEXT DEFAULT '',
                created_at INTEGER,
                is_active INTEGER DEFAULT 1
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                channel_link TEXT,
                price_per_sub INTEGER,
                target_subs INTEGER,
                paid_points INTEGER,
                created_at INTEGER,
                status TEXT DEFAULT 'active',
                current_subs INTEGER DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                ad_id INTEGER,
                claimed INTEGER DEFAULT 0,
                claimed_at INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, ad_id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS bet_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet_amount INTEGER,
                win_amount INTEGER,
                is_win INTEGER,
                bet_data TEXT,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at INTEGER,
                reward_given INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS transfer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                amount INTEGER,
                created_at INTEGER,
                comment TEXT DEFAULT ''
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                reward INTEGER,
                uses INTEGER DEFAULT 0,
                max_uses INTEGER,
                created_by INTEGER,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS promo_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS mines_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                multiplier REAL DEFAULT 1.0,
                mines_count INTEGER,
                opened_cells INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                grid TEXT,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS tower_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                level INTEGER DEFAULT 0,
                bombs INTEGER DEFAULT 1,
                mult REAL DEFAULT 1.0,
                status TEXT DEFAULT 'active',
                grid TEXT,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS stars_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                stars INTEGER,
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS darts_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                choice TEXT,
                result TEXT,
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS blackjack_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                player_cards TEXT,
                dealer_cards TEXT,
                status TEXT DEFAULT 'active',
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id INTEGER PRIMARY KEY,
                last_claim INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS spin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS crash_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                multiplier REAL,
                status TEXT,
                auto_cashout REAL,
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS crypto_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                currency TEXT,
                amount_crypto REAL,
                address TEXT,
                status TEXT DEFAULT 'pending',
                created_at INTEGER,
                invoice_id TEXT
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS pyramid_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_amount INTEGER,
                level INTEGER DEFAULT 1,
                multiplier REAL DEFAULT 1.0,
                status TEXT DEFAULT 'active',
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS miner_data (
                user_id INTEGER PRIMARY KEY,
                mine_level INTEGER DEFAULT 0,
                business_level INTEGER DEFAULT 0,
                villa_level INTEGER DEFAULT 0,
                last_collect INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS exchange_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                price INTEGER,
                status TEXT DEFAULT 'active',
                created_at INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS nft_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                level INTEGER DEFAULT 1,
                rarity TEXT DEFAULT 'common',
                price INTEGER,
                created_at INTEGER,
                for_sale INTEGER DEFAULT 0,
                sale_price INTEGER DEFAULT 0,
                description TEXT DEFAULT ''
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS tic_tac_toe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1 INTEGER,
                player2 INTEGER,
                board TEXT DEFAULT '---------',
                current_turn INTEGER,
                status TEXT DEFAULT 'waiting',
                created_at INTEGER,
                bet_amount INTEGER DEFAULT 0
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS treasury (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                balance_coin INTEGER DEFAULT 0,
                balance_point INTEGER DEFAULT 0,
                updated_at INTEGER DEFAULT 0
            )
        ''')

        cur.execute(
            "INSERT OR IGNORE INTO treasury (id, balance_coin, balance_point, updated_at) VALUES (1, 10000000, 0, 0)")

        cur.execute('''
            CREATE TABLE IF NOT EXISTS check_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id TEXT,
                user_id INTEGER,
                activated_at INTEGER,
                UNIQUE(check_id, user_id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована успешно")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")


def ensure_all_columns():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        required_columns_users = {
            'user_id': 'INTEGER PRIMARY KEY',
            'username': 'TEXT DEFAULT ""',
            'display_name': 'TEXT DEFAULT ""',
            'first_name': 'TEXT DEFAULT ""',
            'last_name': 'TEXT DEFAULT ""',
            'balance_coin': 'INTEGER DEFAULT 0',
            'balance_point': 'INTEGER DEFAULT 0',
            'bonus_last_time': 'INTEGER DEFAULT 0',
            'banned_until': 'INTEGER DEFAULT 0',
            'muted_until': 'INTEGER DEFAULT 0',
            'ban_reason': 'TEXT DEFAULT ""',
            'mute_reason': 'TEXT DEFAULT ""',
            'registered': 'INTEGER DEFAULT 1',
            'total_wins': 'INTEGER DEFAULT 0',
            'total_losses': 'INTEGER DEFAULT 0',
            'total_games': 'INTEGER DEFAULT 0',
            'referral_code': 'TEXT DEFAULT ""',
            'referred_by': 'INTEGER DEFAULT 0',
            'referral_earnings': 'INTEGER DEFAULT 0',
            'referral_percent': 'INTEGER DEFAULT 5',
            'referral_withdrawn': 'INTEGER DEFAULT 0',
            'created_at': 'INTEGER DEFAULT 0',
            'is_anonymous': 'INTEGER DEFAULT 0',
            'stars_balance': 'INTEGER DEFAULT 0',
            'last_roulette_time': 'INTEGER DEFAULT 0',
            'last_fortune_time': 'INTEGER DEFAULT 0',
            'bank_balance': 'INTEGER DEFAULT 0',
            'last_spin_time': 'INTEGER DEFAULT 0',
            'about_text': 'TEXT DEFAULT ""',
            'rank_title': 'TEXT DEFAULT "Новичок"',
            'custom_username': 'TEXT DEFAULT ""',
            'is_scammer': 'INTEGER DEFAULT 0',
            'is_admin_rank': 'INTEGER DEFAULT 0',
            'is_donater': 'INTEGER DEFAULT 0',
            'is_official': 'INTEGER DEFAULT 0',
            'last_game_time': 'INTEGER DEFAULT 0',
            'daily_bonus_last': 'INTEGER DEFAULT 0',
            'daily_bonus_streak': 'INTEGER DEFAULT 0',
            'total_games_day': 'INTEGER DEFAULT 0',
            'last_game_day': 'INTEGER DEFAULT 0',
            'titles': 'TEXT DEFAULT "[]"',
            'treasury_access': 'INTEGER DEFAULT 0',
        }

        cur.execute("PRAGMA table_info(users)")
        existing_columns_users = [col[1] for col in cur.fetchall()]

        for col_name, col_type in required_columns_users.items():
            if col_name not in existing_columns_users and col_name != 'user_id':
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    logger.info(f"✅ Добавлена колонка users.{col_name}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"⚠️ Не удалось добавить users.{col_name}: {e}")

        required_columns_nft = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'owner_id': 'INTEGER',
            'name': 'TEXT',
            'level': 'INTEGER DEFAULT 1',
            'rarity': 'TEXT DEFAULT "common"',
            'price': 'INTEGER',
            'created_at': 'INTEGER',
            'for_sale': 'INTEGER DEFAULT 0',
            'sale_price': 'INTEGER DEFAULT 0',
            'description': 'TEXT DEFAULT ""'
        }

        cur.execute("PRAGMA table_info(nft_items)")
        existing_columns_nft = [col[1] for col in cur.fetchall()]

        for col_name, col_type in required_columns_nft.items():
            if col_name not in existing_columns_nft and col_name != 'id':
                try:
                    cur.execute(f"ALTER TABLE nft_items ADD COLUMN {col_name} {col_type}")
                    logger.info(f"✅ Добавлена колонка nft_items.{col_name}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"⚠️ Не удалось добавить nft_items.{col_name}: {e}")

        conn.commit()
        conn.close()
        logger.info("✅ Все колонки существуют")

    except Exception as e:
        logger.error(f"❌ Ошибка проверки колонок: {e}")


def get_user(user_id: int) -> Optional[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO users (user_id, balance_coin, balance_point, total_wins, total_losses, total_games, created_at, stars_balance, last_game_time) 
                VALUES (?, 0, 0, 0, 0, 0, ?, 0, 0)
            """, (user_id, int(time.time())))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        conn.close()

        columns = [
            'user_id', 'username', 'display_name', 'first_name', 'last_name',
            'balance_coin', 'balance_point', 'bonus_last_time',
            'banned_until', 'muted_until', 'ban_reason', 'mute_reason',
            'registered', 'total_wins', 'total_losses', 'total_games',
            'referral_code', 'referred_by', 'referral_earnings', 'referral_percent',
            'referral_withdrawn', 'created_at', 'is_anonymous', 'stars_balance',
            'last_roulette_time', 'last_fortune_time', 'bank_balance',
            'last_spin_time', 'about_text', 'rank_title', 'custom_username',
            'is_scammer', 'is_admin_rank', 'is_donater', 'is_official', 'last_game_time',
            'daily_bonus_last', 'daily_bonus_streak',
            'total_games_day', 'last_game_day', 'titles', 'treasury_access',
            'event_day', 'event_stash_last', 'event_boss_dmg', 'event_boss_last',
            'event_wheel_last', 'event_points',
            'quest_q_games', 'quest_q_wins', 'quest_q_stash', 'quest_q_boss',
            'db5_checked', 'db5_last', 'db5_streak', 'db5_opened', 'db5_grid', 'db5_won',
            'inventory'
        ]

        result = dict(zip(columns, row))
        if 'titles' in result and not isinstance(result['titles'], str):
            result['titles'] = '[]'
        return result
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        return None


def update_user(user_id: int, **kwargs) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        for key, value in kwargs.items():
            cur.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
        return False


def add_bet_history(user_id: int, game_type: str, bet_amount: int, win_amount: int, is_win: int,
                    bet_data: str = "") -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bet_history 
            (user_id, game_type, bet_amount, win_amount, is_win, bet_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, game_type, bet_amount, win_amount, is_win, bet_data, int(time.time())))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления истории ставок: {e}")
        return False


def get_user_stats(user_id: int) -> Dict:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losses,
                SUM(win_amount) as total_won
            FROM bet_history 
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                'total_bets': row[0] or 0,
                'wins': row[1] or 0,
                'losses': row[2] or 0,
                'total_won': row[3] or 0
            }
        return {'total_bets': 0, 'wins': 0, 'losses': 0, 'total_won': 0}
    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
        return {'total_bets': 0, 'wins': 0, 'losses': 0, 'total_won': 0}


def get_user_bet_history(user_id: int, limit: int = 10) -> List[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, game_type, bet_amount, win_amount, is_win, bet_data, created_at
            FROM bet_history 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                'id': row[0],
                'game_type': row[1],
                'bet_amount': row[2],
                'win_amount': row[3],
                'is_win': row[4],
                'bet_data': row[5],
                'created_at': row[6]
            })
        return result
    except Exception as e:
        logger.error(f"Ошибка получения истории ставок: {e}")
        return []


def generate_referral_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def get_referrals_count(user_id: int) -> int:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Ошибка получения рефералов: {e}")
        return 0


def get_referral_earnings(user_id: int) -> int:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT SUM(total_earned) FROM referrals WHERE referrer_id = ?", (user_id,))
        total = cur.fetchone()[0]
        conn.close()
        return total or 0
    except Exception as e:
        logger.error(f"Ошибка получения реферальных средств: {e}")
        return 0


def generate_check_id() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def format_number(num: int) -> str:
    return f"{num:,}".replace(",", " ")


def parse_amount(text: str) -> int:
    text = str(text).lower().strip()
    multiplier = 1
    if text.endswith('ккк'):
        multiplier = 1000000000
        text = text[:-3]
    elif text.endswith('кк'):
        multiplier = 1000000
        text = text[:-2]
    elif text.endswith('к'):
        multiplier = 1000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def parse_bet_amount(text: str, user_balance: int) -> tuple:
    text = str(text).lower().strip()
    if text in ['все', 'вб']:
        return user_balance, user_balance
    amount = parse_amount(text)
    return amount, amount


def get_time_until(timestamp: int) -> str:
    now = int(time.time())
    diff = timestamp - now
    if diff <= 0:
        return "0 секунд"
    hours = diff // 3600
    minutes = (diff % 3600) // 60
    seconds = diff % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if seconds > 0:
        parts.append(f"{seconds} сек")
    return " ".join(parts)


def check_bonus_available(user_id: int) -> Tuple[bool, int]:
    user = get_user(user_id)
    if not user:
        return False, 0
    now = int(time.time())
    last = user.get('bonus_last_time', 0)
    next_bonus = last + 3600
    if now >= next_bonus:
        return True, 0
    else:
        return False, next_bonus - now


def get_roulette_color(number: int) -> str:
    if number == 0:
        return "зелёное"
    red = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    if number in red:
        return "красное"
    else:
        return "чёрное"


def get_roulette_emoji(number: int) -> str:
    if number == 0:
        return "🟢"
    red = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    if number in red:
        return "🔴"
    else:
        return "⚫"


def is_admin(user_id: int) -> bool:
    """Owner, configured admins, and users explicitly promoted in the database."""
    if (OWNER_ID > 0 and user_id == OWNER_ID) or user_id in ADMIN_IDS:
        return True
    try:
        with sqlite3.connect(DB_FILE) as conn:
            row = conn.execute("SELECT is_admin_rank FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row[0])
    except sqlite3.Error:
        return False


def is_banned(user_id: int) -> Tuple[bool, str, int]:
    user = get_user(user_id)
    if not user:
        return False, "", 0
    now = int(time.time())
    if user.get('banned_until', 0) > now:
        return True, user.get('ban_reason', ''), user.get('banned_until', 0)
    return False, "", 0


def is_muted(user_id: int) -> Tuple[bool, str, int]:
    user = get_user(user_id)
    if not user:
        return False, "", 0
    now = int(time.time())
    if user.get('muted_until', 0) > now:
        return True, user.get('mute_reason', ''), user.get('muted_until', 0)
    return False, "", 0


def get_user_by_username(username: str) -> Optional[Dict]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? OR custom_username = ?", (username, username))
        row = cur.fetchone()
        conn.close()
        if row:
            columns = [
                'user_id', 'username', 'display_name', 'first_name', 'last_name',
                'balance_coin', 'balance_point', 'bonus_last_time',
                'banned_until', 'muted_until', 'ban_reason', 'mute_reason',
                'registered', 'total_wins', 'total_losses', 'total_games',
                'referral_code', 'referred_by', 'referral_earnings', 'referral_percent',
                'referral_withdrawn', 'created_at', 'is_anonymous', 'stars_balance',
                'last_roulette_time', 'last_fortune_time', 'bank_balance',
                'last_spin_time', 'about_text', 'rank_title', 'custom_username',
                'is_scammer', 'is_admin_rank', 'is_donater', 'is_official', 'last_game_time',
                'daily_bonus_last', 'daily_bonus_streak',
                'total_games_day', 'last_game_day', 'titles', 'treasury_access'
            ]
            return dict(zip(columns, row))
        return None
    except Exception as e:
        logger.error(f"Ошибка получения пользователя по username {username}: {e}")
        return None


def add_transfer_history(from_user_id: int, to_user_id: int, amount: int, comment: str = "") -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transfer_history (from_user_id, to_user_id, amount, created_at, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (from_user_id, to_user_id, amount, int(time.time()), comment))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления истории перевода: {e}")
        return False


def get_all_users() -> List[int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        return []


def get_top_players(limit: int = 10) -> List[Tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, display_name, balance_coin 
            FROM users 
            ORDER BY balance_coin DESC 
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Ошибка получения топ игроков: {e}")
        return []


def get_top_point(limit: int = 10) -> List[Tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, display_name, balance_point 
            FROM users 
            ORDER BY balance_point DESC 
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Ошибка получения топ поинтов: {e}")
        return []


def get_top_games(limit: int = 10) -> List[Tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, display_name, total_games 
            FROM users 
            ORDER BY total_games DESC 
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Ошибка получения топ игр: {e}")
        return []


def get_top_games_day(limit: int = 10) -> List[Tuple]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, display_name, total_games_day 
            FROM users 
            ORDER BY total_games_day DESC 
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Ошибка получения топ игр за день: {e}")
        return []


def get_treasury_balance() -> Tuple[int, int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT balance_coin, balance_point FROM treasury WHERE id = 1")
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0] or 0, row[1] or 0
        return 0, 0
    except Exception as e:
        logger.error(f"Ошибка получения баланса казны: {e}")
        return 0, 0


def update_treasury(balance_coin: int, balance_point: int) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE treasury SET balance_coin = ?, balance_point = ?, updated_at = ? WHERE id = 1",
                    (balance_coin, balance_point, int(time.time())))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления казны: {e}")
        return False


# ==================== CRYPTO PAY API ====================

async def create_crypto_invoice(user_id: int, amount_vfg: int, currency: str) -> Optional[Dict]:
    try:
        amount_crypto = CRYPTO_PRICES.get(currency, 1.0) * (amount_vfg / 100000)

        async with aiohttp.ClientSession() as session:
            headers = {
                "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN,
                "Content-Type": "application/json"
            }
            data = {
                "amount": amount_crypto,
                "currency_type": "crypto",
                "asset": currency,
                "description": f"Пополнение RCOIN·BOT на {amount_vfg} RCOIN",
                "payload": str(user_id)
            }

            async with session.post(f"{CRYPTO_PAY_URL}/createInvoice", headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('ok'):
                        invoice = result.get('result')
                        conn = sqlite3.connect(DB_FILE)
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO crypto_payments (user_id, amount, currency, amount_crypto, invoice_id, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (user_id, amount_vfg, currency, amount_crypto, invoice.get('invoice_id'),
                              int(time.time())))
                        conn.commit()
                        conn.close()
                        return invoice
        return None
    except Exception as e:
        logger.error(f"Ошибка создания крипто-счета: {e}")
        return None


async def check_crypto_payment(invoice_id: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN,
                "Content-Type": "application/json"
            }
            async with session.get(f"{CRYPTO_PAY_URL}/getInvoices?invoice_ids={invoice_id}", headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('ok') and result.get('result'):
                        invoice = result['result']['items'][0]
                        return invoice.get('status', 'pending')
        return 'pending'
    except Exception as e:
        logger.error(f"Ошибка проверки крипто-платежа: {e}")
        return 'pending'


async def check_crypto_payment_by_address(amount: int, currency: str) -> bool:
    try:
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки оплаты: {e}")
        return False


# ==================== ПРОВЕРКА ПОДПИСКИ ====================

async def check_required_subscription(user_id: int) -> Dict[str, bool]:
    results = {'channel': False, 'chat': False}
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        results['channel'] = member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки на канал {REQUIRED_CHANNEL} для {user_id}: {e}")
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHAT, user_id=user_id)
        results['chat'] = member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки на чат {REQUIRED_CHAT} для {user_id}: {e}")
    return results


async def is_subscribed_to_channel(user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки на канал {channel} для {user_id}: {e}")
        return False


# ==================== FSM СОСТОЯНИЯ ====================

class GameState(StatesGroup):
    roulette_waiting = State()
    roulette_bet = State()
    dice_waiting = State()
    dice_bet = State()
    fortune_waiting = State()
    sun_waiting = State()
    mines_playing = State()
    blackjack_playing = State()
    darts_playing = State()
    crash_playing = State()
    pyramid_playing = State()
    miner_playing = State()

    exchange_waiting = State()
    exchange_orders = State()

    ad_channel = State()
    ad_price = State()
    ad_subs = State()

    check_amount = State()
    check_activations = State()
    check_desc = State()
    check_pass = State()
    check_pass_enter = State()

    admin_target = State()
    admin_duration = State()
    admin_reason = State()
    admin_amount = State()
    admin_action = State()
    admin_mailing = State()

    promo_create_code = State()
    promo_create_reward = State()
    promo_create_uses = State()

    bank_deposit = State()
    bank_withdraw = State()

    change_name = State()
    games_menu = State()

    stars_donate = State()
    crypto_amount = State()

    miner_work = State()

    nft_create = State()
    nft_buy = State()
    nft_transfer = State()
    nft_upgrade = State()
    nft_sell_price = State()
    nft_sell_desc = State()
    nft_buy_username = State()

    ttt_play = State()
    ttt_join = State()
    ttt_bet = State()

    hi_lo_play = State()


class AdminStates(StatesGroup):
    admin_target = State()
    admin_duration = State()
    admin_reason = State()
    admin_amount = State()
    admin_mailing = State()


class TreasuryStates(StatesGroup):
    treasury_amount = State()


# ==================== МИДЛВЭРЫ ====================

class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            if is_admin(user_id):
                return await handler(event, data)
            banned, reason, until = is_banned(user_id)
            if banned:
                await event.answer(
                    f"{PREMIUM_EMOJI_TEXT['lock']} Вы забанены до {datetime.fromtimestamp(until).strftime('%d.%m.%Y %H:%M')}\n"
                    f"Причина: {reason}"
                )
                return
            muted, reason, until = is_muted(user_id)
            if muted:
                await event.answer(
                    f"{PREMIUM_EMOJI_TEXT['lock']} Вы замучены до {datetime.fromtimestamp(until).strftime('%d.%m.%Y %H:%M')}\n"
                    f"Причина: {reason}"
                )
                return
            text = event.text or ""
            command = text.split()[0].split("@", 1)[0].lower() if text.startswith("/") else ""
            public_commands = {"/start", "/menu", "/help", "/помощь"}
            protected_command = text.startswith("/") and command not in public_commands
            protected_text = text.lower().startswith(
                ('куб', 'рулетка', 'фортуна', 'кф', 'солнце', 'игры', 'профиль', 'баскет', 'мины', 'дартс', 'очко',
                 'банк', 'барабан', 'краш', 'пирамида', 'майнер', 'хило', 'маркет', 'кн'))
            if protected_command or protected_text:
                sub_status = await check_required_subscription(user_id)
                if not sub_status['channel'] or not sub_status['chat']:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"Подписаться на канал",
                                              url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
                        [InlineKeyboardButton(text=f"Подписаться на чат",
                                              url=f"https://t.me/{REQUIRED_CHAT.replace('@', '')}")],
                        [InlineKeyboardButton(text=f"Проверить подписку", callback_data="check_sub")]
                    ])
                    await event.answer(
                        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Для использования бота необходимо подписаться:</b>\n\n"
                        f"{'✅' if sub_status['channel'] else '❌'} Канал: {REQUIRED_CHANNEL}\n"
                        f"{'✅' if sub_status['chat'] else '❌'} Чат: {REQUIRED_CHAT}\n\n"
                        "Подпишитесь и нажмите кнопку проверки.",
                        reply_markup=kb
                    )
                    return
        return await handler(event, data)


dp.message.middleware(SubscriptionMiddleware())


@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    sub_status = await check_required_subscription(user_id)
    if sub_status['channel'] and sub_status['chat']:
        await callback.message.delete()
        await callback.message.answer(
            f"{PREMIUM_EMOJI_TEXT['check']} <b>Подписка подтверждена!</b>\nТеперь вы можете использовать бота.")
        await callback.answer("Подписка подтверждена!")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Подписаться на канал",
                                  url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton(text=f"Подписаться на чат", url=f"https://t.me/{REQUIRED_CHAT.replace('@', '')}")],
            [InlineKeyboardButton(text=f"Проверить подписку", callback_data="check_sub")]
        ])
        text = f"{PREMIUM_EMOJI_TEXT['lock']} <b>Вы не подписаны на все обязательные ресурсы:</b>\n\n"
        text += f"{'✅' if sub_status['channel'] else '❌'} Канал: {REQUIRED_CHANNEL}\n"
        text += f"{'✅' if sub_status['chat'] else '❌'} Чат: {REQUIRED_CHAT}"
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer("Подписка не подтверждена")


# ==================== ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КНОПОК БАЛАНСА ====================

def get_balance_keyboard(user_id: int) -> Tuple[InlineKeyboardMarkup, str]:
    available, time_left = check_bonus_available(user_id)
    buttons = []
    if available:
        buttons.append([InlineKeyboardButton(
            text="Получить бонус",
            callback_data="get_bonus",
            icon_custom_emoji_id=EMOJI_IDS["donate"]
        )])
    buttons.append([InlineKeyboardButton(
        text="Заработать", callback_data="go_earn",
        icon_custom_emoji_id=EMOJI_IDS["balance"]
    )])
    buttons.extend([
        [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
         InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton(text="❄️ Ивенты", callback_data="menu_events"),
         InlineKeyboardButton(text="🎒 Склад", callback_data="menu_stash")],
        [InlineKeyboardButton(text="❔ Помощь", callback_data="menu_help")]
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    bonus_text = ""
    if not available:
        bonus_text = f"\n⏳ Бонус через: {get_time_until(int(time.time()) + time_left)}"
    return kb, bonus_text


# ==================== КЛАВИАТУРА ИГР ====================

def get_games_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    games = [
        ("Кубик", "game_dice_desc", EMOJI_IDS["dice"]),
        ("Рулетка", "game_roulette_desc", EMOJI_IDS["roulette"]),
        ("Фортуна", "game_fortune_desc", EMOJI_IDS["fortune"]),
        ("Баскет", "game_basket_desc", EMOJI_IDS["basket"]),
        ("Мины", "game_mines_desc", EMOJI_IDS["mines"]),
        ("Дартс", "game_darts_desc", EMOJI_IDS["darts"]),
        ("Очко", "game_blackjack_desc", EMOJI_IDS["blackjack"]),
        ("Краш", "game_crash_desc", EMOJI_IDS["crash"]),
        ("Солнце", "game_sun_desc", EMOJI_IDS["sun"]),
        ("Охота", "game_hunt_desc", EMOJI_IDS["hunt"]),
        ("Спин", "game_spin_desc", EMOJI_IDS["spin"]),
        ("Футбол", "game_football_desc", EMOJI_IDS["football"]),
        ("Пирамида", "game_pyramid_desc", EMOJI_IDS["pyramid"]),
        ("Майнер", "game_miner_desc", EMOJI_IDS["miner"]),
        ("Хи-Ло", "game_hi_lo_desc", EMOJI_IDS["hi_lo"]),
        ("Крестики-Нолики", "game_ttt_desc", EMOJI_IDS["ttt"]),
    ]

    per_page = 6
    total_pages = (len(games) + per_page - 1) // per_page
    start = page * per_page
    end = min(start + per_page, len(games))

    builder = InlineKeyboardBuilder()

    for name, callback_data, emoji_id in games[start:end]:
        builder.button(
            text=name,
            callback_data=callback_data,
            icon_custom_emoji_id=emoji_id
        )
    builder.adjust(2)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"games_page_{page - 1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"games_page_{page + 1}"
        ))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(
        text="🏠 Назад",
        callback_data="back_to_balance"
    ))

    return builder.as_markup()


# ==================== ОПИСАНИЯ ИГР ====================

GAME_DESCRIPTIONS = {
    "game_dice_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['dice']} Кубик",
        "description": (
            "Классическая игра с кубиком!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Выберите число (1-6) или комбинацию\n"
            "• Сделайте ставку\n"
            "• Если выпадает ваше число — вы побеждаете!\n\n"
            "📈 <b>Коэффициенты:</b>\n"
            "• Число 1-6 → x5\n"
            "• Чёт/Нечёт → x2\n"
            "• Мал (1-3)/Бол (4-6) → x2\n"
            "• Радужный → x10 (шанс 1%)\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>куб 100 3</code> – ставка 100 на число 3\n"
            "<code>куб 100 1 2 3</code> – ставка на несколько чисел"
        )
    },
    "game_roulette_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['roulette']} Рулетка",
        "description": (
            "Европейская рулетка с зеро!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Выберите тип ставки\n"
            "• Сделайте ставку\n"
            "• Ждите результат!\n\n"
            "📈 <b>Коэффициенты:</b>\n"
            "• Красное/Чёрное → x2\n"
            "• Чёт/Нечёт → x2\n"
            "• 1-18 / 19-36 → x2\n"
            "• Зеро → x35\n"
            "• Число 0-36 → x35\n\n"
            "⏱ КД: 3 секунды\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>рулетка 100к к</code> – красное\n"
            "<code>рулетка 100 7</code> – число 7"
        )
    },
    "game_fortune_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['fortune']} Колесо Фортуны",
        "description": (
            "Крути колесо и получай множитель!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Колесо определяет множитель\n\n"
            "📈 <b>Шансы:</b>\n"
            "• x0 → 47%\n"
            "• x0.5 → 23%\n"
            "• x1 → 15%\n"
            "• x2 → 10%\n"
            "• x5 → 5%\n\n"
            "⏱ КД: 2 секунды\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>фортуна 100</code> или <code>кф 100</code>"
        )
    },
    "game_basket_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['basket']} Баскет",
        "description": (
            "Кидай мяч и угадывай результат!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Выберите исход броска\n"
            "• Сделайте ставку\n\n"
            "📈 <b>Коэффициенты:</b>\n"
            "• Попадание → x2.5\n"
            "• Мимо → x1.6\n"
            "• Чистое попадание → x5\n"
            "• Застрял → x5\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>баскет 100 п</code> – попадание\n"
            "<code>баскет 100 м</code> – мимо\n"
            "<code>баскет 100 чп</code> – чистое попадание\n"
            "<code>баскет 100 з</code> – застрял"
        )
    },
    "game_mines_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['mines']} Мины",
        "description": (
            "Открывай клетки и не попади на мину!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Поле 5×5 (25 клеток)\n"
            "• Выберите количество мин (1-10)\n"
            "• Открывайте клетки\n"
            "• Чем больше открыто — тем выше множитель\n"
            "• Можно забрать выигрыш в любой момент\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>мины 100 3</code> – 100 RCOIN, 3 мины"
        )
    },
    "game_darts_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['darts']} Дартс",
        "description": (
            "Метайте дротики и угадывайте сектор!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Выберите сектор\n"
            "• Сделайте ставку\n\n"
            "📈 <b>Коэффициенты:</b>\n"
            "• Красное → x2\n"
            "• Белое → x2\n"
            "• Центр → x5\n"
            "• Мимо → x5\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>дартс 100 к</code> – красное\n"
            "<code>дартс 100 б</code> – белое\n"
            "<code>дартс 100 ц</code> – центр\n"
            "<code>дартс 100 м</code> – мимо"
        )
    },
    "game_blackjack_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['blackjack']} Очко (Блэкджек)",
        "description": (
            "Игра против дилера. Набери 21!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Получите карты\n"
            "• Решайте: взять ещё или остановиться\n"
            "• Победа если у вас больше очков чем у дилера\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>очко 100</code> – ставка 100 RCOIN"
        )
    },
    "game_crash_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['crash']} Краш",
        "description": (
            "Ракета взлетает... Забери выигрыш до краша!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Ракета летит, множитель растёт\n"
            "• Заберите выигрыш в любой момент\n"
            "• Если ракета крашнулась — ставка сгорает\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>краш 100 2.5</code> – ставка 100 RCOIN, авто-забор при 2.5x\n"
            "<code>краш 100</code> – ставка 100 RCOIN"
        )
    },
    "game_sun_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['sun']} Солнце",
        "description": (
            "Найди солнце на поле 3×3!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Выберите клетку\n"
            "• Получите случайный множитель\n\n"
            "📈 <b>Множители:</b>\n"
            "x0, x1, x2, x3, x4, x10\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>солнце 100</code> – ставка 100 RCOIN"
        )
    },
    "game_hunt_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['hunt']} Охота",
        "description": (
            "Охота на диких зверей!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Вы охотник, выбираете цель\n"
            "• Если попали — получаете множитель!\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>охота 100</code> – ставка 100 RCOIN"
        )
    },
    "game_spin_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['spin']} Спин",
        "description": (
            "Крутите слот-машину с фруктами!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Автомат выдаёт комбинацию\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>спин 100</code> – ставка 100 RCOIN"
        )
    },
    "game_football_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['football']} Футбол",
        "description": (
            "Удар по воротам!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Выберите исход удара\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>футбол 100 г</code> – гол\n"
            "<code>футбол 100 м</code> – мимо"
        )
    },
    "game_pyramid_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['pyramid']} Пирамида",
        "description": (
            "Поднимайся по пирамиде и увеличивай множитель!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Вы находитесь на уровне 1\n"
            "• Каждый новый уровень увеличивает множитель\n"
            "• Можно забрать выигрыш в любой момент\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>пирамида 100</code> – ставка 100 RCOIN"
        )
    },
    "game_miner_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['miner']} Майнер",
        "description": (
            "Пассивный заработок RCOIN!\n\n"
            "🏗️ <b>Как работает:</b>\n"
            "• Купите уровень майнинга\n"
            "• Получайте доход каждый час\n"
            "• Улучшайте свои здания\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>майнер</code> – открыть меню майнера"
        )
    },
    "game_hi_lo_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['hi_lo']} Хи-Ло",
        "description": (
            "Угадай, будет следующая карта выше или ниже!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Сделайте ставку\n"
            "• Вам показывают карту\n"
            "• Угадайте, будет следующая карта выше или ниже\n"
            "• Если угадали — множитель растёт!\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>хило 100</code> – ставка 100 RCOIN"
        )
    },
    "game_ttt_desc": {
        "title": f"{PREMIUM_EMOJI_TEXT['ttt']} Крестики-Нолики",
        "description": (
            "Играйте с друзьями в крестики-нолики на деньги!\n\n"
            "🎯 <b>Как играть:</b>\n"
            "• Отправьте <code>кн 1000</code> (ответом на сообщение соперника)\n"
            "• Соперник принимает или отклоняет вызов\n"
            "• Играйте по очереди\n"
            "• Победитель получает ставку соперника!\n\n"
            "📈 <b>Правила:</b>\n"
            "• Игроки делают ходы по очереди\n"
            "• Тот, кто соберет 3 в ряд - побеждает\n"
            "• При ничьей ставки возвращаются\n\n"
            "📝 <b>Формат:</b>\n"
            "<code>кн 1000</code> в ответ на сообщение соперника"
        )
    }
}


@dp.callback_query(F.data.startswith("games_page_"))
async def games_page_callback(callback: CallbackQuery):
    page = int(callback.data.split('_')[2])
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Выберите игру:</b>\n\n"
        "Нажмите на кнопку с названием игры,\n"
        "чтобы узнать подробности и правила.",
        reply_markup=get_games_keyboard(page)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("game_"))
async def game_desc_callback(callback: CallbackQuery):
    game_key = callback.data
    game_info = GAME_DESCRIPTIONS.get(game_key)

    if not game_info:
        await callback.answer("❌ Описание игры не найдено.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Назад к играм",
            callback_data="back_to_games",
            icon_custom_emoji_id=EMOJI_IDS["games"]
        )]
    ])

    text = f"{game_info['title']}\n\n{game_info['description']}"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "back_to_games")
async def back_to_games(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Выберите игру:</b>\n\n"
        "Нажмите на кнопку с названием игры,\n"
        "чтобы узнать подробности и правила.",
        reply_markup=get_games_keyboard(0)
    )
    await callback.answer()


# ==================== ГЕНЕРАЦИЯ ЧЕКОВ БОТОМ ====================

async def generate_auto_checks():
    """Генерирует чеки каждые 1.3 часа (4680 секунд)"""
    while True:
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("""
                SELECT check_id FROM checks 
                WHERE is_active = 1 AND owner_id = 0
                LIMIT 1
            """)
            existing = cur.fetchone()

            if not existing:
                check_id = generate_check_id()
                amount = 15000000
                max_activations = 15

                treasury_vfg, treasury_point = get_treasury_balance()
                if treasury_vfg < amount:
                    logger.warning(
                        f"⚠️ Недостаточно в казне для создания чека! Нужно: {format_number(amount)}, доступно: {format_number(treasury_vfg)}")
                    conn.close()
                    await asyncio.sleep(4680)
                    continue

                update_treasury(treasury_vfg - amount, treasury_point)

                cur.execute("""
                    INSERT INTO checks (check_id, owner_id, amount, max_activations, description, created_at)
                    VALUES (?, 0, ?, ?, ?, ?)
                """, (check_id, amount, max_activations,
                      f"🎁 Автоматический чек для RCOIN·BOT! {amount // 1000000}кк RCOIN {max_activations} активаций",
                      int(time.time())))
                conn.commit()
                conn.close()

                logger.info(f"✅ Создан автоматический чек: {check_id} на {format_number(amount)} RCOIN")

                try:
                    link = f"https://t.me/{BOT_USERNAME}?start=check_{check_id}"
                    await bot.send_message(
                        REQUIRED_CHAT,
                        f"🎉 <b>НОВЫЙ АВТОМАТИЧЕСКИЙ ЧЕК!</b>\n\n"
                        f"💰 <b>Сумма:</b> {format_number(amount)} RCOIN\n"
                        f"📊 <b>Активаций:</b> {max_activations}\n\n"
                        f"🔗 <b>Активируй чек:</b>\n"
                        f"<code>{link}</code>\n\n"
                        f"<i>Удачи всем в пушке! 🚀</i>\n"
                        f"Каждый может активировать чек ТОЛЬКО 1 РАЗ!",
                        disable_web_page_preview=True
                    )
                    logger.info(f"✅ Чек {check_id} отправлен в чат")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки чека в чат: {e}")
            else:
                conn.close()

        except Exception as e:
            logger.error(f"❌ Ошибка в генераторе чеков: {e}")

        await asyncio.sleep(4680)


# ==================== КОМАНДА /START ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject = None):
    user_id = message.from_user.id
    username = message.from_user.username or "без_ника"
    display_name = message.from_user.first_name or username
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    user = get_user(user_id)
    update_data = {
        'username': username,
        'display_name': display_name,
        'first_name': first_name,
        'last_name': last_name
    }
    if user and user.get('registered', 0) == 0:
        update_data['registered'] = 1
    update_user(user_id, **update_data)

    if command and command.args:
        args = command.args.strip()
        if args.startswith('promo_'):
            promo_code = args.replace('promo_', '')
            await activate_promo(message, promo_code)
            return
        elif args.startswith('check_'):
            check_id = args.replace('check_', '')
            await activate_check(message, check_id)
            return

    user = get_user(user_id)
    balance_coin = user.get('balance_coin', 0)
    balance_point = user.get('balance_point', 0)
    display_name = user.get('display_name', username)
    kb, bonus_text = get_balance_keyboard(user_id)

    welcome_text = (
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Добро пожаловать в RCOIN·BOT!</b>\n"
        f"Удача на твоей стороне!\n\n"
        f"{PREMIUM_EMOJI_TEXT['profile']} <b>Имя:</b> {display_name}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс:</b> {format_number(balance_coin)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Баланс:</b> {format_number(balance_point)} RBP{bonus_text}\n"
        f"{PREMIUM_EMOJI_TEXT['star']} <b>Звёзды:</b> {user.get('stars_balance', 0)}\n"
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>Банк:</b> {format_number(user.get('bank_balance', 0))} RCOIN\n\n"
        f"📋 <b>Доступные команды:</b>\n"
        f"• {PREMIUM_EMOJI_TEXT['games']} <b>Игры</b> – список игр\n"
        f"• {PREMIUM_EMOJI_TEXT['profile']} <b>Профиль</b> – твой профиль\n"
        f"• <b>Б</b> или <b>б</b> – показать баланс\n"
        f"• <b>Бонус</b> – получить бонус (2500 RCOIN раз в час)\n"
        f"• <b>Топ</b> – топ игроков\n"
        f"• <b>Статистика</b> – твоя статистика\n"
        f"{PREMIUM_EMOJI_TEXT['ad']} <b>Рекл</b> – рекламный центр\n"
        f"• <b>Поинт</b> – баланс RBP\n"
        f"• <b>Обмен</b> – обмен валют\n"
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Чек</b> – чековая книжка\n"
        f"{PREMIUM_EMOJI_TEXT['donate']} <b>Донат</b> – пополнение\n"
        f"{PREMIUM_EMOJI_TEXT['referral']} <b>Рефералы</b> – реферальная система\n"
        f"• <b>Помощь</b> – помощь\n"
        f"• <b>Обновы</b> – список обновлений\n"
        f"{PREMIUM_EMOJI_TEXT['settings']} <b>Настройки</b> – настройки бота\n"
        f"• <b>О боте</b> – информация о боте\n"
        f"• <b>История</b> – история игр\n"
        f"• <b>Промо</b> – активировать промокод\n"
        f"• <b>Ежедневный</b> – ежедневный бонус\n"
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>Банк</b> – банковская система\n"
        f"• <b>Барабан</b> – крутить барабан (раз в 24ч)\n"
        f"• <b>О себе</b> – изменить описание профиля\n"
        f"{PREMIUM_EMOJI_TEXT['market']} <b>Маркет</b> – маркет NFT и юзернеймов\n"
        f"{PREMIUM_EMOJI_TEXT['games']} <b>КН</b> – крестики-нолики\n"
        f"{PREMIUM_EMOJI_TEXT['treasury']} <b>Казна</b> – баланс казны\n\n"
        f"🎲 <b>Команды игр:</b>\n"
        f"• <code>куб 100 3</code> – ставка на число\n"
        f"• <code>рулетка 100к к</code> – ставка на красное\n"
        f"• <code>фортуна 200к</code> – колесо фортуны\n"
        f"• <code>солнце 100</code> – игра Солнце\n"
        f"• <code>баскет 100 п</code> – игра Баскет\n"
        f"• <code>мины 100 3</code> – игра Мины\n"
        f"• <code>дартс 100 к</code> – игра Дартс\n"
        f"• <code>очко 100</code> – игра Очко\n"
        f"• <code>краш 100 2.5</code> – игра Краш\n"
        f"• <code>охота 100</code> – игра Охота\n"
        f"• <code>спин 100</code> – игра Спин\n"
        f"• <code>футбол 100 г</code> – игра Футбол\n"
        f"• <code>пирамида 100</code> – игра Пирамида\n"
        f"• <code>майнер</code> – меню Майнера\n"
        f"• <code>хило 100</code> – игра Хи-Ло\n"
        f"• <code>кн 1000</code> (в ответ на сообщение соперника) – Крестики-Нолики\n\n"
        f"💸 <b>Перевод RCOIN:</b>\n"
        f"• <code>Дать 100к @username</code> – перевести 100 000 RCOIN\n"
        f"• <code>Нк 1000 123456789</code> – перевести 1000 RCOIN по ID\n\n"
        f"<i>Приятной игры!</i>"
    )

    try:
        if Path(IMAGE_PATH).exists():
            await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(IMAGE_PATH),
                caption=welcome_text,
                reply_markup=kb
            )
        else:
            await message.answer(welcome_text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Ошибка отправки приветствия: {e}")
        await message.answer(welcome_text, reply_markup=kb)


# ==================== КОМАНДА МАРКЕТ ====================

@dp.message(F.text.lower() == "маркет")
@dp.message(Command("маркет"))
async def cmd_market(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Мои NFT", callback_data="nft_my", icon_custom_emoji_id=EMOJI_IDS["nft"])],
        [InlineKeyboardButton(text=f"Маркет NFT", callback_data="nft_market",
                              icon_custom_emoji_id=EMOJI_IDS["market"])],
        [InlineKeyboardButton(text=f"Создать NFT", callback_data="nft_create", icon_custom_emoji_id=EMOJI_IDS["nft"])],
        [InlineKeyboardButton(text=f"Улучшить NFT", callback_data="nft_upgrade",
                              icon_custom_emoji_id=EMOJI_IDS["nft"])],
        [InlineKeyboardButton(text=f"Купить юзернейм", callback_data="nft_buy_username",
                              icon_custom_emoji_id=EMOJI_IDS["username_emoji"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM nft_items WHERE owner_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['market']} <b>МАРКЕТ</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['nft']} <b>Ваши NFT:</b> {count}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс:</b> {format_number(user.get('balance_coin', 0))} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>RBP:</b> {format_number(user.get('balance_point', 0))}\n\n"
        f"📌 <b>Что такое NFT?</b>\n"
        f"NFT — это уникальные цифровые предметы,\n"
        f"которые можно покупать, продавать и улучшать.\n\n"
        f"<b>Редкости и цены:</b>\n"
        f"🟢 Обычный — 1 000 000 RCOIN\n"
        f"🔵 Необычный — 10 000 000 RCOIN\n"
        f"🟣 Редкий — 50 000 000 RCOIN\n"
        f"🟠 Эпический — 150 000 000 RCOIN\n"
        f"🔴 Легендарный — 500 000 000 RCOIN\n\n"
        f"<i>Улучшайте свои NFT для увеличения цены!</i>",
        reply_markup=kb
    )


# ==================== КОМАНДА КАЗНА ====================

# ==================== КАЗНА - ПОЛНОСТЬЮ РАБОЧАЯ ====================

@dp.message(F.text.lower() == "казна")
@dp.message(Command("казна"))
async def cmd_treasury(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("❌ Ошибка")
        return

    balance_coin, balance_point = get_treasury_balance()
    treasury_access = user.get('treasury_access', 0)
    total_value = balance_coin + (balance_point * 50000)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ О казне", callback_data="treasury_info")],
    ])

    if treasury_access == 1 or is_admin(user_id):
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="💰 Пополнить", callback_data="treasury_deposit"),
            InlineKeyboardButton(text="🏦 Снять", callback_data="treasury_withdraw")
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_balance")
    ])

    await message.answer(
        f"🏛️ <b>КАЗНА</b>\n\n"
        f"💰 RCOIN: {format_number(balance_coin)}\n"
        f"💎 RBP: {format_number(balance_point)}\n"
        f"📊 Суммарно: {format_number(total_value)} RCOIN",
        reply_markup=kb
    )


@dp.callback_query(F.data == "treasury_info")
async def treasury_info_callback(callback: CallbackQuery):
    await callback.answer("📖 Казна - общий фонд бота", show_alert=True)


@dp.callback_query(F.data == "treasury_deposit")
async def treasury_deposit(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 000", callback_data="dep_1000"),
         InlineKeyboardButton(text="5 000", callback_data="dep_5000"),
         InlineKeyboardButton(text="10 000", callback_data="dep_10000")],
        [InlineKeyboardButton(text="50 000", callback_data="dep_50000"),
         InlineKeyboardButton(text="100 000", callback_data="dep_100000"),
         InlineKeyboardButton(text="500 000", callback_data="dep_500000")],
        [InlineKeyboardButton(text="1 000 000", callback_data="dep_1000000"),
         InlineKeyboardButton(text="5 000 000", callback_data="dep_5000000"),
         InlineKeyboardButton(text="10 000 000", callback_data="dep_10000000")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="dep_custom")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="treasury_back")]
    ])

    await callback.message.edit_text(
        f"💰 <b>ПОПОЛНЕНИЕ</b>\n\n"
        f"Баланс: {format_number(user.get('balance_coin', 0))} RCOIN\n"
        f"В казне: {format_number(get_treasury_balance()[0])} RCOIN",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data == "treasury_withdraw")
async def treasury_withdraw(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    balance_coin, _ = get_treasury_balance()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 000", callback_data="wd_1000"),
         InlineKeyboardButton(text="5 000", callback_data="wd_5000"),
         InlineKeyboardButton(text="10 000", callback_data="wd_10000")],
        [InlineKeyboardButton(text="50 000", callback_data="wd_50000"),
         InlineKeyboardButton(text="100 000", callback_data="wd_100000"),
         InlineKeyboardButton(text="500 000", callback_data="wd_500000")],
        [InlineKeyboardButton(text="1 000 000", callback_data="wd_1000000"),
         InlineKeyboardButton(text="5 000 000", callback_data="wd_5000000"),
         InlineKeyboardButton(text="10 000 000", callback_data="wd_10000000")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="wd_custom")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="treasury_back")]
    ])

    await callback.message.edit_text(
        f"🏦 <b>СНЯТИЕ</b>\n\n"
        f"В казне: {format_number(balance_coin)} RCOIN",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("dep_"))
async def treasury_deposit_amount(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    data = callback.data.split('_')

    if data[1] == 'custom':
        await callback.message.delete()
        await callback.message.answer(
            f"💰 <b>Введите сумму</b>\n\n"
            f"Форматы: 1к=1000, 1кк=1000000\n"
            f"Для отмены: отмена"
        )
        await state.set_state("deposit_custom")
        await callback.answer()
        return

    amount = int(data[1])

    if user.get('balance_coin', 0) < amount:
        await callback.answer(f"❌ Недостаточно! У вас: {format_number(user.get('balance_coin', 0))} RCOIN",
                              show_alert=True)
        return

    balance_coin, balance_point = get_treasury_balance()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - amount)
    update_treasury(balance_coin + amount, balance_point)

    await callback.message.edit_text(
        f"✅ <b>ПОПОЛНЕНО!</b>\n\n"
        f"💰 +{format_number(amount)} RCOIN\n"
        f"📊 В казне: {format_number(balance_coin + amount)} RCOIN"
    )
    await asyncio.sleep(2)
    await cmd_treasury(callback.message)
    await callback.answer(f"✅ +{format_number(amount)} RCOIN", show_alert=True)


@dp.callback_query(F.data.startswith("wd_"))
async def treasury_withdraw_amount(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    data = callback.data.split('_')

    if data[1] == 'custom':
        await callback.message.delete()
        await callback.message.answer(
            f"🏦 <b>Введите сумму</b>\n\n"
            f"Форматы: 1к=1000, 1кк=1000000\n"
            f"Для отмены: отмена"
        )
        await state.set_state("withdraw_custom")
        await callback.answer()
        return

    amount = int(data[1])
    balance_coin, balance_point = get_treasury_balance()

    if balance_coin < amount:
        await callback.answer(f"❌ В казне {format_number(balance_coin)} RCOIN", show_alert=True)
        return

    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)
    update_treasury(balance_coin - amount, balance_point)

    await callback.message.edit_text(
        f"✅ <b>СНЯТО!</b>\n\n"
        f"💰 -{format_number(amount)} RCOIN\n"
        f"📊 В казне: {format_number(balance_coin - amount)} RCOIN"
    )
    await asyncio.sleep(2)
    await cmd_treasury(callback.message)
    await callback.answer(f"✅ -{format_number(amount)} RCOIN", show_alert=True)


@dp.message(StateFilter("deposit_custom"))
async def deposit_custom_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_treasury(message)
        return

    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❌ Введите положительное число")
        return

    user = get_user(user_id)

    if user.get('balance_coin', 0) < amount:
        await message.answer(f"❌ Недостаточно! У вас: {format_number(user.get('balance_coin', 0))} RCOIN")
        return

    balance_coin, balance_point = get_treasury_balance()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - amount)
    update_treasury(balance_coin + amount, balance_point)

    await state.clear()
    await message.answer(f"✅ Пополнено {format_number(amount)} RCOIN!")
    await cmd_treasury(message)


@dp.message(StateFilter("withdraw_custom"))
async def withdraw_custom_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_treasury(message)
        return

    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❌ Введите положительное число")
        return

    balance_coin, balance_point = get_treasury_balance()

    if balance_coin < amount:
        await message.answer(f"❌ В казне {format_number(balance_coin)} RCOIN")
        return

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)
    update_treasury(balance_coin - amount, balance_point)

    await state.clear()
    await message.answer(f"✅ Снято {format_number(amount)} RCOIN!")
    await cmd_treasury(message)


@dp.callback_query(F.data == "treasury_back")
async def treasury_back(callback: CallbackQuery):
    await cmd_treasury(callback.message)
    await callback.answer()


# ==================== АКТИВАЦИЯ ЧЕКА ====================

async def activate_check(message: Message, check_id: str):
    user_id = message.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id FROM check_activations 
        WHERE check_id = ? AND user_id = ?
    """, (check_id, user_id))
    existing = cur.fetchone()

    if existing:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} ❌ Вы уже активировали этот чек! Каждый пользователь может активировать чек ТОЛЬКО 1 раз.")
        conn.close()
        return

    cur.execute(
        "SELECT owner_id, amount, max_activations, activations, password, description FROM checks WHERE check_id = ? AND is_active = 1",
        (check_id,))
    row = cur.fetchone()

    if not row:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Чек не найден или уже неактивен.")
        conn.close()
        return

    owner_id, amount, max_act, activations, password, description = row

    if activations >= max_act:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Чек уже использован максимальное количество раз.")
        conn.close()
        return

    if owner_id == user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя активировать свой собственный чек.")
        conn.close()
        return

    if password:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Чек защищён паролем.\n"
            f"📝 Описание: {description}\n\n"
            f"Введите пароль для активации:"
        )
        from aiogram.fsm.context import FSMContext
        state = FSMContext(storage=storage, key=message.from_user.id)
        await state.set_state(GameState.check_pass_enter)
        await state.update_data(check_id=check_id)
        return

    await process_check_activation(message, check_id, owner_id, amount, max_act, activations)


@dp.message(GameState.check_pass_enter)
async def check_pass_enter(message: Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text.strip()

    data = await state.get_data()
    check_id = data.get('check_id')

    if not check_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка: чек не найден. Попробуйте заново.")
        await state.clear()
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "SELECT owner_id, amount, max_activations, activations, password, description FROM checks WHERE check_id = ? AND is_active = 1",
        (check_id,))
    row = cur.fetchone()

    if not row:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Чек не найден или уже неактивен.")
        await state.clear()
        conn.close()
        return

    owner_id, amount, max_act, activations, db_password, description = row

    if password != db_password:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Неверный пароль! Попробуйте снова.")
        conn.close()
        return

    conn.close()

    if user_id == owner_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя активировать свой чек.")
        await state.clear()
        return

    await process_check_activation(message, check_id, owner_id, amount, max_act, activations)
    await state.clear()


async def process_check_activation(message: Message, check_id: str, owner_id: int, amount: int, max_act: int,
                                   activations: int):
    user_id = message.from_user.id

    new_activations = activations + 1

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO check_activations (check_id, user_id, activated_at)
        VALUES (?, ?, ?)
    """, (check_id, user_id, int(time.time())))

    cur.execute("UPDATE checks SET activations = ? WHERE check_id = ?", (new_activations, check_id))

    if new_activations >= max_act:
        cur.execute("UPDATE checks SET is_active = 0 WHERE check_id = ?", (check_id,))

    conn.commit()
    conn.close()

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)

    try:
        await bot.send_message(
            owner_id,
            f"{PREMIUM_EMOJI_TEXT['check']} <b>Чек активирован!</b>\n\n"
            f"🆔 ID чека: {check_id}\n"
            f"👤 Активировал: {user.get('display_name', user.get('username', user_id))}\n"
            f"💰 Сумма: {format_number(amount)} RCOIN\n"
            f"📊 Активаций: {new_activations}/{max_act}"
        )
    except:
        pass

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>ЧЕК АКТИВИРОВАН!</b>\n\n"
        f"💰 Вы получили {format_number(amount)} RCOIN!\n"
        f"📊 Новый баланс: {format_number(user.get('balance_coin', 0) + amount)} RCOIN</blockquote>"
    )


# ==================== КОМАНДА КУПИТЬ ЮЗЕРНЕЙМ ====================

@dp.message(F.text.lower().startswith("+юзер"))
async def cmd_buy_username(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Формат: <code>+юзер @username</code>")
        return

    username = parts[1].replace('@', '').strip()

    if len(username) < 3:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Юзернейм минимум 3 символа.")
        return

    if not username.isalnum():
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Юзернейм должен содержать только латинские буквы и цифры.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE custom_username = ?", (username,))
    existing = cur.fetchone()
    conn.close()

    if existing:
        owner_id = existing[0]
        owner = get_user(owner_id)
        owner_name = owner.get('display_name', owner.get('username', str(owner_id)))
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Юзернейм @{username} уже занят пользователем {owner_name}"
        )
        return

    price = 100000000

    if user.get('balance_coin', 0) < price:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN.\n"
            f"💰 Нужно: {format_number(price)} RCOIN\n"
            f"💰 У вас: {format_number(user.get('balance_coin', 0))} RCOIN"
        )
        return

    new_balance = user.get('balance_coin', 0) - price

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        cur.execute("""
            UPDATE users 
            SET balance_coin = ?, custom_username = ? 
            WHERE user_id = ?
        """, (new_balance, username, user_id))

        conn.commit()
        conn.close()

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['username_emoji']} <b>ЮЗЕРНЕЙМ УСПЕШНО КУПЛЕН!</b>\n\n"
            f"🔹 Юзернейм: @{username}\n"
            f"💰 Стоимость: {format_number(price)} RCOIN\n"
            f"📊 Новый баланс: {format_number(new_balance)} RCOIN\n\n"
            f"✅ Проверьте профиль командой <b>Профиль</b></blockquote>"
        )

    except Exception as e:
        logger.error(f"Ошибка покупки юзернейма: {e}")
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка базы данных: {e}")


# ==================== РЕФЕРАЛЬНЫЕ КОМАНДЫ ====================

@dp.message(F.text.lower() == "рефералы")
@dp.message(Command("рефералы"))
async def cmd_referrals(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    if not user.get('referral_code'):
        code = generate_referral_code()
        update_user(user_id, referral_code=code)
        user = get_user(user_id)

    referrals_count = get_referrals_count(user_id)
    referral_code = user.get('referral_code', '')
    referral_earnings = get_referral_earnings(user_id)
    referral_percent = user.get('referral_percent', 5)
    referral_withdrawn = user.get('referral_withdrawn', 0)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Мои рефералы",
            callback_data="ref_my",
            icon_custom_emoji_id=EMOJI_IDS["referral"]
        )],
        [InlineKeyboardButton(
            text=f"Назад",
            callback_data="back_to_balance",
            icon_custom_emoji_id=EMOJI_IDS["balance"]
        )]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['referral']} <b>Реферальная система</b>\n\n"
        f"📊 <b>Ваши рефералы:</b> {referrals_count}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Заработано:</b> {format_number(referral_earnings)} RCOIN\n"
        f"💸 <b>Выведено:</b> {format_number(referral_withdrawn)} RCOIN\n"
        f"📊 <b>Доступно:</b> {format_number(referral_earnings - referral_withdrawn)} RCOIN\n"
        f"📈 <b>Процент с рефералов:</b> {referral_percent}%\n\n"
        f"🔑 <b>Ваш реферальный код:</b>\n<code>{referral_code}</code>\n\n"
        f"📝 <b>Как это работает:</b>\n"
        f"1. Отправь свой код другу\n"
        f"2. Друг вводит <code>/start {referral_code}</code>\n"
        f"3. Ты получаешь {referral_percent}% от каждой ставки друга!\n\n"
        f"📋 <b>Ссылка-приглашение:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}?start={referral_code}</code>\n\n"
        f"💸 <b>Вывод средств:</b>\n<code>вывести реф 1000</code> – вывести 1000 RCOIN",
        reply_markup=kb
    )


@dp.message(F.text.lower().startswith("вывести реф"))
async def cmd_withdraw_ref(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\nПример: <code>вывести реф 1000</code>")
        return
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return
    if amount <= 0:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
        return
    referral_earnings = get_referral_earnings(user_id)
    referral_withdrawn = user.get('referral_withdrawn', 0)
    available = referral_earnings - referral_withdrawn
    if available < amount:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\nДоступно: {format_number(available)} RCOIN\nЗапрошено: {format_number(amount)} RCOIN")
        return
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount,
                referral_withdrawn=referral_withdrawn + amount)
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Вывод выполнен успешно!</b>\n\n💵 Выведено: {format_number(amount)} RCOIN\n💰 <b>Новый баланс:</b> {format_number(user.get('balance_coin', 0) + amount)} RCOIN\n📊 <b>Остаток:</b> {format_number(available - amount)} RCOIN")


# ==================== БАНКОВСКАЯ СИСТЕМА ====================

MIN_BANK_AMOUNT = 100


@dp.message(F.text.lower() == "банк")
@dp.message(Command("банк"))
async def cmd_bank(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    balance = user.get('balance_coin', 0)
    bank = user.get('bank_balance', 0)
    bank_limit = user.get('bank_limit', 500000000)
    total = balance + bank

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Положить в банк", callback_data="bank_deposit",
                              icon_custom_emoji_id=EMOJI_IDS["bank"]),
         InlineKeyboardButton(text=f"🏦 Снять с банка", callback_data="bank_withdraw",
                              icon_custom_emoji_id=EMOJI_IDS["bank"])],
        [InlineKeyboardButton(text=f"📊 Баланс банка", callback_data="bank_balance",
                              icon_custom_emoji_id=EMOJI_IDS["bank"]),
         InlineKeyboardButton(text=f"📈 Повысить лимит банка", callback_data="bank_upgrade_limit",
                              icon_custom_emoji_id=EMOJI_IDS["bank"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>БАНКОВСКАЯ СИСТЕМА</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Ваш баланс:</b> {format_number(balance)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>В банке:</b> {format_number(bank)} RCOIN\n"
        f"📊 <b>Всего:</b> {format_number(total)} RCOIN\n"
        f"📈 <b>Лимит банка:</b> {format_number(bank_limit)} RCOIN\n\n"
        f"📌 <b>Лимиты:</b>\n"
        f"• Пополнение: до {format_number(bank_limit)} RCOIN\n"
        f"• Минимум: {format_number(MIN_BANK_AMOUNT)} RCOIN\n\n"
        f"<i>Депозиты защищены от проигрышей!</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data == "bank_upgrade_limit")
async def bank_upgrade_limit(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.", show_alert=True)
        return

    current_limit = user.get('bank_limit', 500000000)
    if current_limit >= 10000000000:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} У вас максимальный лимит банка (10 000 000 000 RCOIN).",
                              show_alert=True)
        return

    new_limit = current_limit + 500000000
    cost = max(current_limit // 10, 100000)

    if user.get('balance_coin', 0) < cost:
        await callback.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN!\nНужно: {format_number(cost)} RCOIN\nУ вас: {format_number(user.get('balance_coin', 0))} RCOIN",
            show_alert=True
        )
        return

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - cost, bank_limit=new_limit)

    await callback.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} Лимит банка повышен до {format_number(new_limit)} RCOIN!\n"
        f"💰 Списано: {format_number(cost)} RCOIN",
        show_alert=True
    )
    await cmd_bank(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "bank_deposit")
async def bank_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>ПОПОЛНЕНИЕ БАНКА</b>\n\n"
        f"Введите сумму для депозита:\n"
        f"• Минимум: {format_number(MIN_BANK_AMOUNT)} RCOIN\n"
        f"Форматы: 1к=1000, 1кк=1 000 000, 1ккк=1 000 000 000\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад в банк", callback_data="bank_back",
                                  icon_custom_emoji_id=EMOJI_IDS["bank"])]
        ])
    )
    await state.set_state(GameState.bank_deposit)
    await callback.answer()


@dp.callback_query(F.data == "bank_withdraw")
async def bank_withdraw(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>СНЯТИЕ С БАНКА</b>\n\n"
        f"Введите сумму для снятия:\n"
        f"• Минимум: {format_number(MIN_BANK_AMOUNT)} RCOIN\n"
        f"Форматы: 1к=1000, 1кк=1 000 000, 1ккк=1 000 000 000\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад в банк", callback_data="bank_back",
                                  icon_custom_emoji_id=EMOJI_IDS["bank"])]
        ])
    )
    await state.set_state(GameState.bank_withdraw)
    await callback.answer()


@dp.message(GameState.bank_deposit)
async def bank_deposit_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_bank(message)
        return

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        await state.clear()
        return

    amount = parse_amount(message.text)
    bank_limit = user.get('bank_limit', 500000000)

    if amount < MIN_BANK_AMOUNT:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Минимальная сумма депозита — {format_number(MIN_BANK_AMOUNT)} RCOIN!</b>\n"
            f"Вы ввели: {format_number(amount)} RCOIN\n\n"
            f"Попробуйте снова:"
        )
        return

    current_bank = user.get('bank_balance', 0)
    if current_bank + amount > bank_limit:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Превышен лимит банка!</b>\n"
            f"📈 Лимит: {format_number(bank_limit)} RCOIN\n"
            f"🏦 В банке: {format_number(current_bank)} RCOIN\n"
            f"💰 Можно положить: {format_number(bank_limit - current_bank)} RCOIN"
        )
        return

    current_balance = user.get('balance_coin', 0)

    if current_balance < amount:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN\n"
            f"💰 Нужно: {format_number(amount)} RCOIN"
        )
        return

    new_balance = current_balance - amount
    new_bank = current_bank + amount

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance_coin = ?, bank_balance = ? WHERE user_id = ?",
                    (new_balance, new_bank, user_id))
        conn.commit()
        conn.close()

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['bank']} <b>ДЕПОЗИТ ВЫПОЛНЕН!</b>\n\n"
            f"💰 <b>Сумма:</b> {format_number(amount)} RCOIN\n"
            f"🏦 <b>В банке:</b> {format_number(new_bank)} RCOIN\n"
            f"💰 <b>Баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка депозита: {e}")
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка базы данных: {e}")
        await state.clear()


@dp.message(GameState.bank_withdraw)
async def bank_withdraw_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_bank(message)
        return

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        await state.clear()
        return

    amount = parse_amount(message.text)

    if amount < MIN_BANK_AMOUNT:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Минимальная сумма снятия — {format_number(MIN_BANK_AMOUNT)} RCOIN!</b>\n"
            f"Вы ввели: {format_number(amount)} RCOIN\n\n"
            f"Попробуйте снова:"
        )
        return

    current_bank = user.get('bank_balance', 0)
    current_balance = user.get('balance_coin', 0)

    if current_bank < amount:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств в банке!</b>\n"
            f"🏦 В банке: {format_number(current_bank)} RCOIN\n"
            f"💰 Нужно: {format_number(amount)} RCOIN"
        )
        return

    new_balance = current_balance + amount
    new_bank = current_bank - amount

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance_coin = ?, bank_balance = ? WHERE user_id = ?",
                    (new_balance, new_bank, user_id))
        conn.commit()
        conn.close()

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['bank']} <b>СНЯТИЕ ВЫПОЛНЕНО!</b>\n\n"
            f"💰 <b>Сумма:</b> {format_number(amount)} RCOIN\n"
            f"🏦 <b>В банке:</b> {format_number(new_bank)} RCOIN\n"
            f"💰 <b>Баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка снятия: {e}")
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка базы данных: {e}")
        await state.clear()


@dp.callback_query(F.data == "bank_balance")
async def bank_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.", show_alert=True)
        return

    balance = user.get('balance_coin', 0)
    bank = user.get('bank_balance', 0)
    bank_limit = user.get('bank_limit', 500000000)
    total = balance + bank

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>БАЛАНС БАНКА</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Ваш баланс:</b> {format_number(balance)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['bank']} <b>В банке:</b> {format_number(bank)} RCOIN\n"
        f"📊 <b>Всего:</b> {format_number(total)} RCOIN\n"
        f"📈 <b>Лимит банка:</b> {format_number(bank_limit)} RCOIN\n"
        f"📊 <b>Доступно для депозита:</b> {format_number(bank_limit - bank)} RCOIN",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад в банк", callback_data="bank_back",
                                  icon_custom_emoji_id=EMOJI_IDS["bank"])]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "bank_back")
async def bank_back(callback: CallbackQuery):
    await cmd_bank(callback.message)
    await callback.answer()


# ==================== ОБМЕН ВАЛЮТ ====================

@dp.message(F.text.lower() == "обмен")
@dp.message(Command("обмен"))
async def cmd_exchange(message: Message):
    user_id = message.from_user.id

    if message.chat.type != 'private':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Перейти в ЛС бота", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Обмен валют доступен ТОЛЬКО в личных сообщениях бота!</b>\n\n"
            "Нажмите кнопку ниже, чтобы перейти в ЛС:",
            reply_markup=kb
        )
        return

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, type, amount, price, created_at 
        FROM exchange_orders 
        WHERE status = 'active'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    orders = cur.fetchall()
    conn.close()

    text = f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ОБМЕН ВАЛЮТ</b>\n\n"
    text += f"{PREMIUM_EMOJI_TEXT['balance']} <b>RCOIN:</b> {format_number(user.get('balance_coin', 0))}\n"
    text += f"{PREMIUM_EMOJI_TEXT['diamond']} <b>RBP:</b> {format_number(user.get('balance_point', 0))}\n\n"
    text += f"📊 <b>Курс обмена:</b>\n"
    text += f"• <b>ПОКУПКА:</b> 100 000 RCOIN = 1 RBP\n"
    text += f"• <b>ПРОДАЖА:</b> 1 RBP = 50 000 RCOIN\n\n"
    text += f"📊 <b>Активные P2P предложения:</b>\n"

    if not orders:
        text += "📭 <b>Нет активных предложений.</b>\n\n"
    else:
        for order in orders:
            order_id, uid, typ, amount, price, created = order
            user_ord = get_user(uid)
            name = user_ord.get('display_name', f"User {uid}") if user_ord else f"User {uid}"
            typ_text = "ПОКУПКА" if typ == "buy" else "ПРОДАЖА"
            text += f"🆔 #{order_id} {name}\n"
            text += f"📌 {typ_text}: {format_number(amount)} RBP по {format_number(price)} RCOIN\n"
            text += f"📅 {datetime.fromtimestamp(created).strftime('%d.%m %H:%M')}\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"RCOIN → RBP (ПОКУПКА)", callback_data="exchange_vfg_to_point",
                              icon_custom_emoji_id=EMOJI_IDS["diamond"])],
        [InlineKeyboardButton(text=f"RBP → RCOIN (ПРОДАЖА)", callback_data="exchange_point_to_vfg",
                              icon_custom_emoji_id=EMOJI_IDS["diamond"])],
        [InlineKeyboardButton(text=f"Курс: 1 RBP = 50 000 RCOIN", callback_data="exchange_rate",
                              icon_custom_emoji_id=EMOJI_IDS["bank"])],
        [InlineKeyboardButton(text=f"P2P Обменник", callback_data="exchange_p2p",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "exchange_vfg_to_point")
async def exchange_vfg_to_point(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if callback.message.chat.type != 'private':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Обмен доступен только в ЛС бота!", show_alert=True)
        return

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ПОКУПКА RBP</b>\n\n"
        f"Введите количество RCOIN для обмена:\n"
        f"Минимум: 1 RCOIN\n"
        f"Курс: 100 000 RCOIN = 1 RBP\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="exchange_back",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.exchange_waiting)
    await state.update_data(exchange_type="vfg_to_point")
    await callback.answer()


@dp.callback_query(F.data == "exchange_point_to_vfg")
async def exchange_point_to_vfg(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if callback.message.chat.type != 'private':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Обмен доступен только в ЛС бота!", show_alert=True)
        return

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ПРОДАЖА RBP</b>\n\n"
        f"Введите количество RBP для обмена:\n"
        f"Минимум: 1 RBP\n"
        f"Курс: 1 RBP = 50 000 RCOIN\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="exchange_back",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.exchange_waiting)
    await state.update_data(exchange_type="point_to_vfg")
    await callback.answer()


@dp.callback_query(F.data == "exchange_p2p")
async def exchange_p2p(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, type, amount, price, created_at 
        FROM exchange_orders 
        WHERE status = 'active'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    orders = cur.fetchall()
    conn.close()

    text = f"{PREMIUM_EMOJI_TEXT['balance']} <b>P2P ОБМЕННИК</b>\n\n"
    text += "📊 <b>Активные предложения:</b>\n\n"

    if not orders:
        text += "📭 <b>Нет активных предложений.</b>\n\n"
    else:
        for order in orders:
            order_id, uid, typ, amount, price, created = order
            user_ord = get_user(uid)
            name = user_ord.get('display_name', f"User {uid}") if user_ord else f"User {uid}"
            typ_text = "ПОКУПКА" if typ == "buy" else "ПРОДАЖА"
            text += f"🆔 #{order_id} {name}\n"
            text += f"📌 {typ_text}: {format_number(amount)} RBP по {format_number(price)} RCOIN\n"
            text += f"📅 {datetime.fromtimestamp(created).strftime('%d.%m %H:%M')}\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Выставить ордер на покупку", callback_data="p2p_buy",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Выставить ордер на продажу", callback_data="p2p_sell",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Принять ордер", callback_data="p2p_accept",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="exchange_back", icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "p2p_accept")
async def p2p_accept(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>ПРИНЯТЬ ОРДЕР</b>\n\n"
        f"Введите ID ордера, который хотите принять:\n"
        f"Например: <code>1</code>\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>"
    )
    await state.set_state(GameState.exchange_orders)
    await state.update_data(order_type="accept")
    await callback.answer()


@dp.callback_query(F.data == "p2p_buy")
async def p2p_buy(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>ВЫСТАВИТЬ ОРДЕР НА ПОКУПКУ</b>\n\n"
        f"Введите сумму RBP, которую хотите купить:\n"
        f"Минимум: 1 RBP\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>"
    )
    await state.set_state(GameState.exchange_orders)
    await state.update_data(order_type="buy")
    await callback.answer()


@dp.callback_query(F.data == "p2p_sell")
async def p2p_sell(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>ВЫСТАВИТЬ ОРДЕР НА ПРОДАЖУ</b>\n\n"
        f"Введите сумму RBP, которую хотите продать:\n"
        f"Минимум: 1 RBP\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>"
    )
    await state.set_state(GameState.exchange_orders)
    await state.update_data(order_type="sell")
    await callback.answer()


@dp.message(GameState.exchange_orders)
async def exchange_orders_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_exchange(message)
        return

    data = await state.get_data()
    order_type = data.get('order_type')

    if order_type == "accept":
        try:
            order_id = int(message.text)
        except ValueError:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число (ID ордера).")
            return

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT id, user_id, type, amount, price FROM exchange_orders WHERE id = ? AND status = 'active'",
                    (order_id,))
        order = cur.fetchone()

        if not order:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ордер не найден или уже неактивен.")
            conn.close()
            return

        order_id_db, owner_id, typ, amount, price = order

        if owner_id == user_id:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя принять свой собственный ордер.")
            conn.close()
            return

        user = get_user(user_id)
        owner = get_user(owner_id)

        if not user or not owner:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
            conn.close()
            return

        total_cost = amount * price

        if typ == "buy":
            if user.get('balance_point', 0) < amount:
                await message.answer(
                    f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RBP! У вас: {format_number(user.get('balance_point', 0))}")
                conn.close()
                return

            update_user(user_id, balance_point=user.get('balance_point', 0) - amount)
            update_user(owner_id, balance_coin=owner.get('balance_coin', 0) + total_cost)
        else:
            if user.get('balance_coin', 0) < total_cost:
                await message.answer(
                    f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! У вас: {format_number(user.get('balance_coin', 0))}")
                conn.close()
                return

            update_user(user_id, balance_coin=user.get('balance_coin', 0) - total_cost)
            update_user(owner_id, balance_point=owner.get('balance_point', 0) + amount)

        cur.execute("UPDATE exchange_orders SET status = 'completed' WHERE id = ?", (order_id_db,))
        conn.commit()
        conn.close()

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>ОРДЕР #{order_id_db} ВЫПОЛНЕН!</b>\n\n"
            f"📊 <b>Сумма:</b> {format_number(amount)} RBP\n"
            f"💰 <b>Цена:</b> {format_number(price)} RCOIN за 1 RBP\n"
            f"💵 <b>Общая сумма:</b> {format_number(total_cost)} RCOIN</blockquote>"
        )
        await state.clear()
        return

    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    if amount <= 0:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
        return

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.")
        await state.clear()
        return

    if order_type == "sell":
        if user.get('balance_point', 0) < amount:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RBP! Доступно: {format_number(user.get('balance_point', 0))}")
            return

    await state.update_data(amount=amount)
    await message.answer(
        f"💰 <b>Введите цену за 1 RBP</b>\n\n"
        f"Текущий курс: 50 000 RCOIN за 1 RBP\n"
        f"Вы можете выставить свою цену (минимум 10 000 RCOIN)\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Отмена:</b> напишите <code>отмена</code>"
    )
    await state.set_state(GameState.exchange_orders)


@dp.message(GameState.exchange_orders)
async def exchange_orders_price(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_exchange(message)
        return

    try:
        price = int(message.text)
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    if price < 10000:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная цена: 10 000 RCOIN за 1 RBP")
        return

    data = await state.get_data()
    order_type = data.get('order_type')
    amount = data.get('amount')

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.")
        await state.clear()
        return

    if order_type == "sell":
        if user.get('balance_point', 0) < amount:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RBP! Доступно: {format_number(user.get('balance_point', 0))}")
            await state.clear()
            return
        update_user(user_id, balance_point=user.get('balance_point', 0) - amount)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exchange_orders (user_id, type, amount, price, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, order_type, amount, price, int(time.time())))
    conn.commit()
    conn.close()

    await state.clear()
    typ_text = "ПОКУПКУ" if order_type == "buy" else "ПРОДАЖУ"
    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>ОРДЕР НА {typ_text} ВЫСТАВЛЕН!</b>\n\n"
        f"📊 <b>Сумма:</b> {format_number(amount)} RBP\n"
        f"💰 <b>Цена за 1 RBP:</b> {format_number(price)} RCOIN\n"
        f"💵 <b>Общая сумма:</b> {format_number(amount * price)} RCOIN\n\n"
        f"📌 <b>Статус:</b> Активен</blockquote>"
    )


@dp.callback_query(F.data == "exchange_rate")
async def exchange_rate(callback: CallbackQuery):
    await callback.answer(
        "📊 КУРС ОБМЕНА:\n\n"
        "ПОКУПКА RBP:\n"
        "100 000 RCOIN = 1 RBP\n\n"
        "ПРОДАЖА RBP:\n"
        "1 RBP = 50 000 RCOIN",
        show_alert=True
    )


@dp.callback_query(F.data == "exchange_back")
async def exchange_back(callback: CallbackQuery):
    await cmd_exchange(callback.message)
    await callback.answer()


@dp.message(GameState.exchange_waiting)
async def exchange_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.chat.type != 'private':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Перейти в ЛС бота", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Обмен валют доступен ТОЛЬКО в личных сообщениях бота!</b>\n\n"
            "Нажмите кнопку ниже, чтобы перейти в ЛС:",
            reply_markup=kb
        )
        await state.clear()
        return

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_exchange(message)
        return

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        await state.clear()
        return

    data = await state.get_data()
    exchange_type = data.get('exchange_type')

    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число. Попробуйте снова:")
        return

    if amount <= 0:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной. Попробуйте снова:")
        return

    if exchange_type == "vfg_to_point":
        if amount < 1:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная сумма: 1 RCOIN. Попробуйте снова:")
            return

        current_vfg = user.get('balance_coin', 0)
        if current_vfg < amount:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
                f"💰 Ваш баланс: {format_number(current_vfg)} RCOIN\n"
                f"💰 Нужно: {format_number(amount)} RCOIN"
            )
            return

        point_amount = amount // 100000
        if point_amount == 0:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} Сумма слишком мала.\n"
                f"Для получения 1 RBP нужно 100 000 RCOIN.\n"
                f"У вас: {format_number(amount)} RCOIN\n\n"
                f"Попробуйте снова:"
            )
            return

        used_vfg = point_amount * 100000
        new_vfg = current_vfg - used_vfg
        new_point = user.get('balance_point', 0) + point_amount

        update_user(user_id, balance_coin=new_vfg, balance_point=new_point)

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['diamond']} <b>ПОКУПКА RBP ВЫПОЛНЕНА!</b>\n\n"
            f"💰 <b>Потрачено:</b> {format_number(used_vfg)} RCOIN\n"
            f"💎 <b>Получено:</b> {format_number(point_amount)} RBP\n"
            f"📊 <b>Курс:</b> 100 000 RCOIN = 1 RBP\n\n"
            f"💰 <b>Новый баланс RCOIN:</b> {format_number(new_vfg)}\n"
            f"💎 <b>Новый баланс RBP:</b> {format_number(new_point)}</blockquote>"
        )
        await state.clear()

    elif exchange_type == "point_to_vfg":
        if amount < 1:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная сумма: 1 RBP. Попробуйте снова:")
            return

        current_point = user.get('balance_point', 0)
        if current_point < amount:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RBP!</b>\n"
                f"💎 Ваш баланс: {format_number(current_point)} RBP\n"
                f"💎 Нужно: {format_number(amount)} RBP"
            )
            return

        vfg_amount = amount * 50000
        new_point = current_point - amount
        new_vfg = user.get('balance_coin', 0) + vfg_amount

        update_user(user_id, balance_coin=new_vfg, balance_point=new_point)

        await message.answer(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['diamond']} <b>ПРОДАЖА RBP ВЫПОЛНЕНА!</b>\n\n"
            f"💎 <b>Потрачено:</b> {format_number(amount)} RBP\n"
            f"💰 <b>Получено:</b> {format_number(vfg_amount)} RCOIN\n"
            f"📊 <b>Курс:</b> 1 RBP = 50 000 RCOIN\n\n"
            f"💰 <b>Новый баланс RCOIN:</b> {format_number(new_vfg)}\n"
            f"💎 <b>Новый баланс RBP:</b> {format_number(new_point)}</blockquote>"
        )
        await state.clear()

    else:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка. Попробуйте заново через /обмен")
        await state.clear()


# ==================== ИГРА КУБИК ====================

@dp.message(F.text.lower().startswith("куб"))
async def game_dice(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>куб 100 3</code> – ставка на число 1-6 (5x)\n"
            "• <code>куб все 3</code> – ВЕСЬ баланс на число 3\n"
            "• <code>куб вб 3</code> – ВЕСЬ баланс на число 3\n"
            "• <code>куб 100 1 2 3</code> – ставка на несколько чисел\n"
            "• <code>куб 50 чет</code> – ставка на чёт (2x)\n"
            "• <code>куб 50 нечет</code> – ставка на нечёт (2x)\n"
            "• <code>куб 50 мал</code> – ставка на 1-3 (2x)\n"
            "• <code>куб 50 бол</code> – ставка на 4-6 (2x)\n"
            "• <code>куб 50 р</code> – радужный (1%, 10x)"
        )
        return

    try:
        amount_str = parts[1]
        choices = parts[2:]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    total_bet = bet_amount * len(choices)
    total_deduct = deduct_amount * len(choices)

    if total_bet <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < total_deduct:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN\n"
            f"🎯 Ставка: {format_number(total_bet)} RCOIN ({len(choices)} ставок по {format_number(bet_amount)} RCOIN)"
        )
        return

    valid_choices = ['1', '2', '3', '4', '5', '6', 'чет', 'нечет', 'мал', 'бол', 'р']
    for choice in choices:
        if choice not in valid_choices:
            await message.reply(
                f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неверный выбор!</b>\n"
                f"Варианты: 1-6, чет, нечет, мал, бол, р"
            )
            return

    update_user(user_id, last_game_time=now)

    dice_msg = await message.answer_dice(emoji="🎲")
    await asyncio.sleep(2.5)
    roll = dice_msg.dice.value

    update_user(user_id, balance_coin=current_balance - total_deduct)

    win = False
    multiplier = 0
    winning_choices = []

    for choice in choices:
        if choice.isdigit() and 1 <= int(choice) <= 6:
            if int(choice) == roll:
                win = True
                multiplier = 5
                winning_choices.append(choice)
        elif choice == 'чет' and roll % 2 == 0:
            win = True
            multiplier = 2
            winning_choices.append(choice)
        elif choice == 'нечет' and roll % 2 == 1:
            win = True
            multiplier = 2
            winning_choices.append(choice)
        elif choice == 'мал' and roll in [1, 2, 3]:
            win = True
            multiplier = 2
            winning_choices.append(choice)
        elif choice == 'бол' and roll in [4, 5, 6]:
            win = True
            multiplier = 2
            winning_choices.append(choice)
        elif choice == 'р':
            if random.randint(1, 100) == 1:
                win = True
                multiplier = 10
                winning_choices.append(choice)

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    choice_display = {
        '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
        'чет': 'Чёт', 'нечет': 'Нечёт', 'мал': 'Мал (1-3)', 'бол': 'Бол (4-6)', 'р': 'Радужный 🌈'
    }
    choices_display = ', '.join([choice_display.get(c, c) for c in choices])

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    user = get_user(user_id)
    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if win:
        winnings = bet_amount * multiplier
        new_balance = current_balance - total_deduct + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        win_choices_display = ', '.join([choice_display.get(c, c) for c in winning_choices])

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['dice']} <b>Игра КУБИК - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Выбор:</b> {choices_display}\n"
            f"🎲 <b>Выпало:</b> {roll}\n"
            f"💸 <b>Ставка:</b> {bet_display} ({len(choices)} ставок)\n"
            f"📈 <b>Множитель:</b> {multiplier}x\n"
            f"🎯 <b>Сыграло:</b> {win_choices_display}\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "dice", total_bet, winnings, 1, f"choices={choices}, roll={roll}")
    else:
        new_balance = current_balance - total_deduct
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['dice']} <b>Игра КУБИК - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Выбор:</b> {choices_display}\n"
            f"🎲 <b>Выпало:</b> {roll}\n"
            f"💸 <b>Ставка:</b> {bet_display} ({len(choices)} ставок)\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "dice", total_bet, 0, 0, f"choices={choices}, roll={roll}")

    await asyncio.sleep(0.5)
    await message.reply(result_text)


# ==================== ИГРА РУЛЕТКА ====================

@dp.message(F.text.lower().startswith("рулетка"))
async def game_roulette(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    last_time = user.get('last_roulette_time', 0)
    now = int(time.time())
    if now - last_time < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {3 - (now - last_time)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>рулетка 100к к</code> – красное (2x)\n"
            "• <code>рулетка все к</code> – ВЕСЬ баланс на красное\n"
            "• <code>рулетка вб к</code> – ВЕСЬ баланс на красное\n"
            "• <code>рулетка 50 7</code> – число 7 (35x)\n"
            "• <code>рулетка все 7</code> – ВЕСЬ баланс на число 7\n"
            "• <code>рулетка 100 чет</code> – чёт (2x)\n"
            "• <code>рулетка 100 нечет</code> – нечёт (2x)\n"
            "• <code>рулетка 100 б</code> – 1-18 (2x)\n"
            "• <code>рулетка 100 м</code> – 19-36 (2x)\n"
            "• <code>рулетка 100 з</code> – зеро (35x)"
        )
        return

    try:
        amount_str = parts[1]
        bet = parts[2]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    valid_bets = ['к', 'ч', 'з', 'чет', 'нечет', 'б', 'м']
    if bet not in valid_bets and not bet.isdigit():
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} Неверная ставка. Варианты: к, ч, з, чет, нечет, б, м, число 0-36")
        return
    if bet.isdigit() and not (0 <= int(bet) <= 36):
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Число от 0 до 36.")
        return

    update_user(user_id, last_roulette_time=now)

    gif_url = "https://media1.tenor.com/m/u5qKQfM69VwAAAAC/casino.gif"
    try:
        anim_msg = await bot.send_animation(
            chat_id=message.chat.id,
            animation=gif_url,
            reply_to_message_id=message.message_id
        )
        await asyncio.sleep(2.0)
        await anim_msg.delete()
    except Exception as e:
        logger.error(f"Ошибка отправки GIF рулетки: {e}")

    result = random.randint(0, 36)
    win = False
    multiplier = 0

    red = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    black = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

    if bet == 'к' and result in red:
        win = True
        multiplier = 2
    elif bet == 'ч' and result in black:
        win = True
        multiplier = 2
    elif bet == 'з' and result == 0:
        win = True
        multiplier = 35
    elif bet == 'чет' and result != 0 and result % 2 == 0:
        win = True
        multiplier = 2
    elif bet == 'нечет' and result % 2 == 1:
        win = True
        multiplier = 2
    elif bet == 'б' and 1 <= result <= 18:
        win = True
        multiplier = 2
    elif bet == 'м' and 19 <= result <= 36:
        win = True
        multiplier = 2
    elif bet.isdigit() and int(bet) == result:
        win = True
        multiplier = 35

    color = get_roulette_color(result)
    emoji = get_roulette_emoji(result)
    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    bet_names = {
        'к': 'Красное 🔴',
        'ч': 'Чёрное ⚫',
        'з': 'Зеро 🟢',
        'чет': 'Чёт',
        'нечет': 'Нечёт',
        'б': '1-18',
        'м': '19-36'
    }
    bet_display_name = bet_names.get(bet, f"Число {bet}")

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if win:
        winnings = int(bet_amount * multiplier)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['roulette']} <b>Игра РУЛЕТКА - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ставка:</b> {bet_display_name}\n"
            f"🎯 <b>Выпало:</b> {result} {emoji} ({color})\n"
            f"💸 <b>Сумма:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {multiplier}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "roulette", bet_amount, winnings, 1, f"bet={bet}, result={result}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['roulette']} <b>Игра РУЛЕТКА - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ставка:</b> {bet_display_name}\n"
            f"🎯 <b>Выпало:</b> {result} {emoji} ({color})\n"
            f"💸 <b>Сумма:</b> {bet_display} проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "roulette", bet_amount, 0, 0, f"bet={bet}, result={result}")

    await message.reply(result_text)


# ==================== ИГРА ФОРТУНА ====================

@dp.message(F.text.lower().startswith(("фортуна", "кф")))
async def game_fortune(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    last_time = user.get('last_fortune_time', 0)
    now = int(time.time())
    if now - last_time < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_time)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>фортуна 100</code> – ставка 100 RCOIN\n"
            "• <code>фортуна все</code> – ВЕСЬ баланс\n"
            "• <code>фортуна вб</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    update_user(user_id, last_fortune_time=now)

    multipliers = [0, 0, 0.5, 1, 2, 5]
    weights = [47, 23, 15, 10, 5, 0]

    mult = random.choices(multipliers, weights=weights, k=1)[0]

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if mult > 0:
        winnings = int(bet_amount * mult)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        mult_emoji = "🎉" if mult >= 2 else "😊" if mult >= 1 else "🤔"

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['fortune']} <b>Игра ФОРТУНА - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {mult}x {mult_emoji}\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "fortune", bet_amount, winnings, 1, f"mult={mult}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['fortune']} <b>Игра ФОРТУНА - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> 0x 😢\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(deduct_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "fortune", bet_amount, 0, 0, f"mult=0")

    await message.reply(result_text)


# ==================== ИГРА ДАРТС ====================

@dp.message(F.text.lower().startswith(("дс", "дартс")))
async def game_darts(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>дс 100 б</code> – белое (2x)\n"
            "• <code>дс все б</code> – ВЕСЬ баланс на белое\n"
            "• <code>дс вб б</code> – ВЕСЬ баланс на белое\n"
            "• <code>дс 100 к</code> – красное (2x)\n"
            "• <code>дс 100 ц</code> – центр (5x)\n"
            "• <code>дс 100 м</code> – мимо (5x)"
        )
        return

    amount_str = parts[1]
    choice = parts[2]

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if bet_amount > current_balance:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN\n"
            f"💰 Нужно: {format_number(bet_amount)} RCOIN"
        )
        return

    valid_choices = ['б', 'к', 'ц', 'м']
    if choice not in valid_choices:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неверный выбор!</b>\n\n"
            "Варианты:\n"
            "• <code>б</code> – белое (2x) ⚪\n"
            "• <code>к</code> – красное (2x) 🔴\n"
            "• <code>ц</code> – центр (5x) 🎯\n"
            "• <code>м</code> – мимо (5x) ❌"
        )
        return

    update_user(user_id, last_game_time=now)

    darts_msg = await message.answer_dice(emoji="🎯")
    await asyncio.sleep(2.5)
    roll = darts_msg.dice.value

    outcomes = {
        1: {'name': 'Мимо ❌', 'code': 'м', 'mult': 5},
        2: {'name': 'Красное 🔴', 'code': 'к', 'mult': 2},
        3: {'name': 'Белое ⚪', 'code': 'б', 'mult': 2},
        4: {'name': 'Красное 🔴', 'code': 'к', 'mult': 2},
        5: {'name': 'Белое ⚪', 'code': 'б', 'mult': 2},
        6: {'name': 'Центр 🎯', 'code': 'ц', 'mult': 5}
    }

    outcome = outcomes[roll]
    mult = outcome['mult']
    outcome_name = outcome['name']
    result_code = outcome['code']

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if choice == result_code:
        winnings = int(bet_amount * mult)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        if amount_str in ['все', 'вб']:
            bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
        else:
            bet_display = f"{format_number(bet_amount)} RCOIN"

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['darts']} <b>Игра ДАРТС - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ваш выбор:</b> {choice}\n"
            f"🎯 <b>Результат:</b> {outcome_name}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {mult}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "darts", bet_amount, winnings, 1,
                        f"choice={choice}, result={result_code}, roll={roll}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        if amount_str in ['все', 'вб']:
            bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
        else:
            bet_display = f"{format_number(bet_amount)} RCOIN"

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['darts']} <b>Игра ДАРТС - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ваш выбор:</b> {choice}\n"
            f"🎯 <b>Результат:</b> {outcome_name}\n"
            f"💸 <b>Ставка:</b> {bet_display} проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "darts", bet_amount, 0, 0, f"choice={choice}, result={result_code}, roll={roll}")

    await asyncio.sleep(0.5)
    await message.reply(result_text)


# ==================== ИГРА ОЧКО (БЛЭКДЖЕК) ====================

class BlackjackGame:
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    @staticmethod
    def create_deck():
        deck = []
        for suit in BlackjackGame.SUITS:
            for rank in BlackjackGame.RANKS:
                deck.append(f"{rank}{suit}")
        random.shuffle(deck)
        return deck

    @staticmethod
    def get_card_value(card: str) -> int:
        rank = card[:-1]
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)

    @staticmethod
    def get_hand_value(hand: List[str]) -> int:
        value = 0
        aces = 0
        for card in hand:
            if card.startswith('A'):
                aces += 1
            else:
                value += BlackjackGame.get_card_value(card)
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        return value

    @staticmethod
    def display_cards(hand: List[str]) -> str:
        return ' '.join(hand)


@dp.message(F.text.lower().startswith("очко"))
async def game_blackjack(message: Message, state: FSMContext):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>очко 100</code> – 100 RCOIN\n"
            "• <code>очко все</code> – ВЕСЬ баланс\n"
            "• <code>очко вб</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    update_user(user_id, last_game_time=now)

    deck = BlackjackGame.create_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]

    player_value = BlackjackGame.get_hand_value(player_cards)
    dealer_value = BlackjackGame.get_hand_value(dealer_cards)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if player_value == 21 and len(player_cards) == 2:
        winnings = int(bet_amount * 1.5)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        await message.reply(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['blackjack']} <b>Игра ОЧКО - БЛЭКДЖЕК!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
            f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards)} = {dealer_value}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> 1.5x\n"
            f"✅ <b>Итог:</b> БЛЭКДЖЕК! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "blackjack", bet_amount, winnings, 1, f"player={player_value}, dealer={dealer_value}")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO blackjack_games (user_id, bet_amount, player_cards, dealer_cards, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, bet_amount, json.dumps(player_cards), json.dumps(dealer_cards), int(time.time())))
    game_id = cur.lastrowid
    conn.commit()
    conn.close()

    update_user(user_id, balance_coin=current_balance - deduct_amount,
                total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
    await state.update_data(game_id=game_id)
    await state.set_state(GameState.blackjack_playing)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Ещё", callback_data=f"bj_hit_{game_id}",
                              icon_custom_emoji_id=EMOJI_IDS["blackjack"]),
         InlineKeyboardButton(text=f"Стоп", callback_data=f"bj_stand_{game_id}",
                              icon_custom_emoji_id=EMOJI_IDS["blackjack"])]
    ])

    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['blackjack']} <b>Игра ОЧКО</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
        f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
        f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards[:1])} + ?\n"
        f"💸 <b>Ставка:</b> {bet_display}\n\n"
        f"<i>Выберите действие:</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("bj_hit_"))
async def blackjack_hit(callback: CallbackQuery, state: FSMContext):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, player_cards, dealer_cards, status FROM blackjack_games WHERE id = ?",
                (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, player_cards_json, dealer_cards_json, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    player_cards = json.loads(player_cards_json)
    dealer_cards = json.loads(dealer_cards_json)

    deck = BlackjackGame.create_deck()
    used_cards = player_cards + dealer_cards
    for card in used_cards:
        if card in deck:
            deck.remove(card)

    player_cards.append(deck.pop())
    player_value = BlackjackGame.get_hand_value(player_cards)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE blackjack_games SET player_cards = ? WHERE id = ?", (json.dumps(player_cards), game_id))
    conn.commit()
    conn.close()

    user = get_user(user_id)

    if player_value > 21:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE blackjack_games SET status = 'lost' WHERE id = ?", (game_id,))
        conn.commit()
        conn.close()

        update_user(user_id, total_losses=user.get('total_losses', 0) + 1)
        await state.clear()

        await callback.message.edit_text(
            f"<blockquote>💥 <b>Игра ОЧКО - ПЕРЕБОР!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(user.get('balance_coin', 0))} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "blackjack", bet_amount, 0, 0, f"player={player_value}, bust")
        await callback.answer()
        return

    dealer_value = BlackjackGame.get_hand_value(dealer_cards)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Ещё", callback_data=f"bj_hit_{game_id}",
                              icon_custom_emoji_id=EMOJI_IDS["blackjack"]),
         InlineKeyboardButton(text=f"Стоп", callback_data=f"bj_stand_{game_id}",
                              icon_custom_emoji_id=EMOJI_IDS["blackjack"])]
    ])

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['blackjack']} <b>Игра ОЧКО</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
        f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards[:1])} + ?\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
        f"<i>Выберите действие:</i>",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("bj_stand_"))
async def blackjack_stand(callback: CallbackQuery, state: FSMContext):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, player_cards, dealer_cards, status FROM blackjack_games WHERE id = ?",
                (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, player_cards_json, dealer_cards_json, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    player_cards = json.loads(player_cards_json)
    dealer_cards = json.loads(dealer_cards_json)

    player_value = BlackjackGame.get_hand_value(player_cards)
    dealer_value = BlackjackGame.get_hand_value(dealer_cards)

    deck = BlackjackGame.create_deck()
    used_cards = player_cards + dealer_cards
    for card in used_cards:
        if card in deck:
            deck.remove(card)

    while dealer_value < 17:
        dealer_cards.append(deck.pop())
        dealer_value = BlackjackGame.get_hand_value(dealer_cards)

    win = False
    winnings = 0

    if dealer_value > 21:
        win = True
        winnings = bet_amount * 2
    elif player_value > dealer_value:
        win = True
        winnings = bet_amount * 2
    elif player_value == dealer_value:
        winnings = bet_amount
    else:
        win = False

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE blackjack_games SET status = 'completed', dealer_cards = ? WHERE id = ?",
                (json.dumps(dealer_cards), game_id))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0)

    if win:
        new_balance += winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1)
        result_text = (
            f"<blockquote>✅ <b>Игра ОЧКО - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
            f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards)} = {dealer_value}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "blackjack", bet_amount, winnings, 1, f"player={player_value}, dealer={dealer_value}")
    elif player_value == dealer_value:
        new_balance += bet_amount
        update_user(user_id, balance_coin=new_balance)
        result_text = (
            f"<blockquote>🤝 <b>Игра ОЧКО - НИЧЬЯ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
            f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards)} = {dealer_value}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN возвращена\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "blackjack", bet_amount, 0, 0, f"player={player_value}, dealer={dealer_value}, draw")
    else:
        update_user(user_id, total_losses=user.get('total_losses', 0) + 1)
        result_text = (
            f"<blockquote>❌ <b>Игра ОЧКО - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Ваши карты:</b> {BlackjackGame.display_cards(player_cards)} = {player_value}\n"
            f"🎴 <b>Карты дилера:</b> {BlackjackGame.display_cards(dealer_cards)} = {dealer_value}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "blackjack", bet_amount, 0, 0, f"player={player_value}, dealer={dealer_value}")

    await callback.message.edit_text(result_text)
    await callback.answer()
    await state.clear()


# ==================== ИГРА БАСКЕТ ====================

@dp.message(F.text.lower().startswith("баскет"))
async def game_basket(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>баскет 100 п</code> – попадание (2.5x)\n"
            "• <code>баскет 100 м</code> – мимо (1.6x)\n"
            "• <code>баскет 100 чп</code> – чистое попадание (5x)\n"
            "• <code>баскет 100 з</code> – застрял (5x)"
        )
        return

    try:
        amount_str = parts[1]
        amount = parse_amount(amount_str)
        choice = parts[2]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма ставки должна быть числом.")
        return

    if amount <= 0:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма ставки должна быть положительной.")
        return

    current_balance = user.get('balance_coin', 0)
    if current_balance < amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    valid_choices = ['п', 'м', 'чп', 'з']
    if choice not in valid_choices:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неверный выбор!</b>\n\n"
            "Варианты:\n"
            "• п – попадание (2.5x) 🎯\n"
            "• м – мимо (1.6x) ❌\n"
            "• чп – чистое попадание (5x) 🏆\n"
            "• з – застрял (5x) 💫"
        )
        return

    update_user(user_id, last_game_time=now)

    basket_msg = await message.answer_dice(emoji="🏀")
    await asyncio.sleep(2.5)
    roll = basket_msg.dice.value

    outcomes = {
        1: {'name': 'Мимо ❌', 'mult': 1.6, 'code': 'м'},
        2: {'name': 'Мимо ❌', 'mult': 1.6, 'code': 'м'},
        3: {'name': 'Застрял 💫', 'mult': 5.0, 'code': 'з'},
        4: {'name': 'Попадание 🎯', 'mult': 2.5, 'code': 'п'},
        5: {'name': 'Чистое попадание =͟͟͞͞🏀', 'mult': 5.0, 'code': 'чп'}
    }

    outcome = outcomes.get(roll, outcomes[1])
    mult = outcome['mult']
    outcome_name = outcome['name']
    result_code = outcome['code']

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - amount)

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if choice == result_code:
        winnings = int(amount * mult)
        new_balance = current_balance - amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['basket']} <b>Игра БАСКЕТ - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Результат:</b> {outcome_name}\n"
            f"💸 <b>Ставка:</b> {format_number(amount)} RCOIN\n"
            f"📈 <b>Множитель:</b> {mult}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "basket", amount, winnings, 1, f"choice={choice}, result={result_code}, roll={roll}")
    else:
        new_balance = current_balance - amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['basket']} <b>Игра БАСКЕТ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Результат:</b> {outcome_name}\n"
            f"💸 <b>Ставка:</b> {format_number(amount)} RCOIN проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "basket", amount, 0, 0, f"choice={choice}, result={result_code}, roll={roll}")

    await asyncio.sleep(0.5)
    await message.reply(result_text)


# ==================== ИГРА СОЛНЦЕ ====================

@dp.message(F.text.lower().startswith("солнце"))
async def game_sun(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>солнце 100</code> – 100 RCOIN\n"
            "• <code>солнце все</code> – ВЕСЬ баланс\n"
            "• <code>солнце вб</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    update_user(user_id, last_game_time=now)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    update_user(user_id, balance_coin=current_balance - deduct_amount)
    multipliers = [0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 10]
    weights = [40, 40, 20, 20, 15, 15, 10, 8, 5, 3, 1]
    selected_mult = random.choices(multipliers, weights=weights, k=1)[0]
    positions = list(range(9))
    chosen_pos = random.choice(positions)

    buttons = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            row.append(InlineKeyboardButton(
                text="☀️",
                callback_data=f"sun_{idx}_{chosen_pos}_{selected_mult}_{bet_amount}_{deduct_amount}_{amount_str}",
                icon_custom_emoji_id=EMOJI_IDS["sun"]
            ))
        buttons.append(row)
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['sun']} <b>Игра СОЛНЦЕ</b>\n\n"
        f"👤 <b>Игрок:</b> {display_name}\n"
        f"💰 <b>Ставка:</b> {bet_display}\n"
        f"🎯 <b>Множители:</b> x0, x1, x2, x3, x4, x10\n"
        f"Выберите солнце:",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("sun_"))
async def sun_choice_callback(callback: CallbackQuery):
    data = callback.data.split('_')
    idx = int(data[1])
    chosen_pos = int(data[2])
    selected_mult = int(data[3])
    bet_amount = int(data[4])
    deduct_amount = int(data[5])
    amount_str = data[6]
    user_id = callback.from_user.id
    user = get_user(user_id)
    display_name = user.get('display_name', callback.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    await callback.message.edit_reply_markup(reply_markup=None)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if idx == chosen_pos:
        if selected_mult > 0:
            winnings = bet_amount * selected_mult
            new_balance = user.get('balance_coin', 0) + winnings
            update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                        total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
            result_text = (
                f"<blockquote>{PREMIUM_EMOJI_TEXT['sun']} <b>Игра СОЛНЦЕ - ПОБЕДА!</b>\n\n"
                f"👤 <b>Игрок:</b> {display_name}\n"
                f"💸 <b>Ставка:</b> {bet_display}\n"
                f"🎯 <b>Множитель:</b> {selected_mult}x\n"
                f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
                f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
            )
            add_bet_history(user_id, "sun", bet_amount, winnings, 1, f"mult={selected_mult}")
        else:
            new_balance = user.get('balance_coin', 0)
            update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                        total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
            result_text = (
                f"<blockquote>{PREMIUM_EMOJI_TEXT['sun']} <b>Игра СОЛНЦЕ - ПРОИГРЫШ!</b>\n\n"
                f"👤 <b>Игрок:</b> {display_name}\n"
                f"💸 <b>Ставка:</b> {bet_display}\n"
                f"🎯 <b>Множитель:</b> 0x\n"
                f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(deduct_amount)} RCOIN\n\n"
                f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
            )
            add_bet_history(user_id, "sun", bet_amount, 0, 0, f"mult=0")
    else:
        new_balance = user.get('balance_coin', 0)
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['sun']} <b>Игра СОЛНЦЕ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"🎯 <b>Множитель:</b> 0x (не угадал)\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(deduct_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "sun", bet_amount, 0, 0, f"mult=0")

    await callback.message.answer(result_text)
    await callback.answer()


# ==================== ИГРА МИНЫ ====================

class MinesStates(StatesGroup):
    playing = State()


def create_mines_keyboard(game_id: int, grid: List[int], opened_cells: int,
                          game_over: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(25):
        if game_over:
            if grid and i < len(grid):
                if grid[i] == 1:
                    builder.button(
                        text=" ",
                        callback_data=f"mines_none_{game_id}",
                        icon_custom_emoji_id=EMOJI_IDS["mines"]
                    )
                elif grid[i] == -1:
                    builder.button(
                        text=" ",
                        callback_data=f"mines_none_{game_id}",
                        icon_custom_emoji_id=EMOJI_IDS["diamond"]
                    )
                else:
                    builder.button(
                        text=" ",
                        callback_data=f"mines_none_{game_id}",
                        icon_custom_emoji_id=EMOJI_IDS["mines"]
                    )
            else:
                builder.button(text="⬛", callback_data=f"mines_none_{game_id}")
        else:
            if grid and i < len(grid) and grid[i] == -1:
                builder.button(
                    text=" ",
                    callback_data=f"mines_none_{game_id}",
                    icon_custom_emoji_id=EMOJI_IDS["diamond"]
                )
            else:
                builder.button(
                    text="⬛",
                    callback_data=f"mines_open_{game_id}_{i}"
                )
    builder.adjust(5)

    if opened_cells > 0 and not game_over:
        builder.button(
            text=f"💰 Забрать",
            callback_data=f"mines_cashout_{game_id}",
            icon_custom_emoji_id=EMOJI_IDS["balance"]
        )
    if not game_over:
        builder.button(
            text=f"❌ Отмена",
            callback_data=f"mines_cancel_{game_id}"
        )
    builder.adjust(5)
    return builder.as_markup()


@dp.message(F.text.lower().startswith("мины"))
async def game_mines(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>мины 100 3</code> – 100 RCOIN, 3 мины\n"
            "• <code>мины все 3</code> – ВЕСЬ баланс, 3 мины\n"
            "• <code>мины вб 3</code> – ВЕСЬ баланс, 3 мины\n"
            "• <code>мины 100 1</code> – 100 RCOIN, 1 мина\n"
            "• <code>мины 100 10</code> – 100 RCOIN, 10 мин (макс x1000!)"
        )
        return

    try:
        amount_str = parts[1]
        mines_count = int(parts[2])
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма и количество мин должны быть числами.")
        return

    if mines_count < 1 or mines_count > 10:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Количество мин должно быть от 1 до 10.")
        return

    current_balance = user.get('balance_coin', 0)
    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0 or current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n💰 Баланс: {format_number(current_balance)} RCOIN")
        return

    grid = [0] * 25
    mine_positions = random.sample(range(25), mines_count)
    for pos in mine_positions:
        grid[pos] = 1

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mines_games (user_id, bet_amount, mines_count, grid, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, bet_amount, mines_count, json.dumps(grid), int(time.time())))
    game_id = cur.lastrowid
    conn.commit()
    conn.close()

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    if state:
        await state.update_data(game_id=game_id)
        await state.set_state(MinesStates.playing)

    kb = create_mines_keyboard(game_id, grid, 0)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    max_mult = MULTIPLIERS.get(mines_count, {}).get(24, 1.0)

    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['mines']} <b>Игра МИНЫ</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {bet_display}\n"
        f"💣 <b>Мин:</b> {mines_count}\n"
        f"📈 <b>Множитель:</b> 1.00x\n"
        f"📊 <b>Макс множитель:</b> {max_mult}x\n"
        f"💰 <b>Макс выигрыш:</b> {format_number(int(bet_amount * max_mult))} RCOIN\n\n"
        f"<i>Выберите клетку чтобы продолжить</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("mines_open_"))
async def mines_open_cell(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split('_')
    game_id = int(data[2])
    try:
        cell_index = int(data[3])
        if not 0 <= cell_index < 25:
            raise ValueError
    except (ValueError, IndexError):
        await callback.answer("Некорректная клетка.", show_alert=True)
        return
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, mines_count, grid, opened_cells, status FROM mines_games WHERE id = ?",
                (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, mines_count, grid_json, opened_cells, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    grid = json.loads(grid_json)

    if grid[cell_index] == -1:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Эта клетка уже открыта.", show_alert=True)
        return

    if grid[cell_index] == 1:
        grid[cell_index] = -1
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE mines_games SET grid = ?, status = 'lost' WHERE id = ?", (json.dumps(grid), game_id))
        conn.commit()
        conn.close()

        kb = create_mines_keyboard(game_id, grid, opened_cells, True)
        user = get_user(user_id)

        await callback.message.edit_text(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['mines']} <b>Игра МИНЫ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"💣 <b>Мин:</b> {mines_count}\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(bet_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(user.get('balance_coin', 0))} RCOIN</blockquote>",
            reply_markup=kb
        )
        await callback.answer("💥 Вы попали на мину!", show_alert=True)
        await state.clear()
        return

    grid[cell_index] = -1
    opened_cells += 1

    mult = MULTIPLIERS.get(mines_count, {}).get(opened_cells, 1.0)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE mines_games SET grid = ?, opened_cells = ?, multiplier = ? WHERE id = ?",
                (json.dumps(grid), opened_cells, mult, game_id))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    potential_win = int(bet_amount * mult)

    kb = create_mines_keyboard(game_id, grid, opened_cells)

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Игра МИНЫ</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"💣 <b>Мин:</b> {mines_count}\n"
        f"📈 <b>Множитель:</b> {mult:.2f}x\n"
        f"📊 <b>Потенциальный выигрыш:</b> {format_number(potential_win)} RCOIN\n"
        f"📌 <b>Открыто клеток:</b> {opened_cells}\n\n"
        f"<i>Выберите следующую клетку или заберите выигрыш</i>",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("mines_cashout_"))
async def mines_cashout(callback: CallbackQuery, state: FSMContext):
    try:
        game_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректная игра", show_alert=True); return
    user_id = callback.from_user.id
    with sqlite3.connect(DB_FILE, timeout=20) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT user_id, bet_amount, multiplier, opened_cells, status, mines_count, grid FROM mines_games WHERE id=?", (game_id,)).fetchone()
        if not row:
            conn.rollback(); await callback.answer("Игра не найдена", show_alert=True); return
        game_user_id, bet, mult, opened, status, mines_count, grid_json = row
        if game_user_id != user_id:
            conn.rollback(); await callback.answer("Это не твоя игра", show_alert=True); return
        if status != "active":
            conn.rollback(); await callback.answer("Игра уже завершена", show_alert=True); return
        if int(opened or 0) <= 0:
            conn.rollback(); await callback.answer("Сначала открой хотя бы одну клетку", show_alert=True); return
        win = int(int(bet) * float(mult))
        changed = conn.execute("UPDATE mines_games SET status='won' WHERE id=? AND status='active'", (game_id,)).rowcount
        if changed != 1:
            conn.rollback(); await callback.answer("Игра уже завершена", show_alert=True); return
        conn.execute("UPDATE users SET balance_coin=balance_coin+?, total_wins=total_wins+1 WHERE user_id=?", (win, user_id))
        new_balance = conn.execute("SELECT balance_coin FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        conn.commit()
    grid = json.loads(grid_json) if grid_json else []
    kb = create_mines_keyboard(game_id, grid, opened, True)
    await callback.message.edit_text(
        f"<blockquote>💰 <b>Игра МИНЫ — ВЫИГРЫШ!</b>\n\n"
        f"💸 Ставка: {format_number(bet)} RCOIN\n📈 Множитель: {float(mult):.2f}x\n"
        f"💎 Открыто клеток: {opened}\n✅ Получено: +{format_number(win)} RCOIN\n"
        f"📊 Новый баланс: {format_number(new_balance)} RCOIN</blockquote>", reply_markup=kb)
    add_bet_history(user_id, "mines", bet, win, 1, f"mines={mines_count}, opened={opened}")
    await callback.answer("Выигрыш зачислен", show_alert=True)
    await state.clear()



@dp.callback_query(F.data.startswith("mines_cancel_"))
async def mines_cancel(callback: CallbackQuery, state: FSMContext):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, status FROM mines_games WHERE id = ?", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0) + bet_amount
    update_user(user_id, balance_coin=new_balance)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE mines_games SET status = 'cancelled' WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Игра МИНЫ отменена</b>\n\n"
        f"💰 Ставка {format_number(bet_amount)} RCOIN возвращена.\n"
        f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN"
    )
    await callback.answer("❌ Игра отменена", show_alert=True)
    await state.clear()


@dp.callback_query(F.data.startswith("mines_none_"))
async def mines_none(callback: CallbackQuery):
    await callback.answer()


# ==================== ИГРА БАШНЯ ====================
# Поле 5x5. Игрок открывает по одной клетке сверху вниз. Попал на мину — проигрыш.
# Множители растут с каждым уровнем (по скриншоту: x1.19, x1.48, x1.86, x2.32, x2.90...).

TOWER_MULT = [1.0, 1.19, 1.48, 1.86, 2.32, 2.90, 3.62, 4.52, 5.65, 7.06]


def build_tower_grid() -> list:
    """Сетка 5 уровней x 5 колонок. В каждом уровне 4 безопасные клетки и 1 мина."""
    grid = []
    for _ in range(5):
        row = [0] * 5
        bomb = random.randint(0, 4)
        row[bomb] = 1
        grid.append(row)
    return grid


def tower_kb(grid: list, level: int, game_id: int, bombs: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row_i in range(5):
        for col_i in range(5):
            if row_i < level and grid[row_i][col_i] == 1:
                builder.button(text=" ", callback_data=f"tower_none_{game_id}",
                               icon_custom_emoji_id=EMOJI_IDS["mines"])
            elif row_i < level:
                builder.button(text=" ", callback_data=f"tower_none_{game_id}",
                               icon_custom_emoji_id=EMOJI_IDS["diamond"])
            else:
                builder.button(text=" ", callback_data=f"tower_pick_{game_id}_{row_i}_{col_i}",
                               icon_custom_emoji_id=EMOJI_IDS["question"])
        builder.adjust(5)
    if level > 0:
        builder.button(text="💰 Забрать выигрыш", callback_data=f"tower_cashout_{game_id}",
                       icon_custom_emoji_id=EMOJI_IDS["win"])
    if level == 0:
        builder.button(text="💥 Отменить игру", callback_data=f"tower_cancel_{game_id}")
    builder.adjust(5)
    return builder.as_markup()


@dp.message(F.text.lower().startswith("башн"))
async def cmd_tower(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка данных.")
        return
    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>башня 500</code> – 500 RCOIN\n"
            "• <code>башня все</code> – весь баланс\n"
            "• <code>башня вб</code> – весь баланс"
        )
        return
    amount_str = parts[1]
    current_balance = user.get('balance_coin', 0)
    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)
    if bet_amount <= 0 or current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN")
        return

    grid = build_tower_grid()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO tower_games (user_id, bet_amount, level, bombs, mult, status, grid, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (user_id, bet_amount, 0, 1, 1.0, 'active', json.dumps(grid), int(time.time())))
    game_id = cur.lastrowid
    conn.commit()
    conn.close()
    update_user(user_id, balance_coin=current_balance - deduct_amount)

    kb = tower_kb(grid, 0, game_id, 1)
    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Игра БАШНЯ · начни игру!</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"💣 <b>Мин:</b> 1\n\n"
        f"📈 <b>Следующий уровень:</b>\n"
        + "\n".join(
            f"  {i+1} • <b>x{TOWER_MULT[i+1]:.2f}</b>" for i in range(min(5, len(TOWER_MULT)-1))) + "\n\n"
        f"<i>Выбирай клетку.</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("tower_pick_"))
async def tower_pick(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, _, gid_s, row_s, col_s = callback.data.split("_", 4)
    game_id = int(gid_s)
    row_i = int(row_s)
    col_i = int(col_s)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, level, bombs, mult, status, grid FROM tower_games WHERE id=?",
                (game_id,))
    game = cur.fetchone()
    conn.close()
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    gu, bet, level, bombs, mult, status, grid_json = game
    if gu != user_id:
        await callback.answer("Это не твоя игра", show_alert=True)
        return
    if status != 'active':
        await callback.answer("Игра завершена", show_alert=True)
        return
    if row_i != level:
        await callback.answer("Сначала открывай текущий уровень", show_alert=True)
        return
    grid = json.loads(grid_json)
    if grid[row_i][col_i] == 1:
        grid[row_i][col_i] = -1
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("UPDATE tower_games SET grid=?, status='lost' WHERE id=?", (json.dumps(grid), game_id))
        conn.commit(); conn.close()
        user = get_user(user_id)
        kb = tower_kb(grid, level + 1, game_id, bombs)
        await callback.message.edit_text(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['mines']} <b>БАШНЯ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet)} RCOIN\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(bet)} RCOIN\n"
            f"📊 <b>Баланс:</b> {format_number(user.get('balance_coin', 0))} RCOIN</blockquote>",
            reply_markup=kb)
        await callback.answer("💥 Попал на мину!", show_alert=True)
        return
    grid[row_i][col_i] = -1
    level += 1
    mult = TOWER_MULT[level] if level < len(TOWER_MULT) else TOWER_MULT[-1] * (1 + (level - len(TOWER_MULT)) * 0.3)
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("UPDATE tower_games SET level=?, mult=?, grid=? WHERE id=?",
              (level, mult, json.dumps(grid), game_id))
    conn.commit(); conn.close()
    user = get_user(user_id)
    pot = int(bet * mult)
    kb = tower_kb(grid, level, game_id, bombs)
    if level >= 5:
        grid = json.loads(json.dumps(grid))  # показать всю сетку
        kb = tower_kb(grid, 5, game_id, bombs)
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Игра БАШНЯ · игра идёт</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet)} RCOIN\n"
            f"📊 <b>Все уровни пройдены!</b>\n"
            f"💰 Выигрыш: {format_number(pot)} RCOIN",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data=f"tower_cashout_{game_id}")
            ]]))
    else:
        nxt = []
        for i in range(1, 6):
            if level + i < len(TOWER_MULT):
                nxt.append(f"{level+i} • <b>x{TOWER_MULT[level+i]:.2f}</b>")
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Игра БАШНЯ · игра идёт</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet)} RCOIN\n"
            f"📊 <b>Уровень:</b> {level}/5\n"
            f"📈 <b>Множитель:</b> x{mult:.2f}\n"
            f"💰 <b>Выигрыш:</b> {format_number(pot)} RCOIN\n"
            f"📊 <b>Следующий:</b>\n" + "\n".join(nxt[:3]) + "\n\n"
            f"<i>Выбирай клетку или забери выигрыш.</i>",
            reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("tower_cashout_"))
async def tower_cashout(callback: CallbackQuery):
    try:
        game_id = int(callback.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректная игра", show_alert=True); return
    user_id = callback.from_user.id
    with sqlite3.connect(DB_FILE, timeout=20) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT user_id, bet_amount, level, mult, status, grid FROM tower_games WHERE id=?", (game_id,)).fetchone()
        if not row:
            conn.rollback(); await callback.answer("Игра не найдена", show_alert=True); return
        game_user_id, bet, level, mult, status, grid_json = row
        if game_user_id != user_id:
            conn.rollback(); await callback.answer("Это не твоя игра", show_alert=True); return
        if status != "active":
            conn.rollback(); await callback.answer("Игра уже завершена", show_alert=True); return
        if int(level or 0) <= 0:
            conn.rollback(); await callback.answer("Сначала открой клетку", show_alert=True); return
        win = int(int(bet) * float(mult))
        changed = conn.execute("UPDATE tower_games SET status='won' WHERE id=? AND status='active'", (game_id,)).rowcount
        if changed != 1:
            conn.rollback(); await callback.answer("Игра уже завершена", show_alert=True); return
        conn.execute("UPDATE users SET balance_coin=balance_coin+?, total_wins=total_wins+1 WHERE user_id=?", (win, user_id))
        new_balance = conn.execute("SELECT balance_coin FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        conn.commit()
    grid = json.loads(grid_json) if grid_json else []
    await callback.message.edit_text(
        f"<blockquote>💰 <b>БАШНЯ — ВЫИГРЫШ!</b>\n\nСтавка: {format_number(bet)} RCOIN\n"
        f"Уровень: {level}\nМножитель: x{float(mult):.2f}\n"
        f"Получено: +{format_number(win)} RCOIN\nНовый баланс: {format_number(new_balance)} RCOIN</blockquote>",
        reply_markup=tower_kb(grid, 5, game_id, 1))
    add_bet_history(user_id, "tower", bet, win, 1, f"level={level}")
    await callback.answer("Выигрыш зачислен", show_alert=True)



@dp.callback_query(F.data.startswith("tower_cancel_"))
async def tower_cancel(callback: CallbackQuery):
    game_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, status FROM tower_games WHERE id=?", (game_id,))
    game = cur.fetchone()
    conn.close()
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    gu, bet, status = game
    if gu != user_id:
        await callback.answer("Это не твоя игра", show_alert=True)
        return
    if status != 'active':
        await callback.answer("Игра завершена", show_alert=True)
        return
    user = get_user(user_id)
    new_bal = user.get('balance_coin', 0) + bet
    update_user(user_id, balance_coin=new_bal)
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("UPDATE tower_games SET status='cancelled' WHERE id=?", (game_id,))
    conn.commit(); conn.close()
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Игра БАШНЯ отменена</b>\n\n"
        f"💰 Ставка {format_number(bet)} RCOIN возвращена.\n"
        f"📊 <b>Баланс:</b> {format_number(new_bal)} RCOIN")
    await callback.answer("💥 Игра отменена", show_alert=True)


@dp.callback_query(F.data.startswith("tower_none_"))
async def tower_none(callback: CallbackQuery):
    await callback.answer()


# ==================== ИГРА АРЕНА (2 игрока, ставка, шанс) ====================
# Игрок ставит ставку. Находит соперника. Через 15 сек шарик катится по ленте
# и останавливается возле победителя (у кого больший шанс — чаще выигрывает).

_arena_waiting = {}   # bet_amount -> [player_id]


@dp.message(F.text.lower().startswith("арена"))
async def cmd_arena(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка данных.")
        return
    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} <b>АРЕНА</b>\n\n"
            "Примеры:\n"
            "• <code>арена 500</code> – ставка 500 RCOIN\n"
            "• <code>арена 1000</code> – ставка 1000 RCOIN\n\n"
            "<i>Ждёшь второго игрока с той же ставкой → шарик катится → кто ближе — тот выигрывает!</i>"
        )
        return
    amount_str = parts[1]
    cur_bal = user.get("balance_coin", 0)
    bet, deduct = parse_bet_amount(amount_str, cur_bal)
    if bet <= 0 or cur_bal < deduct:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Баланс: {format_number(cur_bal)}")
        return

    # ищем соперника с той же ставкой
    rival_id = None
    for b, plist in list(_arena_waiting.items()):
        if b == bet and plist:
            rival_id = plist.pop(0)
            if not plist:
                del _arena_waiting[b]
            break
    if rival_id is None:
        _arena_waiting.setdefault(bet, []).append(user_id)
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} <b>АРЕНА</b>\n\n"
            f"💸 Ставка: {format_number(bet)} RCOIN\n"
            f"⏳ Ждём соперника с такой же ставкой...\n\n"
            f"<i>Команда повторно через пару секунд: <code>арена {amount_str}</code></i>"
        )
        return

    # старт матча: два игрока, шарик
    update_user(user_id, balance_coin=cur_bal - deduct)
    rival = get_user(rival_id)
    update_user(rival_id, balance_coin=(rival.get("balance_coin", 0) - deduct))
    # шанс ~ пропорционально балансу (при равных ставках — 50/50, бонус за больший рейтинг)
    chance_a = 50
    chance_b = 50
    pool = bet * 2 * 0.9  # 10% рейк казино
    win_amount = int(pool)

    b = InlineKeyboardBuilder()
    b.button(text="🎲 Запустить шар", callback_data=f"arena_roll_{user_id}_{rival_id}_{bet}")
    b.adjust(1)
    msg = await message.reply(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>АРЕНА — МАТЧ!</b>\n\n"
        f"⚔️ {user.get('display_name', '—')} (шанс {chance_a}%)\n"
        f"🤝 vs\n"
        f"⚔️ {rival.get('display_name', '—')} (шанс {chance_b}%)\n\n"
        f"💸 Приз: <b>{format_number(win_amount)} RCOIN</b>\n\n"
        f"<i>Нажми «Запустить шар» — через 15 сек он остановится возле победителя!</i>",
        reply_markup=b.as_markup()
    )
    # уведомляем соперника
    try:
        await bot.send_message(
            rival_id,
            f"{PREMIUM_EMOJI_TEXT['games']} <b>АРЕНА!</b>\n\n"
            f"Соперник найден: <b>{user.get('display_name', '—')}</b>\n"
            f"Ставка: <b>{format_number(bet)} RCOIN</b>\n"
            f"Приз: <b>{format_number(win_amount)} RCOIN</b>\n\n"
            f"Игра идёт — следи за чатом!"
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("arena_roll_"))
async def arena_roll(callback: CallbackQuery):
    parts = callback.data.split("_")
    a_id = int(parts[2]); b_id = int(parts[3]); bet = int(parts[4])
    user_id = callback.from_user.id
    if user_id not in (a_id, b_id):
        await callback.answer("Только участники матча", show_alert=True)
        return
    # запускаем шар: 15 сек «катится», потом результат
    await callback.answer("🎲 Шар покатился!")
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>АРЕНА — ШАР КАТИТСЯ...</b>\n\n"
        f"{'🎱'*1}  🎲  🎲  🎲  🎲\n\n"
        f"<i>Запуск через 15 секунд...</i>"
    )
    await asyncio.sleep(15)
    a = get_user(a_id); b = get_user(b_id)
    a_name = a.get("display_name", "Игрок А") if a else "Игрок А"
    b_name = b.get("display_name", "Игрок Б") if b else "Игрок Б"
    winner = a_id if random.random() < 0.5 else b_id
    win = int(bet * 2 * 0.9)
    w_user = get_user(winner)
    update_user(winner, balance_coin=(w_user.get("balance_coin", 0) + win),
                total_wins=(w_user.get("total_wins", 0) + 1))
    wname = a_name if winner == a_id else b_name
    await callback.message.edit_text(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['win']} <b>АРЕНА — РЕЗУЛЬТАТ!</b>\n\n"
        f"🎲 Шар остановился возле: <b>{wname}</b>\n\n"
        f"💰 Победитель получает: <b>+{format_number(win)} RCOIN</b></blockquote>"
    )
    await callback.answer("Шар остановился!", show_alert=True)


@dp.callback_query(F.data.startswith("arena_"))
async def arena_none(callback: CallbackQuery):
    await callback.answer()


# ==================== ИГРА КРАШ ====================

@dp.message(F.text.lower().startswith("краш"))
async def cmd_crash(message: Message, state: FSMContext):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.")
        return

    parts = message.text.lower().split()

    if len(parts) < 2:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>краш 100 2.5</code> – ставка 100 RCOIN, множитель x2.5\n"
            "• <code>краш 100</code> – ставка 100 RCOIN (без авто-забора)\n"
            "• <code>краш все 2.5</code> – ВЕСЬ баланс, множитель x2.5\n\n"
            "⚡ <b>Лимиты:</b>\n"
            "• Минимальная ставка: 1.1 RCOIN\n"
            "• Максимальная ставка: 1000 RCOIN\n"
            "• Множитель: от 1.01 до 5.00\n\n"
            "📌 <b>Правила:</b>\n"
            "• Вы выбираете множитель (от 1.01 до 5.00)\n"
            "• Ракета летит до случайного множителя\n"
            "• Если долетела до вашего - ВЫИГРЫШ!\n"
            "• Если крашнулась раньше - ПРОИГРЫШ!\n"
            "⚠️ Чем выше множитель - тем выше риск!"
        )
        return

    current_balance = user.get('balance_coin', 0)
    amount_str = parts[1]

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount < 1.1:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная ставка: 1.1 RCOIN")
        return

    if bet_amount > 1000:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Максимальная ставка: 1000 RCOIN")
        return

    if bet_amount <= 0 or bet_amount > current_balance:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно средств. Баланс: {format_number(current_balance)} RCOIN")
        return

    target_mult = 2.0
    if len(parts) >= 3:
        try:
            target_mult = float(parts[2])
            if target_mult < 1.01 or target_mult > 5.00:
                await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Множитель должен быть от 1.01 до 5.00")
                return
        except ValueError:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число. Пример: <code>краш 100 2.5</code>")
            return

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    r = random.random() * 100

    if r < 30:
        real_mult = round(random.uniform(1.01, 1.10), 2)
    elif r < 55:
        real_mult = round(random.uniform(1.11, 1.30), 2)
    elif r < 75:
        real_mult = round(random.uniform(1.31, 1.60), 2)
    elif r < 88:
        real_mult = round(random.uniform(1.61, 2.50), 2)
    elif r < 95:
        real_mult = round(random.uniform(2.51, 5.00), 2)
    elif r < 99:
        real_mult = round(random.uniform(5.01, 20.00), 2)
    elif r < 99.8:
        real_mult = round(random.uniform(20.01, 100.00), 2)
    elif r < 99.98:
        real_mult = round(random.uniform(100.01, 500.00), 2)
    else:
        real_mult = round(random.uniform(500.01, 1000.00), 2)

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if real_mult >= target_mult:
        win_amount = int(bet_amount * target_mult)
        new_balance = current_balance - deduct_amount + win_amount
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['crash']} <b>ИГРА КРАШ - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
            f"💰 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"🎯 <b>Ваш множитель:</b> {target_mult:.2f}x\n"
            f"🚀 <b>Ракета долетела до:</b> {real_mult:.2f}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(win_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "crash", bet_amount, win_amount, 1, f"target={target_mult}, real={real_mult}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        result_text = (
            f"<blockquote>💥 <b>ИГРА КРАШ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
            f"💰 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"🎯 <b>Ваш множитель:</b> {target_mult:.2f}x\n"
            f"💥 <b>Ракета крашнулась на:</b> {real_mult:.2f}x\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(deduct_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "crash", bet_amount, 0, 0, f"target={target_mult}, crashed_at={real_mult}")

    await message.reply(result_text)


# ==================== ИГРА ОХОТА ====================

@dp.message(F.text.lower().startswith("охота"))
async def game_hunt(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>охота 100</code> – ставка 100 RCOIN\n"
            "• <code>охота все</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    update_user(user_id, last_game_time=now)

    roll = random.random() * 100

    if roll < 0.5:
        mult = 100
        animal = '🐻 Медведь'
    elif roll < 1.5:
        mult = random.choice([10, 11, 12, 13, 14, 15])
        animal = '🐺 Волк'
    elif roll < 4.0:
        mult = random.choice([5, 6, 7, 8])
        animal = '🦊 Лиса'
    elif roll < 8.0:
        mult = random.choice([3, 4])
        animal = '🐰 Заяц'
    else:
        mult = 0
        animal = '💨 Убежал'

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if mult > 0:
        winnings = int(bet_amount * mult)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['hunt']} <b>Игра ОХОТА - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🐾 <b>Добыча:</b> {animal}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {mult}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "hunt", bet_amount, winnings, 1, f"animal={animal}, mult={mult}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)
        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['hunt']} <b>Игра ОХОТА - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🐾 <b>Результат:</b> {animal}\n"
            f"💸 <b>Ставка:</b> {bet_display} проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "hunt", bet_amount, 0, 0, f"animal=miss")

    await message.reply(result_text)


# ==================== ИГРА СПИН ====================

@dp.message(F.text.lower().startswith("спин"))
async def game_spin(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>спин 100</code> – ставка 100 RCOIN\n"
            "• <code>спин все</code> – ВЕСЬ баланс\n"
            "• <code>спин вб</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    update_user(user_id, last_game_time=int(time.time()))

    spin_msg = await message.answer_dice(emoji="🎰")
    await asyncio.sleep(2.5)
    roll = spin_msg.dice.value

    symbols = ['🍇', '🍒', '🍋', '7️⃣']

    idx0 = (roll - 1) % 6
    idx1 = roll % 6
    idx2 = (roll + 1) % 6

    result = [
        symbols[idx0],
        symbols[idx1],
        symbols[idx2]
    ]

    if result[0] == result[1] == result[2]:
        if result[0] == '7️⃣':
            mult = 100
        else:
            mult = 10
        win_text = "🎉 ТРИ ОДИНАКОВЫХ!"
        is_win = 1
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        mult = 2
        win_text = "😊 ДВА ОДИНАКОВЫХ!"
        is_win = 1
    else:
        mult = 0
        win_text = "💀 НИЧЕГО НЕ СОВПАЛО"
        is_win = 0

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if is_win:
        winnings = int(bet_amount * mult)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['spin']} <b>ИГРА СПИН</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎲 <b>Результат:</b> {' '.join(result)}\n"
            f"📊 <b>{win_text}</b>\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {mult}x\n"
            f"✅ <b>Выигрыш:</b> +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "spin", bet_amount, winnings, 1,
                        f"result={' '.join(result)}, mult={mult}, roll={roll}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['spin']} <b>ИГРА СПИН</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎲 <b>Результат:</b> {' '.join(result)}\n"
            f"📊 <b>{win_text}</b>\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"❌ <b>Проигрыш:</b> -{format_number(deduct_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "spin", bet_amount, 0, 0, f"result={' '.join(result)}, mult=0, roll={roll}")

    await message.reply(result_text)


# ==================== ИГРА ФУТБОЛ ====================

@dp.message(F.text.lower().startswith("футбол"))
async def game_football(message: Message):
    user_id = message.from_user.id

    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_game = user.get('last_game_time', 0)
    if now - last_game < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['games']} Подождите {2 - (now - last_game)} секунд перед следующей игрой!")
        return

    parts = message.text.lower().split()
    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>футбол 100 г</code> – гол (1.8x) ⚽\n"
            "• <code>футбол 100 м</code> – мимо (2.8x) ❌\n"
            "• <code>футбол все г</code> – ВЕСЬ баланс на гол"
        )
        return

    try:
        amount_str = parts[1]
        choice = parts[2]
    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)

    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно средств!</b>\n"
            f"💰 Ваш баланс: {format_number(current_balance)} RCOIN"
        )
        return

    if current_balance < deduct_amount:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
            f"💰 Баланс: {format_number(current_balance)} RCOIN"
        )
        return

    valid_choices = ['г', 'м']
    if choice not in valid_choices:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неверный выбор!</b>\n\n"
            "Варианты:\n"
            "• <code>г</code> – гол (1.8x) ⚽\n"
            "• <code>м</code> – мимо (2.8x) ❌"
        )
        return

    update_user(user_id, last_game_time=now)

    football_msg = await message.answer_dice(emoji="⚽")
    await asyncio.sleep(2.5)
    roll = football_msg.dice.value

    outcomes = {
        1: {'name': 'Мимо ❌', 'code': 'м', 'mult': 2.8},
        2: {'name': 'Мимо ❌', 'code': 'м', 'mult': 2.8},
        3: {'name': 'ГОЛ! ⚽', 'code': 'г', 'mult': 1.8},
        4: {'name': 'ГОЛ! ⚽', 'code': 'г', 'mult': 1.8},
        5: {'name': 'ГОЛ! ⚽', 'code': 'г', 'mult': 1.8},
        6: {'name': 'ГОЛ! ⚽', 'code': 'г', 'mult': 1.8},
    }

    outcome = outcomes.get(roll, outcomes[1])
    mult = outcome['mult']
    result_name = outcome['name']
    result_code = outcome['code']

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    is_anonymous = user.get('is_anonymous', 0)

    if is_anonymous:
        display_name = "Аноним"

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    if amount_str in ['все', 'вб']:
        bet_display = f"ВЕСЬ БАЛАНС ({format_number(bet_amount)} RCOIN)"
    else:
        bet_display = f"{format_number(bet_amount)} RCOIN"

    total_games = user.get('total_games', 0) + 1
    total_games_day = user.get('total_games_day', 0) + 1
    last_game_day = user.get('last_game_day', 0)
    now_day = int(time.time()) // 86400

    if last_game_day != now_day:
        total_games_day = 1
        last_game_day = now_day

    await check_titles(user_id, total_games)

    if choice == result_code:
        winnings = int(bet_amount * mult)
        new_balance = current_balance - deduct_amount + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        choice_names = {'г': 'Гол ⚽', 'м': 'Мимо ❌'}

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['football']} <b>Игра ФУТБОЛ - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ваш выбор:</b> {choice_names.get(choice, choice)}\n"
            f"🎯 <b>Результат:</b> {result_name}\n"
            f"💸 <b>Ставка:</b> {bet_display}\n"
            f"📈 <b>Множитель:</b> {mult}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "football", bet_amount, winnings, 1,
                        f"choice={choice}, result={result_code}, roll={roll}")
    else:
        new_balance = current_balance - deduct_amount
        update_user(user_id, balance_coin=new_balance, total_losses=user.get('total_losses', 0) + 1,
                    total_games=total_games, total_games_day=total_games_day, last_game_day=last_game_day)

        choice_names = {'г': 'Гол ⚽', 'м': 'Мимо ❌'}

        result_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['football']} <b>Игра ФУТБОЛ - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {display_name}\n"
            f"🎯 <b>Ваш выбор:</b> {choice_names.get(choice, choice)}\n"
            f"🎯 <b>Результат:</b> {result_name}\n"
            f"💸 <b>Ставка:</b> {bet_display} проиграна\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "football", bet_amount, 0, 0, f"choice={choice}, result={result_code}, roll={roll}")

    await message.reply(result_text)


# ==================== ИГРА ПИРАМИДА ====================

@dp.message(F.text.lower().startswith("пирамида"))
async def cmd_pyramid(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>пирамида 100</code> – ставка 100 RCOIN\n"
            "• <code>пирамида все</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)
    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0 or current_balance < deduct_amount:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Баланс: {format_number(current_balance)}")
        return

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    multipliers = [1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pyramid_games (user_id, bet_amount, level, multiplier, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, bet_amount, 1, 1.0, int(time.time())))
    game_id = cur.lastrowid
    conn.commit()
    conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚪1", callback_data=f"pyr_door_{game_id}_0",
                                 icon_custom_emoji_id=EMOJI_IDS["door"]),
            InlineKeyboardButton(text=f"🚪2", callback_data=f"pyr_door_{game_id}_1",
                                 icon_custom_emoji_id=EMOJI_IDS["door"])
        ],
        [
            InlineKeyboardButton(text=f"🚪3", callback_data=f"pyr_door_{game_id}_2",
                                 icon_custom_emoji_id=EMOJI_IDS["door"]),
            InlineKeyboardButton(text=f"🚪4", callback_data=f"pyr_door_{game_id}_3",
                                 icon_custom_emoji_id=EMOJI_IDS["door"])
        ],
        [
            InlineKeyboardButton(text=f"💰 Забрать", callback_data=f"pyr_cashout_{game_id}",
                                 icon_custom_emoji_id=EMOJI_IDS["balance"]),
            InlineKeyboardButton(text=f"❌ Отмена", callback_data=f"pyr_cancel_{game_id}")
        ]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['pyramid']} <b>ИГРА ПИРАМИДА</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"📊 <b>Уровень:</b> 1\n"
        f"📈 <b>Множитель:</b> 1.00x\n"
        f"💰 <b>Потенциальный выигрыш:</b> {format_number(bet_amount)} RCOIN\n\n"
        f"<i>Выберите дверь для поднятия на уровень выше!</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("pyr_door_"))
async def pyramid_door(callback: CallbackQuery):
    data = callback.data.split('_')
    game_id = int(data[2])
    door_index = int(data[3])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, level, status, multiplier FROM pyramid_games WHERE id = ?", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, level, status, mult = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    if level >= 10:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Вы достигли максимального уровня!", show_alert=True)
        return

    correct_door = random.randint(0, 3)

    if door_index != correct_door:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE pyramid_games SET status = 'lost' WHERE id = ?", (game_id,))
        conn.commit()
        conn.close()

        user = get_user(user_id)
        await callback.message.edit_text(
            f"<blockquote>💥 <b>ИГРА ПИРАМИДА - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"📊 <b>Уровень:</b> {level}\n"
            f"❌ <b>Итог:</b> ПРОИГРЫШ! -{format_number(bet_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(user.get('balance_coin', 0))} RCOIN</blockquote>"
        )
        await callback.answer("💥 Вы проиграли!", show_alert=True)
        return

    new_level = level + 1
    multipliers = [1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]
    new_mult = multipliers[new_level - 1]

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE pyramid_games SET level = ?, multiplier = ? WHERE id = ?",
                (new_level, new_mult, game_id))
    conn.commit()
    conn.close()

    potential_win = int(bet_amount * new_mult)

    user = get_user(user_id)

    if new_level >= 10:
        win_amount = int(bet_amount * new_mult)
        new_balance = user.get('balance_coin', 0) + win_amount
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1)

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE pyramid_games SET status = 'won' WHERE id = ?", (game_id,))
        conn.commit()
        conn.close()

        await callback.message.edit_text(
            f"<blockquote>🏆 <b>ИГРА ПИРАМИДА - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"📊 <b>Уровень:</b> {new_level} (МАКСИМУМ!)\n"
            f"📈 <b>Множитель:</b> {new_mult:.2f}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(win_amount)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "pyramid", bet_amount, win_amount, 1, f"level={new_level}, mult={new_mult}")
        await callback.answer("🏆 Вы достигли вершины пирамиды!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚪1", callback_data=f"pyr_door_{game_id}_0",
                                 icon_custom_emoji_id=EMOJI_IDS["door"]),
            InlineKeyboardButton(text=f"🚪2", callback_data=f"pyr_door_{game_id}_1",
                                 icon_custom_emoji_id=EMOJI_IDS["door"])
        ],
        [
            InlineKeyboardButton(text=f"🚪3", callback_data=f"pyr_door_{game_id}_2",
                                 icon_custom_emoji_id=EMOJI_IDS["door"]),
            InlineKeyboardButton(text=f"🚪4", callback_data=f"pyr_door_{game_id}_3",
                                 icon_custom_emoji_id=EMOJI_IDS["door"])
        ],
        [
            InlineKeyboardButton(text=f"💰 Забрать", callback_data=f"pyr_cashout_{game_id}",
                                 icon_custom_emoji_id=EMOJI_IDS["balance"]),
            InlineKeyboardButton(text=f"❌ Отмена", callback_data=f"pyr_cancel_{game_id}")
        ]
    ])

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['pyramid']} <b>ИГРА ПИРАМИДА</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"📊 <b>Уровень:</b> {new_level}\n"
        f"📈 <b>Множитель:</b> {new_mult:.2f}x\n"
        f"💰 <b>Потенциальный выигрыш:</b> {format_number(potential_win)} RCOIN\n\n"
        f"<i>Выберите дверь для поднятия на уровень выше!</i>",
        reply_markup=kb
    )
    await callback.answer(f"✅ Вы выбрали правильную дверь! Уровень {new_level}")


@dp.callback_query(F.data.startswith("pyr_cashout_"))
async def pyramid_cashout(callback: CallbackQuery):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, multiplier, level, status FROM pyramid_games WHERE id = ?", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, multiplier, level, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    win_amount = int(bet_amount * multiplier)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE pyramid_games SET status = 'won' WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0) + win_amount
    update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1)

    await callback.message.edit_text(
        f"<blockquote>💰 <b>ИГРА ПИРАМИДА - ВЫИГРЫШ!</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"📊 <b>Уровень:</b> {level}\n"
        f"📈 <b>Множитель:</b> {multiplier:.2f}x\n"
        f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(win_amount)} RCOIN\n\n"
        f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
    )
    add_bet_history(user_id, "pyramid", bet_amount, win_amount, 1, f"level={level}, mult={multiplier}")
    await callback.answer("💰 Выигрыш получен!", show_alert=True)


@dp.callback_query(F.data.startswith("pyr_cancel_"))
async def pyramid_cancel(callback: CallbackQuery):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, bet_amount, status FROM pyramid_games WHERE id = ?", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        return

    game_user_id, bet_amount, status = game

    if game_user_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваша игра.", show_alert=True)
        return

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        return

    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0) + bet_amount
    update_user(user_id, balance_coin=new_balance)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE pyramid_games SET status = 'cancelled' WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Игра ПИРАМИДА отменена</b>\n\n"
        f"💰 Ставка {format_number(bet_amount)} RCOIN возвращена.\n"
        f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN"
    )
    await callback.answer("❌ Игра отменена", show_alert=True)


# ==================== ИГРА МАЙНЕР ====================

@dp.message(F.text.lower().startswith("майнер"))
async def cmd_miner(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT mine_level, business_level, villa_level, last_collect, total_earned FROM miner_data WHERE user_id = ?",
        (user_id,))
    row = cur.fetchone()

    if not row:
        cur.execute("""
            INSERT INTO miner_data (user_id, mine_level, business_level, villa_level, last_collect, total_earned)
            VALUES (?, 0, 0, 0, 0, 0)
        """, (user_id,))
        conn.commit()
        cur.execute(
            "SELECT mine_level, business_level, villa_level, last_collect, total_earned FROM miner_data WHERE user_id = ?",
            (user_id,))
        row = cur.fetchone()
    conn.close()

    mine_level, business_level, villa_level, last_collect, total_earned = row

    now = int(time.time())

    mine_income = mine_level * 15000
    business_income = business_level * 30000
    villa_income = villa_level * 100000
    total_income = mine_income + business_income + villa_income

    next_collect = last_collect + 3600
    can_collect = now >= next_collect
    time_left = next_collect - now if not can_collect else 0

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Купить Шахту", callback_data="miner_buy_mine",
                              icon_custom_emoji_id=EMOJI_IDS["miner"]),
         InlineKeyboardButton(text=f"Купить Бизнес-дом", callback_data="miner_buy_business",
                              icon_custom_emoji_id=EMOJI_IDS["miner"])],
        [InlineKeyboardButton(text=f"Купить Виллу", callback_data="miner_buy_villa",
                              icon_custom_emoji_id=EMOJI_IDS["miner"]),
         InlineKeyboardButton(text=f"Собрать доход", callback_data="miner_collect",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Моя статистика", callback_data="miner_stats",
                              icon_custom_emoji_id=EMOJI_IDS["profile"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    status_text = f"Доступно" if can_collect else f"Через {get_time_until(now + time_left)}"

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['miner']} <b>МАЙНЕР</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['mine']} <b>Шахта:</b> {mine_level} ур. | {format_number(mine_income)} RCOIN/час\n"
        f"{PREMIUM_EMOJI_TEXT['business']} <b>Бизнес-дом:</b> {business_level} ур. | {format_number(business_income)} RCOIN/час\n"
        f"{PREMIUM_EMOJI_TEXT['villa']} <b>Вилла:</b> {villa_level} ур. | {format_number(villa_income)} RCOIN/час\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Доход:</b> {format_number(total_income)} RCOIN/час\n"
        f"💰 <b>Всего заработано:</b> {format_number(total_earned)} RCOIN\n\n"
        f"{PREMIUM_EMOJI_TEXT['collect']} <b>Сбор дохода:</b> {status_text}\n\n"
        f"📌 <b>Стоимость улучшений:</b>\n"
        f"{PREMIUM_EMOJI_TEXT['mine']} Шахта: 15 000 000 RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['business']} Бизнес-дом: 30 000 000 RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['villa']} Вилла: 100 000 000 RCOIN",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("miner_buy_"))
async def miner_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    building = callback.data.split('_')[2]

    costs = {
        "mine": 15000000,
        "business": 30000000,
        "villa": 100000000
    }

    fields = {
        "mine": "mine_level",
        "business": "business_level",
        "villa": "villa_level"
    }

    cost = costs.get(building, 0)
    field = fields.get(building)

    user = get_user(user_id)
    if not user:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.", show_alert=True)
        return

    if user.get('balance_coin', 0) < cost:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно: {format_number(cost)}",
                              show_alert=True)
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(f"SELECT {field} FROM miner_data WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    current_level = row[0] if row else 0
    if current_level >= 3:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Максимальный уровень 3!", show_alert=True)
        conn.close()
        return

    new_balance = user.get('balance_coin', 0) - cost
    update_user(user_id, balance_coin=new_balance)

    cur.execute(f"UPDATE miner_data SET {field} = {field} + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    building_names = {
        "mine": "Шахта",
        "business": "Бизнес-дом",
        "villa": "Вилла"
    }

    await callback.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} {building_names[building]} улучшена до уровня {current_level + 1}!")
    await cmd_miner(callback.message)


@dp.callback_query(F.data == "miner_collect")
async def miner_collect(callback: CallbackQuery):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT mine_level, business_level, villa_level, last_collect, total_earned FROM miner_data WHERE user_id = ?",
        (user_id,))
    row = cur.fetchone()

    if not row:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.", show_alert=True)
        return

    mine_level, business_level, villa_level, last_collect, total_earned = row
    now = int(time.time())

    if now < last_collect + 3600:
        wait_time = last_collect + 3600 - now
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['games']} Сбор доступен через {get_time_until(now + wait_time)}",
                              show_alert=True)
        return

    income = (mine_level * 15000) + (business_level * 30000) + (villa_level * 100000)

    if income == 0:
        await callback.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} У вас нет построек для сбора дохода. Купите хотя бы Шахту!", show_alert=True)
        return

    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0) + income
    new_total = total_earned + income

    update_user(user_id, balance_coin=new_balance)
    cur.execute("""
        UPDATE miner_data 
        SET last_collect = ?, total_earned = ?
        WHERE user_id = ?
    """, (now, new_total, user_id))
    conn.commit()
    conn.close()

    await callback.answer(f"{PREMIUM_EMOJI_TEXT['collect']} Собрано {format_number(income)} RCOIN!", show_alert=True)
    await cmd_miner(callback.message)


@dp.callback_query(F.data == "miner_stats")
async def miner_stats(callback: CallbackQuery):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT mine_level, business_level, villa_level, total_earned FROM miner_data WHERE user_id = ?",
                (user_id,))
    row = cur.fetchone()

    if not row:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.", show_alert=True)
        return

    mine_level, business_level, villa_level, total_earned = row

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['miner']} <b>СТАТИСТИКА МАЙНЕРА</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['mine']} <b>Шахта:</b> {mine_level} ур.\n"
        f"{PREMIUM_EMOJI_TEXT['business']} <b>Бизнес-дом:</b> {business_level} ур.\n"
        f"{PREMIUM_EMOJI_TEXT['villa']} <b>Вилла:</b> {villa_level} ур.\n"
        f"💰 <b>Всего заработано:</b> {format_number(total_earned)} RCOIN",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="miner_back", icon_custom_emoji_id=EMOJI_IDS["balance"])]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "miner_back")
async def miner_back(callback: CallbackQuery):
    await cmd_miner(callback.message)
    await callback.answer()


# ==================== ИГРА ХИ-ЛО ====================

async def game_hi_lo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("❌ Ошибка получения данных пользователя.")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.answer(
            f"❌ <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>хило 100</code> – ставка 100 RCOIN\n"
            "• <code>хило все</code> – ВЕСЬ баланс"
        )
        return

    try:
        amount_str = parts[1]
    except ValueError:
        await message.answer("❌ Ошибка в формате.")
        return

    current_balance = user.get('balance_coin', 0)
    bet_amount, deduct_amount = parse_bet_amount(amount_str, current_balance)

    if bet_amount <= 0 or current_balance < deduct_amount:
        await message.answer(f"❌ Недостаточно RCOIN! Баланс: {format_number(current_balance)}")
        return

    deck = list(range(2, 15)) * 4
    random.shuffle(deck)
    current_card = deck.pop()
    multiplier = 1.0
    round_num = 0

    update_user(user_id, balance_coin=current_balance - deduct_amount)

    await state.update_data(
        game_type="hi_lo",
        deck=deck,
        current_card=current_card,
        bet_amount=bet_amount,
        deduct_amount=deduct_amount,
        multiplier=multiplier,
        round=round_num,
        started=False
    )

    card_names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K',
                  14: 'A'}
    card_display = card_names.get(current_card, str(current_card))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎯 НАЧАТЬ ИГРУ",
            callback_data="hi_lo_start",
            icon_custom_emoji_id=EMOJI_IDS["hi_lo"]
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="hi_lo_cancel",
            icon_custom_emoji_id=EMOJI_IDS["lock"]
        )]
    ])

    await message.answer(
        f"🎴 <b>ИГРА ХИ-ЛО</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
        f"💰 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"🎴 <b>Текущая карта:</b> {card_display}\n\n"
        f"<i>Нажмите НАЧАТЬ ИГРУ чтобы продолжить</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data == "hi_lo_start")
async def hi_lo_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    data = await state.get_data()
    if not data or data.get('game_type') != 'hi_lo':
        await callback.answer("❌ Игра не найдена.", show_alert=True)
        return

    await state.update_data(started=True, round=1)

    data = await state.get_data()
    current_card = data.get('current_card')
    bet_amount = data.get('bet_amount')

    card_names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K',
                  14: 'A'}
    card_display = card_names.get(current_card, str(current_card))

    deck = data.get('deck', [])
    remaining = len(deck) + 1
    higher = sum(1 for c in deck if c > current_card)
    lower = sum(1 for c in deck if c < current_card)
    higher_percent = round(higher / remaining * 100, 1)
    lower_percent = round(lower / remaining * 100, 1)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⬆️ ВЫШЕ ({higher_percent}%)",
            callback_data="hi_lo_higher",
            icon_custom_emoji_id=EMOJI_IDS["hi_lo"]
        ),
            InlineKeyboardButton(
                text=f"⬇️ НИЖЕ ({lower_percent}%)",
                callback_data="hi_lo_lower",
                icon_custom_emoji_id=EMOJI_IDS["hi_lo"]
            )],
        [InlineKeyboardButton(
            text="💰 ЗАБРАТЬ (1.0x)",
            callback_data="hi_lo_cashout",
            icon_custom_emoji_id=EMOJI_IDS["balance"]
        )]
    ])

    await callback.message.edit_text(
        f"🎴 <b>ИГРА ХИ-ЛО</b>\n\n"
        f"👤 <b>Игрок:</b> {callback.from_user.username or 'без_ника'}\n"
        f"💰 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"🎴 <b>Текущая карта:</b> {card_display}\n"
        f"📈 <b>Множитель:</b> 1.0x\n"
        f"🔄 <b>Раунд:</b> 1\n"
        f"📊 <b>Шансы:</b> ⬆️ {higher_percent}% | ⬇️ {lower_percent}%\n\n"
        f"<i>Выберите: следующая карта будет выше или ниже?</i>",
        reply_markup=kb
    )
    await callback.answer("🎯 Игра начата!")


@dp.callback_query(F.data == "hi_lo_cancel")
async def hi_lo_cancel(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    data = await state.get_data()
    if not data or data.get('game_type') != 'hi_lo':
        await callback.answer("❌ Игра не найдена.", show_alert=True)
        return

    bet_amount = data.get('bet_amount')
    user = get_user(user_id)
    new_balance = user.get('balance_coin', 0) + bet_amount
    update_user(user_id, balance_coin=new_balance)

    await callback.message.edit_text(
        f"❌ <b>Игра отменена</b>\n\n"
        f"💰 Ставка {format_number(bet_amount)} RCOIN возвращена."
    )
    await state.clear()
    await callback.answer("❌ Игра отменена")


@dp.callback_query(F.data.startswith("hi_lo_higher"))
@dp.callback_query(F.data.startswith("hi_lo_lower"))
async def hi_lo_choice(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    choice = callback.data.split('_')[2]

    data = await state.get_data()
    if not data or data.get('game_type') != 'hi_lo':
        await callback.answer("❌ Игра не найдена.", show_alert=True)
        return

    if not data.get('started', False):
        await callback.answer("❌ Сначала нажмите НАЧАТЬ ИГРУ!", show_alert=True)
        return

    deck = data.get('deck', [])
    current_card = data.get('current_card')
    bet_amount = data.get('bet_amount')
    multiplier = data.get('multiplier', 1.0)
    round_num = data.get('round', 1)

    if not deck:
        await callback.answer("❌ Колода закончилась.", show_alert=True)
        return

    next_card = deck.pop()

    if choice == 'higher':
        win = next_card > current_card
    else:
        win = next_card < current_card

    card_names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K',
                  14: 'A'}
    current_display = card_names.get(current_card, str(current_card))
    next_display = card_names.get(next_card, str(next_card))

    if not win:
        user = get_user(user_id)
        new_balance = user.get('balance_coin', 0)
        update_user(user_id, total_losses=user.get('total_losses', 0) + 1)

        await callback.message.edit_text(
            f"<blockquote>💥 <b>ИГРА ХИ-ЛО - ПРОИГРЫШ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Было:</b> {current_display}\n"
            f"🎴 <b>Стало:</b> {next_display}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"📈 <b>Множитель:</b> {multiplier:.2f}x\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "hi_lo", bet_amount, 0, 0, f"lost_at_round={round_num}")
        await state.clear()
        await callback.answer()
        return

    round_num += 1
    multipliers = [1.5, 2.5, 4.0, 6.5, 10.0]
    if round_num - 1 < len(multipliers):
        new_mult = multipliers[round_num - 1]
    else:
        new_mult = multipliers[-1]

    if round_num > 5:
        winnings = int(bet_amount * new_mult)
        user = get_user(user_id)
        new_balance = user.get('balance_coin', 0) + winnings
        update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1)

        await callback.message.edit_text(
            f"<blockquote>🎉 <b>ИГРА ХИ-ЛО - ПОБЕДА!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
            f"🎴 <b>Было:</b> {current_display}\n"
            f"🎴 <b>Стало:</b> {next_display}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
            f"📈 <b>Множитель:</b> {new_mult:.2f}x\n"
            f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
            f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
        )
        add_bet_history(user_id, "hi_lo", bet_amount, winnings, 1, f"max_rounds={round_num}")
        await state.clear()
        await callback.answer("🏆 МАКСИМУМ! ВЫ ПОБЕДИЛИ!")
        return

    await state.update_data(
        deck=deck,
        current_card=next_card,
        multiplier=new_mult,
        round=round_num
    )

    potential_win = int(bet_amount * new_mult)

    remaining = len(deck) + 1
    higher = sum(1 for c in deck if c > next_card)
    lower = sum(1 for c in deck if c < next_card)
    higher_percent = round(higher / remaining * 100, 1)
    lower_percent = round(lower / remaining * 100, 1)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⬆️ ВЫШЕ ({higher_percent}%)",
            callback_data="hi_lo_higher",
            icon_custom_emoji_id=EMOJI_IDS["hi_lo"]
        ),
            InlineKeyboardButton(
                text=f"⬇️ НИЖЕ ({lower_percent}%)",
                callback_data="hi_lo_lower",
                icon_custom_emoji_id=EMOJI_IDS["hi_lo"]
            )],
        [InlineKeyboardButton(
            text=f"💰 ЗАБРАТЬ ({new_mult:.1f}x)",
            callback_data="hi_lo_cashout",
            icon_custom_emoji_id=EMOJI_IDS["balance"]
        )]
    ])

    user = get_user(user_id)
    await callback.message.edit_text(
        f"🎴 <b>ИГРА ХИ-ЛО</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"💰 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"🎴 <b>Текущая карта:</b> {next_display}\n"
        f"📈 <b>Множитель:</b> {new_mult:.2f}x\n"
        f"🔄 <b>Раунд:</b> {round_num}\n"
        f"💰 <b>Потенциальный выигрыш:</b> {format_number(potential_win)} RCOIN\n"
        f"📊 <b>Шансы:</b> ⬆️ {higher_percent}% | ⬇️ {lower_percent}%\n\n"
        f"<i>Выберите: следующая карта будет выше или ниже?</i>",
        reply_markup=kb
    )
    await callback.answer(f"✅ Вы угадали! Множитель: {new_mult:.2f}x")


@dp.callback_query(F.data == "hi_lo_cashout")
async def hi_lo_cashout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    data = await state.get_data()
    if not data or data.get('game_type') != 'hi_lo':
        await callback.answer("❌ Игра не найдена.", show_alert=True)
        return

    if not data.get('started', False):
        await callback.answer("❌ Сначала нажмите НАЧАТЬ ИГРУ!", show_alert=True)
        return

    bet_amount = data.get('bet_amount')
    multiplier = data.get('multiplier', 1.0)

    user = get_user(user_id)
    winnings = int(bet_amount * multiplier)
    new_balance = user.get('balance_coin', 0) + winnings
    update_user(user_id, balance_coin=new_balance, total_wins=user.get('total_wins', 0) + 1)

    await callback.message.edit_text(
        f"<blockquote>💰 <b>ИГРА ХИ-ЛО - ВЫИГРЫШ!</b>\n\n"
        f"👤 <b>Игрок:</b> {user.get('display_name', callback.from_user.username or 'без_ника')}\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n"
        f"📈 <b>Множитель:</b> {multiplier:.2f}x\n"
        f"✅ <b>Итог:</b> ПОБЕДА! +{format_number(winnings)} RCOIN\n\n"
        f"📊 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN</blockquote>"
    )
    add_bet_history(user_id, "hi_lo", bet_amount, winnings, 1, f"cashout_at={multiplier:.2f}x")
    await state.clear()
    await callback.answer(f"💰 Выигрыш {format_number(winnings)} RCOIN получен!")


# ==================== КРЕСТИКИ-НОЛИКИ (КН) ====================

@dp.message(F.text.lower().startswith("кн"))
async def cmd_ttt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    parts = message.text.lower().split()

    if len(parts) < 2:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Создать игру", callback_data="ttt_create",
                                  icon_custom_emoji_id=EMOJI_IDS["ttt"])],
            [InlineKeyboardButton(text=f"Активные игры", callback_data="ttt_list",
                                  icon_custom_emoji_id=EMOJI_IDS["ttt"])],
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                                  icon_custom_emoji_id=EMOJI_IDS["balance"])]
        ])
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['ttt']} <b>КРЕСТИКИ-НОЛИКИ</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n\n"
            f"📌 <b>Как играть:</b>\n"
            f"1. <code>кн 1000</code> (в ответ на сообщение соперника)\n"
            f"2. Соперник принимает вызов\n"
            f"3. Играйте по очереди!\n"
            f"4. Победитель забирает ставку!\n\n"
            f"<i>Первый ход делает создатель игры.</i>",
            reply_markup=kb
        )
        return

    if message.reply_to_message:
        opponent_id = message.reply_to_message.from_user.id
        if opponent_id == user_id:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя играть с самим собой.")
            return

        try:
            bet_amount = parse_amount(parts[1])
            if bet_amount <= 0:
                await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ставка должна быть положительной.")
                return
        except:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите сумму ставки.")
            return

        user = get_user(user_id)
        opponent = get_user(opponent_id)

        if not opponent:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Пользователь не найден.")
            return

        if user.get('balance_coin', 0) < bet_amount:
            await message.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно средств. Нужно: {format_number(bet_amount)} RCOIN")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Принять", callback_data=f"ttt_accept_{opponent_id}_{bet_amount}",
                                  icon_custom_emoji_id=EMOJI_IDS["ttt"]),
             InlineKeyboardButton(text=f"Отклонить", callback_data=f"ttt_decline_{opponent_id}")]
        ])

        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['ttt']} <b>ВЫЗОВ В КРЕСТИКИ-НОЛИКИ!</b>\n\n"
            f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
            f"👤 <b>Соперник:</b> {opponent.get('display_name', 'User ' + str(opponent_id))}\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
            f"<i>Победитель забирает {format_number(bet_amount * 2)} RCOIN!</i>"
        )

        try:
            await bot.send_message(
                opponent_id,
                f"{PREMIUM_EMOJI_TEXT['ttt']} <b>ВЫЗОВ В КРЕСТИКИ-НОЛИКИ!</b>\n\n"
                f"👤 <b>Игрок:</b> {user.get('display_name', message.from_user.username or 'без_ника')}\n"
                f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
                f"Нажмите кнопку, чтобы принять или отклонить вызов.",
                reply_markup=kb
            )
        except:
            pass
        return

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
        f"Пример: <code>кн 1000</code> (в ответ на сообщение соперника)"
    )


@dp.callback_query(F.data.startswith("ttt_accept_"))
async def ttt_accept_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split('_')
    opponent_id = int(data[2])
    bet_amount = int(data[3])
    user_id = callback.from_user.id

    user = get_user(user_id)
    opponent = get_user(opponent_id)

    if not opponent:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Соперник не найден.", show_alert=True)
        return

    if user.get('balance_coin', 0) < bet_amount:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно средств для ставки.", show_alert=True)
        return

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - bet_amount)
    update_user(opponent_id, balance_coin=opponent.get('balance_coin', 0) - bet_amount)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tic_tac_toe (player1, player2, current_turn, status, created_at, bet_amount)
        VALUES (?, ?, ?, 'active', ?, ?)
    """, (opponent_id, user_id, opponent_id, int(time.time()), bet_amount))
    game_id = cur.lastrowid
    conn.commit()
    conn.close()

    kb = get_ttt_keyboard(game_id, "---------", opponent_id, user_id)

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['ttt']} <b>ИГРА НАЧАЛАСЬ!</b>\n\n"
        f"❌ {opponent.get('display_name', 'User ' + str(opponent_id))} (X)\n"
        f"⭕ {user.get('display_name', 'User ' + str(user_id))} (O)\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
        f"<i>Ход: X</i>",
        reply_markup=kb
    )

    try:
        await bot.send_message(
            opponent_id,
            f"{PREMIUM_EMOJI_TEXT['ttt']} <b>ИГРА НАЧАЛАСЬ!</b>\n\n"
            f"❌ {opponent.get('display_name', 'User ' + str(opponent_id))} (X)\n"
            f"⭕ {user.get('display_name', 'User ' + str(user_id))} (O)\n"
            f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
            f"<i>Ваш ход!</i>",
            reply_markup=kb
        )
    except:
        pass

    await callback.answer("✅ Игра начата!")


@dp.callback_query(F.data.startswith("ttt_decline_"))
async def ttt_decline_callback(callback: CallbackQuery):
    await callback.message.edit_text(f"{PREMIUM_EMOJI_TEXT['lock']} Вы отклонили вызов.")
    await callback.answer("❌ Вы отклонили вызов.")


def get_ttt_keyboard(game_id: int, board: str, current_turn: int, user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            char = board[idx] if idx < len(board) else '-'
            if char == '-':
                text = "⬜"
                callback_data = f"ttt_move_{game_id}_{idx}"
            elif char == 'X':
                text = "❌"
                callback_data = "ttt_none"
            else:
                text = "⭕"
                callback_data = "ttt_none"
            row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        kb.row(*row)

    kb.button(text=f"Выйти из игры", callback_data=f"ttt_quit_{game_id}")
    return kb.as_markup()


@dp.callback_query(F.data.startswith("ttt_move_"))
async def ttt_move(callback: CallbackQuery):
    data = callback.data.split('_')
    game_id = int(data[2])
    position = int(data[3])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT player1, player2, current_turn, board, status, bet_amount
        FROM tic_tac_toe
        WHERE id = ?
    """, (game_id,))
    game = cur.fetchone()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        conn.close()
        return

    p1, p2, current, board, status, bet_amount = game

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        conn.close()
        return

    if current != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['games']} Сейчас не ваш ход.", show_alert=True)
        conn.close()
        return

    if position < 0 or position >= len(board) or board[position] != '-':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Эта клетка уже занята.", show_alert=True)
        conn.close()
        return

    player_symbol = 'X' if user_id == p1 else 'O'
    board_list = list(board)
    board_list[position] = player_symbol
    board = ''.join(board_list)

    win_lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    ]

    winner = None
    for a, b, c in win_lines:
        if board[a] == board[b] == board[c] and board[a] != '-':
            winner = board[a]
            break

    next_turn = p2 if user_id == p1 else p1

    if winner:
        cur.execute("UPDATE tic_tac_toe SET board = ?, status = 'finished' WHERE id = ?", (board, game_id))
        conn.commit()
        conn.close()

        winner_id = p1 if winner == 'X' else p2
        loser_id = p2 if winner_id == p1 else p1

        user_winner = get_user(winner_id)
        user_loser = get_user(loser_id)

        win_amount = bet_amount * 2
        update_user(winner_id, balance_coin=user_winner.get('balance_coin', 0) + win_amount)

        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['win']} <b>ИГРА ЗАВЕРШЕНА!</b>\n\n"
            f"👤 <b>Победитель:</b> {user_winner.get('display_name', 'User ' + str(winner_id))}\n"
            f"💸 <b>Выигрыш:</b> {format_number(win_amount)} RCOIN\n\n"
            f"🎯 <b>Итоговая доска:</b>",
            reply_markup=get_ttt_keyboard(game_id, board, 0, user_id)
        )

        try:
            await bot.send_message(
                loser_id,
                f"{PREMIUM_EMOJI_TEXT['lose']} <b>ИГРА ЗАВЕРШЕНА!</b>\n\n"
                f"👤 <b>Победитель:</b> {user_winner.get('display_name', 'User ' + str(winner_id))}\n"
                f"💸 <b>Проигрыш:</b> {format_number(bet_amount)} RCOIN"
            )
        except:
            pass

        await callback.answer(
            f"{PREMIUM_EMOJI_TEXT['win']} Вы победили!" if winner_id == user_id else f"{PREMIUM_EMOJI_TEXT['lose']} Соперник победил!")
        return

    if '-' not in board:
        cur.execute("UPDATE tic_tac_toe SET board = ?, status = 'draw' WHERE id = ?", (board, game_id))
        conn.commit()
        conn.close()

        update_user(p1, balance_coin=get_user(p1).get('balance_coin', 0) + bet_amount)
        update_user(p2, balance_coin=get_user(p2).get('balance_coin', 0) + bet_amount)

        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['balance']} <b>НИЧЬЯ!</b>\n\n"
            f"💸 Ставки возвращены.",
            reply_markup=get_ttt_keyboard(game_id, board, 0, user_id)
        )
        await callback.answer("🤝 Ничья!")
        return

    cur.execute("UPDATE tic_tac_toe SET board = ?, current_turn = ? WHERE id = ?",
                (board, next_turn, game_id))
    conn.commit()
    conn.close()

    player = get_user(user_id)
    opponent = get_user(next_turn)

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['ttt']} <b>КРЕСТИКИ-НОЛИКИ</b>\n\n"
        f"❌ {player.get('display_name', 'User ' + str(user_id))} (X)\n"
        f"⭕ {opponent.get('display_name', 'User ' + str(next_turn))} (O)\n"
        f"💸 <b>Ставка:</b> {format_number(bet_amount)} RCOIN\n\n"
        f"<i>Ход: {'X' if next_turn == p1 else 'O'}</i>",
        reply_markup=get_ttt_keyboard(game_id, board, next_turn, user_id)
    )

    try:
        await bot.send_message(
            next_turn,
            f"{PREMIUM_EMOJI_TEXT['ttt']} <b>Ваш ход в игре!</b>\n\n"
            f"🆔 ID игры: {game_id}"
        )
    except:
        pass

    await callback.answer("✅ Ход сделан!")


@dp.callback_query(F.data.startswith("ttt_quit_"))
async def ttt_quit(callback: CallbackQuery):
    game_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT player1, player2, status, bet_amount FROM tic_tac_toe WHERE id = ?", (game_id,))
    game = cur.fetchone()

    if not game:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра не найдена.", show_alert=True)
        conn.close()
        return

    p1, p2, status, bet_amount = game

    if status != 'active':
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Игра уже завершена.", show_alert=True)
        conn.close()
        return

    if user_id != p1 and user_id != p2:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Вы не в этой игре.", show_alert=True)
        conn.close()
        return

    opponent = p2 if user_id == p1 else p1

    user_quit = get_user(user_id)
    user_opp = get_user(opponent)

    update_user(opponent, balance_coin=user_opp.get('balance_coin', 0) + bet_amount * 2)

    cur.execute("UPDATE tic_tac_toe SET status = 'quit' WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>ИГРА ЗАВЕРШЕНА</b>\n\n"
        f"👤 Игрок {user_quit.get('display_name', 'User ' + str(user_id))} вышел из игры.\n"
        f"👤 {user_opp.get('display_name', 'User ' + str(opponent))} победил! +{format_number(bet_amount * 2)} RCOIN"
    )

    try:
        await bot.send_message(
            opponent,
            f"{PREMIUM_EMOJI_TEXT['win']} <b>Игра #{game_id} завершена</b>\n\n"
            f"Соперник вышел из игры.\n"
            f"💰 Вы получили {format_number(bet_amount * 2)} RCOIN!"
        )
    except:
        pass

    await callback.answer("🚪 Вы вышли из игры")


@dp.callback_query(F.data == "ttt_none")
async def ttt_none(callback: CallbackQuery):
    await callback.answer()


# ==================== СИСТЕМА ТИТУЛОВ ====================

TITLES = {
    1000: f"{PREMIUM_EMOJI_TEXT['games']} ИГРОК",
    2500: f"{PREMIUM_EMOJI_TEXT['diamond']} БОЕЦ",
    5000: f"{PREMIUM_EMOJI_TEXT['darts']} СНАЙПЕР",
    10000: f"{PREMIUM_EMOJI_TEXT['star']} ЛЕГЕНДА",
    25000: f"{PREMIUM_EMOJI_TEXT['crash']} МАСТЕР",
    50000: f"{PREMIUM_EMOJI_TEXT['nft']} ГРАНД",
    100000: f"{PREMIUM_EMOJI_TEXT['bank']} ИМПЕРАТОР"
}


async def check_titles(user_id: int, total_games: int):
    user = get_user(user_id)
    if not user:
        return

    titles = json.loads(user.get('titles', '[]'))
    current_title = user.get('rank_title', 'Новичок')

    for games, title in sorted(TITLES.items()):
        if total_games >= games and title not in titles:
            titles.append(title)
            update_user(user_id, titles=json.dumps(titles))

    new_title = 'Новичок'
    for games, title in sorted(TITLES.items()):
        if total_games >= games:
            new_title = title

    if new_title != current_title:
        update_user(user_id, rank_title=new_title)


# ==================== КОМАНДА ТОП ====================

@dp.message(F.text.lower() == "топ")
@dp.message(Command("топ"))
async def cmd_top(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Топ RCOIN", callback_data="top_vfg", icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Топ RBP", callback_data="top_point",
                              icon_custom_emoji_id=EMOJI_IDS["diamond"])],
        [InlineKeyboardButton(text=f"Топ по играм", callback_data="top_games",
                              icon_custom_emoji_id=EMOJI_IDS["games"])],
        [InlineKeyboardButton(text=f"Топ за день", callback_data="top_games_day",
                              icon_custom_emoji_id=EMOJI_IDS["games"])],
        [InlineKeyboardButton(text=f"Еженедельный конкурс", callback_data="top_weekly",
                              icon_custom_emoji_id=EMOJI_IDS["star"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['star']} <b>ТОП ИГРОКОВ</b>\n\n"
        "Выберите категорию:",
        reply_markup=kb
    )


@dp.callback_query(F.data == "top_vfg")
async def top_vfg_callback(callback: CallbackQuery):
    top = get_top_players(10)
    text = f"{PREMIUM_EMOJI_TEXT['balance']} <b>ТОП ПО БАЛАНСУ RCOIN</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, name, balance) in enumerate(top, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = name or f"User {uid}"
        text += f"{medal} {name} – {format_number(balance)} RCOIN\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад к топу", callback_data="back_to_top",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "top_point")
async def top_point_callback(callback: CallbackQuery):
    top = get_top_point(10)
    text = f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ТОП ПО БАЛАНСУ RBP</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, name, balance) in enumerate(top, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = name or f"User {uid}"
        text += f"{medal} {name} – {format_number(balance)} RBP\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад к топу", callback_data="back_to_top",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "top_games")
async def top_games_callback(callback: CallbackQuery):
    top = get_top_games(10)
    text = f"{PREMIUM_EMOJI_TEXT['games']} <b>ТОП ПО КОЛИЧЕСТВУ ИГР</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, name, games) in enumerate(top, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = name or f"User {uid}"
        text += f"{medal} {name} – {format_number(games)} игр\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад к топу", callback_data="back_to_top",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "top_games_day")
async def top_games_day_callback(callback: CallbackQuery):
    top = get_top_games_day(10)
    text = f"{PREMIUM_EMOJI_TEXT['games']} <b>ТОП ПО ИГРАМ ЗА ДЕНЬ</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, name, games) in enumerate(top, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = name or f"User {uid}"
        text += f"{medal} {name} – {format_number(games)} игр\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад к топу", callback_data="back_to_top",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "top_weekly")
async def top_weekly_callback(callback: CallbackQuery):
    week_ago = int(time.time()) - 7 * 86400

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, display_name, COUNT(*) as games
        FROM bet_history
        WHERE created_at > ?
        GROUP BY user_id
        ORDER BY games DESC
        LIMIT 10
    """, (week_ago,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        text = f"{PREMIUM_EMOJI_TEXT['star']} <b>ЕЖЕНЕДЕЛЬНЫЙ КОНКУРС</b>\n\n📭 Нет данных за неделю."
    else:
        text = f"{PREMIUM_EMOJI_TEXT['star']} <b>ЕЖЕНЕДЕЛЬНЫЙ КОНКУРС</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, name, games) in enumerate(rows, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            name = name or f"User {uid}"
            text += f"{medal} {name} – {format_number(games)} игр\n"
        text += f"\n📅 За неделю: {datetime.fromtimestamp(week_ago).strftime('%d.%m')} - {datetime.now().strftime('%d.%m')}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад к топу", callback_data="back_to_top",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "back_to_top")
async def back_to_top(callback: CallbackQuery):
    await cmd_top(callback.message)
    await callback.answer()


# ==================== БАРАБАН ====================

@dp.message(F.text.lower() == "барабан")
@dp.message(Command("барабан"))
async def cmd_spin(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_spin = user.get('last_spin_time', 0)
    cooldown = 86400

    if now - last_spin < cooldown:
        wait_time = cooldown - (now - last_spin)
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['games']} <b>Барабан доступен через:</b>\n{get_time_until(now + wait_time)}"
        )
        return

    gif_url = "https://media1.tenor.com/m/DWr_REKXbgIAAAAC/spin-and.gif"
    try:
        anim_msg = await bot.send_animation(
            chat_id=message.chat.id,
            animation=gif_url,
            reply_to_message_id=message.message_id
        )
        await asyncio.sleep(2.5)
        await anim_msg.delete()
    except Exception as e:
        logger.error(f"Ошибка отправки GIF барабана: {e}")

    win_amount = random.randint(1000, 500000)

    new_balance = user.get('balance_coin', 0) + win_amount
    update_user(user_id, balance_coin=new_balance, last_spin_time=now)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO spin_history (user_id, amount, created_at) VALUES (?, ?, ?)",
                (user_id, win_amount, now))
    conn.commit()
    conn.close()

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['spin']} <b>БАРАБАН!</b>\n\n"
        f"🎉 Вы выиграли {format_number(win_amount)} RCOIN!\n"
        f"💰 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN\n\n"
        f"<i>Следующий спин через 24 часа</i></blockquote>"
    )


# ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================

@dp.message(F.text.lower() == "ежедневный")
@dp.message(Command("ежедневный"))
async def cmd_daily_bonus(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    now = int(time.time())
    last_claim = user.get('daily_bonus_last', 0)
    streak = user.get('daily_bonus_streak', 0)

    if now - last_claim < 86400:
        wait_time = 86400 - (now - last_claim)
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['games']} <b>Ежедневный бонус уже получен!</b>\n\n"
            f"Следующий бонус через: {get_time_until(now + wait_time)}\n"
            f"🔥 Текущая серия: {streak} дней"
        )
        return

    bonus = 500 + streak * 100
    new_streak = streak + 1

    update_user(user_id, balance_coin=user.get('balance_coin', 0) + bonus,
                daily_bonus_last=now, daily_bonus_streak=new_streak)

    total_games = user.get('total_games', 0)
    await check_titles(user_id, total_games)

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['donate']} <b>Ежедневный бонус!</b>\n\n"
        f"💰 Вы получили {format_number(bonus)} RCOIN\n"
        f"🔥 Серия: {new_streak} дней\n"
        f"📊 Новый баланс: {format_number(user.get('balance_coin', 0) + bonus)} RCOIN</blockquote>"
    )


# ==================== ЕЖЕДНЕВНЫЙ БОНУС 5x5 ====================
# Поле 5x5 с кнопками «?». Для игры нужно добавить юзернейм бота в описание
# профиля и нажать «Проверить». Кол-во открываемых ячеек и выигрыш растут по дням серии.


def _db5_day_config(streak: int) -> tuple:
    """Возвращает (кол-во ячеек, макс выигрыш) для дня серии."""
    if streak <= 1:
        return (3, 150_000)
    if streak == 2:
        return (4, 250_000)
    return (5, 400_000)


def _db5_openable(streak: int) -> int:
    return _db5_day_config(streak)[0]


def _db5_questions_kb(grid: list, opened: int, streak: int, game_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    openable = _db5_openable(streak)
    for i in range(25):
        if grid[i] == 1:
            builder.button(text=" ", callback_data=f"db5_none_{game_id}",
                           icon_custom_emoji_id=EMOJI_IDS["diamond"])
        elif grid[i] == 2:
            builder.button(text=" ", callback_data=f"db5_none_{game_id}",
                           icon_custom_emoji_id=EMOJI_IDS["question"])
        else:
            builder.button(text=" ", callback_data=f"db5_open_{game_id}_{i}",
                           icon_custom_emoji_id=EMOJI_IDS["question"])
    builder.adjust(5)
    if opened > 0 and opened < openable:
        builder.button(text="💰 Забрать", callback_data=f"db5_cashout_{game_id}")
    builder.adjust(5)
    return builder.as_markup()


@dp.message(F.text.lower().in_({"ежедневный бонус", "бонус 5х5", "бонус 5x5", "дб5", "игра бонус"}))
@dp.message(Command("бонус5"))
async def cmd_db5(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка данных.")
        return
    now = int(time.time())
    today = _event_today()

    # проверка юзернейма бота в описании профиля
    need_check = user.get("db5_checked", 0) < now - 86400 * 30
    about = (user.get("about_text") or "").strip()

    verified = False
    if not need_check:
        verified = True
    elif about and BOT_USERNAME and BOT_USERNAME.strip("@").lower() in about.lower():
        verified = True
        need_check = False

    if need_check:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['question']} <b>Ежедневный бонус 5x5</b>\n\n"
            f"Чтобы играть, добавь юзернейм бота <code>@{BOT_USERNAME.strip('@')}</code> "
            f"в описание профиля («О себе») и нажми кнопку «Проверить».\n\n"
            f"<i>Команда «О себе <ваш текст>» — изменить описание.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Проверить", callback_data="db5_check")
            ]])
        )
        return

    # новый день — создаём поле
    last = user.get("db5_last", 0)
    streak = user.get("db5_streak", 0)
    if last < 1 or (now - last) >= 86400:
        if last < 1:
            streak = 1
        else:
            streak = streak + 1
        openable = _db5_openable(streak)
        import random
        grid = [0] * 25
        idx = random.sample(range(25), openable)
        for k in idx:
            grid[k] = 2  # 2 = вопрос (открывается)
        # резервируем «приз» на каждую открываемую ячейку
        won_cells = [random.randint(10_000, _db5_day_config(streak)[1] // max(openable, 1)) for _ in range(openable)]
        update_user(user_id, db5_last=now, db5_streak=streak, db5_opened=0,
                    db5_grid=json.dumps({"g": grid, "w": won_cells}), db5_won=0)
    else:
        streak += 0  # уже играем в тот же день

    user = get_user(user_id)
    grid_data = user.get("db5_grid") or "{}"
    try:
        gd = json.loads(grid_data)
        grid = gd.get("g", [0] * 25)
    except Exception:
        grid = [0] * 25
    opened = user.get("db5_opened", 0)
    openable = _db5_openable(streak)
    game_id_tok = f"db5_{user_id}_{now}"
    kb = _db5_questions_kb(grid, opened, streak, game_id_tok)
    maxw = _db5_day_config(streak)[1]
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['question']} <b>Ежедневный бонус 5x5</b>\n\n"
        f"🔥 Серия: {streak} день\n"
        f"🗂 Открыть ячеек: {openable}\n"
        f"💰 Макс выигрыш: {format_number(maxw)} RCOIN\n\n"
        f"<i>Открывай ячейки и забирай выигрыш!</i>",
        reply_markup=kb
    )


@dp.callback_query(F.data == "db5_check")
async def db5_check(callback: CallbackQuery):
    user_id = callback.from_user.id
    bio = ""
    try:
        chat = await bot.get_chat(user_id)
        bio = (getattr(chat, "bio", None) or "").strip()
    except Exception as exc:
        logger.info("Не удалось прочитать bio пользователя %s: %s", user_id, exc)
    required = "@" + BOT_USERNAME.strip("@")
    if required.lower() in bio.lower():
        update_user(user_id, db5_checked=int(time.time()))
        await callback.answer("Проверено! Ежедневный бонус открыт.", show_alert=True)
        # Ask the player to reopen the command; no mutation of Telegram's Message object.
        await callback.message.answer("✅ Проверка пройдена. Отправь команду /бонус5, чтобы открыть поле 5×5.")
    else:
        await callback.answer(
            f"Не удалось найти {required} в Telegram-описании. Добавь его в поле «О себе» и повтори проверку.",
            show_alert=True)


@dp.callback_query(F.data.startswith("db5_open_"))
async def db5_open(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    # Callback format: db5_open_db5_<user_id>_<timestamp>_<cell>.
    # The game token itself contains underscores, so split from the right.
    try:
        prefix, cell_raw = callback.data.rsplit("_", 1)
        game_tok = prefix[len("db5_open_"):]
        cell = int(cell_raw)
        tok_parts = game_tok.split("_")
        if len(tok_parts) != 3 or tok_parts[0] != "db5" or int(tok_parts[1]) != user_id:
            raise ValueError("wrong owner")
        if not 0 <= cell < 25:
            raise ValueError("bad cell")
    except (ValueError, IndexError):
        await callback.answer("Кнопка устарела. Открой ежедневный бонус заново.", show_alert=True)
        return
    user = get_user(user_id)
    gd = json.loads(user.get("db5_grid") or "{}")
    grid = gd.get("g", [0] * 25)
    won = gd.get("w", [])
    if grid[cell] == 1:
        await callback.answer("Уже открыто", show_alert=True)
        return
    if grid[cell] == 0:
        await callback.answer("Пусто, попробуй другую", show_alert=True)
        return
    # открыли приз
    grid[cell] = 1
    opened = user.get("db5_opened", 0) + 1
    openable = _db5_openable(user.get("db5_streak", 1))
    prize = won[opened - 1] if opened - 1 < len(won) else 5000
    user_reward = user.get("db5_won", 0) + prize
    update_user(user_id, db5_grid=json.dumps({"g": grid, "w": won}),
                db5_opened=opened, db5_won=user_reward)
    new_user = get_user(user_id)
    kb = _db5_questions_kb(grid, opened, user.get("db5_streak", 1), game_tok)
    if opened >= openable:
        # все открыты — забрать автоматически
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['win']} <b>Бонус 5x5 завершён!</b>\n\n"
            f"💰 Выигрыш: <b>+{format_number(user_reward)} RCOIN</b>\n"
            f"📊 Баланс: {format_number(new_user.get('balance_coin', 0) + user_reward)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data=f"db5_fin_{game_tok}")
            ]])
        )
    else:
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['question']} <b>Бонус 5x5</b>\n\n"
            f"🔥 Серия: {new_user.get('db5_streak', 1)} день\n"
            f"Открыто: {opened}/{openable}\n"
            f"Текущий выигрыш: {format_number(user_reward)} RCOIN\n\n"
            f"<i>Открывай дальше или забирай!</i>",
            reply_markup=kb
        )
    await callback.answer(f"+{format_number(prize)} RCOIN")


@dp.callback_query(F.data.startswith("db5_cashout_"))
@dp.callback_query(F.data.startswith("db5_fin_"))
async def db5_cashout(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    reward = user.get("db5_won", 0)
    if reward <= 0:
        await callback.answer("Нет выигрыша", show_alert=True)
        return
    # Conditional update prevents double credit if Telegram retries the callback.
    with sqlite3.connect(DB_FILE, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT balance_coin, db5_won FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or int(row[1] or 0) <= 0:
            conn.rollback()
            await callback.answer("Выигрыш уже получен или отсутствует.", show_alert=True)
            return
        reward = int(row[1])
        new_balance = int(row[0] or 0) + reward
        conn.execute("UPDATE users SET balance_coin=?, db5_won=0 WHERE user_id=? AND db5_won=?",
                     (new_balance, user_id, reward))
        conn.commit()
    await callback.message.edit_text(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['win']} <b>Бонус 5x5 — ВЫИГРЫШ!</b>\n\n"
        f"💰 Получено: <b>+{format_number(reward)} RCOIN</b>\n"
        f"📊 Новый баланс: {format_number(new_balance)} RCOIN</blockquote>"
    )
    await callback.answer("💰 Выигрыш получен!", show_alert=True)


@dp.callback_query(F.data.startswith("db5_none_"))
async def db5_none(callback: CallbackQuery):
    await callback.answer()


# ==================== КОМАНДА СКЛАД (личный инвентарь) ====================
# Сюда складываются тгп-айтемы и подарки. Показывает коллекцию предметов.

@dp.message(F.text.lower().in_({"склад", "мой склад", "инвентарь", "инвент"}))
@dp.message(Command("склад"))
async def cmd_sklad(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка данных.")
        return
    try:
        inv = json.loads(user.get("inventory") or "[]")
    except Exception:
        inv = []
    if not inv:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Твой склад</b>\n\n"
            f"📦 Здесь будут предметы, найденные в ивентах.\n"
            f"<i>Открывай «Зимний склад» и собирай коллекцию!</i>",
            reply_markup=_event_kb([_event_btn("К ивентам", "ev_menu", "door")]))
        return
    lines = [f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Твой склад</b> ({len(inv)} шт.)\n"]
    for itm in inv:
        key = itm.get("key") or "question"
        name = itm.get("name") or "Сувенир"
        lines.append(f"{PREMIUM_EMOJI_TEXT.get(key, '🎁')} {name} — <i>x{itm.get('qty', 1)}</i>")
    await message.answer("\n".join(lines),
                         reply_markup=_event_kb([_event_btn("К ивентам", "ev_menu", "door")]))


# ==================== ПОМОЩЬ САНТЕ ЗА КОИНЫ ====================
# Аналог удара по боссу: платишь ставку, Санта получает урон, тебе капает награда.

@dp.message(F.text.lower().in_({"помочь санте", "помощь санте", "помог санте", "санте"}))
@dp.message(Command("санте"))
async def cmd_help_santa(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка данных.")
        return
    parts = message.text.split()
    amount_str = parts[1] if len(parts) > 1 else "1000"
    cur_bal = user.get("balance_coin", 0)
    bet, deduct = parse_bet_amount(amount_str, cur_bal)
    if bet <= 0 or cur_bal < deduct:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Баланс: {format_number(cur_bal)}")
        return
    today = _event_today()
    if user.get("event_day") == today and user.get("event_boss_last", 0) > 0:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ты уже помогал Санте сегодня. Завтра!")
        return
    damage = _rnd.randint(10000, 120000)
    _event_boss_hit(damage)
    reward = damage * 2 + int(bet*0.5)
    update_user(user_id, balance_coin=cur_bal + reward,
                event_day=today, event_boss_last=int(time.time()),
                event_boss_dmg=user.get("event_boss_dmg", 0) + damage)
    boss = _event_boss_state()
    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['win']} <b>ПОМОЩЬ САНТЕ!</b>\n\n"
        f"💸 Потрачено: {format_number(bet)} RCOIN\n"
        f"⚔️ Урон Санте: <b>{format_number(damage)}</b>\n"
        f"🎁 Награда: <b>+{format_number(reward)} RCOIN</b>\n\n"
        f"HP босса: {format_number(boss['hp'])} / {format_number(boss['max'])}\n"
        f"<code>{_event_bar(boss['max'] - boss['hp'], boss['max'])}</code>")


# ==================== КОМАНДА ЛОГ ====================

@dp.message(F.text.lower() == "лог")
@dp.message(Command("лог"))
async def cmd_log(message: Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Команда доступна только для администраторов!")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT bet_amount, win_amount, is_win, bet_data, created_at
        FROM bet_history
        WHERE game_type = 'roulette'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("📭 Нет записей по рулетке.")
        return

    text = f"{PREMIUM_EMOJI_TEXT['roulette']} <b>ЛОГ РУЛЕТКИ (последние 10)</b>\n\n"

    for i, row in enumerate(rows, 1):
        bet_amount, win_amount, is_win, bet_data, created_at = row

        try:
            data = eval(bet_data)
            bet = data.get('bet', '?')
            result = data.get('result', '?')
        except:
            bet = '?'
            result = '?'

        color = get_roulette_color(result)
        emoji = get_roulette_emoji(result)

        result_text = f"{PREMIUM_EMOJI_TEXT['win']} ВЫИГРЫШ" if is_win else f"{PREMIUM_EMOJI_TEXT['lose']} ПРОИГРЫШ"
        amount = win_amount if is_win else bet_amount

        time_str = datetime.fromtimestamp(created_at).strftime('%d.%m %H:%M')

        text += f"{i}. {bet} → {result} {emoji} ({color}) | {result_text} | {format_number(amount)} RCOIN | {time_str}\n"

    await message.answer(text)


# ==================== КОМАНДА ПРОФИЛЬ ====================

@dp.message(F.text.lower() == "профиль")
@dp.message(Command("профиль"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    try:
        stats = get_user_stats(user_id)
        referrals = get_referrals_count(user_id)
        referral_earnings = get_referral_earnings(user_id)

        display_name = user.get('display_name', message.from_user.first_name or "без_ника")
        custom_username = user.get('custom_username', '')
        is_anonymous = user.get('is_anonymous', 0)
        balance_coin = user.get('balance_coin', 0)
        balance_point = user.get('balance_point', 0)
        bank_balance = user.get('bank_balance', 0)
        stars_balance = user.get('stars_balance', 0)
        rank_title = user.get('rank_title', 'Новичок')
        titles = json.loads(user.get('titles', '[]'))

        if custom_username and custom_username != '':
            username_display = f"{PREMIUM_EMOJI_TEXT['username_emoji']} Юзернейм: @{custom_username}\n"
        else:
            username_display = f"{PREMIUM_EMOJI_TEXT['username_emoji']} Юзернейм: <b>Не куплен</b>\n"

        titles_text = " ".join(titles) if titles else "Нет"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Мои юзеры", callback_data="profile_my_users"),
             InlineKeyboardButton(text=f"Мой ID", callback_data="profile_my_id")],
            [InlineKeyboardButton(text=f"Игры", callback_data="go_games"),
             InlineKeyboardButton(text=f"Баланс", callback_data="back_to_balance")],
            [InlineKeyboardButton(text=f"Экономика", callback_data="profile_economy")],
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance")]
        ])

        profile_text = (
            f"{PREMIUM_EMOJI_TEXT['profile']} <b>ПРОФИЛЬ</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👤 Имя: {display_name}\n"
            f"{username_display}"
            f"🔒 Анонимность: {'✅ Включена' if is_anonymous else '❌ Выключена'}\n"
            f"🏷️ Титул: {rank_title}\n"
            f"💎 Титулы: {titles_text}\n"
            f"⭐ Звёзды: {format_number(stars_balance)}\n"
            f"🏦 Банк: {format_number(bank_balance)} RCOIN\n"
            f"📝 О себе: {user.get('about_text', 'Не указано')}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс RCOIN:</b> {format_number(balance_coin)}\n"
            f"{PREMIUM_EMOJI_TEXT['diamond']} <b>RBP:</b> {format_number(balance_point)}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>СТАТИСТИКА</b>\n"
            f"• Всего игр: {stats['total_bets']}\n"
            f"✅ Побед: {stats['wins']}\n"
            f"❌ Поражений: {stats['losses']}\n"
            f"• Выиграно: {format_number(stats['total_won'])} RCOIN\n"
            f"• % побед: {round(stats['wins'] / max(stats['total_bets'], 1) * 100, 1)}%\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"{PREMIUM_EMOJI_TEXT['referral']} <b>РЕФЕРАЛЫ</b>\n"
            f"• Рефералов: {referrals}\n"
            f"• Заработано: {format_number(referral_earnings)} RCOIN\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔄 <b>Сменить имя:</b> <code>сменить ник НовоеИмя</code> (150 000 RCOIN)\n"
            f"💸 <b>Вывод реф.:</b> <code>вывести реф 1000</code>\n"
            f"📝 <b>Описание:</b> <code>о себе Текст</code>\n"
            f"{PREMIUM_EMOJI_TEXT['username_emoji']} <b>Купить юзернейм:</b> <code>+юзер @username</code> (100 000 000 RCOIN)"
        )

        await message.answer(profile_text, reply_markup=kb)

    except Exception as e:
        logger.error(f"Ошибка в профиле: {e}")
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Произошла ошибка при загрузке профиля. Попробуйте позже.")


# ==================== КОЛБЭКИ ПРОФИЛЯ ====================

@dp.callback_query(F.data == "profile_economy")
async def profile_economy_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Числами", callback_data="economy_numbers"),
         InlineKeyboardButton(text=f"Сокращенно", callback_data="economy_short")],
        [InlineKeyboardButton(text=f"Назад в профиль", callback_data="back_to_profile")]
    ])

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['treasury']} <b>ЭКОНОМИКА</b>\n\n"
        f"Выберите способ отображения баланса:",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data == "economy_numbers")
async def economy_numbers_callback(callback: CallbackQuery):
    await callback.answer("📊 Выбран отображение числами", show_alert=True)


@dp.callback_query(F.data == "economy_short")
async def economy_short_callback(callback: CallbackQuery):
    await callback.answer("📊 Выбран отображение сокращенно (к, кк, ккк)", show_alert=True)


@dp.callback_query(F.data == "profile_my_users")
async def profile_my_users(callback: CallbackQuery):
    user_id = callback.from_user.id

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT custom_username FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
    except:
        row = None

    custom_username = row[0] if row and row[0] else ''

    if not custom_username:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Купить юзернейм", callback_data="buy_username")],
            [InlineKeyboardButton(text=f"Назад в профиль", callback_data="back_to_profile")]
        ])
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['username_emoji']} <b>У вас нет купленного юзернейма</b>\n\n"
            "Купить юзернейм можно командой:\n"
            "<code>+юзер @username</code>\n\n"
            "💰 Стоимость: 100 000 000 RCOIN",
            reply_markup=kb
        )
        await callback.answer()
        return

    text = (
        f"{PREMIUM_EMOJI_TEXT['username_emoji']} <b>Ваш юзернейм</b>\n\n"
        f"🔹 Юзернейм: @{custom_username}\n"
        f"🆔 Ваш ID: {user_id}\n\n"
        f"✅ Юзернейм уникален!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад в профиль", callback_data="back_to_profile")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "profile_my_id")
async def profile_my_id(callback: CallbackQuery):
    user_id = callback.from_user.id

    text = (
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Ваш ID</b>\n\n"
        f"📛 Ваш ID в боте: <code>{user_id}</code>\n\n"
        f"💡 <b>По этому ID вам могут переводить:</b>\n"
        f"• RCOIN: <code>Дать 100 {user_id}</code>\n"
        f"• RBP: <code>Перевод 100 {user_id}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Копировать ID", callback_data=f"copy_id_{user_id}")],
        [InlineKeyboardButton(text=f"Назад в профиль", callback_data="back_to_profile")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("copy_id_"))
async def copy_id_callback(callback: CallbackQuery):
    user_id = callback.data.split('_')[2]
    await callback.answer(f"✅ ID скопирован: {user_id}", show_alert=True)


@dp.callback_query(F.data == "buy_username")
async def buy_username_from_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['username_emoji']} <b>Как купить юзернейм</b>\n\n"
        "💰 Стоимость: 100 000 000 RCOIN\n\n"
        "📝 <b>Команда:</b>\n"
        "<code>+юзер @желаемый_юзернейм</code>\n\n"
        "📌 Юзернейм минимум 3 символа, только латиница",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад в профиль", callback_data="back_to_profile")]
        ])
    )
    await callback.answer()


@dp.message(Command("menu"))
@dp.message(F.text.lower() == "меню")
async def cmd_main_menu(message: Message):
    user = get_user(message.from_user.id)
    kb, bonus_text = get_balance_keyboard(message.from_user.id)
    await message.answer(
        f"💎 <b>RCOIN·BOT — главное меню</b>\n\n"
        f"👤 {user.get('display_name', message.from_user.first_name or 'Игрок')}\n"
        f"💰 Баланс: <b>{format_number(user.get('balance_coin', 0))} RCOIN</b>\n"
        f"{bonus_text}", reply_markup=kb)

@dp.callback_query(F.data == "menu_games")
async def menu_games_callback(callback: CallbackQuery):
    await callback.message.edit_text("🎮 <b>Игры</b>\nВыбери игру:", reply_markup=get_games_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "menu_profile")
async def menu_profile_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    stats = get_user_stats(user_id)
    text = (
        f"{PREMIUM_EMOJI_TEXT['profile']} <b>ПРОФИЛЬ</b>\n\n"
        f"👤 Имя: <b>{user.get('display_name') or callback.from_user.first_name or 'Игрок'}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Баланс: <b>{format_number(user.get('balance_coin', 0))} RCOIN</b>\n"
        f"💎 RBP: <b>{format_number(user.get('balance_point', 0))}</b>\n"
        f"🎮 Игр: <b>{stats.get('total_bets', 0)}</b>\n"
        f"🏆 Побед: <b>{stats.get('wins', 0)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
         InlineKeyboardButton(text="💰 Баланс", callback_data="back_to_balance")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_balance")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "menu_events")
async def menu_events_callback(callback: CallbackQuery):
    await show_events(callback.message, edit=True)
    await callback.answer()

@dp.callback_query(F.data == "menu_stash")
async def menu_stash_callback(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    try:
        inv = json.loads(user.get("inventory") or "[]")
    except (TypeError, json.JSONDecodeError):
        inv = []
    if not inv:
        body = "📦 Здесь пока пусто. Предметы можно находить в зимнем событии."
    else:
        lines = [f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ТВОЙ СКЛАД</b> ({len(inv)} шт.)"]
        for item in inv:
            key = item.get("key", "question")
            lines.append(f"{PREMIUM_EMOJI_TEXT.get(key, '🎁')} {item.get('name', 'Сувенир')} ×{item.get('qty', 1)}")
        body = "\n".join(lines)
    await callback.message.edit_text(body, reply_markup=_event_kb([_event_btn("❄️ К ивентам", "ev_menu", "door")], [_event_btn("⬅️ В меню", "back_to_balance", "door")]))
    await callback.answer()

@dp.callback_query(F.data == "menu_help")
async def menu_help_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "❔ <b>Помощь</b>\n\n/start — запуск\n/menu — главное меню\n/игры — игры\n/профиль — профиль\n/склад — инвентарь\n/ивенты — события",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_balance")]]))
    await callback.answer()

@dp.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    await cmd_profile(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "go_games")
async def go_games_callback(callback: CallbackQuery):
    await callback.answer("📱 Используйте команду /игры", show_alert=True)


@dp.callback_query(F.data == "back_to_balance")
async def back_to_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer("Ошибка получения данных.", show_alert=True)
        return
    display_name = user.get('display_name', callback.from_user.username or "без_ника")
    balance_coin = user.get('balance_coin', 0)
    balance_point = user.get('balance_point', 0)
    kb, bonus_text = get_balance_keyboard(user_id)
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['profile']} <b>Имя:</b> {display_name}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс:</b> {format_number(balance_coin)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Баланс:</b> {format_number(balance_point)} RBP{bonus_text}",
        reply_markup=kb
    )
    await callback.answer()


# ==================== КОЛБЭКИ БАЛАНСА ====================

@dp.callback_query(F.data == "get_bonus")
async def bonus_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.", show_alert=True)
        return
    available, time_left = check_bonus_available(user_id)
    if not available:
        await callback.answer(
            f"{PREMIUM_EMOJI_TEXT['games']} Бонус недоступен. Следующий через: {get_time_until(int(time.time()) + time_left)}",
            show_alert=True
        )
        return
    bonus = 2500
    new_balance = user.get('balance_coin', 0) + bonus
    update_user(user_id, balance_coin=new_balance, bonus_last_time=int(time.time()))
    await callback.answer(
        f"{PREMIUM_EMOJI_TEXT['donate']} Поздравляем! Вы получили бонус {bonus} RCOIN!\n💰 Новый баланс: {format_number(new_balance)} RCOIN",
        show_alert=True
    )
    display_name = user.get('display_name', callback.from_user.username or "без_ника")
    balance_point = user.get('balance_point', 0)
    kb, bonus_text = get_balance_keyboard(user_id)
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['profile']} <b>Имя:</b> {display_name}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс:</b> {format_number(new_balance)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Баланс:</b> {format_number(balance_point)} RBP{bonus_text}",
        reply_markup=kb
    )


@dp.callback_query(F.data == "go_earn")
async def earn_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if callback.message.chat.type != 'private':
        await callback.answer("📲 Перейдите в ЛС бота для заработка!", show_alert=True)
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, channel_link, price_per_sub, target_subs, current_subs FROM ads WHERE status = 'active'")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                                  icon_custom_emoji_id=EMOJI_IDS["balance"])]
        ])
        await callback.message.edit_text("📭 <b>Активных рекламных заданий нет.</b>", reply_markup=kb)
        await callback.answer()
        return
    text = f"{PREMIUM_EMOJI_TEXT['balance']} <b>Заработай RCOIN!</b>\n\nПодпишись на каналы и получи награду:\n\n"
    builder = InlineKeyboardBuilder()
    for ad_id, channel, price, target, current in rows:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT claimed FROM subscriptions WHERE user_id = ? AND ad_id = ?", (user_id, ad_id))
        claimed = cur.fetchone()
        conn.close()
        if claimed and claimed[0] == 1:
            status = f"✅ Получено"
        else:
            status = f"💰 +{price} RCOIN"
        builder.button(text=f"📢 {channel} {status}", callback_data=f"sub_{ad_id}")
    builder.adjust(1)
    builder.button(text=f"Назад", callback_data="back_to_balance", icon_custom_emoji_id=EMOJI_IDS["balance"])
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("sub_"))
async def sub_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    ad_id = int(callback.data.split('_')[1])
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT claimed FROM subscriptions WHERE user_id = ? AND ad_id = ?", (user_id, ad_id))
    existing = cur.fetchone()
    conn.close()
    if existing and existing[0] == 1:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Вы уже получили награду за это задание.", show_alert=True)
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT channel_link, price_per_sub, owner_id, target_subs, current_subs FROM ads WHERE id = ?",
                (ad_id,))
    ad = cur.fetchone()
    conn.close()
    if not ad:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Реклама не найдена.", show_alert=True)
        return
    channel_link, price, owner_id, target, current = ad
    if not await is_subscribed_to_channel(user_id, channel_link):
        await callback.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} Вы не подписаны на канал {channel_link}.\nПодпишитесь и нажмите снова.",
            show_alert=True)
        return
    user = get_user(user_id)
    if user:
        update_user(user_id, balance_coin=user.get('balance_coin', 0) + price)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO subscriptions (user_id, ad_id, claimed, claimed_at) VALUES (?, ?, 1, ?)",
                (user_id, ad_id, int(time.time())))
    cur.execute("UPDATE ads SET current_subs = current_subs + 1 WHERE id = ?", (ad_id,))
    cur.execute("SELECT current_subs, target_subs FROM ads WHERE id = ?", (ad_id,))
    current_updated, target_updated = cur.fetchone()
    if current_updated >= target_updated:
        cur.execute("UPDATE ads SET status = 'completed' WHERE id = ?", (ad_id,))
    conn.commit()
    conn.close()
    await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Вы получили {price} RCOIN за подписку!", show_alert=True)
    await callback.message.delete()


# ==================== КОМАНДА БАЛАНСА ====================

@dp.message(F.text.lower().in_({'б', 'бал', 'баланс'}))
@dp.message(Command("б"))
@dp.message(Command("Б"))
@dp.message(Command("бал"))
@dp.message(Command("Бал"))
@dp.message(Command("баланс"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    display_name = user.get('display_name', message.from_user.username or "без_ника")
    balance_coin = user.get('balance_coin', 0)
    balance_point = user.get('balance_point', 0)

    kb, bonus_text = get_balance_keyboard(user_id)

    await message.reply(
        f"{PREMIUM_EMOJI_TEXT['profile']} <b>Имя:</b> {display_name}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс:</b> {format_number(balance_coin)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Баланс:</b> {format_number(balance_point)} RBP{bonus_text}",
        reply_markup=kb
    )


# ==================== КОМАНДА БОНУС ====================

@dp.message(F.text.lower() == "бонус")
@dp.message(Command("бонус"))
async def cmd_bonus(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    available, time_left = check_bonus_available(user_id)
    if not available:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['games']} <b>Бонус недоступен</b>\nСледующий бонус через: {get_time_until(int(time.time()) + time_left)}\nБонус: 2500 RCOIN")
        return
    bonus = 2500
    new_balance = user.get('balance_coin', 0) + bonus
    update_user(user_id, balance_coin=new_balance, bonus_last_time=int(time.time()))
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['donate']} <b>Поздравляем!</b>\nВы получили бонус {bonus} RCOIN!\n\n💰 <b>Новый баланс:</b> {format_number(new_balance)} RCOIN\n⏳ Следующий бонус через 1 час")


# ==================== КОМАНДА ПОИНТ ====================

@dp.message(F.text.lower() == "поинт")
@dp.message(Command("поинт"))
async def cmd_point(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Ваш баланс RBP:</b> {format_number(user.get('balance_point', 0))}\n\n"
        f"1 RBP = 50 000 RCOIN\n"
        f"Обмен: /обмен"
    )


# ==================== КОМАНДА РЕКЛ ====================

@dp.message(F.text.lower() == "рекл")
async def cmd_ad(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    if message.chat.type != 'private':
        await message.answer("📲 Рекламный центр работает только в ЛС!")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Создать рекламу", callback_data="ad_create",
                              icon_custom_emoji_id=EMOJI_IDS["ad"])],
        [InlineKeyboardButton(text=f"Мои рекламы", callback_data="ad_my", icon_custom_emoji_id=EMOJI_IDS["ad"])],
        [InlineKeyboardButton(text=f"Заработать", callback_data="ad_earn", icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['ad']} <b>Рекламный центр</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} RBP: {format_number(user.get('balance_point', 0))}\n"
        f"{PREMIUM_EMOJI_TEXT['donate']} RCOIN: {format_number(user.get('balance_coin', 0))}",
        reply_markup=kb
    )


@dp.callback_query(F.data == "ad_create")
async def ad_create_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Только для администраторов.", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Введите ссылку на канал (@channel):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_ad", icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.ad_channel)
    await callback.answer()


@dp.callback_query(F.data == "back_to_ad")
async def back_to_ad(callback: CallbackQuery):
    await cmd_ad(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "ad_my")
async def ad_my_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Только для администраторов.", show_alert=True)
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, channel_link, price_per_sub, target_subs, current_subs, status FROM ads WHERE owner_id = ?",
        (callback.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await callback.message.edit_text(
            "📭 Нет реклам.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_ad",
                                      icon_custom_emoji_id=EMOJI_IDS["games"])]
            ])
        )
        await callback.answer()
        return

    text = "📋 <b>Ваши рекламы</b>\n\n"
    builder = InlineKeyboardBuilder()
    for row in rows:
        ad_id, channel, price, target, current, status = row
        text += f"ID: {ad_id}\n📢 {channel}\n💰 {price} RBP | {current}/{target}\n📊 {status}\n\n"
        builder.button(text=f"🗑 Удалить #{ad_id}", callback_data=f"ad_del_{ad_id}")
    builder.adjust(1)
    builder.button(text=f"Назад", callback_data="back_to_ad", icon_custom_emoji_id=EMOJI_IDS["games"])
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("ad_del_"))
async def ad_delete_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Только для администраторов.", show_alert=True)
        return

    ad_id = int(callback.data.split('_')[2])

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id, paid_points FROM ads WHERE id = ?", (ad_id,))
    row = cur.fetchone()

    if not row:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Реклама не найдена.", show_alert=True)
        conn.close()
        return

    owner_id, paid_points = row

    owner = get_user(owner_id)
    if owner:
        update_user(owner_id, balance_point=owner.get('balance_point', 0) + paid_points)

    cur.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
    conn.commit()
    conn.close()

    await callback.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} Реклама удалена! Возвращено {format_number(paid_points)} RBP",
        show_alert=True)
    await callback.message.delete()


@dp.callback_query(F.data == "ad_earn")
async def ad_earn_callback(callback: CallbackQuery):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, channel_link, price_per_sub, target_subs, current_subs FROM ads WHERE status = 'active'")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await callback.message.edit_text(
            "📭 Нет активных заданий.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_ad",
                                      icon_custom_emoji_id=EMOJI_IDS["games"])]
            ])
        )
        await callback.answer()
        return
    text = f"{PREMIUM_EMOJI_TEXT['balance']} <b>Заработай RCOIN!</b>\n\nПодпишись на каналы и получи награду:\n\n"
    builder = InlineKeyboardBuilder()
    for ad_id, channel, price, target, current in rows:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT claimed FROM subscriptions WHERE user_id = ? AND ad_id = ?", (callback.from_user.id, ad_id))
        claimed = cur.fetchone()
        conn.close()
        if claimed and claimed[0] == 1:
            status = f"✅ Получено"
        else:
            status = f"💰 +{price} RCOIN"
        builder.button(text=f"📢 {channel} {status}", callback_data=f"sub_{ad_id}")
    builder.adjust(1)
    builder.button(text=f"Назад", callback_data="back_to_ad", icon_custom_emoji_id=EMOJI_IDS["games"])
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@dp.message(GameState.ad_channel)
async def ad_channel_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    channel = message.text.strip()
    if not channel.startswith('@') and not channel.startswith('https://t.me/'):
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите корректную ссылку на канал.")
        return

    await state.update_data(channel=channel)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['balance']} Введите цену за подписку (RBP):")
    await state.set_state(GameState.ad_price)


@dp.message(GameState.ad_price)
async def ad_price_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:
        price = int(message.text)
        if price <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Цена должна быть положительной.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    await state.update_data(price=price)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['balance']} Введите количество подписчиков:")
    await state.set_state(GameState.ad_subs)


@dp.message(GameState.ad_subs)
async def ad_subs_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:
        target = int(message.text)
        if target <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Количество должно быть положительным.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    user_id = message.from_user.id
    data = await state.get_data()
    channel = data.get('channel')
    price = data.get('price')

    user = get_user(user_id)
    if user.get('balance_point', 0) < target * price:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RBP!</b>\n"
            f"💎 Нужно: {format_number(target * price)} RBP\n"
            f"💎 У вас: {format_number(user.get('balance_point', 0))} RBP")
        await state.clear()
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ads (owner_id, channel_link, price_per_sub, target_subs, paid_points, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, channel, price, target, target * price, int(time.time())))
    ad_id = cur.lastrowid
    conn.commit()
    conn.close()

    update_user(user_id, balance_point=user.get('balance_point', 0) - target * price)

    await state.clear()
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Реклама создана!</b>\n\n"
        f"📢 Канал: {channel}\n"
        f"💰 Цена за подписку: {price} RBP\n"
        f"📊 Цель: {target} подписчиков\n"
        f"💎 Потрачено: {format_number(target * price)} RBP\n"
        f"🆔 ID рекламы: {ad_id}"
    )


# ==================== ЧЕКОВАЯ КНИЖКА ====================

@dp.message(F.text.lower() == "чек")
async def cmd_check_book(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Создать чек", callback_data="chk_create",
                              icon_custom_emoji_id=EMOJI_IDS["check"])],
        [InlineKeyboardButton(text=f"Мои чеки", callback_data="chk_my", icon_custom_emoji_id=EMOJI_IDS["check"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Чековая книжка</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс RCOIN:</b> {format_number(user.get('balance_coin', 0))}\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>RBP:</b> {format_number(user.get('balance_point', 0))}",
        reply_markup=kb
    )


@dp.callback_query(F.data == "chk_create")
async def check_create_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Создание чека</b>\n\nВведите сумму RCOIN для чека:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_check",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.check_amount)
    await callback.answer()


@dp.callback_query(F.data == "back_to_check")
async def back_to_check(callback: CallbackQuery):
    await cmd_check_book(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "chk_my")
async def check_my_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT check_id, amount, activations, max_activations, description, password, created_at FROM checks WHERE owner_id = ? AND is_active = 1",
        (user_id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await callback.message.edit_text(
            "📭 <b>У вас нет созданных чеков.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_check",
                                      icon_custom_emoji_id=EMOJI_IDS["games"])]
            ])
        )
        await callback.answer()
        return

    text = "📂 <b>Ваши чеки</b>\n\n"
    builder = InlineKeyboardBuilder()

    for row in rows:
        check_id, amount, activations, max_act, desc, password, created = row
        text += f"📌 ID: <code>{check_id}</code>\n💰 {format_number(amount)} RCOIN | {activations}/{max_act}\n📝 {desc or 'нет'}\n🔑 {'есть' if password else 'нет'}\n\n"

        builder.button(text=f"📝 Описание {check_id}", callback_data=f"chk_desc_{check_id}")
        builder.button(text=f"🔑 Пароль {check_id}", callback_data=f"chk_pass_{check_id}")
        builder.button(text=f"❌ Удалить {check_id}", callback_data=f"chk_del_{check_id}")
        builder.button(text=f"🔗 Ссылка {check_id}", callback_data=f"chk_link_{check_id}")
        builder.adjust(2)

    builder.button(text=f"Назад", callback_data="back_to_check", icon_custom_emoji_id=EMOJI_IDS["games"])
    builder.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.message(GameState.check_amount)
async def check_amount_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_check_book(message)
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    user = get_user(user_id)
    if user.get('balance_coin', 0) < amount:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\nНужно: {format_number(amount)} RCOIN\nУ вас: {format_number(user.get('balance_coin', 0))} RCOIN")
        await state.clear()
        return

    await state.update_data(amount=amount)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} Введите количество активаций:")
    await state.set_state(GameState.check_activations)


@dp.message(GameState.check_activations)
async def check_activations_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_check_book(message)
        return

    try:
        max_act = int(message.text)
        if max_act <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Количество должно быть положительным.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    data = await state.get_data()
    amount = data.get('amount')

    check_id = generate_check_id()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO checks (check_id, owner_id, amount, max_activations, created_at) VALUES (?, ?, ?, ?, ?)",
        (check_id, user_id, amount, max_act, int(time.time())))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) - amount)
    await state.clear()

    link = f"https://t.me/{BOT_USERNAME}?start=check_{check_id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Добавить описание", callback_data=f"chk_desc_{check_id}")],
        [InlineKeyboardButton(text=f"Добавить пароль", callback_data=f"chk_pass_{check_id}")],
        [InlineKeyboardButton(text=f"Удалить чек", callback_data=f"chk_del_{check_id}")],
        [InlineKeyboardButton(text=f"Получить ссылку", callback_data=f"chk_link_{check_id}")],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_check", icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>Чек создан!</b>\n\n"
        f"🆔 ID: <code>{check_id}</code>\n"
        f"💰 {format_number(amount)} RCOIN\n"
        f"📊 {max_act} активаций\n\n"
        f"🔗 <b>Ссылка для активации:</b>\n"
        f"<code>{link}</code>\n\n"
        f"<i>Нажмите на ссылку или скопируйте её</i></blockquote>",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("chk_desc_"))
async def check_desc_callback(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split('_')[2]
    await state.update_data(check_id=check_id)
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['check']} Введите описание для чека:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data=f"chk_back_{check_id}",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.check_desc)
    await callback.answer()


@dp.message(GameState.check_desc)
async def check_desc_input(message: Message, state: FSMContext):
    desc = message.text.strip()
    data = await state.get_data()
    check_id = data.get('check_id')

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE checks SET description = ? WHERE check_id = ?", (desc, check_id))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} Описание добавлено!")
    await check_my_callback_for_user(message, message.from_user.id)


@dp.callback_query(F.data.startswith("chk_pass_"))
async def check_pass_callback(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split('_')[2]
    await state.update_data(check_id=check_id)
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['check']} Введите пароль для чека (или оставьте пустым):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data=f"chk_back_{check_id}",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.check_pass)
    await callback.answer()


@dp.message(GameState.check_pass)
async def check_pass_input(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    check_id = data.get('check_id')

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE checks SET password = ? WHERE check_id = ?", (password, check_id))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} Пароль установлен!")
    await check_my_callback_for_user(message, message.from_user.id)


@dp.callback_query(F.data.startswith("chk_back_"))
async def check_back_callback(callback: CallbackQuery):
    check_id = callback.data.split('_')[2]
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT check_id, amount, activations, max_activations, description, password FROM checks WHERE check_id = ?",
        (check_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Чек не найден.", show_alert=True)
        return

    check_id, amount, activations, max_act, desc, password = row

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Добавить описание", callback_data=f"chk_desc_{check_id}")],
        [InlineKeyboardButton(text=f"Добавить пароль", callback_data=f"chk_pass_{check_id}")],
        [InlineKeyboardButton(text=f"Удалить чек", callback_data=f"chk_del_{check_id}")],
        [InlineKeyboardButton(text=f"Получить ссылку", callback_data=f"chk_link_{check_id}")],
        [InlineKeyboardButton(text=f"Назад к чекам", callback_data="back_to_my_checks",
                              icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(
        f"📌 <b>Информация о чеке</b>\n\n"
        f"🆔 ID: <code>{check_id}</code>\n"
        f"💰 Сумма: {format_number(amount)} RCOIN\n"
        f"📊 Активаций: {activations}/{max_act}\n"
        f"📝 Описание: {desc or 'нет'}\n"
        f"🔑 Пароль: {'есть' if password else 'нет'}",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_my_checks")
async def back_to_my_checks(callback: CallbackQuery):
    await check_my_callback(callback)
    await callback.answer()


@dp.callback_query(F.data.startswith("chk_link_"))
async def check_link_callback(callback: CallbackQuery):
    check_id = callback.data.split('_')[2]
    link = f"https://t.me/{BOT_USERNAME}?start=check_{check_id}"
    await callback.answer(f"🔗 Ссылка на чек:\n{link}", show_alert=True)


@dp.callback_query(F.data.startswith("chk_del_"))
async def check_del_callback(callback: CallbackQuery):
    check_id = callback.data.split('_')[2]
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id, amount FROM checks WHERE check_id = ?", (check_id,))
    row = cur.fetchone()

    if not row:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Чек не найден.", show_alert=True)
        return

    owner_id, amount = row
    if owner_id != user_id:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваш чек.", show_alert=True)
        return

    cur.execute("DELETE FROM checks WHERE check_id = ?", (check_id,))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)

    await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Чек удалён! {format_number(amount)} RCOIN возвращены.",
                          show_alert=True)
    await check_my_callback(callback)


async def check_my_callback_for_user(message: Message, user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT check_id, amount, activations, max_activations, description, password, created_at FROM checks WHERE owner_id = ? AND is_active = 1",
        (user_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer(
            "📭 <b>У вас нет созданных чеков.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_check",
                                      icon_custom_emoji_id=EMOJI_IDS["games"])]
            ])
        )
        return

    text = "📂 <b>Ваши чеки</b>\n\n"
    builder = InlineKeyboardBuilder()

    for row in rows:
        check_id, amount, activations, max_act, desc, password, created = row
        text += f"📌 ID: <code>{check_id}</code>\n💰 {format_number(amount)} RCOIN | {activations}/{max_act}\n📝 {desc or 'нет'}\n🔑 {'есть' if password else 'нет'}\n\n"

        builder.button(text=f"📝 Описание {check_id}", callback_data=f"chk_desc_{check_id}")
        builder.button(text=f"🔑 Пароль {check_id}", callback_data=f"chk_pass_{check_id}")
        builder.button(text=f"❌ Удалить {check_id}", callback_data=f"chk_del_{check_id}")
        builder.button(text=f"🔗 Ссылка {check_id}", callback_data=f"chk_link_{check_id}")
        builder.adjust(2)

    builder.button(text=f"Назад", callback_data="back_to_check", icon_custom_emoji_id=EMOJI_IDS["games"])
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


# ==================== ПРОМОКОДЫ ====================

async def activate_promo(message: Message, promo_code: str):
    user_id = message.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, reward, max_uses, uses FROM promo_codes WHERE code = ?", (promo_code,))
    promo = cur.fetchone()

    if not promo:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} <b>Промокод не найден!</b>")
        conn.close()
        return

    promo_id, reward, max_uses, uses = promo

    if max_uses > 0 and uses >= max_uses:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Промокод уже использован максимальное количество раз!</b>")
        conn.close()
        return

    cur.execute("SELECT id FROM promo_uses WHERE user_id = ? AND promo_id = ?", (user_id, promo_id))
    if cur.fetchone():
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} <b>Вы уже использовали этот промокод!</b>")
        conn.close()
        return

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + reward)
    cur.execute("UPDATE promo_codes SET uses = uses + 1 WHERE id = ?", (promo_id,))
    cur.execute("INSERT INTO promo_uses (user_id, promo_id, used_at) VALUES (?, ?, ?)",
                (user_id, promo_id, int(time.time())))
    conn.commit()
    conn.close()

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['donate']} <b>Промокод активирован!</b>\n\n"
        f"💰 Вы получили {format_number(reward)} RCOIN!\n"
        f"📊 Новый баланс: {format_number(user.get('balance_coin', 0) + reward)} RCOIN</blockquote>"
    )


@dp.message(F.text.lower() == "промо")
@dp.message(Command("промо"))
async def cmd_promo(message: Message):
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Активация промокода</b>\n\n"
        "Чтобы активировать промокод, используйте команду:\n"
        "<code>/start promo_ВАШ_ПРОМОКОД</code>\n\n"
        "Или просто нажмите на ссылку:\n"
        f"<code>https://t.me/{BOT_USERNAME}?start=promo_ВАШ_ПРОМОКОД</code>"
    )


@dp.message(Command("create_promo"))
async def cmd_create_promo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Только для администраторов.")
        return

    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} Введите код промокода:")
    await state.set_state(GameState.promo_create_code)


@dp.message(GameState.promo_create_code)
async def promo_create_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) < 3:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Код должен быть минимум 3 символа.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id FROM promo_codes WHERE code = ?", (code,))
    if cur.fetchone():
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Такой промокод уже существует.")
        conn.close()
        return
    conn.close()

    await state.update_data(code=code)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['balance']} Введите награду (RCOIN):")
    await state.set_state(GameState.promo_create_reward)


@dp.message(GameState.promo_create_reward)
async def promo_create_reward(message: Message, state: FSMContext):
    try:
        reward = int(message.text)
        if reward <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Награда должна быть положительной.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    await state.update_data(reward=reward)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} Введите максимальное количество использований (0 - безлимит):")
    await state.set_state(GameState.promo_create_uses)


@dp.message(GameState.promo_create_uses)
async def promo_create_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text)
        if max_uses < 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Количество использований не может быть отрицательным.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    data = await state.get_data()
    code = data.get('code')
    reward = data.get('reward')
    user_id = message.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO promo_codes (code, reward, max_uses, created_by, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (code, reward, max_uses, user_id, int(time.time())))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>Промокод создан!</b>\n\n"
        f"🔑 <b>Код:</b> <code>{code}</code>\n"
        f"💰 <b>Награда:</b> {format_number(reward)} RCOIN\n"
        f"📊 <b>Использований:</b> {'Безлимит' if max_uses == 0 else max_uses}\n\n"
        f"🔗 <b>Ссылка:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}?start=promo_{code}</code></blockquote>"
    )


# ==================== КОМАНДА ДОНАТ ====================

@dp.message(F.text.lower() == "донат")
@dp.message(Command("донат"))
async def cmd_donate(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Пополнить звёздами", callback_data="donate_stars",
                              icon_custom_emoji_id=EMOJI_IDS["donate"])],
        [InlineKeyboardButton(text=f"Пополнить криптовалютой", callback_data="donate_crypto",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])],
        [InlineKeyboardButton(text=f"Курсы", callback_data="donate_rates", icon_custom_emoji_id=EMOJI_IDS["bank"])]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['donate']} <b>Пополнение баланса</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} Ваш баланс: {format_number(user.get('balance_coin', 0))} RCOIN\n\n"
        f"<b>Способы пополнения:</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['star']} <b>Telegram Stars</b>\n"
        f"1 ⭐ = 5 RBP\n\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Криптовалюта</b>\n"
        f"1$ = 20 RBP\n"
        f"BTC, ETH, TON - по текущему курсу",
        reply_markup=kb
    )


@dp.callback_query(F.data == "donate_stars")
async def donate_stars(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['star']} <b>Пополнение через Telegram Stars</b>\n\n"
        f"💰 <b>Ваш баланс RBP:</b> {format_number(user.get('balance_point', 0))}\n\n"
        "Введите количество RBP, которое хотите получить:\n"
        "Минимум: 1 RBP\n\n"
        "Курс: 1 ⭐ = 5 RBP\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} Отмена: напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_donate",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.stars_donate)
    await callback.answer()


@dp.message(GameState.stars_donate)
async def stars_donate_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_donate(message)
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
            return
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число.")
        return

    stars_needed = amount // 5
    if stars_needed < 1:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная сумма: 1 RBP (1 ⭐).")
        return

    prices = [
        LabeledPrice(label=f"{amount} RBP", amount=stars_needed * 100)
    ]

    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=f"Пополнение RBP",
            description=f"Пополнение баланса на {amount} RBP",
            payload=f"stars_{user_id}_{amount}",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="stars_payment",
            need_name=False,
            need_phone_number=False,
            need_email=False
        )
        await state.clear()
        await message.answer(f"{PREMIUM_EMOJI_TEXT['star']} Оплата создана! Подтвердите покупку в Telegram.")
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {e}")
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка при создании оплаты. Попробуйте позже.")


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload

    if payload.startswith("stars_"):
        parts = payload.split('_')
        if len(parts) >= 3:
            amount = int(parts[2])
            user = get_user(user_id)
            new_point = user.get('balance_point', 0) + amount
            update_user(user_id, balance_point=new_point)

            await message.answer(
                f"<blockquote>{PREMIUM_EMOJI_TEXT['star']} <b>ПОПОЛНЕНИЕ УСПЕШНО!</b>\n\n"
                f"💰 <b>Получено:</b> {format_number(amount)} RBP\n"
                f"💎 <b>Новый баланс RBP:</b> {format_number(new_point)}\n\n"
                f"Спасибо за пополнение! 🎉</blockquote>"
            )


@dp.callback_query(F.data == "donate_crypto")
async def donate_crypto(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₿ BTC", callback_data="crypto_btc")],
        [InlineKeyboardButton(text="⟠ ETH", callback_data="crypto_eth")],
        [InlineKeyboardButton(text="₮ USDT", callback_data="crypto_usdt")],
        [InlineKeyboardButton(text="💎 TON", callback_data="crypto_ton")],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_donate", icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Пополнение криптовалютой</b>\n\n"
        "Выберите валюту для пополнения:\n\n"
        "📊 <b>Курсы (за 1$):</b>\n"
        "• BTC: по текущему курсу\n"
        "• ETH: по текущему курсу\n"
        "• USDT: 20 RBP за 1$\n"
        "• TON: по текущему курсу\n\n"
        f"💰 <b>Кошелек для оплаты:</b>\n"
        f"<code>{CRYPTO_WALLET}</code>\n\n"
        "<i>Минимальная сумма пополнения: 100 RBP</i>",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("crypto_"))
async def crypto_select(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split('_')[1].upper()
    await state.update_data(currency=currency, exchange_type="crypto_payment")

    await callback.message.edit_text(
        f"💰 <b>Пополнение в {currency}</b>\n\n"
        f"Введите сумму в RBP, которую хотите получить:\n"
        f"Минимум: 100 RBP\n"
        f"Максимум: 10 000 000 RBP\n\n"
        f"Пример: <code>1000</code> - получите 1000 RBP\n\n"
        f"💰 <b>Кошелек для оплаты:</b>\n"
        f"<code>{CRYPTO_WALLET}</code>\n\n"
        f"После оплаты нажмите кнопку 'Проверить оплату'\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} Для отмены напишите <code>отмена</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Проверить оплату", callback_data="crypto_check",
                                  icon_custom_emoji_id=EMOJI_IDS["balance"])],
            [InlineKeyboardButton(text=f"Назад", callback_data="back_to_donate_crypto",
                                  icon_custom_emoji_id=EMOJI_IDS["games"])]
        ])
    )
    await state.set_state(GameState.exchange_waiting)
    await callback.answer()


@dp.callback_query(F.data == "crypto_check")
async def crypto_check(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    amount = data.get('amount')
    currency = data.get('currency')

    if not amount:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Сначала введите сумму пополнения!", show_alert=True)
        return

    paid = await check_crypto_payment_by_address(amount, currency)

    if paid:
        user = get_user(user_id)
        update_user(user_id, balance_point=user.get('balance_point', 0) + amount)
        await callback.message.edit_text(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>ПОПОЛНЕНИЕ ПОДТВЕРЖДЕНО!</b>\n\n"
            f"💰 <b>Сумма:</b> {format_number(amount)} RBP\n"
            f"💎 <b>Новый баланс:</b> {format_number(user.get('balance_point', 0) + amount)} RBP</blockquote>"
        )
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Оплата подтверждена!", show_alert=True)
        await state.clear()
    else:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['games']} Оплата не найдена. Проверьте кошелек и попробуйте снова.",
                              show_alert=True)


@dp.callback_query(F.data == "back_to_donate_crypto")
async def back_to_donate_crypto(callback: CallbackQuery):
    await donate_crypto(callback)
    await callback.answer()


@dp.callback_query(F.data == "back_to_donate")
async def back_to_donate(callback: CallbackQuery):
    await cmd_donate(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "donate_rates")
async def donate_rates(callback: CallbackQuery):
    await callback.answer(
        "📊 <b>КУРСЫ ПОПОЛНЕНИЯ</b>\n\n"
        "⭐ Telegram Stars:\n"
        "1 ⭐ = 5 RBP\n\n"
        "💰 Криптовалюта:\n"
        "1 USD = 20 RBP\n"
        "BTC/ETH/TON — динамический курс\n\n"
        "💱 Конвертация:\n"
        "1 RBP = 50 000 RCOIN",
        show_alert=True
    )


# ==================== КОМАНДА ОБНОВЫ ====================

@dp.message(F.text.lower() == "обновы")
@dp.message(Command("обновы"))
async def cmd_updates(message: Message):
    updates_text = (
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Список обновлений RCOIN·BOT</b>\n\n"
        "📅 <b>Версия 9.3</b>\n"
        "• <b>Пирамида</b>: обновлена механика — теперь 4 двери (2 ряда по 2)\n"
        "• <b>Хи-Ло</b>: добавлены проценты шансов на победу\n"
        "• <b>Убран лимит перевода</b> до 1ккк RCOIN\n"
        "• <b>Казна</b>: добавлена кнопка 'О казне' с информацией\n"
        "• <b>Авто-чеки</b>: добавлена кнопка 'Добавить в группу'\n"
        "• <b>Дизайн</b>: улучшен внешний вид кнопок и сообщений\n"
        "• <b>Профиль</b>: исправлены ошибки отображения\n"
        "• <b>Убрана игра Боулинг</b> для оптимизации\n\n"
        "📅 <b>Версия 9.2</b>\n"
        "• <b>Исправлена</b> игра Спин\n"
        "• <b>Добавлена</b> кнопка Назад в Казна\n"
        "• <b>Добавлены</b> кнопки Пополнить/Снять в Казна\n"
        "• <b>Исправлена</b> клавиатура в Профиль\n"
        "• <b>Улучшена</b> обработка ошибок\n\n"
        "📅 <b>Версия 9.1</b>\n"
        "• Добавлена <b>автоматическая генерация чеков</b> каждые 1.3 часа\n"
        "• Чеки на 15кк RCOIN с 15 активациями\n"
        "• Деньги на чеки берутся из <b>Казны</b>\n"
        "• Добавлена инструкция по добавлению бота в чат\n\n"
        "📅 <b>Версия 9.0</b>\n"
        "• Добавлена игра <b>Крестики-Нолики</b> на деньги ❌⭕\n"
        "• Добавлен <b>Маркет</b> с NFT и юзернеймами\n"
        "• Добавлен <b>Инвентарь</b> для NFT\n"
        "• Добавлена <b>Казна</b> с доступом по админ-панели\n"
        "• Добавлена кнопка <b>Экономика</b> в профиле\n"
        "• Добавлена возможность <b>покупать юзернеймы</b>\n"
        "• Изменены <b>цены на NFT</b>: от 1кк до 500кк\n"
        "• Максимальный уровень <b>Майнера</b> теперь 3\n"
        "• Убраны обычные эмодзи, везде <b>TG Premium</b> ✨\n\n"
        "👑 <b>Поддержка:</b> @WERTYNERSHINEBB"
    )
    await message.answer(updates_text)


# ==================== КОМАНДА НАСТРОЙКИ ====================

@dp.message(F.text.lower() == "настройки")
@dp.message(Command("настройки"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    is_anonymous = user.get('is_anonymous', 0)
    anon_status = "Включена" if is_anonymous else "Выключена"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Анонимность: {anon_status}", callback_data="toggle_anon",
                              icon_custom_emoji_id=EMOJI_IDS["settings"])],
        [InlineKeyboardButton(text=f"Профиль", callback_data="go_profile", icon_custom_emoji_id=EMOJI_IDS["profile"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['settings']} <b>Настройки</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} <b>Анонимность:</b> {anon_status}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} <b>Баланс RCOIN:</b> {format_number(user.get('balance_coin', 0))}\n\n"
        f"Анонимность скрывает ваше имя в играх.\n"
        f"Стоимость: 15 000 RCOIN",
        reply_markup=kb
    )


@dp.callback_query(F.data == "toggle_anon")
async def toggle_anonymous(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных.", show_alert=True)
        return

    current = user.get('is_anonymous', 0)

    if current == 0:
        if user.get('balance_coin', 0) < 15000:
            await callback.answer(
                f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN!\nНужно: 15 000 RCOIN\nУ вас: {format_number(user.get('balance_coin', 0))} RCOIN",
                show_alert=True
            )
            return
        update_user(user_id, is_anonymous=1, balance_coin=user.get('balance_coin', 0) - 15000)
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Анонимность включена! Списано 15 000 RCOIN",
                              show_alert=True)
    else:
        update_user(user_id, is_anonymous=0)
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['check']} Анонимность выключена", show_alert=True)

    await cmd_settings(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "go_profile")
async def go_profile_callback(callback: CallbackQuery):
    await cmd_profile(callback.message)
    await callback.answer()


# ==================== КОМАНДА О БОТЕ ====================

@dp.message(F.text.lower() == "о боте")
@dp.message(Command("о боте"))
async def cmd_about(message: Message):
    about_text = (
        f"{PREMIUM_EMOJI_TEXT['games']} <b>О RCOIN·BOT</b>\n\n"
        "RCOIN·BOT — это многофункциональный игровой бот для Telegram.\n\n"
        "🎮 <b>Игры:</b>\n"
        "• 🎲 Кубик — классика с множителями до 10x\n"
        "• 🎰 Рулетка — европейская рулетка с зеро\n"
        "• 🏀 Баскет — угадай результат броска до 5x\n"
        "• 🎡 Колесо Фортуны — удача с 47% на 0x\n"
        "• 💣 Мины — поле 5x5 с множителями до 25x\n"
        "• 🎯 Дартс — точность до 5x\n"
        "• 🃏 Очко — игра против дилера\n"
        "• ☀️ Солнце — найди солнце на поле 3x3\n"
        "• 🚀 Краш — ракета с множителем\n"
        "• 🎯 Охота — охота на зверей до x100\n"
        "• 🎰 Спин — слот-машина\n"
        "• ⚽ Футбол — удар по воротам\n"
        "• 🏛️ Пирамида — поднимайся по уровням (4 двери)\n"
        "• ⛏️ Майнер — пассивный заработок\n"
        "• 🎴 Хи-Ло — угадай выше или ниже (с процентами)\n"
        "• ❌⭕ Крестики-Нолики — игра с другом на деньги\n\n"
        "💰 <b>Валюты:</b>\n"
        "• RCOIN — основная игровая валюта\n"
        "• RBP — премиум валюта\n"
        "• ⭐ Stars — для пополнения\n\n"
        "📋 <b>Функции:</b>\n"
        "• Реферальная система\n"
        "• Чековая книжка\n"
        "• Рекламный центр\n"
        "• Система бонусов\n"
        "• Ежедневный бонус\n"
        "• Банковская система\n"
        "• Барабан\n"
        "• Обмен валют\n"
        "• P2P Обменник\n"
        "• Промокоды\n"
        "• Анонимность\n"
        "• Покупка юзернейма\n"
        "• Донат через криптовалюту\n"
        "• Маркет NFT\n"
        "• Система титулов\n"
        "• Еженедельный конкурс\n"
        "• Казна\n"
        "• Автоматические чеки каждые 1.3 часа\n\n"
        "👑 <b>Поддержка:</b> @WERTYNERSHINEBB\n"
        f"📢 <b>Канал:</b> {REQUIRED_CHANNEL}\n"
        f"💬 <b>Чат:</b> {REQUIRED_CHAT}\n\n"
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Приятной игры!</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Начать играть", callback_data="go_games", icon_custom_emoji_id=EMOJI_IDS["games"])]
    ])

    await message.answer(about_text, reply_markup=kb)


# ==================== КОМАНДА ИСТОРИЯ ====================

@dp.message(F.text.lower() == "история")
@dp.message(Command("история"))
async def cmd_history(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    history = get_user_bet_history(user_id, 20)

    if not history:
        await message.answer("📭 <b>История игр пуста.</b>\n\nНачните играть, чтобы заполнить историю!")
        return

    text = "📜 <b>История ваших игр</b>\n\n"

    game_names = {
        'dice': f"{PREMIUM_EMOJI_TEXT['dice']} Кубик",
        'roulette': f"{PREMIUM_EMOJI_TEXT['roulette']} Рулетка",
        'fortune': f"{PREMIUM_EMOJI_TEXT['fortune']} Фортуна",
        'sun': f"{PREMIUM_EMOJI_TEXT['sun']} Солнце",
        'basket': f"{PREMIUM_EMOJI_TEXT['basket']} Баскет",
        'mines': f"{PREMIUM_EMOJI_TEXT['mines']} Мины",
        'darts': f"{PREMIUM_EMOJI_TEXT['darts']} Дартс",
        'blackjack': f"{PREMIUM_EMOJI_TEXT['blackjack']} Очко",
        'crash': f"{PREMIUM_EMOJI_TEXT['crash']} Краш",
        'hunt': f"{PREMIUM_EMOJI_TEXT['hunt']} Охота",
        'spin': f"{PREMIUM_EMOJI_TEXT['spin']} Спин",
        'football': f"{PREMIUM_EMOJI_TEXT['football']} Футбол",
        'pyramid': f"{PREMIUM_EMOJI_TEXT['pyramid']} Пирамида",
        'hi_lo': f"{PREMIUM_EMOJI_TEXT['hi_lo']} Хи-Ло",
    }

    for i, game in enumerate(history[:10], 1):
        game_name = game_names.get(game['game_type'], game['game_type'])
        result = f"{PREMIUM_EMOJI_TEXT['win']} Выигрыш" if game['is_win'] else f"{PREMIUM_EMOJI_TEXT['lose']} Проигрыш"
        amount = game['win_amount'] if game['is_win'] else game['bet_amount']

        time_str = datetime.fromtimestamp(game['created_at']).strftime('%d.%m %H:%M')

        text += f"{i}. {game_name} | {result} | {format_number(amount)} RCOIN | {time_str}\n"

    if len(history) > 10:
        text += f"\n... и ещё {len(history) - 10} игр"

    stats = get_user_stats(user_id)
    text += f"\n\n📊 <b>Всего игр:</b> {stats['total_bets']}"
    text += f"\n✅ <b>Побед:</b> {stats['wins']}"
    text += f"\n❌ <b>Поражений:</b> {stats['losses']}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Обновить", callback_data="refresh_history",
                              icon_custom_emoji_id=EMOJI_IDS["games"])],
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_balance",
                              icon_custom_emoji_id=EMOJI_IDS["balance"])]
    ])

    await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "refresh_history")
async def refresh_history(callback: CallbackQuery):
    await cmd_history(callback.message)
    await callback.answer()


# ==================== КОМАНДА ПОМОЩЬ ====================

@dp.message(F.text.lower() == "помощь")
@dp.message(F.text.lower() == "help")
@dp.message(Command("помощь"))
async def cmd_help(message: Message):
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>Помощь по RCOIN·BOT</b>\n\n"
        "📋 <b>Основные команды:</b>\n"
        "• /start – запуск\n"
        "• Б или бал – баланс\n"
        "• Профиль – профиль\n"
        "• Бонус – бонус 2500 RCOIN (раз в час)\n"
        "• Топ – топ игроков\n"
        "• Статистика – статистика\n"
        "• Игры – список игр\n"
        "• Поинт – баланс RBP\n"
        "• Обмен – обмен валют\n"
        "• Рекл – рекламный центр\n"
        "• Рефералы – реф. система\n"
        "• Донат – пополнение\n"
        "• Обновы – список обновлений\n"
        "• Настройки – настройки бота\n"
        "• О боте – информация о боте\n"
        "• История – история игр\n"
        "• Промо – активация промокода\n"
        "• Ежедневный – ежедневный бонус\n"
        "• Банк – банковская система\n"
        "• Барабан – крутить барабан\n"
        "• О себе – изменить описание\n"
        "• Лог – лог рулетки (админ)\n"
        "• Дать или Нк – перевод RCOIN\n"
        "• +юзер – купить юзернейм\n"
        "• Маркет – маркет NFT и юзернеймов\n"
        "• КН – крестики-нолики\n"
        "• Казна – баланс казны\n\n"
        "🎲 <b>Игры:</b>\n"
        "• <code>куб 100 3</code> – кубик\n"
        "• <code>рулетка 100к к</code> – рулетка\n"
        "• <code>фортуна 100</code> или <code>кф 100</code> – фортуна\n"
        "• <code>солнце 100</code> – солнце\n"
        "• <code>баскет 100 п</code> – баскет\n"
        "• <code>мины 100 3</code> – мины (1-10 мин)\n"
        "• <code>дартс 100 к</code> – дартс\n"
        "• <code>очко 100</code> – очко\n"
        "• <code>краш 100 2.5</code> – краш\n"
        "• <code>охота 100</code> – охота\n"
        "• <code>спин 100</code> – спин\n"
        "• <code>футбол 100 г</code> – футбол\n"
        "• <code>пирамида 100</code> – пирамида\n"
        "• <code>майнер</code> – майнер\n"
        "• <code>хило 100</code> – хи-ло\n"
        "• <code>кн 1000</code> (в ответ на сообщение) – крестики-нолики\n\n"
        "💸 <b>Форматы сумм:</b>\n"
        "• 1к = 1 000\n"
        "• 1кк = 1 000 000\n"
        "• 1ккк = 1 000 000 000\n"
        "• все или вб = весь баланс\n\n"
        "👑 <b>Поддержка:</b> @WERTYNERSHINEBB"
    )


# ==================== КОМАНДА NFT (ЧЕРЕЗ МАРКЕТ) ====================

@dp.callback_query(F.data == "nft_my")
async def nft_my_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, level, rarity, price, description FROM nft_items WHERE owner_id = ? ORDER BY rarity DESC",
        (user_id,))
    items = cur.fetchall()
    conn.close()

    if not items:
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['nft']} <b>У вас нет NFT</b>\n\n"
            "Купите или создайте свой первый NFT!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_market",
                                      icon_custom_emoji_id=EMOJI_IDS["market"])]
            ])
        )
        await callback.answer()
        return

    text = f"{PREMIUM_EMOJI_TEXT['nft']} <b>ИНВЕНТАРЬ NFT</b>\n\n"
    for item_id, name, level, rarity, price, desc in items:
        rarity_emoji = {
            'common': '🟢',
            'uncommon': '🔵',
            'rare': '🟣',
            'epic': '🟠',
            'legendary': '🔴'
        }.get(rarity, '🟢')

        rarity_names = {
            'common': 'Обычный',
            'uncommon': 'Необычный',
            'rare': 'Редкий',
            'epic': 'Эпический',
            'legendary': 'Легендарный'
        }.get(rarity, 'Обычный')

        text += f"{rarity_emoji} <b>{name}</b>\n"
        text += f"📊 Уровень: {level} | Редкость: {rarity_names}\n"
        text += f"💰 Цена: {format_number(price)} RCOIN\n"
        text += f"🆔 ID: {item_id}\n"
        text += f"📝 {desc or 'Нет описания'}\n"
        text += f"➡️ Продать: <code>nft продать {item_id} 100000</code>\n"
        text += f"➡️ Выставить на маркет: <code>nft выставить {item_id} 100000 описание</code>\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_market", icon_custom_emoji_id=EMOJI_IDS["market"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "nft_market")
async def nft_market_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, owner_id, name, level, rarity, price, description FROM nft_items WHERE for_sale = 1 ORDER BY price ASC")
    items = cur.fetchall()
    conn.close()

    if not items:
        await callback.message.edit_text(
            f"{PREMIUM_EMOJI_TEXT['market']} <b>МАРКЕТ NFT</b>\n\n"
            "📭 На рынке нет NFT на продажу.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Назад", callback_data="back_to_market",
                                      icon_custom_emoji_id=EMOJI_IDS["market"])]
            ])
        )
        await callback.answer()
        return

    text = f"{PREMIUM_EMOJI_TEXT['market']} <b>МАРКЕТ NFT</b>\n\n"
    for item_id, owner_id, name, level, rarity, price, desc in items:
        rarity_emoji = {
            'common': '🟢',
            'uncommon': '🔵',
            'rare': '🟣',
            'epic': '🟠',
            'legendary': '🔴'
        }.get(rarity, '🟢')

        rarity_names = {
            'common': 'Обычный',
            'uncommon': 'Необычный',
            'rare': 'Редкий',
            'epic': 'Эпический',
            'legendary': 'Легендарный'
        }.get(rarity, 'Обычный')

        owner = get_user(owner_id)
        owner_name = owner.get('display_name', f"User {owner_id}") if owner else f"User {owner_id}"

        text += f"{rarity_emoji} <b>{name}</b>\n"
        text += f"👤 Владелец: {owner_name}\n"
        text += f"📊 Уровень: {level} | Редкость: {rarity_names}\n"
        text += f"💰 Цена: {format_number(price)} RCOIN\n"
        text += f"📝 {desc or 'Нет описания'}\n"
        text += f"🆔 ID: {item_id}\n"
        text += f"➡️ Купить: <code>nft купить {item_id}</code>\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Назад", callback_data="back_to_market", icon_custom_emoji_id=EMOJI_IDS["market"])]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "nft_create")
async def nft_create_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if user.get('balance_coin', 0) < 100000:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Минимум 100 000 RCOIN для создания NFT.",
                              show_alert=True)
        return

    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['nft']} <b>СОЗДАНИЕ NFT</b>\n\n"
        "Введите название для вашего NFT (минимум 3 символа):\n\n"
        f"{PREMIUM_EMOJI_TEXT['lock']} Для отмены напишите <code>отмена</code>"
    )
    await state.set_state(GameState.nft_create)
    await callback.answer()


@dp.message(GameState.nft_create)
async def nft_create_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_market(message)
        return

    name = message.text.strip()
    if len(name) < 3:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Название должно быть минимум 3 символа. Попробуйте снова:")
        return

    user = get_user(user_id)
    if user.get('balance_coin', 0) < 100000:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно 100 000 RCOIN.")
        await state.clear()
        return

    rarity_weights = ['common', 'uncommon', 'rare', 'epic', 'legendary']
    rarity = random.choices(rarity_weights, weights=[50, 30, 15, 4, 1], k=1)[0]

    prices = {
        'common': 1000000,
        'uncommon': 10000000,
        'rare': 50000000,
        'epic': 150000000,
        'legendary': 500000000
    }

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO nft_items (owner_id, name, level, rarity, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, 1, rarity, prices[rarity], int(time.time())))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - 100000)

    rarity_names = {
        'common': '🟢 Обычный',
        'uncommon': '🔵 Необычный',
        'rare': '🟣 Редкий',
        'epic': '🟠 Эпический',
        'legendary': '🔴 Легендарный'
    }

    await state.clear()
    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['nft']} <b>NFT СОЗДАН!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"📛 Название: {name}\n"
        f"📊 Редкость: {rarity_names[rarity]}\n"
        f"💰 Цена: {format_number(prices[rarity])} RCOIN\n\n"
        f"💸 Списано: 100 000 RCOIN</blockquote>"
    )


@dp.callback_query(F.data == "nft_upgrade")
async def nft_upgrade_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, name, level, rarity, price FROM nft_items WHERE owner_id = ?", (user_id,))
    items = cur.fetchall()
    conn.close()

    if not items:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} У вас нет NFT для улучшения.", show_alert=True)
        return

    text = f"{PREMIUM_EMOJI_TEXT['nft']} <b>УЛУЧШЕНИЕ NFT</b>\n\n"
    for item_id, name, level, rarity, price in items:
        cost = price // 2
        text += f"🆔 {item_id} | {name} (ур. {level}) | Улучшить: {format_number(cost)} RCOIN\n"

    text += "\nВведите ID NFT для улучшения:\n"
    text += f"{PREMIUM_EMOJI_TEXT['lock']} Для отмены напишите <code>отмена</code>"

    await callback.message.edit_text(text)
    await state.set_state(GameState.nft_upgrade)
    await callback.answer()


@dp.message(GameState.nft_upgrade)
async def nft_upgrade_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_market(message)
        return

    try:
        item_id = int(message.text)
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число (ID NFT).")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id, level, price FROM nft_items WHERE id = ?", (item_id,))
    item = cur.fetchone()
    conn.close()

    if not item:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} NFT не найден.")
        return

    owner_id, level, price = item

    if owner_id != user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваш NFT.")
        return

    cost = price // 2
    if cost < 100000:
        cost = 100000

    user = get_user(user_id)

    if user.get('balance_coin', 0) < cost:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно: {format_number(cost)} RCOIN")
        return

    new_level = level + 1
    new_price = int(price * 1.5)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE nft_items SET level = ?, price = ? WHERE id = ?", (new_level, new_price, item_id))
    conn.commit()
    conn.close()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - cost)

    await state.clear()
    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>NFT УЛУЧШЕН!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"📊 Новый уровень: {new_level}\n"
        f"💰 Новая цена: {format_number(new_price)} RCOIN\n"
        f"💸 Списано: {format_number(cost)} RCOIN</blockquote>"
    )


@dp.message(F.text.lower().startswith("nft продать"))
async def nft_sell(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()

    if len(parts) < 3:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Пример: <code>nft продать 123 100000</code>"
        )
        return

    try:
        item_id = int(parts[2])
        price = int(parts[3])
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите числа.")
        return

    if price <= 0:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Цена должна быть положительной.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id FROM nft_items WHERE id = ?", (item_id,))
    item = cur.fetchone()

    if not item:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} NFT не найден.")
        conn.close()
        return

    owner_id = item[0]

    if owner_id != user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваш NFT.")
        conn.close()
        return

    cur.execute("UPDATE nft_items SET for_sale = 0, sale_price = 0 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>NFT ПРОДАН!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"💰 Продано за {format_number(price)} RCOIN</blockquote>"
    )


@dp.message(F.text.lower().startswith("nft выставить"))
async def nft_sell_market(message: Message, state: FSMContext):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=3)

    if len(parts) < 4:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Пример: <code>nft выставить 123 100000 Описание NFT</code>"
        )
        return

    try:
        item_id = int(parts[2])
        price = int(parts[3])
        desc = parts[4] if len(parts) > 4 else ""
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите числа.")
        return

    if price <= 0:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Цена должна быть положительной.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id FROM nft_items WHERE id = ?", (item_id,))
    item = cur.fetchone()

    if not item:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} NFT не найден.")
        conn.close()
        return

    owner_id = item[0]

    if owner_id != user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Это не ваш NFT.")
        conn.close()
        return

    cur.execute("UPDATE nft_items SET for_sale = 1, sale_price = ?, description = ? WHERE id = ?",
                (price, desc, item_id))
    conn.commit()
    conn.close()

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['market']} <b>NFT ВЫСТАВЛЕН НА МАРКЕТ!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"💰 Цена: {format_number(price)} RCOIN\n"
        f"📝 Описание: {desc or 'Нет'}</blockquote>"
    )


@dp.message(F.text.lower().startswith("nft купить"))
async def nft_buy(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Пример: <code>nft купить 123</code>"
        )
        return

    try:
        item_id = int(parts[2])
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число (ID NFT).")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT owner_id, sale_price FROM nft_items WHERE id = ? AND for_sale = 1", (item_id,))
    item = cur.fetchone()

    if not item:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} NFT не найден или не на продаже.")
        conn.close()
        return

    owner_id, price = item

    if owner_id == user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя купить свой собственный NFT.")
        conn.close()
        return

    user = get_user(user_id)

    if user.get('balance_coin', 0) < price:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно: {format_number(price)} RCOIN")
        conn.close()
        return

    owner = get_user(owner_id)

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - price)
    update_user(owner_id, balance_coin=owner.get('balance_coin', 0) + price)

    cur.execute("UPDATE nft_items SET owner_id = ?, for_sale = 0 WHERE id = ?", (user_id, item_id))
    conn.commit()
    conn.close()

    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['check']} <b>NFT КУПЛЕН!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"💰 Цена: {format_number(price)} RCOIN\n\n"
        f"💸 С вашего баланса списано {format_number(price)} RCOIN</blockquote>"
    )


@dp.callback_query(F.data == "nft_buy_username")
async def nft_buy_username_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if user.get('balance_coin', 0) < 100000000:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно 100 000 000 RCOIN.", show_alert=True)
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT user_id, custom_username, display_name FROM users WHERE custom_username != ''")
    users = cur.fetchall()
    conn.close()

    if not users:
        await callback.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нет доступных юзернеймов для покупки.", show_alert=True)
        return

    text = f"{PREMIUM_EMOJI_TEXT['username_emoji']} <b>КУПИТЬ ЮЗЕРНЕЙМ</b>\n\n"
    text += "Доступные юзернеймы:\n\n"

    for uid, username, name in users:
        if uid != user_id:
            text += f"@{username} — {name} (ID: {uid})\n"

    text += "\nВведите ID пользователя, чей юзернейм хотите купить:\n"
    text += f"{PREMIUM_EMOJI_TEXT['lock']} Для отмены напишите <code>отмена</code>"

    await callback.message.edit_text(text)
    await state.set_state(GameState.nft_buy_username)
    await callback.answer()


@dp.message(GameState.nft_buy_username)
async def nft_buy_username_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_market(message)
        return

    try:
        target_id = int(message.text)
    except ValueError:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число (ID пользователя).")
        return

    if target_id == user_id:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя купить свой собственный юзернейм.")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT custom_username FROM users WHERE user_id = ?", (target_id,))
    row = cur.fetchone()

    if not row or not row[0]:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} У пользователя нет юзернейма.")
        conn.close()
        return

    username = row[0]

    user = get_user(user_id)
    if user.get('balance_coin', 0) < 100000000:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Недостаточно RCOIN! Нужно 100 000 000 RCOIN.")
        conn.close()
        return

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - 100000000)
    update_user(target_id, custom_username='')
    update_user(user_id, custom_username=username)

    conn.close()

    await state.clear()
    await message.answer(
        f"<blockquote>{PREMIUM_EMOJI_TEXT['username_emoji']} <b>ЮЗЕРНЕЙМ КУПЛЕН!</b>\n\n"
        f"🔹 Юзернейм: @{username}\n"
        f"💰 Стоимость: 100 000 000 RCOIN\n\n"
        f"✅ Проверьте профиль командой <b>Профиль</b></blockquote>"
    )


@dp.callback_query(F.data == "back_to_market")
async def back_to_market(callback: CallbackQuery):
    await cmd_market(callback.message)
    await callback.answer()


# ==================== КОМАНДА СМЕНЫ ИМЕНИ ====================

@dp.message(F.text.lower().startswith("сменить ник"))
async def cmd_change_name(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\nПример: <code>сменить ник НовоеИмя</code>\nСтоимость: 150 000 RCOIN")
        return
    new_name = parts[2].strip()
    if len(new_name) < 2 or len(new_name) > 30:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Имя должно быть от 2 до 30 символов.")
        return
    if user.get('balance_coin', 0) < 150000:
        await message.answer(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\nНужно: 150 000 RCOIN\nУ вас: {format_number(user.get('balance_coin', 0))} RCOIN")
        return
    update_user(user_id, balance_coin=user.get('balance_coin', 0) - 150000, display_name=new_name)
    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['check']} <b>Имя успешно изменено!</b>\n\n👤 <b>Новое имя:</b> {new_name}\n💰 <b>Новый баланс:</b> {format_number(user.get('balance_coin', 0) - 150000)} RCOIN")


# ==================== КОМАНДА О СЕБЕ ====================

@dp.message(F.text.lower() == "о себе")
@dp.message(Command("о себе"))
async def cmd_about_me(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    about = user.get('about_text', '')
    if not about:
        about = "Пользователь не указал информацию о себе"

    await message.answer(
        f"📝 <b>О себе</b>\n\n"
        f"<i>{about}</i>\n\n"
        f"Чтобы изменить описание, отправьте:\n"
        f"<code>о себе Новое описание</code>"
    )


@dp.message(F.text.lower().startswith("о себе "))
async def cmd_set_about(message: Message):
    user_id = message.from_user.id
    about = message.text[7:].strip()

    if len(about) > 500:
        await message.answer(f"{PREMIUM_EMOJI_TEXT['lock']} Описание не должно превышать 500 символов.")
        return

    update_user(user_id, about_text=about)
    await message.answer(f"{PREMIUM_EMOJI_TEXT['check']} <b>Описание профиля обновлено!</b>")


# ==================== КОМАНДА СТАТИСТИКА ====================

@dp.message(F.text.lower() == "статистика")
@dp.message(Command("статистика"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    if stats['total_bets'] == 0:
        await message.answer("📊 У вас пока нет сыгранных игр.")
        return
    text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"🎯 Всего игр: {stats['total_bets']}\n"
        f"✅ Побед: {stats['wins']}\n"
        f"❌ Поражений: {stats['losses']}\n"
        f"💰 Всего выиграно: {format_number(stats['total_won'])} RCOIN\n"
        f"📈 Процент побед: {round(stats['wins'] / stats['total_bets'] * 100, 1)}%\n"
        f"📉 Средняя ставка: {format_number(stats['total_won'] // max(stats['wins'], 1))} RCOIN"
    )
    await message.answer(text)


# ==================== КОНФИГУРАЦИЯ КОМИССИЙ ====================
TRANSFER_COMMISSION = 15
MIN_TRANSFER_AMOUNT = 1


# ==================== КОМАНДА ПЕРЕВОДА RCOIN ====================

@dp.message(F.text.lower().startswith(("дать", "нк")))
async def cmd_transfer(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    text = message.text
    parts = text.split(maxsplit=3)

    if len(parts) < 2:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>Дать 100к @username</code> – перевести 100 000 RCOIN\n"
            "• <code>Дать 100к @username привет</code> – с комментарием\n"
            "• <code>Нк 1000 123456789</code> – перевести 1000 RCOIN по ID\n"
            "• <code>Дать 10</code> – в ответ на сообщение пользователя\n"
            f"Минимальная сумма: {MIN_TRANSFER_AMOUNT} RCOIN\n"
            f"Комиссия: {TRANSFER_COMMISSION}% (покупатель платит)"
        )
        return

    try:
        amount_str = parts[1]
        amount = parse_amount(amount_str)

        if amount < MIN_TRANSFER_AMOUNT:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная сумма перевода — {MIN_TRANSFER_AMOUNT} RCOIN.")
            return
        if amount <= 0:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
            return

        comment = ""
        target_user = None
        target_id = None

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_user = get_user(target_id)
            if not target_user:
                await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Пользователь не найден в базе.")
                return
            if len(parts) >= 3:
                comment = parts[2]
        elif len(parts) >= 3:
            target = parts[2]
            if target.isdigit():
                target_id = int(target)
                target_user = get_user(target_id)
            else:
                if target.startswith('@'):
                    target = target[1:]
                target_user = get_user_by_username(target)
                if target_user:
                    target_id = target_user['user_id']
            if len(parts) >= 4:
                comment = parts[3]
        else:
            await message.reply(
                f"{PREMIUM_EMOJI_TEXT['lock']} Укажите получателя: @username, ID или ответьте на сообщение.")
            return

        if not target_user:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Пользователь не найден.")
            return

        if target_id == user_id:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя перевести RCOIN самому себе.")
            return

        commission = int(amount * TRANSFER_COMMISSION / 100)
        total_cost = amount + commission

        current_balance = user.get('balance_coin', 0)
        if current_balance < total_cost:
            await message.reply(
                f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RCOIN!</b>\n"
                f"💰 Ваш баланс: {format_number(current_balance)} RCOIN\n"
                f"💰 Сумма перевода: {format_number(amount)} RCOIN\n"
                f"💰 Комиссия ({TRANSFER_COMMISSION}%): {format_number(commission)} RCOIN\n"
                f"💰 Итого к списанию: {format_number(total_cost)} RCOIN"
            )
            return

        new_balance = current_balance - total_cost
        update_user(user_id, balance_coin=new_balance)

        target_new_balance = target_user.get('balance_coin', 0) + amount
        update_user(target_id, balance_coin=target_new_balance)

        add_transfer_history(user_id, target_id, amount, comment)

        target_name = target_user.get('display_name', target_user.get('username', f"User {target_id}"))
        sender_name = user.get('display_name', message.from_user.username or "без_ника")

        transfer_text = (
            f"<blockquote>{PREMIUM_EMOJI_TEXT['balance']} <b>Перевод RCOIN</b>\n\n"
            f"👤 <b>От:</b> {sender_name}\n"
            f"👤 <b>Кому:</b> {target_name}\n"
            f"💵 <b>Сумма перевода:</b> {format_number(amount)} RCOIN\n"
            f"💸 <b>Комиссия ({TRANSFER_COMMISSION}%):</b> {format_number(commission)} RCOIN\n"
            f"📊 <b>Итого списано:</b> {format_number(total_cost)} RCOIN\n\n"
            f"💰 <b>Ваш баланс:</b>\n"
            f"<s>{format_number(current_balance)}</s> → {format_number(new_balance)} RCOIN"
        )

        if comment:
            transfer_text += f"\n\n📝 <b>Комментарий:</b> {comment}"

        transfer_text += "</blockquote>"

        await message.reply(transfer_text)

        try:
            target_text = (
                f"<blockquote>{PREMIUM_EMOJI_TEXT['balance']} <b>Вы получили перевод RCOIN!</b>\n\n"
                f"👤 <b>От:</b> {sender_name}\n"
                f"💵 <b>Сумма:</b> {format_number(amount)} RCOIN\n"
                f"💰 <b>Новый баланс:</b> {format_number(target_new_balance)} RCOIN"
            )
            if comment:
                target_text += f"\n\n📝 <b>Комментарий:</b> {comment}"
            target_text += "</blockquote>"

            await bot.send_message(target_id, target_text)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления получателю: {e}")

    except Exception as e:
        logger.error(f"Ошибка обработки перевода: {e}")
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка при обработке перевода. Проверьте формат.")


# ==================== ПЕРЕВОД ПОИНТОВ ====================

@dp.message(F.text.lower().startswith("перевод"))
async def cmd_transfer_point(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка получения данных пользователя.")
        return

    text = message.text
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await message.reply(
            f"{PREMIUM_EMOJI_TEXT['lock']} <b>Неправильный формат!</b>\n\n"
            "Примеры:\n"
            "• <code>Перевод 100 @username</code> – перевести 100 RBP\n"
            "• <code>Перевод 100 123456789</code> – перевести по ID\n"
            "• <code>Перевод 10</code> – в ответ на сообщение пользователя\n"
            "Минимальная сумма: 1 RBP"
        )
        return

    try:
        amount_str = parts[1]
        amount = int(amount_str)
        if amount < 1:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Минимальная сумма перевода — 1 RBP.")
            return
        if amount <= 0:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Сумма должна быть положительной.")
            return

        target_user = None
        target_id = None

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_user = get_user(target_id)
            if not target_user:
                await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Пользователь не найден в базе.")
                return
        elif len(parts) >= 3:
            target = parts[2]
            if target.isdigit():
                target_id = int(target)
                target_user = get_user(target_id)
            else:
                if target.startswith('@'):
                    target = target[1:]
                target_user = get_user_by_username(target)
                if target_user:
                    target_id = target_user['user_id']
        else:
            await message.reply(
                f"{PREMIUM_EMOJI_TEXT['lock']} Укажите получателя: @username, ID или ответьте на сообщение.")
            return

        if not target_user:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Пользователь не найден.")
            return

        if target_id == user_id:
            await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Нельзя перевести RBP самому себе.")
            return

        current_point = user.get('balance_point', 0)
        if current_point < amount:
            await message.reply(
                f"{PREMIUM_EMOJI_TEXT['lock']} <b>Недостаточно RBP!</b>\n"
                f"💎 Ваш баланс: {format_number(current_point)} RBP\n"
                f"💎 Нужно: {format_number(amount)} RBP"
            )
            return

        new_point = current_point - amount
        update_user(user_id, balance_point=new_point)
        update_user(target_id, balance_point=target_user.get('balance_point', 0) + amount)
        add_transfer_history(user_id, target_id, amount)

        target_name = target_user.get('display_name', target_user.get('username', f"User {target_id}"))
        sender_name = user.get('display_name', message.from_user.username or "без_ника")

        await message.reply(
            f"<blockquote>{PREMIUM_EMOJI_TEXT['diamond']} <b>Перевод RBP</b>\n\n"
            f"👤 <b>От:</b> {sender_name}\n"
            f"👤 <b>Кому:</b> {target_name}\n"
            f"💵 <b>Сумма:</b> {format_number(amount)} RBP\n\n"
            f"💎 <b>Ваш баланс RBP:</b>\n"
            f"<s>{format_number(current_point)}</s> → {format_number(new_point)} RBP</blockquote>"
        )

        try:
            await bot.send_message(
                target_id,
                f"<blockquote>{PREMIUM_EMOJI_TEXT['diamond']} <b>Вы получили перевод RBP!</b>\n\n"
                f"👤 <b>От:</b> {sender_name}\n"
                f"💵 <b>Сумма:</b> {format_number(amount)} RBP\n"
                f"💎 <b>Новый баланс:</b> {format_number(target_user.get('balance_point', 0) + amount)} RBP</blockquote>"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления получателю: {e}")

    except ValueError:
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Введите число. Пример: <code>Перевод 100 @username</code>")
    except Exception as e:
        logger.error(f"Ошибка обработки перевода поинтов: {e}")
        await message.reply(f"{PREMIUM_EMOJI_TEXT['lock']} Ошибка при обработке перевода. Проверьте формат.")


# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(Command("адм1308"))
async def cmd_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔨 Бан", callback_data="adm_ban"),
         InlineKeyboardButton(text="🔇 Мут", callback_data="adm_mute")],
        [InlineKeyboardButton(text="✅ Разбан/Размут", callback_data="adm_unban")],
        [InlineKeyboardButton(text="💰 Выдать RCOIN", callback_data="adm_vfg"),
         InlineKeyboardButton(text="💎 Выдать RBP", callback_data="adm_point")],
        [InlineKeyboardButton(text="⭐ Выдать Stars", callback_data="adm_stars")],
        [InlineKeyboardButton(text="💰 Снять RCOIN", callback_data="adm_take_vfg"),
         InlineKeyboardButton(text="💎 Снять RBP", callback_data="adm_take_point")],
        [InlineKeyboardButton(text="⭐ Снять Stars", callback_data="adm_take_stars")],
        [InlineKeyboardButton(text="🔄 Обнулить баланс RCOIN", callback_data="adm_reset_balance"),
         InlineKeyboardButton(text="🏦 Обнулить банк", callback_data="adm_reset_bank")],
        [InlineKeyboardButton(text="💎 Обнулить RBP", callback_data="adm_reset_point"),
         InlineKeyboardButton(text="⚠️ Обнулить всё", callback_data="adm_reset_all")],
        [InlineKeyboardButton(text="🚫 Выдать SCAMMER", callback_data="adm_rank_scammer"),
         InlineKeyboardButton(text="👑 Выдать ADMIN", callback_data="adm_rank_admin")],
        [InlineKeyboardButton(text="💵 Выдать DONATER", callback_data="adm_rank_donater"),
         InlineKeyboardButton(text="✅ Выдать VERIFIED", callback_data="adm_rank_official")],
        [InlineKeyboardButton(text="🗑 Снять все ранги", callback_data="adm_rank_clear")],
        [InlineKeyboardButton(text="🏦 Доступ к казне", callback_data="adm_treasury_access")],
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="adm_stats"),
         InlineKeyboardButton(text="👥 Список пользователей", callback_data="adm_users")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="adm_mailing"),
         InlineKeyboardButton(text="💾 Выгрузка БД", callback_data="adm_export")],
        [InlineKeyboardButton(text="ℹ️ Инфо о пользователе", callback_data="adm_user_info"),
         InlineKeyboardButton(text="📜 История игр", callback_data="adm_user_history")],
    ])

    await message.answer("👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=kb)


# ==================== ОБРАБОТЧИКИ ВЫБОРА ДЕЙСТВИЯ ====================

@dp.callback_query(F.data == "adm_ban")
async def adm_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🔨 <b>БАН</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='ban')
    await callback.answer()


@dp.callback_query(F.data == "adm_mute")
async def adm_mute(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🔇 <b>МУТ</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='mute')
    await callback.answer()


@dp.callback_query(F.data == "adm_unban")
async def adm_unban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("✅ <b>РАЗБАН / РАЗМУТ</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='unban')
    await callback.answer()


@dp.callback_query(F.data == "adm_vfg")
async def adm_vfg(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💰 <b>ВЫДАЧА RCOIN</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='give_vfg')
    await callback.answer()


@dp.callback_query(F.data == "adm_point")
async def adm_point(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💎 <b>ВЫДАЧА RBP</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='give_point')
    await callback.answer()


@dp.callback_query(F.data == "adm_stars")
async def adm_stars(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("⭐ <b>ВЫДАЧА STARS</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='give_stars')
    await callback.answer()


@dp.callback_query(F.data == "adm_take_vfg")
async def adm_take_vfg(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💰 <b>СНЯТИЕ RCOIN</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='take_vfg')
    await callback.answer()


@dp.callback_query(F.data == "adm_take_point")
async def adm_take_point(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💎 <b>СНЯТИЕ RBP</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='take_point')
    await callback.answer()


@dp.callback_query(F.data == "adm_take_stars")
async def adm_take_stars(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("⭐ <b>СНЯТИЕ STARS</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='take_stars')
    await callback.answer()


@dp.callback_query(F.data == "adm_reset_balance")
async def adm_reset_balance(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🔄 <b>ОБНУЛЕНИЕ БАЛАНСА RCOIN</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='reset_balance')
    await callback.answer()


@dp.callback_query(F.data == "adm_reset_bank")
async def adm_reset_bank(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🏦 <b>ОБНУЛЕНИЕ БАНКА</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='reset_bank')
    await callback.answer()


@dp.callback_query(F.data == "adm_reset_point")
async def adm_reset_point(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💎 <b>ОБНУЛЕНИЕ RBP</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='reset_point')
    await callback.answer()


@dp.callback_query(F.data == "adm_reset_all")
async def adm_reset_all(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("⚠️ <b>ОБНУЛИТЬ ВСЁ</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='reset_all')
    await callback.answer()


@dp.callback_query(F.data == "adm_rank_scammer")
async def adm_rank_scammer(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🚫 <b>ВЫДАЧА РАНГА SCAMMER</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='rank_scammer')
    await callback.answer()


@dp.callback_query(F.data == "adm_rank_admin")
async def adm_rank_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("👑 <b>ВЫДАЧА РАНГА ADMIN</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='rank_admin')
    await callback.answer()


@dp.callback_query(F.data == "adm_rank_donater")
async def adm_rank_donater(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("💵 <b>ВЫДАЧА РАНГА DONATER</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='rank_donater')
    await callback.answer()


@dp.callback_query(F.data == "adm_rank_official")
async def adm_rank_official(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("✅ <b>ВЫДАЧА РАНГА VERIFIED</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='rank_official')
    await callback.answer()


@dp.callback_query(F.data == "adm_rank_clear")
async def adm_rank_clear(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🗑 <b>СНЯТИЕ ВСЕХ РАНГОВ</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='rank_clear')
    await callback.answer()


@dp.callback_query(F.data == "adm_treasury_access")
async def adm_treasury_access(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("🏦 <b>ДОСТУП К КАЗНЕ</b>\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='treasury_access')
    await callback.answer()


@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT SUM(balance_coin) FROM users")
        total_vfg = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(balance_point) FROM users")
        total_point = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(bank_balance) FROM users")
        total_bank = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(stars_balance) FROM users")
        total_stars = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM bet_history")
        total_bets = cur.fetchone()[0] or 0
        conn.close()
        await callback.message.edit_text(
            f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
            f"👥 Пользователей: {format_number(total_users)}\n"
            f"💰 Всего RCOIN: {format_number(total_vfg)}\n"
            f"💎 Всего RBP: {format_number(total_point)}\n"
            f"🏦 Всего в банках: {format_number(total_bank)}\n"
            f"⭐ Всего Stars: {format_number(total_stars)}\n"
            f"🎯 Всего ставок: {format_number(total_bets)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_admin_panel")]])
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}")
    await callback.answer()


@dp.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    users = get_all_users()
    if not users:
        await callback.message.edit_text("📭 Список пользователей пуст.")
        return
    text = f"👥 <b>ПОЛЬЗОВАТЕЛИ ({len(users)})</b>\n\n"
    for i, uid in enumerate(users[:30], 1):
        user = get_user(uid)
        if user:
            name = user.get('display_name', user.get('username', f"User {uid}"))
            text += f"{i}. {name} – {format_number(user.get('balance_coin', 0))} RCOIN\n"
    if len(users) > 30:
        text += f"\n... и ещё {len(users) - 30}"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_admin_panel")]]))
    await callback.answer()


@dp.callback_query(F.data == "adm_mailing")
async def adm_mailing(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text(
        "📨 <b>РАССЫЛКА</b>\n\nВведите текст для рассылки:\n\nДля отмены напишите <code>отмена</code>")
    await state.set_state(AdminStates.admin_mailing)
    await callback.answer()


@dp.callback_query(F.data == "adm_export")
async def adm_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    try:
        import shutil
        backup_name = f"backup_{int(time.time())}.db"
        shutil.copy(DB_FILE, backup_name)
        await callback.message.edit_text(
            f"💾 <b>БАЗА ВЫГРУЖЕНА!</b>\n\n📁 {backup_name}\n📊 {os.path.getsize(backup_name) // 1024} KB",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_admin_panel")]])
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}")
    await callback.answer()


@dp.callback_query(F.data == "adm_user_info")
async def adm_user_info(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("ℹ️ <b>ИНФО О ПОЛЬЗОВАТЕЛЕ</b>\n\nВведите ID:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='user_info')
    await callback.answer()


@dp.callback_query(F.data == "adm_user_history")
async def adm_user_history(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("📜 <b>ИСТОРИЯ ИГР</b>\n\nВведите ID:")
    await state.set_state(AdminStates.admin_target)
    await state.update_data(admin_action='user_history')
    await callback.answer()


@dp.callback_query(F.data == "go_admin_panel")
async def go_admin_panel(callback: CallbackQuery):
    await cmd_admin_panel(callback.message)
    await callback.answer()


# ==================== ГЛАВНЫЙ ОБРАБОТЧИК ВВОДА ID ====================

@dp.message(AdminStates.admin_target)
async def admin_target_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    target = message.text.strip()
    if not target.isdigit():
        await message.answer("❌ Введите числовой ID.")
        return

    target_id = int(target)
    data = await state.get_data()
    action = data.get('admin_action')

    if not action:
        await message.answer("❌ Ошибка. Начните заново через /адм1308")
        await state.clear()
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден.")
        await state.clear()
        return

    await state.update_data(target=target_id)

    if action in ['reset_balance', 'reset_bank', 'reset_point', 'reset_all',
                  'rank_scammer', 'rank_admin', 'rank_donater', 'rank_official', 'rank_clear',
                  'treasury_access', 'unban']:

        if action == 'reset_balance':
            update_user(target_id, balance_coin=0)
            await message.answer(f"✅ Баланс RCOIN обнулен у {target_id}")
        elif action == 'reset_bank':
            update_user(target_id, bank_balance=0)
            await message.answer(f"✅ Банк обнулен у {target_id}")
        elif action == 'reset_point':
            update_user(target_id, balance_point=0)
            await message.answer(f"✅ RBP обнулен у {target_id}")
        elif action == 'reset_all':
            update_user(target_id, balance_coin=0, balance_point=0, bank_balance=0, stars_balance=0, total_wins=0,
                        total_losses=0, total_games=0)
            await message.answer(f"✅ Всё обнулено у {target_id}")
        elif action == 'rank_scammer':
            update_user(target_id, is_scammer=1, is_admin_rank=0, is_donater=0, is_official=0, rank_title='SCAMMER')
            await message.answer(f"🚫 Пользователю {target_id} выдан ранг SCAMMER")
        elif action == 'rank_admin':
            update_user(target_id, is_scammer=0, is_admin_rank=1, is_donater=0, is_official=0, rank_title='ADMIN')
            await message.answer(f"👑 Пользователю {target_id} выдан ранг ADMIN")
        elif action == 'rank_donater':
            update_user(target_id, is_scammer=0, is_admin_rank=0, is_donater=1, is_official=0, rank_title='DONATER')
            await message.answer(f"💵 Пользователю {target_id} выдан ранг DONATER")
        elif action == 'rank_official':
            update_user(target_id, is_scammer=0, is_admin_rank=0, is_donater=0, is_official=1, rank_title='VERIFIED')
            await message.answer(f"✅ Пользователю {target_id} выдан ранг VERIFIED")
        elif action == 'rank_clear':
            update_user(target_id, is_scammer=0, is_admin_rank=0, is_donater=0, is_official=0, rank_title='Новичок')
            await message.answer(f"🗑 У {target_id} сняты все ранги")
        elif action == 'treasury_access':
            current = user.get('treasury_access', 0)
            update_user(target_id, treasury_access=1 if current == 0 else 0)
            await message.answer(f"🏦 Доступ к казне для {target_id}: {'ВКЛЮЧЕН' if current == 0 else 'ВЫКЛЮЧЕН'}")
        elif action == 'unban':
            update_user(target_id, banned_until=0, ban_reason='', muted_until=0, mute_reason='')
            await message.answer(f"✅ Пользователь {target_id} разбанен и размучен!")

        await state.clear()
        return

    if action in ['ban', 'mute']:
        await message.answer("⏱ <b>Длительность</b>\n\nВведите минуты (0 = бессрочно):")
        await state.set_state(AdminStates.admin_duration)
        return

    if action in ['give_vfg', 'give_point', 'give_stars', 'take_vfg', 'take_point', 'take_stars']:
        if action == 'give_vfg' or action == 'take_vfg':
            currency = 'RCOIN'
            bal_key = 'balance_coin'
        elif action == 'give_point' or action == 'take_point':
            currency = 'RBP'
            bal_key = 'balance_point'
        else:
            currency = 'Stars'
            bal_key = 'stars_balance'

        current = user.get(bal_key, 0)
        action_name = "ВЫДАЧА" if action.startswith('give_') else "СНЯТИЕ"

        await message.answer(
            f"💰 <b>{action_name} {currency}</b>\n\n"
            f"👤 ID: {target_id}\n"
            f"💰 Текущий баланс: {format_number(current)} {currency}\n\n"
            f"📝 Введите сумму {currency}:\n"
            f"<i>(для отмены напишите 'отмена')</i>"
        )
        await state.set_state(AdminStates.admin_amount)
        return

    if action == 'user_info':
        stats = get_user_stats(target_id)
        referrals = get_referrals_count(target_id)
        text = (
            f"ℹ️ <b>ИНФО О ПОЛЬЗОВАТЕЛЕ</b>\n\n"
            f"🆔 ID: {target_id}\n"
            f"👤 Имя: {user.get('display_name', 'Не указано')}\n"
            f"💰 RCOIN: {format_number(user.get('balance_coin', 0))}\n"
            f"💎 RBP: {format_number(user.get('balance_point', 0))}\n"
            f"🏦 Банк: {format_number(user.get('bank_balance', 0))}\n"
            f"⭐ Stars: {user.get('stars_balance', 0)}\n"
            f"📊 Всего игр: {stats['total_bets']}\n"
            f"✅ Побед: {stats['wins']}\n"
            f"❌ Поражений: {stats['losses']}\n"
            f"👥 Рефералов: {referrals}\n"
            f"🏷️ Ранг: {user.get('rank_title', 'Новичок')}\n"
            f"🔒 Анонимность: {'Вкл' if user.get('is_anonymous', 0) else 'Выкл'}\n"
            f"🚫 Бан: {'Да' if user.get('banned_until', 0) > int(time.time()) else 'Нет'}\n"
            f"🏦 Доступ к казне: {'Да' if user.get('treasury_access', 0) else 'Нет'}"
        )
        await message.answer(text)
        await state.clear()
        return

    if action == 'user_history':
        history = get_user_bet_history(target_id, 20)
        if not history:
            await message.answer(f"📭 У {target_id} нет игр.")
            await state.clear()
            return
        game_names = {'dice': '🎲 Кубик', 'roulette': '🎰 Рулетка', 'fortune': '🎡 Фортуна', 'basket': '🏀 Баскет',
                      'mines': '💣 Мины', 'darts': '🎯 Дартс', 'blackjack': '🃏 Очко', 'crash': '🚀 Краш',
                      'hunt': '🎯 Охота', 'spin': '🎰 Спин', 'football': '⚽ Футбол', 'pyramid': '🏛️ Пирамида',
                      'hi_lo': '🎴 Хи-Ло'}
        text = f"📜 <b>ИСТОРИЯ ИГР {target_id}</b>\n\n"
        for i, game in enumerate(history[:15], 1):
            game_name = game_names.get(game['game_type'], game['game_type'])
            result = '✅' if game['is_win'] else '❌'
            amount = game['win_amount'] if game['is_win'] else game['bet_amount']
            time_str = datetime.fromtimestamp(game['created_at']).strftime('%d.%m %H:%M')
            text += f"{i}. {game_name} {result} {format_number(amount)} RCOIN | {time_str}\n"
        if len(history) > 15:
            text += f"\n... и ещё {len(history) - 15}"
        await message.answer(text)
        await state.clear()
        return


# ==================== ДЛИТЕЛЬНОСТЬ БАНА/МУТА ====================

@dp.message(AdminStates.admin_duration)
async def admin_duration_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    duration = message.text.strip()
    if not duration.isdigit():
        await message.answer("❌ Введите число.")
        return

    minutes = int(duration)
    data = await state.get_data()
    action = data.get('admin_action')
    target = data.get('target')

    if not target:
        await message.answer("❌ Ошибка. Начните заново.")
        await state.clear()
        return

    until = 0 if minutes == 0 else int(time.time()) + minutes * 60
    await state.update_data(duration=until)

    await message.answer(
        f"📝 <b>ПРИЧИНА</b>\n\nДействие: {'БАН' if action == 'ban' else 'МУТ'}\n👤 {target}\n⏱ {'БЕССРОЧНО' if minutes == 0 else f'{minutes} мин'}\n\nВведите причину:")
    await state.set_state(AdminStates.admin_reason)


# ==================== ПРИЧИНА БАНА/МУТА ====================

@dp.message(AdminStates.admin_reason)
async def admin_reason_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    reason = message.text.strip()
    data = await state.get_data()
    action = data.get('admin_action')
    target = data.get('target')
    until = data.get('duration')

    if not target:
        await message.answer("❌ Ошибка. Начните заново.")
        await state.clear()
        return

    if action == 'ban':
        update_user(target, banned_until=until, ban_reason=reason)
        await message.answer(
            f"🔨 <b>ПОЛЬЗОВАТЕЛЬ {target} ЗАБАНЕН!</b>\n\n📅 До: {'БЕССРОЧНО' if until == 0 else datetime.fromtimestamp(until).strftime('%d.%m.%Y %H:%M')}\n📝 Причина: {reason}")
    elif action == 'mute':
        update_user(target, muted_until=until, mute_reason=reason)
        await message.answer(
            f"🔇 <b>ПОЛЬЗОВАТЕЛЬ {target} ЗАМУЧЕН!</b>\n\n📅 До: {'БЕССРОЧНО' if until == 0 else datetime.fromtimestamp(until).strftime('%d.%m.%Y %H:%M')}\n📝 Причина: {reason}")

    await state.clear()


# ==================== ВВОД СУММЫ ДЛЯ ВЫДАЧИ/СНЯТИЯ ====================

@dp.message(AdminStates.admin_amount)
async def admin_amount_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text.lower() in ['отмена', 'cancel', 'назад']:
        await state.clear()
        await message.answer("❌ Действие отменено.")
        return

    amount_str = message.text.strip()
    if not amount_str.isdigit():
        await message.answer("❌ Введите число.")
        return

    amount = int(amount_str)
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной.")
        return

    data = await state.get_data()
    action = data.get('admin_action')
    target = data.get('target')

    if not target:
        await message.answer("❌ Ошибка. Начните заново.")
        await state.clear()
        return

    user = get_user(target)
    if not user:
        await message.answer(f"❌ Пользователь {target} не найден.")
        await state.clear()
        return

    if action == 'give_vfg':
        new_balance = user.get('balance_coin', 0) + amount
        update_user(target, balance_coin=new_balance)
        await message.answer(
            f"<blockquote>💰 <b>ВЫДАНО {format_number(amount)} RCOIN</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"💰 Новый баланс: {format_number(new_balance)} RCOIN</blockquote>"
        )

    elif action == 'give_point':
        new_balance = user.get('balance_point', 0) + amount
        update_user(target, balance_point=new_balance)
        await message.answer(
            f"<blockquote>💎 <b>ВЫДАНО {format_number(amount)} RBP</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"💎 Новый баланс: {format_number(new_balance)} RBP</blockquote>"
        )

    elif action == 'give_stars':
        new_balance = user.get('stars_balance', 0) + amount
        update_user(target, stars_balance=new_balance)
        await message.answer(
            f"<blockquote>⭐ <b>ВЫДАНО {format_number(amount)} Stars</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"⭐ Новый баланс: {format_number(new_balance)} Stars</blockquote>"
        )

    elif action == 'take_vfg':
        current = user.get('balance_coin', 0)
        if amount > current:
            await message.answer(f"❌ Недостаточно RCOIN! Доступно: {format_number(current)}")
            return
        new_balance = current - amount
        update_user(target, balance_coin=new_balance)
        await message.answer(
            f"<blockquote>💰 <b>СНЯТО {format_number(amount)} RCOIN</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"💰 Новый баланс: {format_number(new_balance)} RCOIN</blockquote>"
        )

    elif action == 'take_point':
        current = user.get('balance_point', 0)
        if amount > current:
            await message.answer(f"❌ Недостаточно RBP! Доступно: {format_number(current)}")
            return
        new_balance = current - amount
        update_user(target, balance_point=new_balance)
        await message.answer(
            f"<blockquote>💎 <b>СНЯТО {format_number(amount)} RBP</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"💎 Новый баланс: {format_number(new_balance)} RBP</blockquote>"
        )

    elif action == 'take_stars':
        current = user.get('stars_balance', 0)
        if amount > current:
            await message.answer(f"❌ Недостаточно Stars! Доступно: {format_number(current)}")
            return
        new_balance = current - amount
        update_user(target, stars_balance=new_balance)
        await message.answer(
            f"<blockquote>⭐ <b>СНЯТО {format_number(amount)} Stars</b>\n\n"
            f"👤 Пользователь: {user.get('display_name', target)}\n"
            f"🆔 ID: {target}\n"
            f"⭐ Новый баланс: {format_number(new_balance)} Stars</blockquote>"
        )

    await state.clear()
    await message.answer("✅ Готово! Можете продолжить в админ-панели.")


# ==================== РАССЫЛКА ====================

@dp.message(AdminStates.admin_mailing)
async def admin_mailing_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Рассылка отменена.")
        return

    text = message.text
    users = get_all_users()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📨 <b>Начинаю рассылку...</b>\n\n👥 Всего: {len(users)}")

    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

        if sent % 50 == 0:
            await status_msg.edit_text(
                f"📨 <b>Идёт рассылка...</b>\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}\n⏳ Осталось: {len(users) - sent - failed}")

    await status_msg.edit_text(
        f"✅ <b>РАССЫЛКА ЗАВЕРШЕНА!</b>\n\n👥 Всего: {len(users)}\n✅ Успешно: {sent}\n❌ Ошибок: {failed}")
    await state.clear()


# ==================== ПРОСТАЯ ВЫДАЧА RCOIN ====================

@dp.message(F.text.lower().startswith("выдать"))
async def simple_give_vfg(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❌ ФОРМАТ: <code>выдать СУММА ID</code>\n\n"
            "Пример: <code>выдать 1000 5257618084</code>"
        )
        return

    try:
        amount = int(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.answer("❌ Сумма и ID должны быть числами!")
        return

    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0!")
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    new_balance = user.get('balance_coin', 0) + amount
    update_user(target_id, balance_coin=new_balance)

    await message.answer(
        f"✅ <b>ВЫДАНО {format_number(amount)} RCOIN</b>\n\n"
        f"👤 Пользователь: {user.get('display_name', target_id)}\n"
        f"🆔 ID: {target_id}\n"
        f"💰 Новый баланс: {format_number(new_balance)} RCOIN"
    )

    try:
        await bot.send_message(
            target_id,
            f"💰 <b>Вам начислили {format_number(amount)} RCOIN!</b>\n\n"
            f"📊 Новый баланс: {format_number(new_balance)} RCOIN"
        )
    except:
        pass


# ==================== ПРОСТАЯ ВЫДАЧА POINT ====================

@dp.message(F.text.lower().startswith("выдатьпоинт"))
async def simple_give_point(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❌ ФОРМАТ: <code>выдатьпоинт СУММА ID</code>\n\n"
            "Пример: <code>выдатьпоинт 1000 5257618084</code>"
        )
        return

    try:
        amount = int(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.answer("❌ Сумма и ID должны быть числами!")
        return

    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0!")
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    new_balance = user.get('balance_point', 0) + amount
    update_user(target_id, balance_point=new_balance)

    await message.answer(
        f"✅ <b>ВЫДАНО {format_number(amount)} RBP</b>\n\n"
        f"👤 Пользователь: {user.get('display_name', target_id)}\n"
        f"🆔 ID: {target_id}\n"
        f"💎 Новый баланс: {format_number(new_balance)} RBP"
    )

    try:
        await bot.send_message(
            target_id,
            f"💎 <b>Вам начислили {format_number(amount)} RBP!</b>\n\n"
            f"📊 Новый баланс: {format_number(new_balance)} RBP"
        )
    except:
        pass


# ==================== ПРОСТОЕ СНЯТИЕ RCOIN ====================

@dp.message(F.text.lower().startswith("снять"))
async def simple_take_vfg(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❌ ФОРМАТ: <code>снять СУММА ID</code>\n\n"
            "Пример: <code>снять 1000 5257618084</code>"
        )
        return

    try:
        amount = int(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.answer("❌ Сумма и ID должны быть числами!")
        return

    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0!")
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    current = user.get('balance_coin', 0)
    if amount > current:
        await message.answer(f"❌ Недостаточно RCOIN! Доступно: {format_number(current)}")
        return

    new_balance = current - amount
    update_user(target_id, balance_coin=new_balance)

    await message.answer(
        f"✅ <b>СНЯТО {format_number(amount)} RCOIN</b>\n\n"
        f"👤 Пользователь: {user.get('display_name', target_id)}\n"
        f"🆔 ID: {target_id}\n"
        f"💰 Новый баланс: {format_number(new_balance)} RCOIN"
    )


# ==================== ПРОСТОЙ БАН ====================

@dp.message(F.text.lower().startswith("забанить"))
async def simple_ban(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "❌ ФОРМАТ: <code>забанить ID ПРИЧИНА</code>\n\n"
            "Пример: <code>забанить 5257618084 Спам</code>"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    reason = parts[2] if len(parts) > 2 else "Без причины"

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    update_user(target_id, banned_until=9999999999, ban_reason=reason)

    await message.answer(
        f"🔨 <b>ПОЛЬЗОВАТЕЛЬ ЗАБАНЕН!</b>\n\n"
        f"🆔 ID: {target_id}\n"
        f"👤 Имя: {user.get('display_name', target_id)}\n"
        f"📝 Причина: {reason}"
    )

    try:
        await bot.send_message(
            target_id,
            f"🔨 <b>Вас забанили!</b>\n\n📝 Причина: {reason}"
        )
    except:
        pass


# ==================== ПРОСТОЙ РАЗБАН ====================

@dp.message(F.text.lower().startswith("разбанить"))
async def simple_unban(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ ФОРМАТ: <code>разбанить ID</code>\n\n"
            "Пример: <code>разбанить 5257618084</code>"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    update_user(target_id, banned_until=0, ban_reason='')

    await message.answer(
        f"✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБАНЕН!</b>\n\n"
        f"🆔 ID: {target_id}\n"
        f"👤 Имя: {user.get('display_name', target_id)}"
    )

    try:
        await bot.send_message(
            target_id,
            f"✅ <b>Вас разбанили!</b>"
        )
    except:
        pass


# ==================== ПРОСТОЙ МУТ ====================

@dp.message(F.text.lower().startswith("замутить"))
async def simple_mute(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "❌ ФОРМАТ: <code>замутить ID ПРИЧИНА</code>\n\n"
            "Пример: <code>замутить 5257618084 Флуд</code>"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    reason = parts[2] if len(parts) > 2 else "Без причины"

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    update_user(target_id, muted_until=9999999999, mute_reason=reason)

    await message.answer(
        f"🔇 <b>ПОЛЬЗОВАТЕЛЬ ЗАМУЧЕН!</b>\n\n"
        f"🆔 ID: {target_id}\n"
        f"👤 Имя: {user.get('display_name', target_id)}\n"
        f"📝 Причина: {reason}"
    )

    try:
        await bot.send_message(
            target_id,
            f"🔇 <b>Вас замутили!</b>\n\n📝 Причина: {reason}"
        )
    except:
        pass


# ==================== ПРОСТОЙ РАЗМУТ ====================

@dp.message(F.text.lower().startswith("размутить"))
async def simple_unmute(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав!")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ ФОРМАТ: <code>размутить ID</code>\n\n"
            "Пример: <code>размутить 5257618084</code>"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    user = get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден!")
        return

    update_user(target_id, muted_until=0, mute_reason='')

    await message.answer(
        f"✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗМУЧЕН!</b>\n\n"
        f"🆔 ID: {target_id}\n"
        f"👤 Имя: {user.get('display_name', target_id)}"
    )

    try:
        await bot.send_message(
            target_id,
            f"✅ <b>Вас размутили!</b>"
        )
    except:
        pass


# ==================== КОМАНДА ИГРЫ ====================

@dp.message(F.text.lower() == "игры")
@dp.message(Command("игры"))
async def cmd_games(message: Message):
    kb = get_games_keyboard(0)
    # Добавляем кнопку открытия веб-аппа с ареной и играми
    try:
        web_btn = [
            InlineKeyboardButton(text="🎮 Открыть Веб-Апп (арена + игры)",
                                 web_app=WebAppInfo(url=WEBAPP_URL))
        ]
        outer = InlineKeyboardMarkup(inline_keyboard=[
            *kb.inline_keyboard,
            web_btn
        ])
    except Exception:
        outer = kb

    await message.answer(
        f"{PREMIUM_EMOJI_TEXT['games']} <b>ВЫБЕРИТЕ ИГРУ</b>\n\n"
        "Нажмите на кнопку с названием игры,\n"
        "чтобы узнать подробности и правила.\n\n"
        "🎮 В веб-аппе — арена на коины и мини-игры.",
        reply_markup=outer
    )


# ==================== ОБРАБОТЧИКИ КНОПОК КАЗНЫ ====================

@dp.callback_query(F.data.startswith("dep_"))
async def treasury_deposit_amount(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    data = callback.data.split('_')

    if data[1] == 'custom':
        await callback.message.edit_text(
            f"💰 <b>Введите сумму</b>\n\n"
            f"Форматы: 1к=1000, 1кк=1000000\n"
            f"Для отмены: отмена"
        )
        await state.set_state("deposit_custom")
        await callback.answer()
        return

    amount = int(data[1])

    if user.get('balance_coin', 0) < amount:
        await callback.answer(f"❌ Недостаточно! У вас: {format_number(user.get('balance_coin', 0))} RCOIN",
                              show_alert=True)
        return

    balance_coin, balance_point = get_treasury_balance()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - amount)
    update_treasury(balance_coin + amount, balance_point)

    await callback.message.edit_text(
        f"✅ <b>ПОПОЛНЕНО!</b>\n\n"
        f"💰 +{format_number(amount)} RCOIN\n"
        f"📊 В казне: {format_number(balance_coin + amount)} RCOIN"
    )
    await asyncio.sleep(1)
    await cmd_treasury(callback.message)
    await callback.answer(f"✅ +{format_number(amount)} RCOIN", show_alert=True)


@dp.callback_query(F.data.startswith("wd_"))
async def treasury_withdraw_amount(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not is_admin(user_id) and user.get('treasury_access', 0) != 1:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return

    data = callback.data.split('_')

    if data[1] == 'custom':
        await callback.message.edit_text(
            f"🏦 <b>Введите сумму</b>\n\n"
            f"Форматы: 1к=1000, 1кк=1000000\n"
            f"Для отмены: отмена"
        )
        await state.set_state("withdraw_custom")
        await callback.answer()
        return

    amount = int(data[1])
    balance_coin, balance_point = get_treasury_balance()

    if balance_coin < amount:
        await callback.answer(f"❌ В казне {format_number(balance_coin)} RCOIN", show_alert=True)
        return

    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)
    update_treasury(balance_coin - amount, balance_point)

    await callback.message.edit_text(
        f"✅ <b>СНЯТО!</b>\n\n"
        f"💰 -{format_number(amount)} RCOIN\n"
        f"📊 В казне: {format_number(balance_coin - amount)} RCOIN"
    )
    await asyncio.sleep(1)
    await cmd_treasury(callback.message)
    await callback.answer(f"✅ -{format_number(amount)} RCOIN", show_alert=True)


@dp.message(StateFilter("deposit_custom"))
async def deposit_custom_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_treasury(message)
        return

    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❌ Введите положительное число")
        return

    user = get_user(user_id)

    if user.get('balance_coin', 0) < amount:
        await message.answer(f"❌ Недостаточно! У вас: {format_number(user.get('balance_coin', 0))} RCOIN")
        return

    balance_coin, balance_point = get_treasury_balance()

    update_user(user_id, balance_coin=user.get('balance_coin', 0) - amount)
    update_treasury(balance_coin + amount, balance_point)

    await state.clear()
    await message.answer(f"✅ Пополнено {format_number(amount)} RCOIN!")
    await cmd_treasury(message)


@dp.message(StateFilter("withdraw_custom"))
async def withdraw_custom_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text.lower() in ['отмена', 'назад', 'cancel']:
        await state.clear()
        await cmd_treasury(message)
        return

    amount = parse_amount(message.text)
    if amount <= 0:
        await message.answer("❌ Введите положительное число")
        return

    balance_coin, balance_point = get_treasury_balance()

    if balance_coin < amount:
        await message.answer(f"❌ В казне {format_number(balance_coin)} RCOIN")
        return

    user = get_user(user_id)
    update_user(user_id, balance_coin=user.get('balance_coin', 0) + amount)
    update_treasury(balance_coin - amount, balance_point)

    await state.clear()
    await message.answer(f"✅ Снято {format_number(amount)} RCOIN!")
    await cmd_treasury(message)


@dp.callback_query(F.data == "treasury_back")
async def treasury_back(callback: CallbackQuery):
    await cmd_treasury(callback.message)
    await callback.answer()


# ==================== ИВЕНТЫ ====================
import random as _rnd

EVENT_STASH_MIN = 15000
EVENT_STASH_MAX = 1000000
EVENT_STASH_CELLS = 3
EVENT_BOSS_HP = 10_000_000
EVENT_BOSS_HP_FINAL = 100_000_000
EVENT_WHEEL = [(5000, 20), (15000, 15), (50000, 12), (150000, 10), (500000, 7),
               (1500000, 4), (5000000, 1.5), (25000000, 0.4), (100000000, 0.1)]
EVENT_QUESTS = [
    ("q_games", "Сыграй 20 игр", 20, 250000),
    ("q_wins", "Выиграй 10 раз", 10, 500000),
    ("q_stash", "Открой склад", 1, 100000),
    ("q_boss", "Ударь босса", 1, 150000),
]


def _event_today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _event_boss_state() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT boss_hp, boss_max, day FROM event_progress WHERE id = 1")
    row = cur.fetchone()
    today = _event_today()
    is_final = datetime.now().month == 12 and datetime.now().day == 31
    max_hp = EVENT_BOSS_HP_FINAL if is_final else EVENT_BOSS_HP
    if not row or row[2] != today or row[1] == 0:
        cur.execute("UPDATE event_progress SET boss_hp = ?, boss_max = ?, day = ? WHERE id = 1",
                    (max_hp, max_hp, today))
        conn.commit()
        hp = max_hp
    else:
        hp = row[0]
    conn.close()
    return {"hp": max(0, hp), "max": max_hp, "final": is_final}


def _event_boss_hit(damage: int) -> None:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT boss_hp FROM event_progress WHERE id = 1")
    row = cur.fetchone()
    hp = max(0, (row[0] if row else 0) - damage)
    cur.execute("UPDATE event_progress SET boss_hp = ? WHERE id = 1", (hp,))
    conn.commit()
    conn.close()


def _event_bar(current: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "▱" * width
    filled = int(width * current / total)
    return "▰" * filled + "▱" * (width - filled)


def _event_kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def _event_btn(text: str, data: str, emoji_key: str | None = None) -> InlineKeyboardButton:
    kw = {"text": text, "callback_data": data}
    if emoji_key and emoji_key in EMOJI_IDS:
        kw["icon_custom_emoji_id"] = EMOJI_IDS[emoji_key]
    return InlineKeyboardButton(**kw)


async def show_events(message: Message, edit: bool = False):
    boss = _event_boss_state()
    text = (
        f"{PREMIUM_EMOJI_TEXT['star']} <b>ИВЕНТЫ</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>Зимний склад</b> — {EVENT_STASH_CELLS} ячейки в день, "
        f"приз от {format_number(EVENT_STASH_MIN)} до {format_number(EVENT_STASH_MAX)} RCOIN\n"
        f"{PREMIUM_EMOJI_TEXT['crash']} <b>Босс</b> — {format_number(boss['hp'])} / "
        f"{format_number(boss['max'])} HP\n"
        f"{PREMIUM_EMOJI_TEXT['spin']} <b>Колесо удачи</b> — раз в 6 часов\n"
        f"{PREMIUM_EMOJI_TEXT['treasury']} <b>Квесты</b> — ежедневные задания\n\n"
        "Выбери ивент:"
    )
    markup = _event_kb(
        [_event_btn("Зимний склад", "ev_stash", "diamond"), _event_btn("Босс", "ev_boss", "crash")],
        [_event_btn("Колесо удачи", "ev_wheel", "spin"), _event_btn("Квесты", "ev_quests", "treasury")],
        [_event_btn("Назад", "back_to_balance", "door")],
    )
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@dp.message(F.text.lower().in_({"ивенты", "ивент", "events"}))
@dp.message(Command("ивенты"))
async def cmd_events(message: Message):
    await show_events(message)


# ---------- Зимний склад ----------
@dp.callback_query(F.data == "ev_stash")
async def ev_stash(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    today = _event_today()
    if user.get("event_day") == today and user.get("event_stash_last", 0) >= EVENT_STASH_CELLS:
        await callback.answer("Склад на сегодня уже открыт", show_alert=True)
        return
    used = user.get("event_stash_last", 0) if user.get("event_day") == today else 0
    if used >= EVENT_STASH_CELLS:
        await callback.answer("Приходи завтра", show_alert=True)
        return
    prize = _rnd.randint(EVENT_STASH_MIN, EVENT_STASH_MAX)
    # Изредка из ячейки выпадает тгп-айтем (новые эмодзи зимнего ивента)
    item_key = None
    if _rnd.random() < 0.4:
        item_key = _rnd.choice(["item_1", "item_2", "item_3", "item_4", "item_5",
                                "item_6", "item_7", "item_8", "item_9"])
    total = user.get("balance_coin", 0) + prize
    update_user(callback.from_user.id, balance_coin=total,
                event_day=today, event_stash_last=used + 1,
                event_points=user.get("event_points", 0) + 1)
    item_line = ""
    if item_key:
        try:
            inventory = json.loads(user.get("inventory") or "[]")
            if not isinstance(inventory, list):
                inventory = []
        except (TypeError, json.JSONDecodeError):
            inventory = []
        existing = next((x for x in inventory if x.get("key") == item_key), None)
        if existing:
            existing["qty"] = int(existing.get("qty", 1)) + 1
        else:
            inventory.append({"key": item_key, "name": f"Зимний сувенир #{item_key[-1]}", "qty": 1})
        update_user(callback.from_user.id, inventory=json.dumps(inventory, ensure_ascii=False))
        item_line = (f"\n🎁 <b>Найден предмет:</b> "
                     f"{PREMIUM_EMOJI_TEXT[item_key]} <i>Зимний сувенир #{item_key[-1]}</i>\n"
                     f"<blockquote>Предмет сохранён на твоём складе!</blockquote>")
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['diamond']} <b>ЗИМНИЙ СКЛАД</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['win']} Ячейка {used + 1}/{EVENT_STASH_CELLS}\n"
        f"Приз: <b>+{format_number(prize)} RCOIN</b>{item_line}\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} Баланс: {format_number(total)}",
        reply_markup=_event_kb(
            [_event_btn("Открыть ещё", "ev_stash", "diamond")]
            if used + 1 < EVENT_STASH_CELLS else
            [_event_btn("К ивентам", "ev_menu", "door")],
        ),
    )
    await callback.answer(f"+{format_number(prize)} RCOIN")


@dp.callback_query(F.data == "ev_menu")
async def ev_menu(callback: CallbackQuery):
    await show_events(callback.message, edit=True)
    await callback.answer()


# ---------- Босс ----------
@dp.callback_query(F.data == "ev_boss")
async def ev_boss(callback: CallbackQuery):
    boss = _event_boss_state()
    user = get_user(callback.from_user.id)
    can_hit = user.get("event_day") != _event_today() or user.get("event_boss_last", 0) == 0
    title = "Главный босс" if boss["final"] else "Санта"
    text = (
        f"{PREMIUM_EMOJI_TEXT['crash']} <b>БИТВА: {title.upper()}</b>\n\n"
        f"HP: <b>{format_number(boss['hp'])}</b> / {format_number(boss['max'])}\n"
        f"<code>{_event_bar(boss['max'] - boss['hp'], boss['max'])}</code>\n\n"
        f"Твой урон за день: <b>{format_number(user.get('event_boss_dmg', 0))}</b>\n"
        "Каждый удар приносит RCOIN по курсу ×2."
    )
    kb = [[_event_btn("Ударить", "ev_boss_hit", "crash" if can_hit else "lock")],
          [_event_btn("К ивентам", "ev_menu", "door")]]
    await callback.message.edit_text(text, reply_markup=_event_kb(*kb))
    await callback.answer()


@dp.callback_query(F.data == "ev_boss_hit")
async def ev_boss_hit(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    today = _event_today()
    if user.get("event_day") == today and user.get("event_boss_last", 0) > 0:
        await callback.answer("Ты уже бил босса сегодня", show_alert=True)
        return
    damage = _rnd.randint(10000, 120000)
    _event_boss_hit(damage)
    reward = damage * 2
    update_user(callback.from_user.id,
                balance_coin=user.get("balance_coin", 0) + reward,
                event_day=today,
                event_boss_last=int(time.time()),
                event_boss_dmg=user.get("event_boss_dmg", 0) + damage)
    boss = _event_boss_state()
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['win']} <b>УДАР!</b>\n\n"
        f"Урон: <b>{format_number(damage)}</b>\n"
        f"Награда: <b>+{format_number(reward)} RCOIN</b>\n\n"
        f"HP босса: {format_number(boss['hp'])} / {format_number(boss['max'])}\n"
        f"<code>{_event_bar(boss['max'] - boss['hp'], boss['max'])}</code>",
        reply_markup=_event_kb([_event_btn("К ивентам", "ev_menu", "door")]),
    )
    await callback.answer(f"-{format_number(damage)} HP")


# ---------- Колесо удачи ----------
@dp.callback_query(F.data == "ev_wheel")
async def ev_wheel(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    now = int(time.time())
    left = 6 * 3600 - (now - user.get("event_wheel_last", 0))
    if left > 0:
        await callback.answer(f"Колесо через {left // 3600} ч", show_alert=True)
        return
    prizes = [p for p, w in EVENT_WHEEL]
    weights = [w for _, w in EVENT_WHEEL]
    prize = _rnd.choices(prizes, weights=weights, k=1)[0]
    update_user(callback.from_user.id,
                balance_coin=user.get("balance_coin", 0) + prize,
                event_wheel_last=now)
    await callback.message.edit_text(
        f"{PREMIUM_EMOJI_TEXT['spin']} <b>КОЛЕСО УДАЧИ</b>\n\n"
        f"{PREMIUM_EMOJI_TEXT['win']} Выпало: <b>{format_number(prize)} RCOIN</b>\n"
        f"{PREMIUM_EMOJI_TEXT['balance']} Баланс: "
        f"{format_number(user.get('balance_coin', 0) + prize)}",
        reply_markup=_event_kb([_event_btn("К ивентам", "ev_menu", "door")]),
    )
    await callback.answer(f"+{format_number(prize)}")


# ---------- Квесты ----------
@dp.callback_query(F.data == "ev_quests")
async def ev_quests(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    games = user.get("total_games", 0)
    wins = user.get("total_wins", 0)
    rows = []
    lines = [f"{PREMIUM_EMOJI_TEXT['treasury']} <b>КВЕСТЫ</b>\n"]
    for key, title, goal, reward in EVENT_QUESTS:
        value = {"q_games": games, "q_wins": wins,
                 "q_stash": user.get("event_points", 0),
                 "q_boss": user.get("event_boss_dmg", 0)}[key]
        done = value >= goal
        lines.append(f"{'✅' if done else '▫️'} {title} — {min(value, goal)}/{goal}, "
                     f"награда {format_number(reward)}")
        if done and user.get(f"quest_{key}", 0) == 0:
            rows.append([_event_btn(f"Забрать: {title}", f"ev_quest_{key}", "win")])
    rows.append([_event_btn("К ивентам", "ev_menu", "door")])
    await callback.message.edit_text("\n".join(lines), reply_markup=_event_kb(*rows))
    await callback.answer()


@dp.callback_query(F.data.startswith("ev_quest_"))
async def ev_quest_claim(callback: CallbackQuery):
    key = callback.data.replace("ev_quest_", "")
    quest = next((q for q in EVENT_QUESTS if q[0] == key), None)
    if not quest:
        await callback.answer("Квест не найден", show_alert=True)
        return
    user = get_user(callback.from_user.id)
    if user.get(f"quest_{key}", 0) == 1:
        await callback.answer("Уже получено", show_alert=True)
        return
    _, title, goal, reward = quest
    update_user(callback.from_user.id,
                balance_coin=user.get("balance_coin", 0) + reward,
                **{f"quest_{key}": 1})
    await callback.answer(f"+{format_number(reward)} RCOIN", show_alert=True)
    await ev_quests(callback)


# ==================== ВЕБ-АПП (HTML-панель) ====================
_WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RCOIN — Игровой центр</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); color:#fff; min-height:100vh; padding:16px; }
  .card { background: rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); border-radius:16px; padding:16px; margin-bottom:14px; backdrop-filter: blur(6px); }
  h1 { font-size:22px; margin-bottom:4px; }
  h2 { font-size:16px; margin-bottom:8px; color:#ffd166; }
  .g { font-size:13px; color:#cfe; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; }
  .game { background:rgba(255,255,255,.12); border-radius:12px; padding:12px; text-align:center; cursor:pointer; }
  .game:hover { background:rgba(255,255,255,.2); }
  .game b { display:block; font-size:13px; margin-top:4px; }
  .arena-stats { display:flex; gap:10px; flex-wrap:wrap; }
  .stat { background:rgba(0,0,0,.3); border-radius:10px; padding:8px 12px; font-size:13px; }
  .btn { display:block; width:100%; padding:12px; margin-top:10px; border:none; border-radius:12px; background:linear-gradient(90deg,#11998e,#38ef7d); color:#fff; font-size:16px; font-weight:700; cursor:pointer; }
  .btn:active { transform:scale(.98); }
  .mini { font-size:12px; opacity:.75; margin-top:10px; }
  #ball { font-size:20px; transition:margin-left 1.5s ease; }
</style>
</head>
<body>
<div class="card">
  <h1>💎 RCOIN — Игровой центр</h1>
  <div class="g">Тренировочные мини-игры без ставок и денежных выплат</div>
  <div class="arena-stats">
    <div class="stat">💰 Баланс: <b id="bal">—</b></div>
    <div class="stat">👥 В лобби: <b id="lobby">0</b></div>
  </div>
</div>

<div class="card">
  <h2>⚔️ Арена — тренировка</h2>
  <div class="g">Демо-режим для проверки анимации. Здесь нет ставок, соперников или начисления RCOIN.</div>
  <button class="btn" onclick="startArena()">⚔️ Запустить тренировку</button>
  <div class="mini" id="arenaInfo">Запусти тренировочный шар.</div>
</div>

<div class="card">
  <h2>🎮 Мини-игры</h2>
  <div class="grid">
    <div class="game" onclick="miniGame('cube')">🎲<b>Кубик</b></div>
    <div class="game" onclick="miniGame('dice')">🎯<b>Рулетка</b></div>
    <div class="game" onclick="miniGame('coin')">🪙<b>Орёл/Решка</b></div>
    <div class="game" onclick="miniGame('card')">🃏<b>Карта</b></div>
  </div>
  <div class="mini" id="miniInfo">Выбери игру.</div>
</div>

<div class="card" style="display:none" id="ballCard">
  <h2>🎱 Шар катится</h2>
  <div id="ball">🎱</div>
</div>

<script>
  const tg = window.Telegram ? Telegram.WebApp : null;
  if (tg) { tg.ready(); tg.expand(); }
  function setText(id, t){ const el=document.getElementById(id); if(el) el.textContent=t; }
  setText('bal', '?');

  function startArena(){
    setText('arenaInfo', '⚔️ Тренировка запущена. Это визуальная демонстрация без ставок.');
    setText('lobby', '0');
    const ballCard = document.getElementById('ballCard');
    ballCard.style.display = 'block';
    document.getElementById('ball').textContent = '🎱';
    setTimeout(()=>{ document.getElementById('ball').style.marginLeft='60%'; }, 200);
    setTimeout(()=>{
      const win = Math.random() < 0.5;
      ballCard.style.display='none';
      setText('arenaInfo', (win ? '🎉 Шар остановился на синем секторе!' : '✨ Шар остановился на серебряном секторе!') + ' Тренировка завершена.');
      setText('lobby','0');
    }, 1600);
  }

  function miniGame(g){
    const names = {cube:'🎲 Кубик', dice:'🎰 Рулетка', coin:'🪙 Орёл/Решка', card:'🃏 Карта'};
    setText('miniInfo', 'Игра: ' + (names[g]||g) + ' — открывается в боте командой!');
  }
</script>
</body>
</html>
"""



@dp.message(Command("grantadmin"))
async def cmd_grant_admin(message: Message):
    if OWNER_ID <= 0 or message.from_user.id != OWNER_ID:
        await message.answer("⛔ Только владелец бота может управлять администраторами.")
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /grantadmin TELEGRAM_ID")
        return
    target = int(parts[1])
    get_user(target)
    update_user(target, is_admin_rank=1, rank_title="ADMIN")
    await message.answer(f"✅ Пользователь {target} получил права администратора. Для снятия прав используй /revokeadmin {target}.")

@dp.message(Command("revokeadmin"))
async def cmd_revoke_admin(message: Message):
    if OWNER_ID <= 0 or message.from_user.id != OWNER_ID:
        await message.answer("⛔ Только владелец бота может управлять администраторами.")
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /revokeadmin TELEGRAM_ID")
        return
    target = int(parts[1])
    if target == OWNER_ID:
        await message.answer("Нельзя снять права владельца.")
        return
    update_user(target, is_admin_rank=0, rank_title="")
    await message.answer(f"✅ Права администратора сняты у {target}.")


# ==================== ЗАПУСК ====================

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан. Создай новый токен через @BotFather и добавь его в переменные окружения.")
        return
    init_db()
    try:
        me = await bot.get_me()
        logger.info(f"Бот запущен: @{me.username}")
    except Exception as e:
        logger.error(f"Проверь BOT_TOKEN: {e}")
        return
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    # Render требует открытый порт — поднимаем простой health-сервер
    try:
        from aiohttp import web as _web

        async def _health(_request):
            return _web.Response(text="Rubin OK")

        async def _webapp(_request):
            return _web.Response(text=_WEBAPP_HTML, content_type="text/html; charset=utf-8")

        _app = _web.Application()
        _app.router.add_get("/", _health)
        _app.router.add_get("/webapp", _webapp)
        _runner = _web.AppRunner(_app)
        await _runner.setup()
        _port = int(os.getenv("PORT") or 8080)
        await _web.TCPSite(_runner, "0.0.0.0", _port).start()
        logger.info(f"Порт {_port} открыт")
    except Exception as exc:
        logger.warning(f"Веб-сервер: {exc}")

    logger.info("Начинаю polling...")
    # Фоновая задача авто-чеков: пятница 23:00 МСК — всем по 1кк, суббота — всем
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot, skip_updates=True)


_auto_check_last = {"fri": "", "sat": ""}


async def auto_check_loop():
    """Каждые 30 сек проверяет день/время и раздаёт чеки из казны."""
    while True:
        try:
            await _maybe_auto_check()
        except Exception as e:
            logger.error(f"auto_check_loop: {e}")
        await asyncio.sleep(30)


async def _maybe_auto_check():
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo("Europe/Moscow")
    except Exception:
        tz = None
    now_msk = datetime.now(tz) if tz else datetime.utcnow()
    weekday = now_msk.weekday()  # 0=пн ... 4=пт, 5=сб
    day_key = now_msk.strftime("%Y-%m-%d")
    # Пятница 23:00 МСК — всем игрокам по 1кк (1 000 000 RCOIN)
    if weekday == 4 and now_msk.hour == 23 and now_msk.minute == 0:
        if _auto_check_last["fri"] != day_key:
            _auto_check_last["fri"] = day_key
            await _distribute_auto_check(1_000_000)
    # Суббота — всем игрокам (ивент-чек)
    if weekday == 5:
        if _auto_check_last["sat"] != day_key:
            await _distribute_saturday_check()
            _auto_check_last["sat"] = day_key


async def _distribute_auto_check(amount: int):
    """Даёт amount каждому пользователю из казны."""
    users = get_all_users()
    bal_coin, bal_point = get_treasury_balance()
    total = amount * len(users)
    if bal_coin < total:
        logger.warning(f"Авто-чек: в казне недостаточно ({bal_coin} < {total})")
        return
    new_treasury = bal_coin - total
    conn = sqlite3.connect(DB_FILE)
    for uid in users:
        cur = conn.cursor()
        row = cur.execute("SELECT balance_coin FROM users WHERE user_id=?", (uid,)).fetchone()
        if row:
            new_b = (row[0] or 0) + amount
            cur.execute("UPDATE users SET balance_coin=? WHERE user_id=?", (new_b, uid))
    conn.commit()
    conn.close()
    update_treasury(new_treasury, bal_point)
    logger.info(f"Авто-чек {format_number(amount)} RCOIN раздан {len(users)} игрокам. Казна: {format_number(new_treasury)}")


async def _distribute_saturday_check():
    """Суббота: каждому из казны выдаётся ивент-чек-item (сумма) и предмет в инвентарь."""
    users = get_all_users()
    bal_coin, bal_point = get_treasury_balance()
    amount = 500_000
    total = amount * len(users)
    if bal_coin < total:
        logger.warning(f"Субботний чек: в казне недостаточно ({bal_coin})")
        return
    new_treasury = bal_coin - total
    conn = sqlite3.connect(DB_FILE)
    import random
    cur = conn.cursor()
    for uid in users:
        row = cur.execute("SELECT balance_coin, inventory FROM users WHERE user_id=?", (uid,)).fetchone()
        if row:
            new_b = (row[0] or 0) + amount
            inv = []
            try:
                inv = json.loads(row[1] or "[]")
            except Exception:
                pass
            inv.append({"key": f"item_{random.randint(1,9)}", "name": "Субботний сувенир", "qty": 1})
            cur.execute("UPDATE users SET balance_coin=?, inventory=? WHERE user_id=?",
                        (new_b, json.dumps(inv), uid))
    conn.commit()
    conn.close()
    update_treasury(new_treasury, bal_point)
    logger.info(f"Субботний чек раздан {len(users)} игрокам. Казна: {format_number(new_treasury)}")


@dp.message(F.text.startswith("/"))
async def unknown_command(message: Message):
    """Give a useful answer for commands this bot does not implement."""
    command = (message.text or "").split()[0]
    await message.answer(
        f"Команда <code>{command}</code> не найдена.\n\n"
        "Открой /start или /menu — там есть доступные разделы. "
        "Для списка возможностей используй /помощь."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
