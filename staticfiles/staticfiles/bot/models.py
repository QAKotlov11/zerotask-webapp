from django.db import models
from django.utils import timezone
import uuid

class User(models.Model):
    """Модель пользователя Telegram"""
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Username")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    chat_id = models.BigIntegerField(verbose_name="Chat ID")
    registration_date = models.DateTimeField(default=timezone.now, verbose_name="Дата регистрации")
    trials_used = models.IntegerField(default=0, verbose_name="Использовано бесплатных решений")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
    
    def __str__(self):
        return f"{self.first_name} (@{self.username})" if self.username else self.first_name
    
    @property
    def trials_left(self):
        """Осталось бесплатных решений"""
        from config import TRIAL_LIMIT
        return max(0, TRIAL_LIMIT - self.trials_used)
    
    @property
    def has_active_subscription(self):
        """Есть ли активная подписка"""
        return self.subscriptions.filter(
            status='active',
            end_date__gt=timezone.now()
        ).exists()
    
    @property
    def active_subscription(self):
        """Активная подписка"""
        return self.subscriptions.filter(
            status='active',
            end_date__gt=timezone.now()
        ).first()

class Subscription(models.Model):
    """Модель подписки пользователя"""
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('expired', 'Истекла'),
        ('cancelled', 'Отменена'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions', verbose_name="Пользователь")
    start_date = models.DateTimeField(default=timezone.now, verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    auto_renewal = models.BooleanField(default=True, verbose_name="Автопродление")
    payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID платежа")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Статус")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=290.00, verbose_name="Сумма")
    currency = models.CharField(max_length=3, default='RUB', verbose_name="Валюта")
    payment_method = models.CharField(max_length=50, default='yookassa', verbose_name="Способ оплаты")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Подписка {self.user.first_name} до {self.end_date.strftime('%d.%m.%Y')}"
    
    @property
    def is_active(self):
        """Активна ли подписка"""
        return self.status == 'active' and self.end_date and self.end_date > timezone.now()
    
    @property
    def days_left(self):
        """Сколько дней осталось"""
        if self.is_active and self.end_date:
            delta = self.end_date - timezone.now()
            return delta.days
        return 0

class Task(models.Model):
    """Модель задачи пользователя"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('processing', 'В обработке'),
        ('completed', 'Завершена'),
        ('failed', 'Ошибка'),
    ]
    
    SOURCE_CHOICES = [
        ('text', 'Текст'),
        ('image', 'Изображение'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', verbose_name="Пользователь")
    description = models.TextField(blank=True, verbose_name="Описание задачи")
    image = models.ImageField(upload_to='tasks/', blank=True, null=True, verbose_name="Фото задачи")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='text', verbose_name="Источник")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    solution = models.TextField(blank=True, verbose_name="Решение")
    solution_image = models.ImageField(upload_to='solutions/', blank=True, null=True, verbose_name="Фото решения")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    error_message = models.TextField(blank=True, null=True, verbose_name="Сообщение об ошибке")
    
    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Задача {self.id} от {self.user.first_name}"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

class BotSettings(models.Model):
    """Настройки бота"""
    key = models.CharField(max_length=100, unique=True, verbose_name="Ключ")
    value = models.TextField(verbose_name="Значение")
    description = models.TextField(blank=True, verbose_name="Описание")
    
    class Meta:
        verbose_name = "Настройка бота"
        verbose_name_plural = "Настройки бота"
    
    def __str__(self):
        return f"{self.key}: {self.value}"
