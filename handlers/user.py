from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from config import ADMIN_IDS, SHOP_NAME
from database import Database
from keyboards import (
    main_menu_kb, gifts_catalog_kb,
    gift_detail_kb, back_to_catalog_kb
)

router = Router()


def is_admin(user_id: int, db_admins: list) -> bool:
    if user_id in ADMIN_IDS:
        return True
    return any(a["user_id"] == user_id for a in db_admins)


# ──────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user = message.from_user
    await db.get_or_create_user(user.id, user.username or "", user.full_name)

    if await db.is_banned(user.id):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return

    admins = await db.get_admins()
    admin_btn = "\n\n🔐 <b>Ты администратор</b> — напиши /admin" if is_admin(user.id, admins) else ""

    await message.answer(
        f"👋 Добро пожаловать в <b>{SHOP_NAME}</b>!\n\n"
        f"Здесь ты можешь купить эксклюзивные подарки за Telegram Stars ⭐\n"
        f"Выбери действие в меню ниже 👇{admin_btn}",
        reply_markup=main_menu_kb()
    )


# ──────────────────────────────────────────────
#  Каталог
# ──────────────────────────────────────────────
@router.message(F.text == "🛍 Каталог")
async def catalog_menu(message: Message, db: Database):
    if await db.is_banned(message.from_user.id):
        return
    gifts = await db.get_gifts()
    if not gifts:
        await message.answer("😔 Сейчас нет доступных подарков. Загляни позже!")
        return
    await message.answer(
        "🎁 <b>Каталог подарков</b>\n\nВыбери подарок:",
        reply_markup=gifts_catalog_kb(gifts)
    )


@router.callback_query(F.data == "catalog")
async def catalog_callback(call: CallbackQuery, db: Database):
    gifts = await db.get_gifts()
    if not gifts:
        await call.message.edit_text("😔 Нет доступных подарков.")
        return
    await call.message.edit_text(
        "🎁 <b>Каталог подарков</b>\n\nВыбери подарок:",
        reply_markup=gifts_catalog_kb(gifts)
    )


@router.callback_query(F.data.startswith("gift:"))
async def gift_detail(call: CallbackQuery, db: Database):
    gift_id = int(call.data.split(":")[1])
    gift = await db.get_gift(gift_id)
    if not gift:
        await call.answer("Подарок не найден!", show_alert=True)
        return

    stock_text = "∞ Неограниченно" if gift["stock"] == -1 else f"{gift['stock']} шт."
    text = (
        f"{gift['emoji']} <b>{gift['name']}</b>\n\n"
        f"📄 {gift['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{gift['price']} ⭐</b>\n"
        f"📦 В наличии: {stock_text}"
    )

    if gift["photo_id"]:
        await call.message.delete()
        await call.message.answer_photo(
            photo=gift["photo_id"],
            caption=text,
            reply_markup=gift_detail_kb(gift_id)
        )
    else:
        await call.message.edit_text(text, reply_markup=gift_detail_kb(gift_id))


# ──────────────────────────────────────────────
#  Мои покупки
# ──────────────────────────────────────────────
@router.message(F.text == "📦 Мои покупки")
async def my_orders(message: Message, db: Database):
    if await db.is_banned(message.from_user.id):
        return
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("📭 У тебя пока нет покупок.")
        return

    lines = ["📦 <b>Твои покупки:</b>\n"]
    for o in orders:
        date = o["created_at"][:10]
        lines.append(f"  {o['emoji']} {o['gift_name']} — {o['amount']}⭐ | {date}")

    await message.answer("\n".join(lines))


# ──────────────────────────────────────────────
#  О магазине
# ──────────────────────────────────────────────
@router.message(F.text == "ℹ️ О магазине")
async def about_shop(message: Message):
    await message.answer(
        f"<b>{SHOP_NAME}</b>\n\n"
        "🌟 Мы продаём уникальные цифровые подарки за Telegram Stars.\n"
        "⭐ Telegram Stars — официальная валюта Telegram.\n"
        "🔒 Все платежи защищены платформой Telegram.\n\n"
        "По вопросам нажми «📞 Поддержка»"
    )


# ──────────────────────────────────────────────
#  Поддержка
# ──────────────────────────────────────────────
@router.message(F.text == "📞 Поддержка")
async def support(message: Message):
    await message.answer(
        "📞 <b>Поддержка</b>\n\n"
        "Если у тебя возникли проблемы с покупкой или вопросы — "
        "напиши нам и мы поможем!\n\n"
        "📧 Контакт: @your_support_username"
    )
