import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from django.core.management import execute_from_command_line
import django
import sys
from asgiref.sync import sync_to_async

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zerotask_backend.settings')
django.setup()

# Импорты Django моделей
from bot.models import User, Subscription, Task
from bot.serializers import UserSerializer, TaskSerializer
from openai import OpenAI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from config import *

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Константы для подписки
SUBSCRIPTION_PRICE = 290
SUBSCRIPTION_DAYS = 30

class MyGDZBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        try:
            logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
            
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            logger.info(f"Создаем/получаем пользователя с telegram_id={user.id}")
            
            # Создаем или получаем пользователя
            db_user, created = await sync_to_async(User.objects.get_or_create)(
                telegram_id=user.id,
                defaults={
                    'username': user.username,
                    'first_name': user.first_name,
                    'chat_id': chat_id,
                }
            )
            
            logger.info(f"Пользователь {'создан' if created else 'получен'}: {db_user.id}")
            
            if not created:
                # Обновляем информацию
                db_user.username = user.username
                db_user.first_name = user.first_name
                db_user.chat_id = chat_id
                await sync_to_async(db_user.save)()
                logger.info("Информация пользователя обновлена")
            
            logger.info("Показываем главное меню")
            await self.show_main_menu(update, context, db_user)
            
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            error_text = "❌ Произошла ошибка при запуске бота. Попробуйте позже."
            if update.message:
                await update.message.reply_text(error_text)
            elif update.callback_query:
                await update.callback_query.edit_message_text(error_text)
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать главное меню"""
        # Получаем данные пользователя асинхронно
        has_subscription = await sync_to_async(lambda: user.has_active_subscription)()
        
        if has_subscription:
            subscription = await sync_to_async(lambda: user.active_subscription)()
            end_date = subscription.end_date.strftime('%d.%m.%Y')
            text = f"👋 Привет! Я бот MyGDZ — помогу решить задачи по фото или тексту.\n\n📌 Подписка активна до {end_date}"
            
            keyboard = [
                [InlineKeyboardButton("🧠 Решить задачу", callback_data="solve_task")],
                [InlineKeyboardButton("🔐 Подписка", callback_data="subscription")],
                [InlineKeyboardButton("📢 Канал", callback_data="channel")],
                [InlineKeyboardButton("💬 Поддержка", callback_data="support")]
            ]
        else:
            trials_left = await sync_to_async(lambda: user.trials_left)()
            text = f"👋 Привет! Я бот MyGDZ — помогу решить задачи по фото или тексту.\n📌 Доступно {trials_left} бесплатных решений, дальше — подписка с безлимитом."
            
            keyboard = [
                [InlineKeyboardButton("🧠 Решить задачу", callback_data="solve_task")],
                [InlineKeyboardButton("🔐 Купить подписку", callback_data="subscription")],
                [InlineKeyboardButton("📢 Канал", callback_data="channel")],
                [InlineKeyboardButton("💬 Поддержка", callback_data="support")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=text, reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user = await sync_to_async(User.objects.get)(telegram_id=query.from_user.id)
        
        if query.data == "solve_task":
            await self.show_solve_task_menu(update, context, user)
        elif query.data == "subscription":
            await self.show_subscription_menu(update, context, user)
        elif query.data == "channel":
            await self.show_channel_menu(update, context, user)
        elif query.data == "support":
            await self.show_contact_support(update, context, user)
        elif query.data == "back_to_menu":
            # Получаем пользователя заново для актуальных данных
            user = await sync_to_async(User.objects.get)(telegram_id=query.from_user.id)
            await self.show_main_menu(update, context, user)
        elif query.data == "open_webapp":
            await self.open_webapp(update, context, user)
        elif query.data == "buy_subscription":
            await self.show_payment_menu(update, context, user)
        elif query.data == "cancel_auto_renewal":
            await self.cancel_auto_renewal(update, context, user)


    
    async def show_solve_task_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать меню решения задач"""
        query = update.callback_query
        
        has_subscription = await sync_to_async(lambda: user.has_active_subscription)()
        
        if has_subscription:
            subscription = await sync_to_async(lambda: user.active_subscription)()
            end_date = subscription.end_date.strftime('%d.%m.%Y')
            text = f"📌 Подписка активна до {end_date}.\n\nЗагружай фото или текст задачи — перейдём в мини-приложение."
            
            keyboard = [
                [InlineKeyboardButton("🚀 Открыть мини-приложение", web_app=WebAppInfo(url=WEBAPP_URL_DEV))],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
            ]
        else:
            trials_left = await sync_to_async(lambda: user.trials_left)()
            if trials_left > 0:
                text = f"У тебя есть {trials_left} бесплатных решений. Осталось: {trials_left}.\n\n📸 Загружай фото или вводи текст — перейдём в мини-приложение."
                
                keyboard = [
                    [InlineKeyboardButton("🚀 Открыть мини-приложение", web_app=WebAppInfo(url=WEBAPP_URL_DEV))],
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
            else:
                text = "Бесплатные решения закончились.\n\nОформи подписку и получай безлимит на 30 дней."
                
                keyboard = [
                    [InlineKeyboardButton("🔐 Купить подписку", callback_data="buy_subscription")],
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    
    async def show_subscription_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать меню подписки"""
        query = update.callback_query
        
        has_subscription = await sync_to_async(lambda: user.has_active_subscription)()
        
        if has_subscription:
            subscription = await sync_to_async(lambda: user.active_subscription)()
            end_date = subscription.end_date.strftime('%d.%m.%Y')
            auto_renewal = "включено" if subscription.auto_renewal else "отключено"
            
            text = f"🔐 Подписка активна до {end_date}.\n\n📌 Автопродление: {auto_renewal}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Продлить на 30 дней", callback_data="buy_subscription")],
                [InlineKeyboardButton("❌ Отменить автопродление", callback_data="cancel_auto_renewal")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
            ]
        else:
            text = f"""🔐 Подписка MyGDZ
— Безлимит на решения задач
— Все ответы с пошаговым объяснением и формулами
— Формат PNG с красивым оформлением
— История задач в твоём профиле

Стоимость: {SUBSCRIPTION_PRICE} ₽ / {SUBSCRIPTION_DAYS} дней"""
            
            keyboard = [
                [InlineKeyboardButton("💳 Перейти к оплате", callback_data="buy_subscription")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    
    async def show_channel_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать меню канала"""
        query = update.callback_query
        
        text = """📢 Наш канал и сайт:
— Свежие новости проекта
— Полезные материалы
— Акции и бонусы для подписчиков"""
        
        keyboard = [
            [InlineKeyboardButton("📲 Перейти в канал", url="https://t.me/your_channel")],
            [InlineKeyboardButton("🌐 Открыть сайт", url="https://your-website.com")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    

    
    async def show_payment_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать меню оплаты"""
        query = update.callback_query
        
        text = """💳 Оплата подписки

Для тестирования используйте:
- Номер карты: 1111 1111 1111 1111
- Срок действия: любой будущий
- CVV: любой

В реальном проекте здесь будет интеграция с YooKassa."""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    
    async def cancel_auto_renewal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Отменить автопродление подписки"""
        query = update.callback_query
        
        has_subscription = await sync_to_async(lambda: user.has_active_subscription)()
        
        if has_subscription:
            subscription = await sync_to_async(lambda: user.active_subscription)()
            subscription.auto_renewal = False
            await sync_to_async(subscription.save)()
            
            text = "✅ Автопродление отменено."
        else:
            text = "❌ У вас нет активной подписки."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    

    async def show_contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Показать меню поддержки с FAQ"""
        query = update.callback_query
        
        text = """💬 Часто задаваемые вопросы:

1️⃣ Как загрузить фото задачи? — Через кнопку «Решить задачу» → «Открыть мини-приложение».
2️⃣ Какие форматы задач поддерживаются? — Фото и текст.
3️⃣ Что в ответе? — Пошаговое решение, формулы, итоговый ответ.
4️⃣ Как работает подписка? — 30 дней безлимита на решения.
5️⃣ Как отменить автопродление? — В разделе «Подписка» кнопка «Отменить автопродление».

📩 Поддержка MyGDZ
Работаем ежедневно с 10:00 до 20:00 МСК."""
        
        keyboard = [
            [InlineKeyboardButton("📲 Написать в поддержку", url="https://t.me/your_support_bot")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    async def open_webapp(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Открыть WebApp"""
        query = update.callback_query
        
        text = "🚀 Открываю мини-приложение для решения задач..."
        keyboard = [
            [InlineKeyboardButton("🔍 Открыть WebApp", web_app=WebAppInfo(url=WEBAPP_URL_DEV))],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_text = """🤖 Помощь по боту MyGDZ

📱 Основные команды:
/start - Главное меню
/help - Эта справка

🔧 Как использовать:
1. Отправьте текст задачи или фото прямо в чат
2. Бот автоматически создаст задачу и откроет WebApp
3. Или нажмите "🧠 Решить задачу" для открытия WebApp
4. Получите пошаговое решение с формулами!

💬 По всем вопросам обращайтесь в поддержку."""
        
        await update.message.reply_text(help_text)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        text = update.message.text
        
        try:
            # Получаем или создаем пользователя
            db_user, created = await sync_to_async(User.objects.get_or_create)(
                telegram_id=user.id,
                defaults={
                    'username': user.username,
                    'first_name': user.first_name,
                    'chat_id': update.effective_chat.id,
                }
            )
            
            if not created:
                # Обновляем информацию
                db_user.username = user.username
                db_user.first_name = user.first_name
                db_user.chat_id = update.effective_chat.id
                await sync_to_async(db_user.save)()
            
            # Проверяем подписку
            has_subscription = await sync_to_async(lambda: db_user.has_active_subscription)()
            trials_left = await sync_to_async(lambda: db_user.trials_left)()
            
            if not has_subscription and trials_left <= 0:
                await update.message.reply_text(
                    "❌ У вас закончились бесплатные попытки. Оформите подписку для продолжения работы.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔐 Оформить подписку", callback_data="subscription")]
                    ])
                )
                return
            
            # Создаем задачу
            task = await sync_to_async(Task.objects.create)(
                user=db_user,
                description=text,
                source='text',
                status='pending'
            )
            
            # Отправляем сообщение о получении задачи
            await update.message.reply_text(
                "✅ Задача получена! Уже решаю...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ])
            )
            
            # Запускаем обработку задачи в Celery
            from bot.tasks import process_task_text
            process_task_text.delay(str(task.id))
            
            # Уменьшаем количество пробных попыток, если нет подписки
            if not has_subscription and trials_left > 0:
                db_user.trials_left = trials_left - 1
                await sync_to_async(db_user.save)()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке текстового сообщения: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке задачи. Попробуйте позже.")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото"""
        user = update.effective_user
        photo = update.message.photo[-1]  # Берем самое большое фото
        
        try:
            # Получаем или создаем пользователя
            db_user, created = await sync_to_async(User.objects.get_or_create)(
                telegram_id=user.id,
                defaults={
                    'username': user.username,
                    'first_name': user.first_name,
                    'chat_id': update.effective_chat.id,
                }
            )
            
            if not created:
                # Обновляем информацию
                db_user.username = user.username
                db_user.first_name = user.first_name
                db_user.chat_id = update.effective_chat.id
                await sync_to_async(db_user.save)()
            
            # Проверяем подписку
            has_subscription = await sync_to_async(lambda: db_user.has_active_subscription)()
            trials_left = await sync_to_async(lambda: db_user.trials_left)()
            
            if not has_subscription and trials_left <= 0:
                await update.message.reply_text(
                    "❌ У вас закончились бесплатные попытки. Оформите подписку для продолжения работы.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔐 Оформить подписку", callback_data="subscription")]
                    ])
                )
                return
            
            # Создаем задачу
            task = await sync_to_async(Task.objects.create)(
                user=db_user,
                description="Фото задача",
                source='image',
                status='pending'
            )
            
            # Скачиваем фото
            file = await context.bot.get_file(photo.file_id)
            file_path = f"media/tasks/{task.id}.jpg"
            
            # Создаем директорию если её нет
            import os
            os.makedirs("media/tasks", exist_ok=True)
            
            # Скачиваем файл
            await file.download_to_drive(file_path)
            
            # Обновляем задачу с путем к файлу
            task.image = f"tasks/{task.id}.jpg"
            await sync_to_async(task.save)()
            
            # Отправляем сообщение о получении задачи
            await update.message.reply_text(
                "📸 Фото получено! Обрабатываю изображение и решаю...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ])
            )
            

            
            # Запускаем обработку задачи в Celery
            from bot.tasks import process_task_image
            process_task_image.delay(str(task.id))
            
            # Уменьшаем количество пробных попыток, если нет подписки
            if not has_subscription and trials_left > 0:
                db_user.trials_left = trials_left - 1
                await sync_to_async(db_user.save)()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке фото. Попробуйте позже.")
    

    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота MyGDZ...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = MyGDZBot()
    bot.run()
