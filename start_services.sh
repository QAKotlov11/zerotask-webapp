#!/bin/bash

echo "🚀 Запуск всех сервисов ZeroTask..."

# Активируем виртуальное окружение
source venv/bin/activate

# Проверяем, что Redis запущен
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📦 Запускаем Redis..."
    brew services start redis
fi

# Запускаем Celery worker в фоне
echo "🔄 Запускаем Celery worker..."
celery -A zerotask_backend worker --loglevel=info &
CELERY_PID=$!

# Запускаем Django сервер
echo "🌐 Запускаем Django сервер..."
python manage.py runserver 8002 &
DJANGO_PID=$!

# Запускаем WebApp сервер
echo "📱 Запускаем WebApp сервер..."
python3 -m http.server 8003 &
WEBAPP_PID=$!

# Запускаем Telegram бота
echo "🤖 Запускаем Telegram бота..."
python telegram_bot.py &
BOT_PID=$!

echo "✅ Все сервисы запущены!"
echo "📊 Статус сервисов:"
echo "   - Django API: http://localhost:8002"
echo "   - WebApp: http://localhost:8003"
echo "   - Admin: http://localhost:8002/admin"
echo "   - Redis: localhost:6379"
echo "   - Celery Worker: активен"
echo "   - Telegram Bot: активен"

echo ""
echo "🛑 Для остановки всех сервисов нажмите Ctrl+C"

# Функция очистки при завершении
cleanup() {
    echo ""
    echo "🛑 Останавливаем сервисы..."
    kill $CELERY_PID $DJANGO_PID $WEBAPP_PID $BOT_PID 2>/dev/null
    echo "✅ Все сервисы остановлены"
    exit 0
}

# Перехватываем сигнал завершения
trap cleanup SIGINT SIGTERM

# Ждем завершения
wait
