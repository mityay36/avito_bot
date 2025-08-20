import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

AVITO_SEARCH_URL = os.getenv('AVITO_SEARCH_URL')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 1800))  # 30 минут по умолчанию

PROXY_HOST=os.getenv('PROXY_HOST')
PROXY_PORT=os.getenv('PROXY_PORT')
PROXY_USER=os.getenv('PROXY_USER')
PROXY_PASS=os.getenv('PROXY_PASS')

TARGET_METRO_STATIONS = {
    'киевская', 'парк культуры', 'октябрьская', 'добрынинская',
    'павелецкая', 'таганская', 'курская', 'комсомольская',
    'проспект мира', 'новослободская', 'белорусская', 'краснопресненская',
    'римская', 'нижегородская', 'бауманская', 'марьина роща',
    'трубная', 'менделеевская', 'крестьянская застава',
    'дубровка', 'кожуховская', 'электрозаводская', 'семеновская'
}

# Более мягкие критерии
FILTER_CRITERIA = {
    'min_area': 30,
    'max_price': 100000,
    'max_metro_time': 20,
    'rooms': [1, 2],
    'preferred_repair': ['евроремонт', 'дизайнерский ремонт', 'хороший ремонт']
}

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}
