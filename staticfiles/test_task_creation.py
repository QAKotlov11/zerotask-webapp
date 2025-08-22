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

def test_task_creation():
    """Тестируем создание задачи и проверяем URL"""
    
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
            description="Тестовая задача для проверки URL",
            source='text',
            status='completed'
        )
        
        print(f"✅ Задача создана: {task.id}")
        
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
        
        # Удаляем тестовую задачу
        task.delete()
        print("🗑️ Тестовая задача удалена")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_task_creation()
