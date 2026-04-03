from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════════════════════════════════════
#  USER keyboards
# ══════════════════════════════════════════════

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="📦 Мои покупки")],
            [KeyboardButton(text="ℹ️ О магазине"), KeyboardButton(text="📞 Поддержка")],
        ],
        resize_keyboard=True
    )


def gifts_catalog_kb(gifts):
    builder = InlineKeyboardBuilder()
    for g in gifts:
        stock_label = "" if g["stock"] == -1 else f" [{g['stock']}шт]"
        builder.button(
            text=f"{g['emoji']} {g['name']} — {g['price']}⭐{stock_label}",
            callback_data=f"gift:{g['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


def gift_detail_kb(gift_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Купить за ⭐", callback_data=f"buy:{gift_id}")
    builder.button(text="🔙 Назад", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def back_to_catalog_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К каталогу", callback_data="catalog")
    return builder.as_markup()


# ══════════════════════════════════════════════
#  ADMIN keyboards
# ══════════════════════════════════════════════

def admin_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Товары"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📋 Заказы")],
            [KeyboardButton(text="👮 Администраторы"), KeyboardButton(text="📣 Рассылка")],
            [KeyboardButton(text="🔙 Выход из админки")],
        ],
        resize_keyboard=True
    )


def admin_gifts_kb(gifts):
    builder = InlineKeyboardBuilder()
    for g in gifts:
        status = "✅" if g["is_active"] else "❌"
        builder.button(
            text=f"{status} {g['emoji']} {g['name']} ({g['price']}⭐)",
            callback_data=f"admgift:{g['id']}"
        )
    builder.button(text="➕ Добавить подарок", callback_data="admgift:add")
    builder.adjust(1)
    return builder.as_markup()


def admin_gift_manage_kb(gift_id: int, is_active: int):
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Деактивировать" if is_active else "✅ Активировать"
    builder.button(text="✏️ Редактировать", callback_data=f"admgift_edit:{gift_id}")
    builder.button(text=toggle_label, callback_data=f"admgift_toggle:{gift_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admgift_del:{gift_id}")
    builder.button(text="🔙 Назад", callback_data="admgift_list")
    builder.adjust(2)
    return builder.as_markup()


def admin_gift_edit_kb(gift_id: int):
    builder = InlineKeyboardBuilder()
    for field, label in [
        ("name", "📝 Название"),
        ("description", "📄 Описание"),
        ("price", "💰 Цену"),
        ("emoji", "😀 Эмодзи"),
        ("stock", "📦 Остаток"),
        ("photo", "🖼 Фото"),
    ]:
        builder.button(text=label, callback_data=f"admgift_field:{gift_id}:{field}")
    builder.button(text="🔙 Назад", callback_data=f"admgift:{gift_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_users_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти пользователя", callback_data="adm_find_user")
    builder.button(text="📋 Все пользователи", callback_data="adm_all_users")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_manage_kb(user_id: int, is_banned: bool):
    builder = InlineKeyboardBuilder()
    ban_label = "✅ Разбанить" if is_banned else "🚫 Забанить"
    builder.button(text=ban_label, callback_data=f"adm_ban:{user_id}:{int(is_banned)}")
    builder.button(text="📦 Покупки юзера", callback_data=f"adm_user_orders:{user_id}")
    builder.button(text="🔙 Назад", callback_data="adm_users_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_admins_kb(admins, root_admin_ids):
    builder = InlineKeyboardBuilder()
    for a in admins:
        if a["user_id"] not in root_admin_ids:
            builder.button(
                text=f"❌ Удалить {a['user_id']}",
                callback_data=f"adm_deladmin:{a['user_id']}"
            )
    builder.button(text="➕ Добавить админа", callback_data="adm_addadmin")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(action: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"confirm:{action}")
    builder.button(text="❌ Нет", callback_data="confirm:cancel")
    builder.adjust(2)
    return builder.as_markup()


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
