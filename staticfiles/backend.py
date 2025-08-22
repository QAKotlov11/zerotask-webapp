from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json
from datetime import datetime
import uuid

app = FastAPI(title="ZeroTask API", version="1.0.0")

# Настройка CORS для WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8003", "https://alekseykotlov.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Простое хранилище задач в памяти (в продакшене используйте базу данных)
tasks = {}

@app.get("/")
async def root():
    return {"message": "ZeroTask API работает! 🚀"}

@app.get("/api/tasks/")
async def get_tasks():
    """Получить список всех задач"""
    return {"tasks": list(tasks.values())}

@app.post("/api/tasks/create/")
async def create_task(
    telegram_id: int = Form(...),
    description: str = Form(""),
    image: UploadFile = File(None)
):
    """Создать новую задачу"""
    try:
        task_id = str(uuid.uuid4())
        
        # Сохраняем информацию о задаче
        task_data = {
            "id": task_id,
            "telegram_id": telegram_id,
            "description": description,
            "image_filename": image.filename if image else None,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Если есть изображение, сохраняем его
        if image:
            # В продакшене сохраняйте файлы в безопасное место
            image_path = f"uploads/{task_id}_{image.filename}"
            task_data["image_path"] = image_path
        
        tasks[task_id] = task_data
        
        # Здесь можно добавить логику для отправки задачи в AI сервис
        # Например, OpenAI GPT-4 для решения задачи
        
        return JSONResponse(
            status_code=201,
            content={
                "id": task_id,
                "message": "Задача успешно создана!",
                "telegram_id": telegram_id
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Ошибка при создании задачи: {str(e)}"}
        )

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Получить задачу по ID"""
    if task_id not in tasks:
        return JSONResponse(
            status_code=404,
            content={"error": "Задача не найдена"}
        )
    return tasks[task_id]

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tasks_count": len(tasks)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
