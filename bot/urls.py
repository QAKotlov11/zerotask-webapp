from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'subscriptions', views.SubscriptionViewSet)
router.register(r'tasks', views.TaskViewSet)

urlpatterns = [
    # API маршруты
    path('api/', include(router.urls)),
    
    # Статистика
    path('api/stats/', views.StatsAPIView.as_view(), name='stats'),
    
    # Пользователь по Telegram ID
    path('api/users/telegram/<int:telegram_id>/', views.UserByTelegramIDAPIView.as_view(), name='user-by-telegram'),
    
    # Создание подписки (для webhook'а)
    path('api/subscriptions/create/', views.SubscriptionViewSet.as_view({'post': 'create_subscription'}), name='create-subscription'),
    
    # Webhook для YooKassa
    path('api/webhooks/yookassa/', views.YooKassaWebhookView.as_view(), name='yookassa-webhook'),
]
