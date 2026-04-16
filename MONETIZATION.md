# 💰 Инструкция по монетизации MindFlow AI

## 📱 Telegram Stars Payments

### 1. Настройка в BotFather

1. Откройте @BotFather в Telegram
2. Выберите вашего бота
3. Отправьте `/newapp` для создания Mini App
4. Отправьте `/mygames` → выберите бота → `Edit Game` → `Add Platform` → `Payment`
5. Подтвердите подключение платежей Telegram Stars

### 2. Ценовая политика

| План | Цена | Экономия |
|------|------|----------|
| Месяц | 150 ⭐ (~$2) | - |
| Год | 999 ⭐ (~$13) | 44% |

### 3. Что получает пользователь Premium

✅ **Все темы оформления** - Glass, Neon, Brutal, Fluid, Purple, Gold
✅ **Безлимитные теги** - создание любых категорий
✅ **AI без ограничений** - неограниченные запросы к AI
✅ **Расширенная аналитика** - детальные отчёты по продуктивности

### 4. Триал период

🎁 **Каждый новый пользователь получает 3 дня Premium бесплатно!**

Это реализовано в `db/repo.py` → `UserRepo.create()`

---

## 🔄 Как работает система оплаты

### Схема оплаты:

```
Пользователь → WebApp/Бот
    ↓
Нажимает "Купить Premium"
    ↓
bot.answer_invoice() с currency="XTR" (Telegram Stars)
    ↓
Telegram обрабатывает платеж
    ↓
F.successful_payment → активация Premium
    ↓
Запись в БД: is_premium=1, premium_until=DATE
```

### Проверка Premium:

```python
# Автоматическая проверка при каждом обращении к UserRepo.get()
if is_premium and premium_until < today:
    is_premium = 0  # Автоматическое отключение
```

---

## 📊 Мониторинг монетизации

### Админ-команды:

| Команда | Описание |
|---------|----------|
| `/admin` | Админ-панель |
| `/userstats` | Общая статистика |
| `/userinfo ID` | Инфо о пользователе |
| `/addpremium ID MONTHS` | Выдать Premium вручную |
| `/removepremium ID` | Забрать Premium |

### Метрики для отслеживания:

- **CR (Conversion Rate)** = Premium пользователи / Всего пользователей
- **ARPU (Average Revenue Per User)** = Доход / Пользователи
- **LTV (Lifetime Value)** = Средний доход с пользователя за всё время
- **Retention** = Возвращаемость пользователей

---

## 🚀 Деплой для продакшена

### Railway (рекомендуется):

```bash
# 1. Создайте аккаунт на railway.app
# 2. Подключите GitHub репозиторий
# 3. Добавьте переменные окружения:

BOT_TOKEN=ваш_токен
OPENAI_API_KEY=ваш_ключ
WEBAPP_URL=https://ваш-проект.railway.app/webapp
API_URL=https://ваш-проект.railway.app
ADMIN_IDS=ваш_telegram_id
RUN_API=true

# 4. Деплой произойдёт автоматически
```

### VPS / Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

---

## 📱 WebApp для Telegram

### Размещение WebApp:

1. **GitHub Pages** (бесплатно):
   ```bash
   cd webapp
   git init
   git push origin gh-pages
   # URL: https://username.github.io/repo/webapp/
   ```

2. **Railway/Vercel** (с API):
   - WebApp файлы в папке `static/`
   - API на FastAPI

### Интеграция с ботом:

```python
# В .env:
WEBAPP_URL=https://ваш-домен.com/webapp
API_URL=https://ваш-домен.com/api
```

---

## 🔐 Безопасность

### ВАЖНО! Проверьте перед запуском:

1. ✅ **Никогда не коммитьте .env файл!**
2. ✅ **PROXY_URL не должен содержать реальные креденшалы в коде**
3. ✅ **BOT_TOKEN должен быть в .env**
4. ✅ **ADMIN_IDS должны быть реальными Telegram ID**

### Проверка безопасности:

```bash
# Убедитесь что .env в .gitignore
grep ".env" C:\kronos\.gitignore
```

---

## 📈 Маркетинговые фишки

### 1. Триал 3 дня
Уже реализовано! Каждый новый пользователь получает Premium на 3 дня.

### 2. Реферальная программа (опционально)
Можно добавить: +7 дней Premium за приглашение друга.

### 3. Скидки
- **Black Friday** - 50% скидка
- **Новый год** - 30% скидка
- **День рождения** - бесплатно месяц

### 4. Премиум функции
Добавьте уникальные функции только для Premium:
- Экспорт данных в PDF/Excel
- Синхронизация с Google Calendar
- Командные задачи
- White-label (свой логотип)

---

## 🧪 Тестирование платежей

### Sandbox режим:

1. Используйте тестовый бот от @BotFather
2. Тестовые Stars выдаются бесплатно
3. Проверьте весь флоу:
   - `/premium` → выбор плана → оплата → успешная активация

### Чек-лист тестирования:

- [ ] Создание задачи
- [ ] Выполнение задачи (начисление XP)
- [ ] Покупка Premium через Stars
- [ ] Проверка истечения Premium
- [ ] WebApp синхронизация
- [ ] Напоминания
- [ ] Админ-команды

---

## 💡 Рекомендации по росту

1. **Viral Loop**: Добавьте "Поделиться результатом" после выполнения задач
2. **Push-уведомления**: Настройте напоминания для неактивных пользователей
3. **Content Marketing**: Публикуйте статьи о продуктивности
4. **Product Hunt**: Запустите там для первых пользователей
5. **Telegram Ads**: Реклама в каналах о продуктивности

---

## 📞 Поддержка

Если возникли вопросы по монетизации:
- Telegram: @ваш_username
- Email: support@ваш-домен.com

---

**Удачи с запуском! 🚀**
