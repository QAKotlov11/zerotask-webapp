import cv2
import numpy as np
from PIL import Image, ImageOps
import io
import base64
import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import Task
from config import OPENAI_API_KEY
import openai

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_task_image(self, task_id):
    """Обработка изображения задачи: OCR + решение"""
    try:
        task = Task.objects.get(id=task_id)
        task.status = 'processing'
        task.save()
        
        # Проверяем, есть ли изображение
        if not task.image:
            # Если нет изображения, это текстовая задача
            return process_text_task(task_id)
        
        # 1. Предобработка изображения
        processed_image = preprocess_image(task.image.path)
        
        # 2. OCR с помощью OpenAI Vision
        extracted_text = extract_text_from_image(processed_image)
        
        # 3. Обновляем описание задачи
        task.description = extracted_text
        task.save()
        
        # 4. Генерируем решение
        solution = generate_solution(extracted_text)
        
        # 5. Создаем изображение решения
        solution_image = create_solution_image(solution)
        
        # 6. Сохраняем результат
        task.solution = solution
        if solution_image:
            task.solution_image.save(
                f'solution_{task_id}.png',
                ContentFile(solution_image),
                save=False
            )
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # Отправляем уведомление о завершении задачи
        try:
            send_task_completed_notification(task)
            send_channel_notification(task)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
        
        logger.info(f"Task {task_id} completed successfully")
        return True
        
    except Exception as exc:
        logger.error(f"Error processing task {task_id}: {exc}")
        task.status = 'failed'
        task.error_message = str(exc)
        task.save()
        
        # Повторная попытка
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=3)
def process_text_task(self, task_id):
    """Обработка текстовой задачи"""
    try:
        task = Task.objects.get(id=task_id)
        task.status = 'processing'
        task.save()
        
        # Генерируем решение для текстовой задачи
        solution = generate_solution(task.description)
        
        # Создаем изображение решения
        solution_image = create_solution_image(solution)
        
        # Сохраняем результат
        task.solution = solution
        if solution_image:
            task.solution_image.save(
                f'solution_{task_id}.png',
                ContentFile(solution_image),
                save=False
            )
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # Отправляем уведомление о завершении задачи
        try:
            send_task_completed_notification(task)
            send_channel_notification(task)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
        
        logger.info(f"Text task {task_id} completed successfully")
        return True
        
    except Exception as exc:
        logger.error(f"Error processing text task {task_id}: {exc}")
        task.status = 'failed'
        task.error_message = str(exc)
        task.save()
        
        # Повторная попытка
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=3)
def process_task_text(self, task_id):
    """Обработка текстовой задачи: только решение"""
    try:
        task = Task.objects.get(id=task_id)
        task.status = 'processing'
        task.save()
        
        # Генерируем решение для текстовой задачи
        solution = generate_solution(task.description)
        
        # Создаем изображение решения
        solution_image = create_solution_image(solution)
        
        # Сохраняем результат
        task.solution = solution
        if solution_image:
            task.solution_image.save(
                f'solution_{task_id}.png',
                ContentFile(solution_image),
                save=False
            )
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # Отправляем уведомление о завершении задачи
        try:
            send_task_completed_notification(task)
            send_channel_notification(task)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
        
        logger.info(f"Text task {task_id} completed successfully")
        return True
        
    except Exception as exc:
        logger.error(f"Error processing text task {task_id}: {exc}")
        task.status = 'failed'
        task.error_message = str(exc)
        task.save()
        
        # Повторная попытка
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

def preprocess_image(image_path):
    """Предобработка изображения для улучшения OCR"""
    try:
        # Загружаем изображение
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Не удалось загрузить изображение")
        
        # Конвертируем в оттенки серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Улучшаем контраст
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Убираем шум
        denoised = cv2.fastNlMeansDenoising(enhanced)
        
        # Сохраняем обработанное изображение
        processed_path = image_path.replace('.', '_processed.')
        cv2.imwrite(processed_path, denoised)
        
        return processed_path
        
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        return image_path  # Возвращаем оригинальное изображение

def extract_text_from_image(image_path):
    """Извлечение текста из изображения с помощью OpenAI Vision"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        with open(image_path, "rb") as image_file:
                    response = client.chat.completions.create(
            model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - эксперт по извлечению текста из изображений. Извлеки весь текст из изображения, особенно математические задачи, формулы и уравнения. Сохрани точность математических выражений. Отвечай только текстом задачи, без дополнительных комментариев."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Извлеки текст из этого изображения. Если это математическая задача, сохрани все формулы и символы точно."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                timeout=30
            )
        
        extracted_text = response.choices[0].message.content.strip()
        logger.info(f"Extracted text: {extracted_text}")
        return extracted_text
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise

def generate_solution(task_text):
    """Генерация решения задачи с помощью OpenAI"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """Ты - эксперт по решению математических задач. 
                    Создавай краткие пошаговые решения в формате HTML с нумерованным списком.
                    Используй обычный текст для формул (без $), но с правильными символами:
                    - 2² вместо 2^2
                    - 4/2 вместо дробей
                    - × для умножения
                    - √ для корня
                    Формат ответа:
                    <ol>
                    <li><strong>Шаг 1:</strong> конкретное действие</li>
                    <li><strong>Шаг 2:</strong> конкретное действие</li>
                    <li><strong>Ответ:</strong> итоговый ответ</li>
                    </ol>
                    Делай решения максимально краткими. Каждый шаг - это одно конкретное действие или вычисление, без лишних объяснений."""
                },
                {
                    "role": "user",
                    "content": f"Реши эту задачу: {task_text}"
                }
            ],
            max_tokens=1500,
            timeout=30
        )
        
        solution = response.choices[0].message.content.strip()
        logger.info(f"Generated solution for: {task_text[:50]}...")
        return solution
        
    except Exception as e:
        logger.error(f"Error generating solution: {e}")
        raise

def create_solution_image(solution_text):
    """Создание изображения с решением"""
    try:
        # Создаем простое изображение с текстом решения
        from PIL import Image, ImageDraw, ImageFont
        
        # Убираем HTML теги для отображения
        clean_text = solution_text.replace('<ol>', '').replace('</ol>', '').replace('<li>', '').replace('</li>', '\n').replace('<strong>', '').replace('</strong>', '')
        
        # Создаем изображение
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Используем стандартный шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Разбиваем текст на строки
        lines = clean_text.split('\n')
        y_position = 20
        
        for line in lines:
            if line.strip():
                draw.text((20, y_position), line.strip(), fill='black', font=font)
                y_position += 25
        
        # Сохраняем в байты
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating solution image: {e}")
        return None

def send_task_completed_notification(task):
    """Отправка уведомления о завершении задачи"""
    logger.info(f"Начинаем отправку уведомления для задачи {task.id}")
    try:
        import threading
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        from config import BOT_TOKEN, WEBAPP_URL_DEV
        
        def send_message_sync():
            try:
                logger.info(f"Создаем бота для отправки уведомления")
                bot = Bot(token=BOT_TOKEN)
                
                text = f"""✅ Задача решена!

📱 Посмотрите решение в мини-приложении"""

                # Ссылка на WebApp с конкретной задачей
                webapp_url = f"{WEBAPP_URL_DEV}?task_id={task.id}"
                logger.info(f"Создаем WebApp URL: {webapp_url}")
                logger.info(f"WEBAPP_URL_DEV из config: {WEBAPP_URL_DEV}")
                
                keyboard = [
                    [InlineKeyboardButton("👀 Посмотреть решение", web_app=WebAppInfo(url=webapp_url))],
                    [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Используем telegram_id как chat_id, если chat_id не установлен
                chat_id = task.user.chat_id if task.user.chat_id else task.user.telegram_id
                logger.info(f"Отправляем уведомление в чат {chat_id} для пользователя {task.user.telegram_id}")
                
                # Отправляем сообщение синхронно с использованием requests
                import requests
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': text,
                    'reply_markup': reply_markup.to_dict()
                }
                
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    logger.info(f"Уведомление о завершении задачи отправлено пользователю {task.user.telegram_id} в чат {chat_id}")
                else:
                    logger.error(f"Ошибка отправки уведомления: {response.status_code} - {response.text}")
                
            except Exception as e:
                logger.error(f"Ошибка в send_message_sync: {e}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=send_message_sync)
        thread.start()
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о завершении задачи: {e}")

def send_channel_notification(task):
    """Отправка уведомления в канал о решенной задаче"""
    try:
        import threading
        import requests
        from config import BOT_TOKEN, CHANNEL_ID, WEBAPP_URL_DEV
        
        def send_channel_message():
            try:
                # Убираем HTML теги из решения для канала
                clean_solution = task.solution.replace('<ol>', '').replace('</ol>', '').replace('<li>', '').replace('</li>', '\n').replace('<strong>', '').replace('</strong>', '')
                
                # Ограничиваем длину решения для канала
                if len(clean_solution) > 500:
                    clean_solution = clean_solution[:500] + "..."
                
                # Экранируем специальные символы для Markdown
                import re
                def escape_markdown(text):
                    # Экранируем символы, которые могут сломать Markdown
                    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    for char in chars_to_escape:
                        text = text.replace(char, f'\\{char}')
                    return text
                
                safe_description = escape_markdown(task.description[:100])
                safe_solution = escape_markdown(clean_solution)
                safe_username = escape_markdown(task.user.username or 'Аноним')
                
                text = f"""🎯 **Новая решенная задача\\!**

📝 **Задача:** {safe_description}{'...' if len(task.description) > 100 else ''}

✅ **Решение готово\\!**

{safe_solution}

👤 **Пользователь:** @{safe_username}
📱 **Посмотреть полное решение:** {WEBAPP_URL_DEV}\\?task\\_id={task.id}"""

                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    'chat_id': CHANNEL_ID,
                    'text': text,
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    logger.info(f"Уведомление в канал отправлено для задачи {task.id}")
                else:
                    logger.error(f"Ошибка отправки в канал: {response.status_code} - {response.text}")
                
            except Exception as e:
                logger.error(f"Ошибка в send_channel_message: {e}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=send_channel_message)
        thread.start()
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления в канал: {e}")
