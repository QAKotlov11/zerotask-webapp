# 🤖 MyGDZ - Telegram Bot с WebApp

Полнофункциональный Telegram бот для решения математических задач с интегрированным WebApp и Django backend.

## ✨ Основные возможности

- **🧠 Решение задач**: Интеграция с OpenAI GPT-4 для пошаговых решений
- **📸 OCR + AI**: Автоматическое извлечение текста из фото и генерация решений
- **📱 WebApp**: Удобный интерфейс для загрузки фото и текста задач
- **⚡ Асинхронная обработка**: Celery + Redis для быстрой обработки изображений
- **💳 Система подписок**: Trial период + платные подписки через YooKassa
- **👥 Управление пользователями**: Админ панель с расширенным функционалом
- **🔄 Автопродление**: Система автоматического продления подписок
- **📊 Статистика**: Отслеживание использования и активности пользователей

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/QAKotlov11/zerotask-webapp.git
cd zerotask-webapp
```

### 2. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации
```bash
cp config.example.py config.py
# Отредактируйте config.py, добавив свои токены
```

### 5. Настройка базы данных
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 6. Установка системных зависимостей
```bash
# Установка Redis (macOS)
brew install redis
brew services start redis

# Или для Ubuntu/Debian:
# sudo apt-get install redis-server
# sudo systemctl start redis
```

### 7. Создание папок для медиа файлов
```bash
mkdir -p media/tasks media/solutions
```

### 8. Запуск сервисов

#### Вариант A: Автоматический запуск всех сервисов
```bash
./start_services.sh
```

#### Вариант B: Ручной запуск
```bash
# Терминал 1: Celery worker
celery -A zerotask_backend worker --loglevel=info

# Терминал 2: Django backend
python manage.py runserver 8002

# Терминал 3: Telegram bot
python telegram_bot.py

# Терминал 4: WebApp
python -m http.server 8003
```

## ⚙️ Конфигурация

### Обязательные настройки в `config.py`:

```python
# Telegram Bot Token от @BotFather
BOT_TOKEN = "your_bot_token_here"

# OpenAI API Key
OPENAI_API_KEY = "your_openai_api_key_here"

# URL для WebApp
WEBAPP_URL_DEV = "https://localhost:8003"
WEBAPP_URL_PROD = "https://yourdomain.com"

# Ссылки на внешние ресурсы
SUPPORT_BOT_URL = "https://t.me/your_support_bot"
CHANNEL_URL = "https://t.me/your_channel"
```

## 🏗️ Архитектура проекта

```
zerotask-webapp/
├── bot/                    # Django приложение
│   ├── models.py          # Модели данных
│   ├── views.py           # API endpoints
│   ├── admin.py           # Админ панель
│   └── urls.py            # URL маршруты
├── zerotask_backend/      # Django проект
│   ├── settings.py        # Настройки
│   └── urls.py            # Главные URL
├── telegram_bot.py        # Основной бот
├── config.py              # Конфигурация
├── index.html             # WebApp интерфейс
└── requirements.txt       # Зависимости
```

## 📱 Использование бота

### Команды:
- `/start` - Главное меню
- `/help` - Справка по боту

### Основные функции:
1. **Решить задачу** → Открытие WebApp для загрузки
2. **Подписка** → Управление подпиской и оплатой
3. **Поддержка** → FAQ и связь с поддержкой
4. **Канал** → Переход в официальный канал

## 💳 Система подписок

- **Trial период**: 3 бесплатных решения
- **Платная подписка**: 290₽ за 30 дней
- **Автопродление**: Включено по умолчанию
- **Платежи**: Интеграция с YooKassa

## 🔧 Админ панель

Доступна по адресу `http://localhost:8002/admin/`

**Возможности:**
- Управление пользователями
- Создание/редактирование подписок
- Просмотр статистики использования
- Мониторинг задач и решений

## 🌐 WebApp

- **URL**: `http://localhost:8003`
- **Функции**: Загрузка фото, ввод текста задач
- **Интеграция**: Автоматическая отправка в OpenAI API

## 🔒 Безопасность

- Валидация пользователей и подписок
- Проверка лимитов доступа
- Безопасная обработка webhook'ов
- Защита от CSRF атак

## 📊 API Endpoints

- `POST /api/tasks/` - Создание задачи
- `GET /api/users/{id}/` - Информация о пользователе
- `POST /api/webhooks/yookassa/` - Webhook YooKassa
- `GET /api/subscriptions/` - Список подписок

## 🚨 Устранение неполадок

### Бот не отвечает:
1. Проверьте токен в `config.py`
2. Убедитесь, что бот запущен
3. Проверьте логи на ошибки

### WebApp не открывается:
1. Проверьте порт 8003
2. Убедитесь, что `http.server` запущен
3. Проверьте URL в `config.py`

### Ошибки Django:
1. Выполните миграции: `python manage.py migrate`
2. Проверьте настройки в `settings.py`
3. Создайте суперпользователя

## 📝 Лицензия

MIT License

## 🤝 Поддержка

По всем вопросам обращайтесь:
- **Telegram**: [@your_support_bot](https://t.me/your_support_bot)
- **Канал**: [@your_channel](https://t.me/your_channel)

## 🎯 Планы развития

- [ ] Интеграция с другими платежными системами
- [ ] Многоязычная поддержка
- [ ] Расширенная аналитика
- [ ] Мобильное приложение
- [ ] API для внешних интеграций

---

**Создано с ❤️ для образовательных целей** 