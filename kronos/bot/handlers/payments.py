from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command
from datetime import datetime, timedelta
import json
import aiosqlite
from db.database import DB_PATH
from core.config import settings

router = Router()

PREMIUM_PRICES = {
    "month": {"stars": 150, "months": 1},
    "year": {"stars": 999, "months": 12}
}


async def create_premium_invoice(message: Message, plan: str = "year"):
    """Create premium invoice from WebApp or command"""
    if plan not in PREMIUM_PRICES:
        plan = "year"
    
    price = PREMIUM_PRICES[plan]
    stars = price["stars"]
    months = price["months"]
    
    title = f"MindFlow Pro - {months} месяц(ев)"
    description = (
        f"Premium подписка на {months} месяц(ев)\n\n"
        "• Все темы оформления\n"
        "• Безлимитные теги\n"
        "• AI без ограничений\n"
        "• Расширенная аналитика"
    )
    
    await message.answer_invoice(
        title=title,
        description=description,
        payload=f"premium_{plan}_{message.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Premium {months} мес.", amount=stars)],
        provider_token="",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплатить {stars} звёзд", pay=True)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ])
    )


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 150 звёзд - Месяц", callback_data="buy_month"),
        ],
        [
            InlineKeyboardButton(text="⭐ 999 звёзд - Год (44% скидка)", callback_data="buy_year"),
        ]
    ])
    
    await message.answer(
        "👑 <b>MindFlow Pro</b>\n\n"
        "Преимущества Premium:\n"
        "🎨 Все темы оформления\n"
        "🏷 Безлимитные теги\n"
        "🔔 Напоминания без ограничений\n"
        "🤖 AI без лимитов\n"
        "📊 Расширенная аналитика\n\n"
        "Выберите план подписки:",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    plan = callback.data.split("_")[1]
    
    if plan not in PREMIUM_PRICES:
        await callback.answer("Неверный план")
        return
    
    price = PREMIUM_PRICES[plan]
    stars = price["stars"]
    months = price["months"]
    
    title = f"MindFlow Pro - {months} месяц(ев)"
    description = (
        f"Premium подписка на {months} месяц(ев)\n\n"
        "• Все темы оформления\n"
        "• Безлимитные теги\n"
        "• AI без ограничений\n"
        "• Расширенная аналитика"
    )
    
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=f"premium_{plan}_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Premium {months} мес.", amount=stars)],
        provider_token="",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплатить {stars} звёзд", pay=True)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Отменено")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payment = message.successful_payment
    
    payload = payment.invoice_payload
    
    if payload.startswith("premium_"):
        parts = payload.split("_")
        plan = parts[1]
        user_id = int(parts[2])
        
        price = PREMIUM_PRICES.get(plan, {"months": 1})
        months = price["months"]
        
        until = datetime.now() + timedelta(days=months * 30)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?",
                (until.strftime('%Y-%m-%d'), user_id)
            )
            await db.commit()
        
        await message.answer(
            f"🎉 <b>Premium активирован!</b>\n\n"
            f"Вы получили MindFlow Pro на {months} месяц(ев)!\n"
            f"Действует до: {until.strftime('%d.%m.%Y')}\n\n"
            f"Спасибо за поддержку! ⭐"
        )
    else:
        await message.answer("✅ Оплата прошла успешно!")


@router.callback_query(F.data == "check_premium")
async def check_premium_status(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT is_premium, premium_until FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    
    if row and row['is_premium']:
        until = row['premium_until'] or "Бессрочно"
        await callback.answer(f"✅ Premium активен до: {until}", show_alert=True)
    else:
        await callback.answer("❌ Premium не активен", show_alert=True)
