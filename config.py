import os
from dotenv import load_dotenv

load_dotenv()

# Telegram настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Avito настройки
AVITO_SEARCH_URL = os.getenv('AVITO_SEARCH_URL')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))

# Целевые станции метро
TARGET_METRO_STATIONS = {
    # Кольцевая линия
    'киевская', 'парк культуры', 'октябрьская', 'добрынинская',
    'павелецкая', 'таганская', 'курская', 'комсомольская',
    'проспект мира', 'новослободская', 'белорусская', 'краснопресненская',

    # Дополнительные станции
    'римская', 'нижегородская', 'бауманская', 'марьина роща',
    'трубная', 'менделеевская', 'крестьянская застава',
    'дубровка', 'кожуховская', 'текстильщики',
}

FILTER_CRITERIA = {
    'min_area': 35,  # минимальная площадь в м²
    'max_price': 75000,  # максимальная цена в рублях
    'max_metro_time': 15,  # максимальное время до метро в минутах
    'rooms': [1, 2],  # количество комнат
    'preferred_repair': ['евроремонт', 'дизайнерский ремонт', 'хороший ремонт']
}

# Headers для запросов
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}
