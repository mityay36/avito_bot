import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from datetime import datetime, timedelta
from config import HEADERS, AVITO_SEARCH_URL, TARGET_METRO_STATIONS, FILTER_CRITERIA


class AvitoScraper:
    def __init__(self):
        self.headers = HEADERS
        self.base_url = "https://www.avito.ru"

    def get_apartments(self):
        """Получение списка квартир с Avito через API"""
        try:
            # Используем внутренний API Avito для более стабильной работы
            api_url = self.convert_search_url_to_api()

            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            apartments = []

            if 'items' in data:
                for item in data['items']:
                    apartment_data = self.parse_apartment_from_api(item)
                    if apartment_data and self.meets_criteria(apartment_data):
                        apartments.append(apartment_data)

            return apartments

        except Exception as e:
            print(f"Ошибка при работе с API, переходим на HTML парсинг: {e}")
            return self.get_apartments_html_fallback()

    def convert_search_url_to_api(self):
        """Конвертация URL поиска в API запрос"""
        api_url = "https://www.avito.ru/web/1/main/items"

        params = {
            'locationId': '637640',  # Москва
            'categoryId': '24',  # Квартиры
            'params[549]': '1059',  # Аренда
            'params': '1,2',  # 1-2 комнатные (исправлено)
            'priceMax': '75000',
            'areaMin': '35',
            'sort': 'date',
            'limit': '50',
            'page': '1'
        }

        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{api_url}?{param_string}"

    def parse_apartment_from_api(self, item):
        """Парсинг квартиры из API ответа"""
        try:
            # Проверка даты - СЕГОДНЯ И ВЧЕРА
            if not self.is_recent_listing(item):
                return None

            apartment_id = item.get('id', '')
            title = item.get('title', 'Без названия')

            # Извлечение цены
            price_info = item.get('priceDetailing', {})
            price_value = price_info.get('value', 0)
            price_text = f"{price_value:,} ₽" if price_value else "Цена не указана"

            # Извлечение местоположения и метро
            location_info = item.get('location', {})
            location = location_info.get('name', 'Местоположение не указано')

            # Извлечение информации о метро
            metro_info = self.extract_metro_from_api_item(item)

            # Формирование URL
            url = f"https://www.avito.ru{item.get('urlPath', '')}"

            # Извлечение изображения
            images = item.get('images', [])
            image_url = images[0].get('636x476') if images else ""

            # Извлечение описания и параметров
            description = item.get('description', '')
            rooms, area = self.extract_apartment_params_from_api(item)

            # Определяем возраст объявления для отображения
            listing_age = self.get_listing_age(item)

            return {
                'id': apartment_id,
                'title': title,
                'price': price_text,
                'price_num': price_value,
                'location': location,
                'metro_info': metro_info,
                'url': url,
                'image_url': image_url,
                'description': description,
                'rooms': rooms,
                'area': area,
                'date_published': item.get('sortTimeStamp', 0),
                'listing_age': listing_age  # Новое поле для отображения возраста
            }

        except Exception as e:
            print(f"Ошибка при парсинге объявления из API: {e}")
            return None

    def is_recent_listing(self, item):
        """Проверка, что объявление опубликовано сегодня или вчера"""
        try:
            timestamp = item.get('sortTimeStamp', 0)
            if timestamp:
                listing_date = datetime.fromtimestamp(timestamp)
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)

                listing_day = listing_date.date()
                return listing_day == today or listing_day == yesterday
            return False
        except:
            return False

    def get_listing_age(self, item):
        """Определение возраста объявления для отображения"""
        try:
            timestamp = item.get('sortTimeStamp', 0)
            if timestamp:
                listing_date = datetime.fromtimestamp(timestamp)
                today = datetime.now().date()

                if listing_date.date() == today:
                    # Если сегодня, показываем время
                    hours_ago = (datetime.now() - listing_date).total_seconds() / 3600
                    if hours_ago < 1:
                        return "📅 Только что"
                    elif hours_ago < 24:
                        return f"📅 {int(hours_ago)} ч назад"
                    else:
                        return "📅 Сегодня"
                else:
                    return "📅 Вчера"
            return "📅 Недавно"
        except:
            return "📅 Недавно"

    def extract_metro_from_api_item(self, item):
        """Извлечение информации о метро из API"""
        metro_info = {'stations': [], 'time': None}

        try:
            # Проверяем в разных местах API ответа
            geo = item.get('geo', {})
            references = geo.get('references', [])

            for ref in references:
                ref_text = str(ref).lower()

                # Поиск времени до метро
                time_match = re.search(r'(\d+)\s*мин', ref_text)
                if time_match:
                    metro_info['time'] = int(time_match.group(1))

                # Поиск станций метро
                for station in TARGET_METRO_STATIONS:
                    if station in ref_text:
                        metro_info['stations'].append(station)

            # Дополнительная проверка в описании и заголовке
            full_text = (item.get('title', '') + ' ' + item.get('description', '')).lower()
            for station in TARGET_METRO_STATIONS:
                if station in full_text and station not in metro_info['stations']:
                    metro_info['stations'].append(station)

        except Exception as e:
            print(f"Ошибка при извлечении информации о метро: {e}")

        return metro_info

    def extract_apartment_params_from_api(self, item):
        """Извлечение параметров квартиры из API"""
        rooms = None
        area = None

        try:
            params = item.get('params', {})

            # Поиск количества комнат
            if 'rooms' in params:
                rooms = int(params['rooms'])
            else:
                title = item.get('title', '').lower()
                room_match = re.search(r'(\d+)-к', title)
                if room_match:
                    rooms = int(room_match.group(1))

            # Поиск площади
            if 'area' in params:
                area = float(params['area'])
            else:
                full_text = item.get('title', '') + ' ' + item.get('description', '')
                area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*м²', full_text)
                if area_match:
                    area = float(area_match.group(1).replace(',', '.'))

        except Exception as e:
            print(f"Ошибка при извлечении параметров: {e}")

        return rooms, area

    def get_apartments_html_fallback(self):
        """Резервный метод парсинга через HTML"""
        try:
            response = requests.get(AVITO_SEARCH_URL, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            apartments = []

            apartment_cards = soup.find_all('div', {'data-marker': 'item'})

            for card in apartment_cards:
                apartment_data = self.parse_apartment_card_updated(card)
                if apartment_data and self.meets_criteria(apartment_data):
                    apartments.append(apartment_data)

            return apartments

        except Exception as e:
            print(f"Ошибка при HTML парсинге: {e}")
            return []

    def parse_apartment_card_updated(self, card):
        """Обновленный парсинг HTML карточки"""
        try:
            # Проверка даты публикации - СЕГОДНЯ И ВЧЕРА
            date_elem = card.find('div', {'data-marker': 'item-date'})
            listing_age = "📅 Недавно"  # По умолчанию

            if date_elem:
                if not self.is_recent_from_text(date_elem.text):
                    return None
                listing_age = self.format_date_from_text(date_elem.text)

            # Заголовок
            title_elem = card.find('a', {'data-marker': 'item-title'})
            title = title_elem.text.strip() if title_elem else "Без названия"

            # Цена - обновленный селектор
            price_elem = card.find('span', {'data-marker': 'item-price'})
            if not price_elem:
                price_elem = card.find('meta', {'itemprop': 'price'})
                if price_elem:
                    price_value = int(price_elem.get('content', 0))
                    price = f"{price_value:,} ₽"
                else:
                    price = "Цена не указана"
                    price_value = 0
            else:
                price = price_elem.text.strip()
                price_value = self.extract_price_number(price)

            # Местоположение и метро
            address_elem = card.find('div', {'data-marker': 'item-address'})
            location = address_elem.text.strip() if address_elem else "Местоположение не указано"

            # Информация о метро
            metro_info = self.extract_metro_from_html(card)

            # Ссылка
            url = self.base_url + title_elem['href'] if title_elem and title_elem.get('href') else ""

            # Изображение
            img_elem = card.find('img', {'data-marker': 'item-photo'})
            if not img_elem:
                img_elem = card.find('img')
            image_url = img_elem['src'] if img_elem else ""

            # Описание
            desc_elem = card.find('div', {'data-marker': 'item-specific-params'})
            if not desc_elem:
                desc_elem = card.find('p', class_='item-description-text')
            description = desc_elem.text.strip() if desc_elem else ""

            # Параметры квартиры
            rooms, area = self.extract_apartment_params(title, description)

            return {
                'title': title,
                'price': price,
                'price_num': price_value,
                'location': location,
                'metro_info': metro_info,
                'url': url,
                'image_url': image_url,
                'description': description,
                'rooms': rooms,
                'area': area,
                'listing_age': listing_age
            }

        except Exception as e:
            print(f"Ошибка при парсинге HTML карточки: {e}")
            return None

    def is_recent_from_text(self, date_text):
        """Проверка, что дата из текста - сегодня или вчера"""
        date_text = date_text.lower().strip()

        # Сегодняшние
        today_keywords = ['сегодня', 'только что', 'минут назад', 'час назад', 'часа назад', 'часов назад']

        # Вчерашние
        yesterday_keywords = ['вчера']

        return (any(keyword in date_text for keyword in today_keywords) or
                any(keyword in date_text for keyword in yesterday_keywords))

    def format_date_from_text(self, date_text):
        """Форматирование даты из текста для отображения"""
        date_text = date_text.lower().strip()

        if 'только что' in date_text or 'минут назад' in date_text:
            return "📅 Только что"
        elif any(word in date_text for word in ['час назад', 'часа назад', 'часов назад']):
            return "📅 Несколько часов назад"
        elif 'сегодня' in date_text:
            return "📅 Сегодня"
        elif 'вчера' in date_text:
            return "📅 Вчера"
        else:
            return "📅 Недавно"

    # Остальные методы остаются без изменений...
    def extract_metro_from_html(self, card):
        """Извлечение информации о метро из HTML"""
        metro_info = {'stations': [], 'time': None}

        try:
            metro_elems = card.find_all('span', string=re.compile('мин|метро', re.I))

            for elem in metro_elems:
                text = elem.text.lower()

                time_match = re.search(r'(\d+)\s*мин', text)
                if time_match:
                    metro_info['time'] = int(time_match.group(1))

                for station in TARGET_METRO_STATIONS:
                    if station in text:
                        metro_info['stations'].append(station)

            full_text = card.get_text().lower()
            for station in TARGET_METRO_STATIONS:
                if station in full_text and station not in metro_info['stations']:
                    metro_info['stations'].append(station)

        except Exception as e:
            print(f"Ошибка при извлечении метро из HTML: {e}")

        return metro_info

    def extract_apartment_params(self, title, description):
        """Извлечение количества комнат и площади"""
        rooms = None
        area = None

        room_patterns = [r'(\d+)-к', r'(\d+)\s*комн', r'(\d+)-комн']

        for pattern in room_patterns:
            match = re.search(pattern, title.lower())
            if match:
                rooms = int(match.group(1))
                break

        area_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*м²',
            r'(\d+(?:[.,]\d+)?)\s*кв\.?м',
            r'площадь[:\s]+(\d+(?:[.,]\d+)?)'
        ]

        full_text = title + ' ' + description
        for pattern in area_patterns:
            match = re.search(pattern, full_text.lower())
            if match:
                area = float(match.group(1).replace(',', '.'))
                break

        return rooms, area

    def extract_price_number(self, price_text):
        """Извлечение числового значения цены"""
        try:
            numbers = re.findall(r'\d+', price_text.replace(' ', ''))
            if numbers:
                return int(''.join(numbers))
        except:
            pass
        return None

    def meets_criteria(self, apartment_data):
        """Проверка соответствия критериям"""
        try:
            if apartment_data.get('price_num') and apartment_data['price_num'] > FILTER_CRITERIA['max_price']:
                return False

            if apartment_data.get('area') and apartment_data['area'] < FILTER_CRITERIA['min_area']:
                return False

            if apartment_data.get('rooms') and apartment_data['rooms'] not in FILTER_CRITERIA['rooms']:
                return False

            metro_time = apartment_data['metro_info'].get('time')
            if metro_time and metro_time > FILTER_CRITERIA['max_metro_time']:
                return False

            metro_stations = apartment_data['metro_info'].get('stations', [])
            if metro_stations:
                return any(station in TARGET_METRO_STATIONS for station in metro_stations)
            else:
                full_text = (apartment_data.get('title', '') + ' ' +
                             apartment_data.get('description', '')).lower()
                return any(station in full_text for station in TARGET_METRO_STATIONS)

        except Exception as e:
            print(f"Ошибка при проверке критериев: {e}")
            return True

    def add_random_delay(self):
        """Случайная задержка между запросами"""
        time.sleep(random.uniform(5, 12))
