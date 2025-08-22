# Пример конфигурационного файла
# Скопируйте этот файл как config.py и заполните своими данными

# Telegram Bot Token (получите у @BotFather)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# OpenAI API Key (получите на https://platform.openai.com/)
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"

# URL для WebApp
WEBAPP_URL_DEV = "https://localhost:8003"
WEBAPP_URL_PROD = "https://yourdomain.com"

# Настройки подписки
SUBSCRIPTION_PRICE = 290.00
SUBSCRIPTION_DAYS = 30
TRIAL_LIMIT = 3

# Настройки OpenAI
OPENAI_MODEL = "gpt-4"
OPENAI_MAX_TOKENS = 2000
OPENAI_TEMPERATURE = 0.7

# Django настройки
DJANGO_SETTINGS_MODULE = "zerotask_backend.settings"

# Логирование
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Ссылки на внешние ресурсы
SUPPORT_BOT_URL = "https://t.me/your_support_bot"
CHANNEL_URL = "https://t.me/your_channel"
