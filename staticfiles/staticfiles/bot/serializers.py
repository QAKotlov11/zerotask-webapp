from rest_framework import serializers
from .models import User, Subscription, Task

class UserSerializer(serializers.ModelSerializer):
    trials_left = serializers.ReadOnlyField()
    has_active_subscription = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'telegram_id', 'username', 'first_name', 'chat_id',
            'registration_date', 'trials_used', 'trials_left',
            'has_active_subscription', 'is_active'
        ]
        read_only_fields = ['id', 'registration_date', 'trials_left', 'has_active_subscription']

class SubscriptionSerializer(serializers.ModelSerializer):
    days_left = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'start_date', 'end_date', 'auto_renewal',
            'payment_id', 'status', 'created_at', 'days_left', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'days_left', 'is_active']

class TaskSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'user', 'user_info', 'description', 'image',
            'created_at', 'status', 'solution', 'solution_image', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']
    
    def get_user_info(self, obj):
        return {
            'telegram_id': obj.user.telegram_id,
            'first_name': obj.user.first_name,
            'username': obj.user.username
        }

class TaskCreateSerializer(serializers.ModelSerializer):
    telegram_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Task
        fields = ['telegram_id', 'description', 'image', 'source']
    
    def create(self, validated_data):
        telegram_id = validated_data.pop('telegram_id')
        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'first_name': 'Пользователь',
                'chat_id': telegram_id,  # Временно используем telegram_id как chat_id
            }
        )
        
        # Проверяем лимиты
        if not user.has_active_subscription and user.trials_left <= 0:
            raise serializers.ValidationError("Бесплатные решения закончились. Оформите подписку.")
        
        # Создаем задачу
        task = Task.objects.create(user=user, **validated_data)
        
        # Увеличиваем счетчик использованных бесплатных решений
        if not user.has_active_subscription:
            user.trials_used += 1
            user.save()
        
        return task

class UserStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_subscriptions = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
