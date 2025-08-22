from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta
from .models import User, Subscription, Task, BotSettings

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'username', 'first_name', 'registration_date', 'trials_used', 'trials_left', 'has_active_subscription', 'is_active']
    list_filter = ['is_active', 'registration_date']
    search_fields = ['telegram_id', 'username', 'first_name']
    readonly_fields = ['trials_left', 'has_active_subscription', 'active_subscription', 'subscription_actions']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('telegram_id', 'username', 'first_name', 'chat_id', 'registration_date')
        }),
        ('Статистика', {
            'fields': ('trials_used', 'trials_left', 'is_active')
        }),
        ('Подписка', {
            'fields': ('has_active_subscription', 'active_subscription'),
            'classes': ('collapse',)
        }),
        ('Управление подпиской', {
            'fields': ('subscription_actions',),
            'classes': ('wide',)
        })
    )
    
    def subscription_actions(self, obj):
        """Действия для управления подпиской"""
        if obj.has_active_subscription:
            subscription = obj.active_subscription
            html = f"""
            <div style="background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Активная подписка:</strong><br>
                Статус: {subscription.get_status_display()}<br>
                Действует до: {subscription.end_date.strftime('%d.%m.%Y')}<br>
                Автопродление: {'Да' if subscription.auto_renewal else 'Нет'}<br>
                <a href="/admin/bot/subscription/{subscription.id}/change/" class="button">Редактировать подписку</a>
            </div>
            """
            return mark_safe(html)
        else:
            html = f"""
            <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Подписка неактивна</strong><br>
                Бесплатных решений осталось: {obj.trials_left}<br>
                <a href="/admin/bot/subscription/add/?user={obj.id}" class="button">Выдать подписку</a>
            </div>
            """
            return mark_safe(html)
    
    subscription_actions.short_description = "Управление подпиской"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('subscriptions')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'start_date', 'end_date', 'days_left', 'is_active', 'auto_renewal', 'payment_method']
    list_filter = ['status', 'start_date', 'end_date', 'auto_renewal', 'payment_method']
    search_fields = ['user__telegram_id', 'user__username', 'user__first_name']
    readonly_fields = ['days_left', 'is_active']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Детали подписки', {
            'fields': ('status', 'start_date', 'end_date', 'auto_renewal')
        }),
        ('Оплата', {
            'fields': ('payment_method', 'amount', 'currency', 'payment_id')
        }),
        ('Статистика', {
            'fields': ('days_left', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """Автоматически устанавливаем дату начала при создании"""
        if not change:  # Если это новая подписка
            obj.start_date = timezone.now()
            if not obj.end_date:
                obj.end_date = timezone.now() + timedelta(days=30)
        super().save_model(request, obj, form, change)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['user', 'description_short', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at', 'completed_at']
    search_fields = ['user__telegram_id', 'user__username', 'description']
    readonly_fields = ['created_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Задача', {
            'fields': ('description', 'image')
        }),
        ('Статус', {
            'fields': ('status', 'solution')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def description_short(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Описание'

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']
    
    fieldsets = (
        ('Настройка', {
            'fields': ('key', 'value', 'description')
        }),
    )
