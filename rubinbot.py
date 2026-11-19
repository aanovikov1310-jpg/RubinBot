#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR-Gram Exchange — single-file Telegram exchange request manager.

Important integration boundary:
* Receipt IDs are NOT cryptographically verified by this program.
* Gram / Iris payouts are NOT sent automatically.
* The supplied Gram URL is a privacy policy; the Iris URL is a chat-manager
  command catalogue. Neither is a verified payment API.
* Therefore receipt verification and payout confirmation are administrator-
  mediated. The bot never marks a payout successful without an explicit
  administrator-entered external confirmation reference.

Python: 3.12+
Install:
    pip install "aiogram>=3.13,<4" "aiosqlite>=0.20"
Optional Telethon is deliberately not used to automate third-party bots.
Do not share Telegram login codes, 2FA passwords, or session files.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# No .env file is required. If variables are not supplied by the hosting
# environment, the bot asks for the token and owner ID in the terminal.
BOT_TOKEN = os.getenv("BOT_TOKEN", "9035207246:AAEFgAbIUUMwrF9SKME774tRM_Kzi8CjKE0").strip()
if not BOT_TOKEN:
    BOT_TOKEN = input("Введите токен Telegram-бота: ").strip()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "5257618084").strip()
if not ADMIN_ID_RAW:
    ADMIN_ID_RAW = input("Введите Telegram ID владельца: ").strip()

DB_PATH = os.getenv("DB_PATH", "exchange.db").strip() or "exchange.db"
RATE_RAW = os.getenv("EXCHANGE_RATE", "0.38").strip()

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 0

try:
    START_RATE = Decimal(RATE_RAW)
    if not START_RATE.is_finite() or START_RATE <= 0:
        raise ValueError
except (InvalidOperation, ValueError):
    START_RATE = Decimal("0.38")

if not BOT_TOKEN or not ADMIN_ID:
    raise SystemExit("Нужны корректные BOT_TOKEN и ADMIN_ID.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("exchange.log", encoding="utf-8")],
)
log = logging.getLogger("prgram_exchange")

dp = Dispatcher()
db: Optional[aiosqlite.Connection] = None
db_lock = asyncio.Lock()
user_flow: dict[int, str] = {}
rate_limits: dict[int, float] = {}
RATE_LIMIT_SECONDS = 2.0

STATUS_WAIT_RECEIPT = "Ожидание чека"
STATUS_REVIEW = "Проверка"
STATUS_ACTIVATION = "Активация"
STATUS_WAIT_PAYOUT = "Ожидание выплаты"
STATUS_PAYOUT = "Выплата"
STATUS_SUCCESS = "Успешно"
STATUS_ERROR = "Ошибка"

USER_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💚 Начать обмен", callback_data="exchange:start")],
    [
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="📜 История", callback_data="history"),
    ],
    [
        InlineKeyboardButton(text="📈 Курс", callback_data="rate"),
        InlineKeyboardButton(text="ℹ️ Информация", callback_data="about"),
    ],
])

CURRENCY_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="💎 Получить Gram", callback_data="currency:gram"),
        InlineKeyboardButton(text="🍬 Получить Ириски", callback_data="currency:iris"),
    ],
    [InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")],
])


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt_decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001")).normalize(), "f")


def parse_positive_decimal(raw: str) -> Decimal:
    value = Decimal(raw.replace(",", "."))
    if not value.is_finite() or value <= 0:
        raise ValueError("Значение должно быть положительным.")
    return value


async def require_db() -> aiosqlite.Connection:
    if db is None:
        raise RuntimeError("Database is not initialized")
    return db


async def init_db() -> None:
    global db
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        created_at TEXT NOT NULL,
        last_seen TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS operations (
        id TEXT PRIMARY KEY,
        receipt_id TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        prgram_amount TEXT,
        rate TEXT,
        payout_amount TEXT,
        currency TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        payout_reference TEXT,
        admin_note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );
    CREATE INDEX IF NOT EXISTS idx_ops_user ON operations(user_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_ops_status ON operations(status, created_at);
    CREATE TABLE IF NOT EXISTS callback_events (
        callback_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        context TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('rate',?)", (str(START_RATE),))
    await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('enabled','1')")
    await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('maintenance','0')")
    await db.commit()


async def audit(actor_id: int, action: str, details: str = "") -> None:
    conn = await require_db()
    await conn.execute(
        "INSERT INTO audit_log(actor_id,action,details,created_at) VALUES(?,?,?,?)",
        (actor_id, action, details[:1500], now_iso()),
    )
    await conn.commit()


async def log_error(context: str, exc: object) -> None:
    details = repr(exc)[:3000]
    log.exception("%s: %s", context, details)
    try:
        conn = await require_db()
        await conn.execute(
            "INSERT INTO errors(context,details,created_at) VALUES(?,?,?)",
            (context[:200], details, now_iso()),
        )
        await conn.commit()
    except Exception:
        log.exception("Could not save error to database")


async def setting(key: str, default: str = "") -> str:
    conn = await require_db()
    cur = await conn.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else default


async def set_setting(key: str, value: str) -> None:
    conn = await require_db()
    await conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    await conn.commit()


async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def touch_user(message: Message) -> None:
    conn = await require_db()
    u = message.from_user
    if not u:
        return
    await conn.execute(
        """INSERT INTO users(user_id,username,full_name,created_at,last_seen)
        VALUES(?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          username=excluded.username, full_name=excluded.full_name,
          last_seen=excluded.last_seen""",
        (u.id, u.username, u.full_name[:250], now_iso(), now_iso()),
    )
    await conn.commit()


async def limited(user_id: int) -> bool:
    now = time.monotonic()
    previous = rate_limits.get(user_id, 0.0)
    if now - previous < RATE_LIMIT_SECONDS:
        return True
    rate_limits[user_id] = now
    return False


async def system_open() -> tuple[bool, str]:
    if await setting("maintenance", "0") == "1":
        return False, "Технический перерыв. Попробуйте позже."
    if await setting("enabled", "1") != "1":
        return False, "Приём новых заявок временно отключён."
    return True, ""


async def send_admin(bot: Bot, text: str, markup: Optional[InlineKeyboardMarkup] = None) -> None:
    try:
        await bot.send_message(ADMIN_ID, text, reply_markup=markup)
    except Exception as exc:
        await log_error("admin notification", exc)


def currency_keyboard(op_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 Получить Gram", callback_data=f"currency:gram:{op_id}"),
            InlineKeyboardButton(text="🍬 Получить Ириски", callback_data=f"currency:iris:{op_id}"),
        ],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")],
    ])


def operation_admin_kb(op_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Чек подтверждён", callback_data=f"adm:approve:{op_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm:reject:{op_id}"),
        ]
    ])


def operation_user_text(row: aiosqlite.Row) -> str:
    return (
        f"🧾 <b>Заявка #{esc(row['id'])}</b>\n"
        f"Чек: <code>{esc(row['receipt_id'])}</code>\n"
        f"PR-Gram: <b>{esc(row['prgram_amount'] or '—')}</b>\n"
        f"Курс: <b>{esc(row['rate'] or '—')}</b>\n"
        f"К выплате: <b>{esc(row['payout_amount'] or '—')}</b>\n"
        f"Валюта: <b>{esc(row['currency'] or 'не выбрана')}</b>\n"
        f"Статус: <b>{esc(row['status'])}</b>\n"
        f"Создана: <code>{esc(row['created_at'])}</code>"
    )


async def get_operation(op_id: str):
    conn = await require_db()
    cur = await conn.execute("SELECT * FROM operations WHERE id=?", (op_id,))
    return await cur.fetchone()


async def create_receipt_operation(user_id: int, receipt_id: str) -> tuple[bool, str]:
    """Create a unique request. Receipt authenticity is intentionally manual."""
    conn = await require_db()
    op_id = uuid.uuid4().hex[:10].upper()
    async with db_lock:
        try:
            await conn.execute("BEGIN IMMEDIATE")
            cur = await conn.execute("SELECT id FROM operations WHERE receipt_id=?", (receipt_id,))
            existing = await cur.fetchone()
            if existing:
                await conn.rollback()
                return False, f"Этот ID чека уже зарегистрирован в заявке #{existing['id']}."
            await conn.execute(
                """INSERT INTO operations
                (id,receipt_id,user_id,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?)""",
                (op_id, receipt_id, user_id, STATUS_REVIEW, now_iso(), now_iso()),
            )
            await conn.commit()
            return True, op_id
        except aiosqlite.IntegrityError:
            await conn.rollback()
            return False, "Этот чек уже зарегистрирован."
        except Exception:
            await conn.rollback()
            raise


async def update_status(op_id: str, status: str, note: str = "") -> bool:
    conn = await require_db()
    cur = await conn.execute("SELECT id FROM operations WHERE id=?", (op_id,))
    if not await cur.fetchone():
        return False
    await conn.execute(
        "UPDATE operations SET status=?,admin_note=?,updated_at=? WHERE id=?",
        (status, note[:1000], now_iso(), op_id),
    )
    await conn.commit()
    return True


async def start_exchange(message: Message) -> None:
    opened, reason = await system_open()
    if not opened:
        await message.answer(f"⚠️ {esc(reason)}", reply_markup=USER_MENU)
        return
    user_flow[message.from_user.id] = "receipt"
    await message.answer(
        "💚 <b>Новая заявка на обмен</b>\n\n"
        "Отправьте ID чека PR-Gram отдельным сообщением.\n"
        "Пока чек не проверен оператором, заявка будет иметь статус «Проверка».\n\n"
        "Не отправляйте пароли, коды входа или данные аккаунта.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")]
        ]),
    )


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await touch_user(message)
    await message.answer(
        "💚 <b>PR-GRAM EXCHANGE</b>\n"
        "<i>Обмен заявок PR-Gram на Gram / Ириски</i>\n\n"
        "Выберите нужный раздел:",
        reply_markup=USER_MENU,
    )


@dp.callback_query(F.data == "exchange:start")
async def cb_exchange(call: CallbackQuery) -> None:
    await call.answer()
    opened, reason = await system_open()
    if not opened:
        await call.message.answer(f"⚠️ {esc(reason)}")
        return
    user_flow[call.from_user.id] = "receipt"
    await call.message.answer(
        "💚 <b>Новая заявка</b>\n\nПришлите ID чека PR-Gram одним сообщением.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel")]
        ]),
    )


@dp.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery) -> None:
    user_flow.pop(call.from_user.id, None)
    await call.answer("Действие отменено")
    await call.message.answer("Главное меню:", reply_markup=USER_MENU)


@dp.message(F.text)
async def text_router(message: Message, bot: Bot) -> None:
    await touch_user(message)
    uid = message.from_user.id
    text = (message.text or "").strip()

    if text.startswith(".verify ") and await is_admin(uid):
        parts = text.split()
        if len(parts) == 3:
            await admin_verify(parts[1], parts[2], bot, message)
        else:
            await message.answer("Использование: <code>.verify OP_ID PRGRAM_AMOUNT</code>")
        return
    if text.startswith(".") and await is_admin(uid):
        await admin_command(message, bot, text)
        return

    if await limited(uid):
        await message.answer("⏳ Подождите немного перед следующим запросом.")
        return

    if user_flow.get(uid) == "receipt":
        # Permit opaque receipt tokens, but reject whitespace/control characters.
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,128}", text):
            await message.answer("Некорректный формат ID. Пришлите ID чека без пробелов.")
            return
        ok, result = await create_receipt_operation(uid, text)
        user_flow.pop(uid, None)
        if not ok:
            await message.answer(f"⚠️ {esc(result)}", reply_markup=USER_MENU)
            return
        await message.answer(
            f"🧾 Заявка <code>#{esc(result)}</code> создана.\n"
            "Статус: <b>Проверка</b>.\n\n"
            "Выберите валюту выплаты:",
            reply_markup=currency_keyboard(result),
        )
        await send_admin(
            bot,
            f"🆕 <b>Новая заявка #{esc(result)}</b>\n"
            f"Пользователь: <code>{uid}</code>\n"
            f"Чек: <code>{esc(text)}</code>\n\n"
            "Проверка чека требует подтверждения через официальный источник.",
            operation_admin_kb(result),
        )
        return

    await message.answer("Используйте кнопки меню ниже.", reply_markup=USER_MENU)


@dp.callback_query(F.data.startswith("currency:"))
async def cb_currency(call: CallbackQuery) -> None:
    await call.answer()
    parts = call.data.split(":")
    if len(parts) != 3:
        return
    currency, op_id = parts[1], parts[2]
    if currency not in ("gram", "iris"):
        return
    conn = await require_db()
    cur = await conn.execute(
        "SELECT * FROM operations WHERE id=? AND user_id=? AND currency IS NULL",
        (op_id, call.from_user.id),
    )
    row = await cur.fetchone()
    if not row:
        await call.message.answer("Заявка не найдена или валюта уже выбрана.")
        return
    rate = Decimal(await setting("rate", str(START_RATE)))
    # Amount and rate are frozen only after the receipt is manually verified.
    cur = await conn.execute(
        "UPDATE operations SET currency=?,updated_at=? WHERE id=? AND user_id=? AND currency IS NULL",
        (currency, now_iso(), op_id, call.from_user.id),
    )
    if cur.rowcount != 1:
        await conn.rollback()
        await call.message.answer("Валюта уже выбрана. Откройте историю заявок.")
        return
    await conn.commit()
    await audit(call.from_user.id, "currency_selected", f"{row['id']}:{currency}")
    await call.message.answer(
        f"Выбрана валюта: <b>{'Gram' if currency == 'gram' else 'Ириски'}</b>.\n"
        "Заявка ожидает проверки чека оператором.\n"
        "Сумма и курс будут зафиксированы после подтверждения чека.",
        reply_markup=USER_MENU,
    )


@dp.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery) -> None:
    await call.answer()
    conn = await require_db()
    cur = await conn.execute("SELECT COUNT(*) AS n FROM operations WHERE user_id=?", (call.from_user.id,))
    total = (await cur.fetchone())["n"]
    cur = await conn.execute(
        "SELECT COUNT(*) AS n FROM operations WHERE user_id=? AND status=?",
        (call.from_user.id, STATUS_SUCCESS),
    )
    success = (await cur.fetchone())["n"]
    cur = await conn.execute("SELECT username,full_name,created_at FROM users WHERE user_id=?", (call.from_user.id,))
    user = await cur.fetchone()
    await call.message.answer(
        "👤 <b>Профиль</b>\n"
        f"ID: <code>{call.from_user.id}</code>\n"
        f"Имя: {esc(user['full_name'] if user else call.from_user.full_name)}\n"
        f"Username: @{esc(user['username'] or 'не указан') if user else 'не указан'}\n"
        f"Всего заявок: <b>{total}</b>\n"
        f"Успешных: <b>{success}</b>",
        reply_markup=USER_MENU,
    )


@dp.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery) -> None:
    await call.answer()
    conn = await require_db()
    cur = await conn.execute(
        "SELECT * FROM operations WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (call.from_user.id,),
    )
    rows = await cur.fetchall()
    if not rows:
        await call.message.answer("📜 История пока пуста.", reply_markup=USER_MENU)
        return
    lines = ["📜 <b>Последние операции</b>"]
    for row in rows:
        lines.append(
            f"\n<code>#{esc(row['id'])}</code> · {esc(row['status'])}\n"
            f"Чек: <code>{esc(row['receipt_id'])}</code> · "
            f"{esc(row['currency'] or 'валюта не выбрана')}"
        )
    await call.message.answer("\n".join(lines), reply_markup=USER_MENU)


@dp.callback_query(F.data == "rate")
async def cb_rate(call: CallbackQuery) -> None:
    await call.answer()
    rate = await setting("rate", str(START_RATE))
    await call.message.answer(
        f"📈 <b>Текущий ориентировочный курс</b>\n"
        f"<code>1 PR-Gram × {esc(rate)}</code>\n\n"
        "Итоговая сумма фиксируется только после ручного подтверждения чека.",
        reply_markup=USER_MENU,
    )


@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(
        "ℹ️ <b>О сервисе</b>\n\n"
        "Бот регистрирует заявки и ведёт историю операций.\n"
        "Проверка чеков и выплаты требуют подтверждения оператором, "
        "поскольку подтверждённые публичные API этих сервисов не настроены.\n"
        "Статус «Успешно» выставляется только после ручного внесения "
        "подтверждения платёжного сервиса.",
        reply_markup=USER_MENU,
    )


async def admin_command(message: Message, bot: Bot, text: str) -> None:
    parts = text.split()
    cmd = parts[0].lower()

    if cmd == ".rate":
        if len(parts) != 2:
            await message.answer("Использование: <code>.rate 0.38</code>")
            return
        try:
            value = parse_positive_decimal(parts[1])
        except Exception:
            await message.answer("Некорректный курс.")
            return
        await set_setting("rate", str(value))
        await audit(ADMIN_ID, "rate_changed", str(value))
        await message.answer(f"✅ Курс обновлён: <b>{esc(value)}</b>")
    elif cmd == ".on":
        await set_setting("enabled", "1")
        await audit(ADMIN_ID, "exchange_enabled")
        await message.answer("✅ Приём заявок включён.")
    elif cmd == ".off":
        await set_setting("enabled", "0")
        await audit(ADMIN_ID, "exchange_disabled")
        await message.answer("⛔ Приём новых заявок выключен.")
    elif cmd == ".maintenance":
        await set_setting("maintenance", "1")
        await audit(ADMIN_ID, "maintenance_on")
        await message.answer("🛠 Технический перерыв включён.")
    elif cmd == ".maintenance_off":
        await set_setting("maintenance", "0")
        await audit(ADMIN_ID, "maintenance_off")
        await message.answer("✅ Технический перерыв завершён.")
    elif cmd == ".stats":
        conn = await require_db()
        cur = await conn.execute("SELECT COUNT(*) n FROM users")
        users = (await cur.fetchone())["n"]
        cur = await conn.execute("SELECT COUNT(*) n FROM operations")
        ops = (await cur.fetchone())["n"]
        cur = await conn.execute("SELECT status,COUNT(*) n FROM operations GROUP BY status")
        statuses = await cur.fetchall()
        body = "\n".join(f"• {esc(r['status'])}: <b>{r['n']}</b>" for r in statuses) or "Нет операций"
        await message.answer(
            f"📊 <b>Статистика</b>\nПользователей: {users}\nЗаявок: {ops}\n{body}"
        )
    elif cmd == ".user":
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Использование: <code>.user ID</code>")
            return
        uid = int(parts[1])
        conn = await require_db()
        cur = await conn.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        u = await cur.fetchone()
        cur = await conn.execute("SELECT COUNT(*) n FROM operations WHERE user_id=?", (uid,))
        count = (await cur.fetchone())["n"]
        if not u:
            await message.answer("Пользователь не найден.")
        else:
            await message.answer(
                f"👤 <b>Пользователь</b>\nID: <code>{uid}</code>\n"
                f"Имя: {esc(u['full_name'])}\nUsername: @{esc(u['username'] or '—')}\n"
                f"Заявок: {count}\nСоздан: <code>{esc(u['created_at'])}</code>"
            )
    elif cmd == ".history":
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Использование: <code>.history ID</code>")
            return
        conn = await require_db()
        cur = await conn.execute(
            "SELECT * FROM operations WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
            (int(parts[1]),),
        )
        rows = await cur.fetchall()
        await message.answer(
            "\n\n".join(operation_user_text(r) for r in rows) if rows else "История пуста."
        )
    elif cmd == ".withdraw":
        conn = await require_db()
        cur = await conn.execute(
            "SELECT * FROM operations WHERE status IN (?,?) ORDER BY created_at",
            (STATUS_WAIT_PAYOUT, STATUS_PAYOUT),
        )
        rows = await cur.fetchall()
        await message.answer(
            "📤 <b>Очередь выплат</b>\n\n" +
            ("\n\n".join(operation_user_text(r) for r in rows) if rows else "Очередь пуста.")
        )
    elif cmd == ".approve":
        if len(parts) != 2:
            await message.answer("Использование: <code>.approve OPERATION_ID</code>")
            return
        await admin_approve(parts[1], bot, message)
    elif cmd == ".reject":
        if len(parts) < 2:
            await message.answer("Использование: <code>.reject OPERATION_ID [причина]</code>")
            return
        await admin_reject(parts[1], " ".join(parts[2:]) or "Чек не подтверждён", bot, message)
    elif cmd == ".paid":
        if len(parts) < 3:
            await message.answer("Использование: <code>.paid OPERATION_ID CONFIRMATION_REFERENCE</code>")
            return
        await admin_paid(parts[1], " ".join(parts[2:]), bot, message)
    elif cmd == ".errors":
        conn = await require_db()
        cur = await conn.execute("SELECT * FROM errors ORDER BY id DESC LIMIT 10")
        rows = await cur.fetchall()
        await message.answer(
            "🧯 <b>Последние ошибки</b>\n\n" +
            ("\n\n".join(f"#{r['id']} {esc(r['context'])}\n<code>{esc(r['details'][:700])}</code>" for r in rows)
             if rows else "Ошибок нет.")
        )
    elif cmd == ".balance":
        await message.answer(
            "Баланс внешних сервисов недоступен: официальные API баланса не подключены. "
            "Не вводите баланс вручную как подтверждённый."
        )
    elif cmd == ".help":
        await message.answer(
            "<b>Команды администратора</b>\n"
            ".rate 0.38 · .stats · .on · .off\n"
            ".user ID · .history ID · .withdraw\n"
            ".maintenance · .maintenance_off · .errors\n"
            ".approve OP_ID · .reject OP_ID [причина]\n"
            ".paid OP_ID CONFIRMATION_REFERENCE · .balance"
        )
    else:
        await message.answer("Неизвестная команда. Напишите <code>.help</code>.")


async def admin_approve(op_id: str, bot: Bot, message: Message) -> None:
    conn = await require_db()
    async with db_lock:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute("SELECT * FROM operations WHERE id=?", (op_id,))
        row = await cur.fetchone()
        if not row:
            await conn.rollback()
            await message.answer("Заявка не найдена.")
            return
        if row["status"] != STATUS_REVIEW:
            await conn.rollback()
            await message.answer(f"Нельзя подтвердить чек из статуса «{esc(row['status'])}».")
            return
        if not row["currency"]:
            await conn.rollback()
            await message.answer("Пользователь ещё не выбрал валюту выплаты.")
            return
        rate = Decimal(await setting("rate", str(START_RATE)))
        # Amount is not available from receipt ID alone; an operator must enter it
        # after verifying the receipt in the original PR-Gram source.
        await conn.rollback()
    await message.answer(
        "Для фиксации суммы используйте:\n"
        "<code>.verify OP_ID PRGRAM_AMOUNT</code>\n"
        "Сначала проверьте чек во внешнем официальном источнике. "
        "Один ID чека сам по себе не доказывает его подлинность."
    )


async def admin_verify(op_id: str, amount_raw: str, bot: Bot, message: Message) -> None:
    try:
        amount = parse_positive_decimal(amount_raw)
    except Exception:
        await message.answer("Некорректная сумма PR-Gram.")
        return
    conn = await require_db()
    async with db_lock:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute("SELECT * FROM operations WHERE id=?", (op_id,))
        row = await cur.fetchone()
        if not row or row["status"] != STATUS_REVIEW or not row["currency"]:
            await conn.rollback()
            await message.answer("Заявка не найдена, уже обработана или валюта не выбрана.")
            return
        rate = Decimal(await setting("rate", str(START_RATE)))
        payout = (amount * rate).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        await conn.execute(
            """UPDATE operations SET prgram_amount=?,rate=?,payout_amount=?,
            status=?,updated_at=?,admin_note=? WHERE id=? AND status=?""",
            (str(amount), str(rate), str(payout), STATUS_WAIT_PAYOUT, now_iso(),
             "Чек проверен оператором; сумма и курс зафиксированы.", op_id, STATUS_REVIEW),
        )
        await conn.commit()
    row = await get_operation(op_id)
    await audit(ADMIN_ID, "receipt_manually_verified", f"{op_id}:{amount}")
    await bot.send_message(
        row["user_id"],
        f"✅ Чек подтверждён оператором.\n\n{operation_user_text(row)}\n\n"
        "Заявка добавлена в очередь выплат. Это ещё не означает, что выплата отправлена."
    )
    await message.answer(f"✅ Чек подтверждён. Заявка #{esc(op_id)} ожидает выплату.")


async def admin_reject(op_id: str, reason: str, bot: Bot, message: Message) -> None:
    row = await get_operation(op_id)
    if not row or row["status"] not in (STATUS_REVIEW, STATUS_WAIT_PAYOUT):
        await message.answer("Заявка не найдена или уже обработана.")
        return
    await update_status(op_id, STATUS_ERROR, reason)
    await audit(ADMIN_ID, "operation_rejected", f"{op_id}:{reason}")
    await bot.send_message(row["user_id"], f"❌ Заявка #{esc(op_id)} отклонена.\nПричина: {esc(reason)}")
    await message.answer("Заявка отклонена.")


async def admin_paid(op_id: str, reference: str, bot: Bot, message: Message) -> None:
    # This is an operator assertion, not a live API confirmation. Require a
    # non-trivial external transaction/reference identifier and audit it.
    if len(reference) < 4 or len(reference) > 200:
        await message.answer("Укажите реальный идентификатор подтверждения платёжного сервиса.")
        return
    conn = await require_db()
    async with db_lock:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute("SELECT * FROM operations WHERE id=?", (op_id,))
        row = await cur.fetchone()
        if not row or row["status"] != STATUS_WAIT_PAYOUT or row["payout_reference"]:
            await conn.rollback()
            await message.answer("Заявка не найдена, выплата уже начата или уже подтверждена.")
            return
        await conn.execute(
            """UPDATE operations SET status=?,payout_reference=?,updated_at=?,
            admin_note=? WHERE id=? AND status=? AND payout_reference IS NULL""",
            (STATUS_SUCCESS, reference, now_iso(), "Подтверждение внесено оператором.", op_id, STATUS_WAIT_PAYOUT),
        )
        await conn.commit()
    await audit(ADMIN_ID, "payout_confirmed_manually", f"{op_id}:{reference}")
    await bot.send_message(
        row["user_id"],
        f"🎉 Выплата по заявке #{esc(op_id)} отмечена подтверждённой оператором.\n"
        f"Референс: <code>{esc(reference)}</code>"
    )
    await message.answer("✅ Подтверждение сохранено, статус «Успешно» установлен.")


@dp.callback_query(F.data.startswith("adm:"))
async def admin_callbacks(call: CallbackQuery, bot: Bot) -> None:
    if call.from_user.id != ADMIN_ID:
        await call.answer("Недостаточно прав", show_alert=True)
        return
    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Некорректный запрос", show_alert=True)
        return
    action, op_id = parts[1], parts[2]
    await call.answer()
    if action == "approve":
        await call.message.answer(
            f"Для ручной проверки заявки #{esc(op_id)}:\n"
            f"<code>.verify {esc(op_id)} PRGRAM_AMOUNT</code>"
        )
    elif action == "reject":
        await admin_reject(op_id, "Отклонено администратором", bot, call.message)


@dp.errors()
async def global_error_handler(event, bot: Bot):
    exc = event.exception
    await log_error("dispatcher", exc)
    return True


async def main() -> None:
    await init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        log.info("Starting @%s (id=%s)", me.username, me.id)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        if db is not None:
            await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Stopped")
