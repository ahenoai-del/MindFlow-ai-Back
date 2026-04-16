# 📖 Гайд по подключению оплаты Telegram Stars

## Что такое Telegram Stars?

Telegram Stars — это внутренняя валюта Telegram, которую пользователи покупают за рубли/доллары. Разработчики получают 100% от стоимости (Telegram не берёт комиссию).

---

## 1. Включить Stars в @BotFather

1. Открой @BotFather в Telegram
2. Отправь `/mybots`
3. Выбери своего бота: **@MindFl0wAIbot**
4. Нажми **Bot Settings** → **Payments**
5. Выбери **Telegram Stars**
6. Нажми **Enable** (включить)

✅ **Готово!** Бот теперь может принимать оплату звёздами.

---

## 2. Как работает оплата (уже реализовано в коде)

### В боте:
```
/premium → Пользователь выбирает план → Invoice с кнопкой оплаты → Звёзды списываются → Premium активируется
```

### В WebApp:
```
Settings → MindFlow Pro → Выбрать план → Кнопка "Купить за звёзды" → Invoice → Premium активируется
```

---

## 3. Цены в звёздах

| План | Звёзды | USD аналог |
|------|--------|------------|
| 1 месяц | ⭐ 150 | ~$2.99 |
| 1 год | ⭐ 999 | ~$19.99 |

**Курс:** 1 звезда ≈ $0.02

---

## 4. Код оплаты (уже написан)

### Файл: `bot/handlers/payments.py`

```python
from aiogram.types import LabeledPrice

PREMIUM_PRICES = {
    "month": {"stars": 150, "months": 1},
    "year": {"stars": 999, "months": 12}
}

# Создание invoice
await message.answer_invoice(
    title="MindFlow Pro - 12 месяцев",
    description="Premium подписка...",
    payload=f"premium_year_{user_id}",
    currency="XTR",  # XTR = Telegram Stars
    prices=[LabeledPrice(label="Premium 12 мес.", amount=999)],
    provider_token="",  # Пусто для Stars!
)

# Обработка успешной оплаты
@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    # Активируем Premium в БД
    ...
```

### В WebApp (index.html):
```javascript
function buyPremium() {
    tg.sendData(JSON.stringify({
        action: 'buy_premium',
        plan: selectedPlan,  // 'month' или 'year'
        stars: 999,
        months: 12
    }));
}
```

---

## 5. Тестирование оплаты

### Способ 1: Через бота
1. Открой @MindFl0wAIbot
2. Напиши `/premium`
3. Выбери план (месяц или год)
4. Нажми "Оплатить X звёзд"
5. Подтверди покупку

### Способ 2: Через WebApp
1. Открой WebApp (кнопка "📱 Открыть приложение")
2. Settings → MindFlow Pro
3. Выбери план
4. Нажми "⭐ Купить за звёзды"

---

## 6. Где взять звёзды для теста?

**Для теста** можно выдать Premium бесплатно командой админа:
```
/addpremium YOUR_USER_ID 1
```

Где `YOUR_USER_ID` — твой Telegram ID (узнать можно у @userinfobot).

---

## 7. Вывод заработанных звёзд

1. Открой @BotFather
2. `/mybots` → выбери бота → **Payments**
3. **Telegram Stars** → **Withdraw**
4. Укажи TON кошелёк для вывода

**Минимум:** 1000 звёзд (~$20)

---

## 8. Преимущества Telegram Stars

✅ **0% комиссия** — ты получаешь всю сумму
✅ **Нет возвратов** — пользователи не могут вернуть деньги
✅ **Мгновенное зачисление**
✅ **Работает в 200+ странах**
✅ **Пользователи покупают звёзды за рубли/доллары в Telegram**

---

## 9. Структура реализации в MindFlow AI

```
bot/handlers/
├── payments.py      # Обработка оплаты, invoices
├── webapp_handler.py # Приём данных из WebApp
└── admin.py         # Ручная выдача Premium

webapp/
└── index.html       # UI покупки Premium, выбор плана

db/
├── database.py      # Таблица users с is_premium, premium_until
└── repo.py          # Запись Premium в БД
```

---

## 10. Проверить что Stars включены

Напиши @BotFather:
```
/mybots → выбери бота → Bot Settings → Payments → Telegram Stars
```

Должно быть: **Enabled** или **Включено**

---

## ⚠️ Важно!

- `provider_token=""` (пустая строка) для Stars
- `currency="XTR"` — это код для Telegram Stars
- `amount` — количество звёзд (целое число)
- После оплаты приходит `successful_payment` событие

---

## Готово! 

Оплата звёздами уже настроена. После включения Stars в @BotFather всё будет работать автоматически.
