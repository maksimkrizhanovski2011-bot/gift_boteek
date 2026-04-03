from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import Database
from keyboards import (
    admin_main_kb, admin_gifts_kb, admin_gift_manage_kb,
    admin_gift_edit_kb, admin_users_kb, admin_user_manage_kb,
    admin_admins_kb, confirm_kb, cancel_kb, main_menu_kb
)

router = Router()


# ══════════════════════════════════════════════
#  FSM States
# ══════════════════════════════════════════════
class AddGift(StatesGroup):
    name = State()
    description = State()
    price = State()
    emoji = State()
    stock = State()
    photo = State()


class EditGift(StatesGroup):
    waiting = State()


class Broadcast(StatesGroup):
    message = State()


class FindUser(StatesGroup):
    waiting = State()


class AddAdmin(StatesGroup):
    waiting = State()


# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════
async def check_admin(user_id: int, db: Database) -> bool:
    if user_id in ADMIN_IDS:
        return True
    return await db.is_admin_db(user_id)


def cancel_check(text: str) -> bool:
    return text == "❌ Отмена"


# ══════════════════════════════════════════════
#  Entry / Exit
# ══════════════════════════════════════════════
@router.message(Command("admin"))
async def admin_panel(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        await message.answer("⛔ Нет доступа.")
        return
    stats = await db.get_stats()
    await message.answer(
        f"👮 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"🛍 Заказов: {stats['total_orders']}\n"
        f"⭐ Выручка: {stats['total_revenue']} Stars\n"
        f"🎁 Активных товаров: {stats['active_gifts']}",
        reply_markup=admin_main_kb()
    )


@router.message(F.text == "🔙 Выход из админки")
async def exit_admin(message: Message):
    await message.answer("Вышел из админ-панели.", reply_markup=main_menu_kb())


# ══════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════
@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 <b>Статистика магазина</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"🚫 Заблокировано: <b>{stats['banned']}</b>\n"
        f"✅ Выполнено заказов: <b>{stats['total_orders']}</b>\n"
        f"⭐ Общая выручка: <b>{stats['total_revenue']} Stars</b>\n"
        f"🎁 Активных товаров: <b>{stats['active_gifts']}</b>"
    )


# ══════════════════════════════════════════════
#  ORDERS
# ══════════════════════════════════════════════
@router.message(F.text == "📋 Заказы")
async def admin_orders(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    orders = await db.get_all_orders(30)
    if not orders:
        await message.answer("Заказов нет.")
        return
    lines = ["📋 <b>Последние 30 заказов:</b>\n"]
    for o in orders:
        name = o["username"] or o["full_name"] or str(o["user_id"])
        lines.append(f"#{o['id']} | {o['emoji']}{o['gift_name']} | {o['amount']}⭐ | @{name}")
    await message.answer("\n".join(lines))


# ══════════════════════════════════════════════
#  GIFTS
# ══════════════════════════════════════════════
@router.message(F.text == "📦 Товары")
async def admin_gifts(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    gifts = await db.get_gifts(only_active=False)
    if not gifts:
        await message.answer(
            "🎁 Товаров нет. Добавь первый!",
            reply_markup=admin_gifts_kb([])
        )
        return
    await message.answer("🎁 <b>Все товары:</b>", reply_markup=admin_gifts_kb(gifts))


@router.callback_query(F.data == "admgift_list")
async def admgift_list(call: CallbackQuery, db: Database):
    gifts = await db.get_gifts(only_active=False)
    await call.message.edit_text("🎁 <b>Все товары:</b>", reply_markup=admin_gifts_kb(gifts))


@router.callback_query(F.data.startswith("admgift:"))
async def admgift_detail(call: CallbackQuery, db: Database):
    raw = call.data.split(":")[1]
    if raw == "add":
        await call.message.edit_text(
            "➕ <b>Добавление подарка</b>\n\nВведи название подарка:",
        )
        await call.message.answer("Введи название:", reply_markup=cancel_kb())
        await call.answer()
        # Запускаем FSM через отдельный хендлер ниже — сигнализируем через callback
        return
    gift_id = int(raw)
    gift = await db.get_gift(gift_id)
    if not gift:
        await call.answer("Не найдено", show_alert=True)
        return
    stock_text = "∞" if gift["stock"] == -1 else str(gift["stock"])
    status = "✅ Активен" if gift["is_active"] else "❌ Неактивен"
    text = (
        f"{gift['emoji']} <b>{gift['name']}</b>\n\n"
        f"📄 {gift['description'] or '—'}\n"
        f"💰 Цена: {gift['price']}⭐\n"
        f"📦 Остаток: {stock_text}\n"
        f"Статус: {status}"
    )
    await call.message.edit_text(text, reply_markup=admin_gift_manage_kb(gift_id, gift["is_active"]))


# Toggle active
@router.callback_query(F.data.startswith("admgift_toggle:"))
async def admgift_toggle(call: CallbackQuery, db: Database):
    gift_id = int(call.data.split(":")[1])
    gift = await db.get_gift(gift_id)
    new_val = 0 if gift["is_active"] else 1
    await db.update_gift(gift_id, is_active=new_val)
    await call.answer("Статус изменён!", show_alert=True)
    # refresh
    gift = await db.get_gift(gift_id)
    stock_text = "∞" if gift["stock"] == -1 else str(gift["stock"])
    status = "✅ Активен" if gift["is_active"] else "❌ Неактивен"
    text = (
        f"{gift['emoji']} <b>{gift['name']}</b>\n\n"
        f"📄 {gift['description'] or '—'}\n"
        f"💰 Цена: {gift['price']}⭐\n"
        f"📦 Остаток: {stock_text}\n"
        f"Статус: {status}"
    )
    await call.message.edit_text(text, reply_markup=admin_gift_manage_kb(gift_id, gift["is_active"]))


# Delete gift
@router.callback_query(F.data.startswith("admgift_del:"))
async def admgift_del_confirm(call: CallbackQuery):
    gift_id = call.data.split(":")[1]
    await call.message.edit_text(
        "⚠️ Удалить товар? Это действие нельзя отменить.",
        reply_markup=confirm_kb(f"delgift:{gift_id}")
    )


@router.callback_query(F.data == "confirm:cancel")
async def confirm_cancel(call: CallbackQuery):
    await call.message.edit_text("Действие отменено.")


@router.callback_query(F.data.startswith("confirm:delgift:"))
async def do_delete_gift(call: CallbackQuery, db: Database):
    gift_id = int(call.data.split(":")[2])
    await db.delete_gift(gift_id)
    await call.message.edit_text("🗑 Товар удалён.")


# ── EDIT GIFT FIELD ───────────────────────────
@router.callback_query(F.data.startswith("admgift_edit:"))
async def admgift_edit_menu(call: CallbackQuery, db: Database):
    gift_id = int(call.data.split(":")[1])
    gift = await db.get_gift(gift_id)
    await call.message.edit_text(
        f"✏️ Редактирование: <b>{gift['name']}</b>\nЧто изменить?",
        reply_markup=admin_gift_edit_kb(gift_id)
    )


FIELD_NAMES = {
    "name": "название",
    "description": "описание",
    "price": "цену (число)",
    "emoji": "эмодзи",
    "stock": "остаток (-1 = безлимит)",
    "photo": "фото (отправь фото или 'убрать')",
}


@router.callback_query(F.data.startswith("admgift_field:"))
async def admgift_field(call: CallbackQuery, state: FSMContext):
    _, gift_id, field = call.data.split(":")
    await state.set_state(EditGift.waiting)
    await state.update_data(gift_id=int(gift_id), field=field)
    await call.message.answer(
        f"Введи новое {FIELD_NAMES.get(field, field)}:",
        reply_markup=cancel_kb()
    )
    await call.answer()


@router.message(EditGift.waiting)
async def process_edit_gift(message: Message, state: FSMContext, db: Database):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    data = await state.get_data()
    gift_id = data["gift_id"]
    field = data["field"]

    if field == "photo":
        if message.photo:
            await db.update_gift(gift_id, photo_id=message.photo[-1].file_id)
        elif (message.text or "").lower() == "убрать":
            await db.update_gift(gift_id, photo_id=None)
        else:
            await message.answer("Отправь фото или напиши 'убрать'.")
            return
    elif field == "price":
        try:
            val = int(message.text)
            if val <= 0:
                raise ValueError
            await db.update_gift(gift_id, price=val)
        except ValueError:
            await message.answer("Введи корректное число больше 0.")
            return
    elif field == "stock":
        try:
            val = int(message.text)
            await db.update_gift(gift_id, stock=val)
        except ValueError:
            await message.answer("Введи число (-1 = безлимит).")
            return
    else:
        await db.update_gift(gift_id, **{field: message.text})

    await state.clear()
    await message.answer("✅ Обновлено!", reply_markup=admin_main_kb())


# ── ADD GIFT FSM ──────────────────────────────
@router.callback_query(F.data == "admgift:add")
async def start_add_gift(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddGift.name)
    await call.message.answer("➕ <b>Добавление нового подарка</b>\n\nВведи название:", reply_markup=cancel_kb())
    await call.answer()


@router.message(AddGift.name)
async def add_gift_name(message: Message, state: FSMContext):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    await state.update_data(name=message.text)
    await state.set_state(AddGift.description)
    await message.answer("Введи описание (или '-' чтобы пропустить):")


@router.message(AddGift.description)
async def add_gift_desc(message: Message, state: FSMContext):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    desc = None if message.text == "-" else message.text
    await state.update_data(description=desc)
    await state.set_state(AddGift.price)
    await message.answer("Введи цену в Stars (только число):")


@router.message(AddGift.price)
async def add_gift_price(message: Message, state: FSMContext):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректное число больше 0.")
        return
    await state.update_data(price=price)
    await state.set_state(AddGift.emoji)
    await message.answer("Введи эмодзи для товара (например 🎁):")


@router.message(AddGift.emoji)
async def add_gift_emoji(message: Message, state: FSMContext):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    await state.update_data(emoji=message.text.strip())
    await state.set_state(AddGift.stock)
    await message.answer("Введи количество в наличии (-1 = безлимитно):")


@router.message(AddGift.stock)
async def add_gift_stock(message: Message, state: FSMContext):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    try:
        stock = int(message.text)
    except ValueError:
        await message.answer("Введи число.")
        return
    await state.update_data(stock=stock)
    await state.set_state(AddGift.photo)
    await message.answer("Отправь фото подарка или напиши '-' чтобы пропустить:")


@router.message(AddGift.photo)
async def add_gift_photo(message: Message, state: FSMContext, db: Database):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    data = await state.get_data()
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    gift_id = await db.add_gift(
        name=data["name"],
        description=data.get("description"),
        price=data["price"],
        emoji=data["emoji"],
        photo_id=photo_id,
        stock=data["stock"]
    )
    await state.clear()
    await message.answer(
        f"✅ Подарок <b>{data['name']}</b> добавлен! ID: #{gift_id}",
        reply_markup=admin_main_kb()
    )


# ══════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════
@router.message(F.text == "👥 Пользователи")
async def admin_users(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    users = await db.get_all_users()
    await message.answer(
        f"👥 <b>Пользователи</b>\n\nВсего: {len(users)}",
        reply_markup=admin_users_kb()
    )


@router.callback_query(F.data == "adm_users_menu")
async def adm_users_menu(call: CallbackQuery, db: Database):
    users = await db.get_all_users()
    await call.message.edit_text(
        f"👥 <b>Пользователи</b>\n\nВсего: {len(users)}",
        reply_markup=admin_users_kb()
    )


@router.callback_query(F.data == "adm_all_users")
async def adm_all_users(call: CallbackQuery, db: Database):
    users = await db.get_all_users()
    lines = ["👥 <b>Все пользователи:</b>\n"]
    for u in users[:50]:
        uname = f"@{u['username']}" if u["username"] else u["full_name"]
        lines.append(f"• {uname} | ID: <code>{u['user_id']}</code>")
    if len(users) > 50:
        lines.append(f"\n...и ещё {len(users) - 50}")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_users_kb())


@router.callback_query(F.data == "adm_find_user")
async def adm_find_user_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(FindUser.waiting)
    await call.message.answer("Введи ID или @username пользователя:", reply_markup=cancel_kb())
    await call.answer()


@router.message(FindUser.waiting)
async def adm_find_user_process(message: Message, state: FSMContext, db: Database):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    text = message.text.strip().lstrip("@")
    # try ID
    user = None
    if text.isdigit():
        user = await db.get_user(int(text))
    if not user:
        # search by username
        async with __import__("aiosqlite").connect(db.db_path) as conn:
            conn.row_factory = __import__("aiosqlite").Row
            async with conn.execute(
                "SELECT * FROM users WHERE username=?", (text,)
            ) as cur:
                user = await cur.fetchone()
    await state.clear()
    if not user:
        await message.answer("Пользователь не найден.", reply_markup=admin_main_kb())
        return
    banned = bool(user["is_banned"])
    uname = f"@{user['username']}" if user["username"] else "—"
    await message.answer(
        f"👤 <b>{user['full_name']}</b>\n"
        f"Username: {uname}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Статус: {'🚫 Забанен' if banned else '✅ Активен'}",
        reply_markup=admin_user_manage_kb(user["user_id"], banned)
    )


@router.callback_query(F.data.startswith("adm_ban:"))
async def adm_ban_toggle(call: CallbackQuery, db: Database):
    _, user_id, was_banned = call.data.split(":")
    user_id = int(user_id)
    was_banned = bool(int(was_banned))
    if was_banned:
        await db.unban_user(user_id)
        await call.answer("Пользователь разбанен.", show_alert=True)
    else:
        await db.ban_user(user_id)
        await call.answer("Пользователь заблокирован.", show_alert=True)
    user = await db.get_user(user_id)
    banned = bool(user["is_banned"])
    uname = f"@{user['username']}" if user["username"] else "—"
    await call.message.edit_text(
        f"👤 <b>{user['full_name']}</b>\n"
        f"Username: {uname}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Статус: {'🚫 Забанен' if banned else '✅ Активен'}",
        reply_markup=admin_user_manage_kb(user_id, banned)
    )


@router.callback_query(F.data.startswith("adm_user_orders:"))
async def adm_user_orders(call: CallbackQuery, db: Database):
    user_id = int(call.data.split(":")[1])
    orders = await db.get_user_orders(user_id)
    if not orders:
        await call.answer("У пользователя нет заказов.", show_alert=True)
        return
    lines = [f"📦 <b>Заказы пользователя {user_id}:</b>\n"]
    for o in orders:
        lines.append(f"#{o['id']} {o['emoji']}{o['gift_name']} — {o['amount']}⭐ | {o['created_at'][:10]}")
    await call.message.edit_text("\n".join(lines))


# ══════════════════════════════════════════════
#  ADMINS MANAGEMENT
# ══════════════════════════════════════════════
@router.message(F.text == "👮 Администраторы")
async def admin_admins(message: Message, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    admins = await db.get_admins()
    lines = ["👮 <b>Администраторы:</b>\n"]
    for a in admins:
        lines.append(f"• ID: <code>{a['user_id']}</code>")
    for rid in ADMIN_IDS:
        lines.append(f"• ID: <code>{rid}</code> (root)")
    await message.answer(
        "\n".join(lines),
        reply_markup=admin_admins_kb(admins, ADMIN_IDS)
    )


@router.callback_query(F.data == "adm_addadmin")
async def adm_addadmin_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddAdmin.waiting)
    await call.message.answer("Введи ID нового администратора:", reply_markup=cancel_kb())
    await call.answer()


@router.message(AddAdmin.waiting)
async def adm_addadmin_process(message: Message, state: FSMContext, db: Database):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return
    if not message.text.isdigit():
        await message.answer("Введи числовой ID.")
        return
    new_id = int(message.text)
    await db.add_admin(new_id, message.from_user.id)
    await state.clear()
    await message.answer(f"✅ Пользователь {new_id} добавлен как администратор.", reply_markup=admin_main_kb())


@router.callback_query(F.data.startswith("adm_deladmin:"))
async def adm_deladmin(call: CallbackQuery, db: Database):
    user_id = int(call.data.split(":")[1])
    await db.remove_admin(user_id)
    await call.answer(f"Администратор {user_id} удалён.", show_alert=True)
    admins = await db.get_admins()
    lines = ["👮 <b>Администраторы:</b>\n"]
    for a in admins:
        lines.append(f"• ID: <code>{a['user_id']}</code>")
    for rid in ADMIN_IDS:
        lines.append(f"• ID: <code>{rid}</code> (root)")
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_admins_kb(admins, ADMIN_IDS)
    )


# ══════════════════════════════════════════════
#  BROADCAST
# ══════════════════════════════════════════════
@router.message(F.text == "📣 Рассылка")
async def broadcast_start(message: Message, state: FSMContext, db: Database):
    if not await check_admin(message.from_user.id, db):
        return
    await state.set_state(Broadcast.message)
    await message.answer(
        "📣 Введи текст рассылки (поддерживается HTML).\n"
        "Все пользователи получат это сообщение.\n\n"
        "Напиши ❌ Отмена чтобы отменить.",
        reply_markup=cancel_kb()
    )


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext, db: Database, bot: Bot):
    if cancel_check(message.text or ""):
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return

    await state.clear()
    users = await db.get_all_users()
    sent = 0
    failed = 0
    status_msg = await message.answer(f"⏳ Отправка... 0/{len(users)}")

    for i, user in enumerate(users):
        try:
            await bot.send_message(user["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ Отправка... {i+1}/{len(users)}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📬 Доставлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )
    await message.answer("Готово.", reply_markup=admin_main_kb())
