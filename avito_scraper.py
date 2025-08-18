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
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        ]

        self.request_count = 0
        self.last_request_time = 0
        self.session = requests.Session()

    print(f"[Scraper] Инициализация с критериями: {FILTER_CRITERIA}")

    def get_apartments(self):
        """Получение списка квартир с Avito через API"""
        try:
            # Используем внутренний API Avito для более стабильной работы
            api_url = self.convert_search_url_to_api()
            print(f"[Scraper] API запрос: {api_url}")

            self.smart_delay()
            self.rotate_user_agent()

            response = requests.get(api_url, headers=self.headers)
            print(f"[Scraper] Статус ответа: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            print(f"[Scraper] Получен ответ, ключи: {list(data.keys())}")

            apartments = []

            if 'items' in data:
                items = data['items']
                print(f"[Scraper] Найдено объявлений в API: {len(items)}")

                for i, item in enumerate(items):
                    print(f"\n[Scraper] === Обработка объявления {i + 1}/{len(items)} ===")
                    apartment_data = self.parse_apartment_from_api(item)

                    if apartment_data:
                        print(f"[Scraper] ✅ Объявление распознано: '{apartment_data['title'][:50]}...'")
                        print(
                            f"[Scraper] Цена: {apartment_data['price']}, Площадь: {apartment_data.get('area', 'не указана')} м²")
                        print(
                            f"[Scraper] Метро: {apartment_data['metro_info']['stations'][:2] if apartment_data['metro_info']['stations'] else 'не найдено'}")

                        if self.meets_criteria(apartment_data):
                            apartments.append(apartment_data)
                            print(f"[Scraper] 🎯 ПОДХОДИТ! Добавлено в список")
                        else:
                            print(f"[Scraper] ❌ Не подходит по критериям")
                    else:
                        print(f"[Scraper] ⚠️ Объявление не удалось распознать")

            else:
                print(f"[Scraper] ❌ Ключ 'items' не найден в ответе API")
                print(f"[Scraper] Доступные ключи: {list(data.keys())}")
                if 'error' in data:
                    print(f"[Scraper] Ошибка API: {data['error']}")

            print(f"\n[Scraper] 📊 Итого подходящих квартир: {len(apartments)} из {len(data.get('items', []))}")
            return apartments

        except requests.exceptions.RequestException as e:
            print(f"[Scraper] ❌ Ошибка HTTP запроса: {e}")
            return self.get_apartments_html_fallback()
        except json.JSONDecodeError as e:
            print(f"[Scraper] ❌ Ошибка парсинга JSON: {e}")
            return self.get_apartments_html_fallback()
        except Exception as e:
            print(f"[Scraper] ❌ Неизвестная ошибка при работе с API: {e}")
            return self.get_apartments_html_fallback()

    def convert_search_url_to_api(self):
        """Конвертация URL поиска в API запрос"""
        # Если задан AVITO_SEARCH_URL, используем его напрямую для тестирования
        if AVITO_SEARCH_URL and AVITO_SEARCH_URL.strip():
            print(f"[Scraper] Используем URL из переменной окружения: {AVITO_SEARCH_URL}")
            return AVITO_SEARCH_URL

        # Иначе формируем API URL
        api_url = "https://www.avito.ru/web/1/main/items"

        params = {
            'locationId': '637640',  # Москва
            'categoryId': '24',  # Квартиры
            'params[549]': '1059',  # Аренда
            'params': '1,2',
            'priceMax': str(FILTER_CRITERIA['max_price']),
            'areaMin': str(FILTER_CRITERIA['min_area']),
            'sort': 'date',
            'limit': '50',
            'page': '1'
        }

        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{api_url}?{param_string}"

        print(f"[Scraper] Сформированный API URL: {full_url}")
        return full_url

    def parse_apartment_from_api(self, item):
        """Парсинг квартиры из API ответа"""
        try:
            # Проверка даты - СЕГОДНЯ И ВЧЕРА
            if not self.is_recent_listing(item):
                print(f"[Scraper] ⏰ Объявление пропущено по дате: {item.get('title', 'Без названия')}")
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
                'listing_age': listing_age
            }

        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при парсинге объявления из API: {e}")
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
                is_recent = listing_day == today or listing_day == yesterday
                print(f"[Scraper] Дата объявления: {listing_day}, сегодня: {today}, подходит: {is_recent}")
                return is_recent
            print(f"[Scraper] ⚠️ Временная метка отсутствует")
            return False
        except Exception as e:
            print(f"[Scraper] ❌ Ошибка проверки даты: {e}")
            return False

    def get_listing_age(self, item):
        """Определение возраста объявления для отображения"""
        try:
            timestamp = item.get('sortTimeStamp', 0)
            if timestamp:
                listing_date = datetime.fromtimestamp(timestamp)
                today = datetime.now().date()

                if listing_date.date() == today:
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
            print(f"[Scraper] ❌ Ошибка при извлечении информации о метро: {e}")

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

            print(f"[Scraper] Параметры: комнат={rooms}, площадь={area}")

        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при извлечении параметров: {e}")

        return rooms, area

    def get_apartments_html_fallback(self):
        """Улучшенный HTML парсинг с защитой от блокировки"""
        print(f"[Scraper] 🌐 Запуск HTML парсинга...")

        try:
            url = AVITO_SEARCH_URL if AVITO_SEARCH_URL else "https://www.avito.ru/moskva/kvartiry/sdam"
            print(f"[Scraper] 📡 Запрос к: {url[:100]}...")

            # ✅ Используем сессию с настройками
            response = self.session.get(url, headers=self.headers, timeout=30)

            print(f"[Scraper] 📊 Статус: {response.status_code}, Размер: {len(response.content)} байт")

            # ✅ Проверка на блокировку
            if response.status_code == 429:
                print(f"[Scraper] 🚫 Получена блокировка 429, увеличиваем задержки...")
                self.request_count += 5  # Увеличиваем счетчик для больших задержек
                time.sleep(60)  # Ждем минуту
                return []

            if response.status_code == 403:
                print(f"[Scraper] 🚫 Доступ запрещен (403), возможно IP заблокирован")
                return []

            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            if 'captcha' in response.text.lower() or 'проверка' in response.text.lower():
                print(f"[Scraper] 🔒 Обнаружена капча, прекращаем парсинг")
                return []

            apartments = []
            apartment_cards = soup.find_all('div', {'data-marker': 'item'})
            print(f"[Scraper] 🏠 Найдено HTML карточек: {len(apartment_cards)}")

            if len(apartment_cards) == 0:
                print(f"[Scraper] ⚠️ Карточки не найдены, возможно изменилась структура или блокировка")
                # Сохраним HTML для отладки
                with open('debug_response.html', 'w', encoding='utf-8') as f:
                    f.write(response.text[:5000])
                print(f"[Scraper] 💾 Первые 5000 символов сохранены в debug_response.html")

            for i, card in enumerate(apartment_cards[:20], 1):  # Ограничиваем до 20 для экономии времени
                print(f"[Scraper] 🔍 Обработка карточки {i}/{min(len(apartment_cards), 20)}")
                apartment_data = self.parse_apartment_card_updated(card)

                if apartment_data:
                    if self.meets_criteria(apartment_data):
                        apartments.append(apartment_data)
                        print(f"[Scraper] ✅ Квартира добавлена: {apartment_data['title'][:50]}...")
                    else:
                        print(f"[Scraper] ❌ Не подходит по критериям")

                time.sleep(random.uniform(0.5, 1.5))

            print(f"[Scraper] 📈 Итого найдено подходящих квартир: {len(apartments)}")
            return apartments

        except requests.exceptions.RequestException as e:
            print(f"[Scraper] ❌ Ошибка запроса: {e}")
            if '429' in str(e):
                print(f"[Scraper] 🚫 Слишком много запросов, увеличиваем задержки...")
                self.request_count += 10
                time.sleep(120)  # Ждем 2 минуты
            return []
        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при HTML парсинге: {e}")
            return []

    def parse_apartment_card_updated(self, card):
        """Обновленный парсинг HTML карточки с улучшенными селекторами"""
        try:
            # Заголовок - пробуем разные селекторы
            title_elem = (card.find('a', {'data-marker': 'item-title'}) or
                          card.find('h3') or
                          card.find('a', class_=re.compile('title')))
            title = title_elem.text.strip() if title_elem else "Без названия"

            # Цена - улучшенные селекторы
            price_elem = (card.find('span', {'data-marker': 'item-price'}) or
                          card.find('meta', {'itemprop': 'price'}) or
                          card.find('span', class_=re.compile('price')))

            if price_elem:
                if price_elem.name == 'meta':
                    price_value = int(price_elem.get('content', 0))
                    price = f"{price_value:,} ₽"
                else:
                    price = price_elem.text.strip()
                    price_value = self.extract_price_number(price)
            else:
                price = "Цена не указана"
                price_value = 0

            # Местоположение
            address_elem = (card.find('div', {'data-marker': 'item-address'}) or
                            card.find('span', class_=re.compile('address')))
            location = address_elem.text.strip() if address_elem else "Местоположение не указано"

            # Информация о метро - улучшенный поиск
            metro_info = self.extract_metro_from_html(card)

            # Ссылка
            url = ""
            if title_elem and title_elem.get('href'):
                href = title_elem['href']
                url = href if href.startswith('http') else self.base_url + href

            # Изображение
            img_elem = (card.find('img', {'data-marker': 'item-photo'}) or
                        card.find('img'))
            image_url = img_elem.get('src', '') if img_elem else ""

            # Описание - пробуем найти в разных местах
            desc_elem = (card.find('div', {'data-marker': 'item-specific-params'}) or
                         card.find('p', class_=re.compile('description')) or
                         card.find('div', class_=re.compile('description')))
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
                'listing_age': "📅 Недавно"
            }

        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при парсинге карточки: {e}")
            return None

    def extract_metro_from_html(self, card):
        """Улучшенное извлечение информации о метро из HTML"""
        metro_info = {'stations': [], 'time': None}

        try:
            # Получаем весь текст карточки
            full_text = card.get_text().lower()

            # Поиск времени до метро с разными вариантами
            time_patterns = [
                r'(\d+)\s*мин(?:ут)?(?:\s*до\s*м(?:етро|\.)?)',
                r'(\d+)\s*мин(?:ут)?(?:\s*пешком)',
                r'(\d+)\s*мин(?:ут)?(?:\s*м\.)',
                r'(\d+)\s*м\.',
            ]

            for pattern in time_patterns:
                matches = re.findall(pattern, full_text)
                if matches:
                    metro_info['time'] = min(int(t) for t in matches)
                    print(f"[Scraper] ⏰ Найдено время до метро: {metro_info['time']} мин")
                    break

            # Поиск станций метро с вариациями
            found_stations = []
            for station in TARGET_METRO_STATIONS:
                patterns = [
                    rf'\b{re.escape(station)}\b',
                    rf'\bм\.\s*{re.escape(station)}\b',
                    rf'\bметро\s+{re.escape(station)}\b',
                    rf'\b{re.escape(station)}\s+метро\b',
                ]

                for pattern in patterns:
                    if re.search(pattern, full_text, re.IGNORECASE):
                        if station not in found_stations:
                            found_stations.append(station)
                            print(f"[Scraper] 🎯 Найдена станция: {station}")
                        break

            metro_info['stations'] = found_stations

        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при извлечении метро: {e}")

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
        """Проверка соответствия критериям с подробным логированием"""
        try:
            print(f"[Scraper] 🔍 Проверка: {apartment_data['title'][:50]}...")

            # Проверка цены
            if apartment_data.get('price_num') and apartment_data['price_num'] > FILTER_CRITERIA['max_price']:
                print(f"[Scraper] ❌ Превышена цена: {apartment_data['price']} > {FILTER_CRITERIA['max_price']}")
                return False

            # Проверка площади
            if apartment_data.get('area') and apartment_data['area'] < FILTER_CRITERIA['min_area']:
                print(f"[Scraper] ❌ Мало площади: {apartment_data['area']} < {FILTER_CRITERIA['min_area']}")
                return False

            # Проверка комнат
            if apartment_data.get('rooms') and apartment_data['rooms'] not in FILTER_CRITERIA['rooms']:
                print(
                    f"[Scraper] ❌ Неподходящее количество комнат: {apartment_data['rooms']} не в {FILTER_CRITERIA['rooms']}")
                return False

            # Проверка времени до метро
            metro_time = apartment_data['metro_info'].get('time')
            if metro_time and metro_time > FILTER_CRITERIA['max_metro_time']:
                print(f"[Scraper] ❌ Далеко до метро: {metro_time} мин > {FILTER_CRITERIA['max_metro_time']}")
                return False

            # Проверка станций метро
            metro_stations = apartment_data['metro_info'].get('stations', [])

            if metro_stations:
                matches = [s for s in metro_stations if s in TARGET_METRO_STATIONS]
                if matches:
                    print(f"[Scraper] ✅ Подходящие станции: {matches}")
                    print(f"[Scraper] ✅ ВСЕ КРИТЕРИИ ПРОЙДЕНЫ!")
                    return True
                else:
                    print(f"[Scraper] ❌ Неподходящие станции: {metro_stations}")
                    return False
            else:
                # Ищем в тексте
                full_text = (apartment_data.get('title', '') + ' ' +
                             apartment_data.get('description', '') + ' ' +
                             apartment_data.get('location', '')).lower()

                found_stations = []
                for station in TARGET_METRO_STATIONS:
                    if station in full_text:
                        found_stations.append(station)

                if found_stations:
                    print(f"[Scraper] ✅ Станции найдены в тексте: {found_stations}")
                    print(f"[Scraper] ✅ ВСЕ КРИТЕРИИ ПРОЙДЕНЫ!")
                    return True
                else:
                    print(f"[Scraper] ❌ Станции метро не найдены")
                    return False

        except Exception as e:
            print(f"[Scraper] ❌ Ошибка при проверке критериев: {e}")
            return False

    def add_random_delay(self):
        """Случайная задержка между запросами"""
        delay = random.uniform(5, 12)
        print(f"[Scraper] ⏳ Задержка {delay:.1f} секунд...")
        time.sleep(delay)

    def smart_delay(self):
        """Умная задержка с увеличением при ошибках"""
        current_time = time.time()

        # Базовая задержка
        base_delay = 15 + (self.request_count * 2)  # Увеличиваем задержку с каждым запросом

        # Если прошлый запрос был недавно, ждем дольше
        time_since_last = current_time - self.last_request_time
        if time_since_last < base_delay:
            additional_delay = base_delay - time_since_last
            print(f"[Scraper] ⏳ Дополнительная задержка: {additional_delay:.1f} сек")
            time.sleep(additional_delay)

        # Случайная задержка для имитации человека
        random_delay = random.uniform(5, 15)
        print(f"[Scraper] ⏰ Случайная задержка: {random_delay:.1f} сек")
        time.sleep(random_delay)

        self.last_request_time = time.time()
        self.request_count += 1

    def rotate_user_agent(self):
        """Ротация User-Agent и других заголовков"""
        self.headers['User-Agent'] = random.choice(self.user_agents)

        # ✅ Дополнительные заголовки для маскировки
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice([
                'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'ru-RU,ru;q=0.9,en;q=0.8',
                'ru,en-US;q=0.7,en;q=0.3'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })

        print(f"[Scraper] 🔄 User-Agent: {self.headers['User-Agent'][:50]}...")
