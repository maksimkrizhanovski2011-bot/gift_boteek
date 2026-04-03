from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message,
    LabeledPrice, PreCheckoutQuery
)

from database import Database
from keyboards import back_to_catalog_kb

router = Router()


# ──────────────────────────────────────────────
#  Инициация покупки
# ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("buy:"))
async def buy_gift(call: CallbackQuery, bot: Bot, db: Database):
    if await db.is_banned(call.from_user.id):
        await call.answer("Вы заблокированы.", show_alert=True)
        return

    gift_id = int(call.data.split(":")[1])
    gift = await db.get_gift(gift_id)

    if not gift or not gift["is_active"]:
        await call.answer("❌ Подарок недоступен!", show_alert=True)
        return

    if gift["stock"] == 0:
        await call.answer("😔 Подарок закончился!", show_alert=True)
        return

    # Создаём pending-заказ
    order_id = await db.create_order(call.from_user.id, gift_id, gift["price"])

    # Отправляем инвойс со Stars
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"{gift['emoji']} {gift['name']}",
        description=gift["description"] or f"Покупка подарка «{gift['name']}»",
        payload=f"order:{order_id}:{gift_id}",
        currency="XTR",                   # Telegram Stars
        prices=[LabeledPrice(label=gift["name"], amount=gift["price"])],
        # provider_token="" — для Stars не нужен
    )
    await call.answer()


# ──────────────────────────────────────────────
#  Pre-checkout (обязательное подтверждение)
# ──────────────────────────────────────────────
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, db: Database):
    parts = query.invoice_payload.split(":")
    # payload = "order:{order_id}:{gift_id}"
    if len(parts) != 3 or parts[0] != "order":
        await query.answer(ok=False, error_message="Неверный заказ.")
        return

    gift_id = int(parts[2])
    gift = await db.get_gift(gift_id)
    if not gift or not gift["is_active"] or gift["stock"] == 0:
        await query.answer(ok=False, error_message="Товар больше недоступен.")
        return

    await query.answer(ok=True)


# ──────────────────────────────────────────────
#  Успешная оплата
# ──────────────────────────────────────────────
@router.message(F.successful_payment)
async def successful_payment(message: Message, db: Database):
    payment = message.successful_payment
    parts = payment.invoice_payload.split(":")
    order_id = int(parts[1])
    gift_id = int(parts[2])

    await db.complete_order(order_id, payment.telegram_payment_charge_id)

    gift = await db.get_gift(gift_id)
    if gift and gift["stock"] > 0:
        await db.decrease_stock(gift_id)

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"{gift['emoji']} <b>{gift['name']}</b> теперь твой!\n\n"
        f"🆔 Номер заказа: <code>#{order_id}</code>\n"
        f"💳 ID платежа: <code>{payment.telegram_payment_charge_id}</code>\n\n"
        f"Спасибо за покупку! 🎉",
        reply_markup=back_to_catalog_kb()
    )
