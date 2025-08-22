from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'subscriptions', views.SubscriptionViewSet)
router.register(r'tasks', views.TaskViewSet)

urlpatterns = [
    # Создание задачи (для WebApp) - перемещаем в начало
    path('tasks/create/', views.TaskCreateView.as_view(), name='create-task'),
    
    # Задачи пользователя по Telegram ID (перемещаем выше роутера)
    path('users/<int:telegram_id>/tasks/', views.UserTasksByTelegramIDAPIView.as_view(), name='user-tasks-by-telegram'),
    
    # Простой тест
    path('simple/', views.SimpleTestView.as_view(), name='simple-test'),
    
    # Тестовый API
    path('test/', views.TestAPIView.as_view(), name='test-api'),
    
    # API маршруты
    path('', include(router.urls)),
    
    # Статистика
    path('stats/', views.StatsAPIView.as_view(), name='stats'),
    
    # Пользователь по Telegram ID
    path('users/telegram/<int:telegram_id>/', views.UserByTelegramIDAPIView.as_view(), name='user-by-telegram'),
    
    # Создание подписки (для webhook'а)
    path('subscriptions/create/', views.SubscriptionViewSet.as_view({'post': 'create_subscription'}), name='create-subscription'),
    
    # Webhook для YooKassa
    path('webhooks/yookassa/', views.YooKassaWebhookView.as_view(), name='yookassa-webhook'),
]
