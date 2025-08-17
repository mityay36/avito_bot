import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FILTER_CRITERIA


class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_apartment_notification(self, apartment_data):
        """Отправка уведомления о новой квартире"""
        try:
            message = self.format_apartment_message(apartment_data)

            if apartment_data['image_url']:
                self.send_photo_with_caption(apartment_data['image_url'], message)
            else:
                self.send_message(message)

        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")

    def format_apartment_message(self, apartment_data):
        """Форматирование сообщения о квартире"""

        quality_emoji = self.get_quality_emoji(apartment_data)
        metro_text = self.format_metro_info(apartment_data['metro_info'])
        repair_info = self.check_repair_quality(apartment_data['title'], apartment_data['description'])

        # Отображаем возраст объявления
        listing_age = apartment_data.get('listing_age', '📅 Недавно')

        message = f"""
{quality_emoji} **НОВАЯ КВАРТИРА НАЙДЕНА!**

{listing_age}

🏠 **{apartment_data['title']}**

💰 **Цена:** {apartment_data['price']}
📏 **Площадь:** {apartment_data.get('area', 'не указана')} м²
🚇 **Метро:** {metro_text}
📍 **Адрес:** {apartment_data['location']}

{repair_info}

📝 **Описание:** 
{apartment_data['description'][:300]}{'...' if len(apartment_data['description']) > 300 else ''}

🔗 [**ПОСМОТРЕТЬ ОБЪЯВЛЕНИЕ**]({apartment_data['url']})

⚡ *Быстрее пишите продавцу!*
        """
        return message.strip()

    def get_quality_emoji(self, apartment_data):
        """Определение качества предложения"""
        score = 0

        text = (apartment_data['title'] + ' ' + apartment_data['description']).lower()
        if any(repair in text for repair in FILTER_CRITERIA['preferred_repair']):
            score += 2

        koltso_stations = {'киевская', 'парк культуры', 'октябрьская', 'добрынинская',
                           'павелецкая', 'таганская', 'курская', 'комсомольская',
                           'проспект мира', 'новослободская', 'белорусская', 'краснопресненская'}
        if any(station in koltso_stations for station in apartment_data['metro_info']['stations']):
            score += 2

        if apartment_data['metro_info']['time'] and apartment_data['metro_info']['time'] <= 10:
            score += 1

        if apartment_data['price_num'] and apartment_data['price_num'] < 60000:
            score += 1

        if score >= 4:
            return "🔥🔥🔥"
        elif score >= 2:
            return "⭐⭐"
        else:
            return "🏠"

    def format_metro_info(self, metro_info):
        """Форматирование информации о метро"""
        if not metro_info['stations']:
            return "Не указано"

        stations_text = ", ".join(metro_info['stations'][:3])
        if len(metro_info['stations']) > 3:
            stations_text += f" и еще {len(metro_info['stations']) - 3}"

        time_text = f" ({metro_info['time']} мин)" if metro_info['time'] else ""

        return f"{stations_text}{time_text}"

    def check_repair_quality(self, title, description):
        """Проверка качества ремонта"""
        text = (title + ' ' + description).lower()

        if any(repair in text for repair in ['евроремонт', 'дизайнерский']):
            return "✨ **Евроремонт** - отличное состояние!"
        elif any(repair in text for repair in ['хороший ремонт', 'после ремонта']):
            return "🔨 **Хороший ремонт** - в порядке"
        elif any(repair in text for repair in ['косметический', 'требует ремонта']):
            return "🚧 **Требует ремонта** - но цена привлекательная"
        else:
            return "🏗️ **Ремонт не указан** - уточните у владельца"

    def send_photo_with_caption(self, photo_url, caption):
        """Отправка фотографии с подписью"""
        url = f"{self.base_url}/sendPhoto"

        payload = {
            'chat_id': self.chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, json=payload)
        return response.json()

    def send_message(self, text):
        """Отправка текстового сообщения"""
        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': text[:4096],
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }

        response = requests.post(url, json=payload)
        return response.json()

    def send_status_message(self, status):
        """Отправка статусного сообщения"""
        message = f"🤖 Статус бота: {status}"
        self.send_message(message)
