from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from datetime import timedelta
import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from .models import User, Subscription, Task
from .serializers import (
    UserSerializer, SubscriptionSerializer, TaskSerializer,
    TaskCreateSerializer, UserStatsSerializer
)
from .tasks import process_task_image

logger = logging.getLogger(__name__)

class SimpleTestView(APIView):
    """Очень простой тест"""
    
    def get(self, request):
        return Response({'status': 'OK', 'message': 'Простой тест работает!'})

class TestAPIView(APIView):
    """Простой тестовый API для проверки"""
    
    def get(self, request):
        return Response({'message': 'Тестовый API работает!'})
    
    def post(self, request):
        return Response({'message': 'POST запрос получен!', 'data': request.data})

class UserViewSet(viewsets.ModelViewSet):
    """API для управления пользователями"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Получить задачи пользователя"""
        user = self.get_object()
        tasks = Task.objects.filter(user=user).order_by('-created_at')
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def subscriptions(self, request, pk=None):
        """Получить подписки пользователя"""
        user = self.get_object()
        subscriptions = Subscription.objects.filter(user=user).order_by('-created_at')
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)

class SubscriptionViewSet(viewsets.ModelViewSet):
    """API для управления подписками"""
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    
    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """Создать подписку (для webhook'а YooKassa)"""
        payment_id = request.data.get('payment_id')
        telegram_id = request.data.get('telegram_id')
        
        if not payment_id or not telegram_id:
            return Response(
                {'error': 'Необходимы payment_id и telegram_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(telegram_id=telegram_id)
            
            # Создаем подписку на 30 дней
            start_date = timezone.now()
            end_date = start_date + timedelta(days=30)
            
            subscription = Subscription.objects.create(
                user=user,
                start_date=start_date,
                end_date=end_date,
                payment_id=payment_id,
                status='active'
            )
            
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def cancel_auto_renewal(self, request, pk=None):
        """Отменить автопродление подписки"""
        subscription = self.get_object()
        subscription.auto_renewal = False
        subscription.save()
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

class TaskViewSet(viewsets.ModelViewSet):
    """API для управления задачами"""
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        return TaskSerializer

class TaskCreateView(APIView):
    """API для создания задачи из WebApp"""
    
    def get(self, request):
        """Тестовый GET метод"""
        return Response({'status': 'OK', 'message': 'TaskCreateView работает!'})
    
    def post(self, request):
        """Создание задачи"""
        try:
            # Получаем данные из запроса
            data = request.data
            logger.info(f"Получены данные задачи: {data}")
            
            # Получаем или создаем пользователя
            telegram_id = data.get('telegram_id', 123456789)  # Временно используем заглушку
            
            user, created = User.objects.get_or_create(
                telegram_id=telegram_id,
                defaults={
                    'username': data.get('username', f'user_{telegram_id}'),
                    'first_name': data.get('first_name', 'Пользователь'),
                    'chat_id': data.get('chat_id', telegram_id),
                }
            )
            
            # Определяем источник задачи
            source = 'text'
            if 'image' in request.FILES:
                source = 'image'
            
            # Создаем задачу
            task = Task.objects.create(
                user=user,
                description=data.get('description', ''),
                source=source,
                status='pending'
            )
            
            # Если есть изображение, сохраняем его
            if 'image' in request.FILES:
                task.image = request.FILES['image']
                task.save()
                
                # Запускаем асинхронную обработку изображения
                process_task_image.delay(str(task.id))
                
                logger.info(f"Задача с изображением создана: ID={task.id}, пользователь={user.telegram_id}")
                
                # Отправляем сообщение пользователю через бота
                self.send_task_received_message(user, task)
                
                return Response({
                    'status': 'success',
                    'message': 'Задача с изображением успешно создана',
                    'task_id': task.id
                })
            
            # Для текстовых задач используем OpenAI для генерации решения
            from .tasks import generate_solution
            import asyncio
            
            try:
                # Генерируем решение с помощью OpenAI
                solution = generate_solution(data.get('description', ''))
                
                # Обновляем задачу с решением
                task.solution = solution
                task.status = 'completed'
                task.completed_at = timezone.now()
                task.save()
                
                logger.info(f"Задача с AI решением создана: ID={task.id}, пользователь={user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Ошибка при генерации решения: {e}")
                # В случае ошибки используем простое решение
                task.solution = f"""<ol>
<li><strong>Анализ задачи:</strong> {data.get('description', '')}</li>
<li><strong>Применение метода:</strong> Используем соответствующий метод решения</li>
<li><strong>Выполнение вычислений:</strong> Получаем промежуточный результат</li>
<li><strong>Ответ:</strong> Итоговое решение задачи</li>
</ol>"""
                task.status = 'completed'
                task.completed_at = timezone.now()
                task.save()
            
            logger.info(f"Задача создана: ID={task.id}, пользователь={user.telegram_id}")
            
            # Отправляем сообщение пользователю через бота
            self.send_task_received_message(user, task)
            
            return Response({
                'status': 'success',
                'message': 'Задача успешно создана',
                'task_id': task.id
            })
            
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            return Response({
                'status': 'error',
                'message': f'Ошибка при создании задачи: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def send_task_received_message(self, user, task):
        """Отправка сообщения о получении задачи"""
        try:
            import asyncio
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            from config import BOT_TOKEN
            
            async def send_message():
                bot = Bot(token=BOT_TOKEN)
                
                text = f"""📝 Задача получена!

⏳ Обрабатываем вашу задачу..."""

                keyboard = [
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Используем telegram_id как chat_id, если chat_id не установлен
                chat_id = user.chat_id if user.chat_id else user.telegram_id
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                
                logger.info(f"Сообщение о получении задачи отправлено пользователю {user.telegram_id} в чат {chat_id}")
            
            # Запускаем асинхронную функцию
            asyncio.run(send_message())
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о получении задачи: {e}")

    def send_task_completed_message(self, user, task):
        """Отправка сообщения о завершении задачи"""
        try:
            import asyncio
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            from config import BOT_TOKEN, WEBAPP_URL_DEV
            
            async def send_message():
                bot = Bot(token=BOT_TOKEN)
                
                text = f"""✅ Задача решена!

📱 Посмотрите решение в мини-приложении"""

                # Ссылка на WebApp с конкретной задачей
                webapp_url = f"{WEBAPP_URL_DEV}?task_id={task.id}"
                
                keyboard = [
                    [InlineKeyboardButton("👀 Посмотреть решение", web_app=WebAppInfo(url=webapp_url))],
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Используем telegram_id как chat_id, если chat_id не установлен
                chat_id = user.chat_id if user.chat_id else user.telegram_id
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                
                logger.info(f"Сообщение о завершении задачи отправлено пользователю {user.telegram_id} в чат {chat_id}")
            
            # Запускаем асинхронную функцию
            asyncio.run(send_message())
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о завершении задачи: {e}")
    
    def put(self, request):
        """PUT метод для тестирования"""
        return Response({'status': 'OK', 'message': 'PUT запрос получен в TaskCreateView!'})

class StatsAPIView(APIView):
    """API для получения статистики"""
    
    def get(self, request):
        """Получить общую статистику"""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.objects.filter(status='active').count()
        total_tasks = Task.objects.count()
        completed_tasks = Task.objects.filter(status='completed').count()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

class UserByTelegramIDAPIView(APIView):
    """API для получения пользователя по Telegram ID"""
    
    def get(self, request, telegram_id):
        """Получить пользователя по Telegram ID"""
        try:
            user = User.objects.get(telegram_id=telegram_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request, telegram_id):
        """Создать или обновить пользователя"""
        user_data = request.data.copy()
        user_data['telegram_id'] = telegram_id
        
        try:
            user = User.objects.get(telegram_id=telegram_id)
            serializer = UserSerializer(user, data=user_data, partial=True)
        except User.DoesNotExist:
            serializer = UserSerializer(data=user_data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserTasksByTelegramIDAPIView(APIView):
    """API для получения задач пользователя по Telegram ID"""
    
    def get(self, request, telegram_id):
        """Получить задачи пользователя по Telegram ID"""
        try:
            user = User.objects.get(telegram_id=telegram_id)
            tasks = Task.objects.filter(user=user).order_by('-created_at')
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

@method_decorator(csrf_exempt, name='dispatch')
class YooKassaWebhookView(APIView):
    """Webhook для обработки уведомлений от YooKassa"""
    
    def post(self, request):
        try:
            # Получаем данные от YooKassa
            data = json.loads(request.body)
            logger.info(f"Получен webhook от YooKassa: {data}")
            
            # Извлекаем необходимые данные
            payment_id = data.get('object', {}).get('id')
            status = data.get('object', {}).get('status')
            amount = data.get('object', {}).get('amount', {}).get('value')
            currency = data.get('object', {}).get('amount', {}).get('currency')
            metadata = data.get('object', {}).get('metadata', {})
            
            # Получаем пользователя из metadata
            telegram_id = metadata.get('telegram_id')
            if not telegram_id:
                logger.error("Telegram ID не найден в metadata")
                return HttpResponse(status=400)
            
            user = get_object_or_404(User, telegram_id=telegram_id)
            
            if status == "succeeded":
                # Создаем или обновляем подписку
                subscription, created = Subscription.objects.get_or_create(
                    user=user,
                    payment_id=payment_id,
                    defaults={
                        'status': 'active',
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=30),
                        'auto_renewal': True,
                        'amount': amount or 290.00,
                        'currency': currency or 'RUB',
                        'payment_method': 'yookassa'
                    }
                )
                
                if not created:
                    # Обновляем существующую подписку
                    subscription.status = 'active'
                    subscription.start_date = timezone.now()
                    subscription.end_date = timezone.now() + timedelta(days=30)
                    subscription.amount = amount or 290.00
                    subscription.currency = currency or 'RUB'
                    subscription.save()
                
                logger.info(f"Подписка успешно создана/обновлена для пользователя {telegram_id}")
                
                # Отправляем сообщение об успешной оплате
                self.send_success_message(user)
                
            else:
                # Отправляем сообщение об ошибке оплаты
                self.send_error_message(user, payment_id)
            
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке webhook YooKassa: {e}")
            return HttpResponse(status=500)
    
    def send_success_message(self, user):
        """Отправка сообщения об успешной оплате"""
        try:
            import asyncio
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            from config import BOT_TOKEN
            
            async def send_message():
                bot = Bot(token=BOT_TOKEN)
                
                text = """✅ Подписка успешно оформлена!

Теперь тебе доступен безлимит на решения задач на 30 дней."""

                keyboard = [
                    [InlineKeyboardButton("🧠 Решить задачу", callback_data="solve_task")],
                    [InlineKeyboardButton("🔐 Подписка", callback_data="subscription")],
                    [InlineKeyboardButton("📢 Канал", url="https://t.me/your_channel")],
                    [InlineKeyboardButton("💬 Поддержка", url="https://t.me/your_support_bot")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=user.chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                
                logger.info(f"Сообщение об успешной оплате отправлено пользователю {user.telegram_id}")
            
            # Запускаем асинхронную функцию
            asyncio.run(send_message())
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об успешной оплате: {e}")
    
    def send_error_message(self, user, payment_id):
        """Отправка сообщения об ошибке оплаты"""
        try:
            import asyncio
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            from config import BOT_TOKEN
            
            async def send_message():
                bot = Bot(token=BOT_TOKEN)
                
                text = """⚠️ Сложности с оплатой.

Попробуйте ещё раз или выберите другой способ."""

                # Ссылка на повторную оплату через YooKassa
                retry_url = f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}"
                
                keyboard = [
                    [InlineKeyboardButton("💳 Повторить оплату", url=retry_url)],
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=user.chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                
                logger.info(f"Сообщение об ошибке оплаты отправлено пользователю {user.telegram_id}")
            
            # Запускаем асинхронную функцию
            asyncio.run(send_message())
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке оплаты: {e}")
