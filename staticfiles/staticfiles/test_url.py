#!/usr/bin/env python3
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем config
from config import WEBAPP_URL_DEV

print(f"WEBAPP_URL_DEV из config.py: {WEBAPP_URL_DEV}")

# Тестируем создание URL для задачи
task_id = "test-task-123"
webapp_url = f"{WEBAPP_URL_DEV}?task_id={task_id}"
print(f"Созданный WebApp URL: {webapp_url}")

# Проверяем, что URL начинается с https
if webapp_url.startswith("https://"):
    print("✅ URL корректный (начинается с https://)")
else:
    print("❌ URL некорректный (не начинается с https://)")
