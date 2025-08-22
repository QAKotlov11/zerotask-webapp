#!/usr/bin/env python3
import sys
import os
import django
import requests
import json

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zerotask_backend.settings')
django.setup()

from bot.models import User, Task
from config import WEBAPP_URL_DEV

def test_real_task():
    """Тестируем создание реальной задачи через API"""
    
    # Получаем первого пользователя
    try:
        user = User.objects.first()
        if not user:
            print("❌ Нет пользователей в базе данных")
            return
        
        print(f"👤 Используем пользователя: {user.username} (ID: {user.id})")
        
        # Создаем тестовую задачу
        task = Task.objects.create(
            user=user,
            description="Решить уравнение: x^2 + 5x + 6 = 0",
            source='text',
            status='pending'
        )
        
        print(f"✅ Задача создана: {task.id}")
        print(f"📝 Описание: {task.description}")
        
        # Проверяем URL
        webapp_url = f"{WEBAPP_URL_DEV}?task_id={task.id}"
        print(f"🔗 WebApp URL: {webapp_url}")
        
        # Проверяем, что URL корректный
        if webapp_url.startswith("https://"):
            print("✅ URL корректный (начинается с https://)")
        else:
            print("❌ URL некорректный")
        
        # Проверяем, что URL содержит правильный домен
        if "ngrok.app" in webapp_url:
            print("✅ URL содержит ngrok.app")
        else:
            print("❌ URL не содержит ngrok.app")
        
        # Тестируем доступность WebApp
        try:
            response = requests.get(webapp_url, timeout=5)
            print(f"🌐 WebApp доступен: {response.status_code}")
        except Exception as e:
            print(f"❌ WebApp недоступен: {e}")
        
        # Удаляем тестовую задачу
        task.delete()
        print("🗑️ Тестовая задача удалена")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_real_task()
