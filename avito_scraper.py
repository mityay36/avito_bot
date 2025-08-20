import requests
import time
import random
import re
import pickle
import os
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
from config import (
    HEADERS, AVITO_SEARCH_URL, TARGET_METRO_STATIONS,
    FILTER_CRITERIA, PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS
)



class AdvancedAvitoScraper:
    def __init__(self):
        self.headers = HEADERS.copy()
        self.base_url = "https://www.avito.ru"
        self.session = requests.Session()
        self.driver = None
        self.cookies_file = "avito_cookies.pkl"
        self.proxy_index = 0
        self.blocked_proxies = set()
        self.ip_blocked = False
        self.last_block_time = 0
        self.block_count = 0

        # Прокси список (добавьте рабочие прокси)
        self.proxies = [
            # Формат: {'host': 'ip', 'port': 'port', 'username': 'user', 'password': 'pass'}
            {'host': PROXY_HOST, 'port': PROXY_PORT, 'username': PROXY_USER, 'password': PROXY_PASS},
        ]
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

        print(f"[AdvancedScraper] 🚀 Инициализация с {len(self.proxies)} прокси")

    def setup_driver(self, use_proxy=True):
        """✅ Исправленная настройка драйвера с авторизованным прокси"""
        try:
            options = uc.ChromeOptions()

            # Базовые настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')

            # User-Agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')

            # ✅ Настройка авторизованного прокси для Selenium
            if use_proxy and self.proxies:
                proxy = self.get_next_proxy()
                if proxy:
                    proxy_url = self.format_proxy_url(proxy)
                    options.add_argument(f'--proxy-server={proxy_url}')
                    print(f"[AdvancedScraper] 🌐 Selenium прокси: {proxy['host']}:{proxy['port']}")
                    self.current_proxy = proxy

            options.add_argument('--window-size=1280,720')

            # Создаем драйвер
            self.driver = uc.Chrome(options=options)

            # Загружаем cookies
            self.load_cookies()

            print(f"[AdvancedScraper] ✅ Драйвер настроен с авторизованным прокси")
            return True

        except Exception as e:
            print(f"[AdvancedScraper] ❌ Ошибка настройки драйвера: {e}")
            return False

    def get_next_proxy(self):
        """Получить следующий прокси с правильным форматом"""
        if not self.proxies:
            return None

        available_proxies = [p for p in self.proxies
                             if f"{p['host']}:{p['port']}" not in self.blocked_proxies]

        if not available_proxies:
            print("[AdvancedScraper] ⚠️ Все прокси заблокированы, сброс списка")
            self.blocked_proxies.clear()
            available_proxies = self.proxies

        return random.choice(available_proxies)

    def format_proxy_url(self, proxy):
        """Форматирование прокси URL с авторизацией"""
        if 'username' in proxy and 'password' in proxy:
            return f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        else:
            return f"http://{proxy['host']}:{proxy['port']}"

    def load_cookies(self):
        """Загрузка сохраненных cookies"""
        if os.path.exists(self.cookies_file):
            try:
                if self.driver.current_url == 'data:,':
                    self.driver.get("https://www.avito.ru")
                    time.sleep(2)

                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            continue
                print(f"[AdvancedScraper] 🍪 Загружено {len(cookies)} cookies")
            except Exception as e:
                print(f"[AdvancedScraper] ⚠️ Ошибка загрузки cookies: {e}")

    def save_cookies(self):
        """Сохранение текущих cookies"""
        if self.driver:
            try:
                cookies = self.driver.get_cookies()
                with open(self.cookies_file, 'wb') as f:
                    pickle.dump(cookies, f)
                print(f"[AdvancedScraper] 💾 Сохранено {len(cookies)} cookies")
            except Exception as e:
                print(f"[AdvancedScraper] ❌ Ошибка сохранения cookies: {e}")

    def check_blocking(self):
        """Проверка на блокировку"""
        if not self.driver:
            return False

        page_source = self.driver.page_source.lower()

        blocking_indicators = [
            'проверка безопасности',
            'captcha',
            'доступ ограничен',
            'заблокирован',
            'robot',
            'bot',
            'автоматический запрос',
            'подозрительная активность'
        ]

        for indicator in blocking_indicators:
            if indicator in page_source:
                print(f"[AdvancedScraper] 🚫 Обнаружена блокировка: {indicator}")
                return True

        # Проверяем статус страницы
        try:
            current_url = self.driver.current_url
            if 'blocked' in current_url or 'captcha' in current_url:
                return True
        except:
            pass

        return False

    def handle_blocking(self):
        """Обработка блокировки"""
        self.ip_blocked = True
        self.last_block_time = time.time()
        self.block_count += 1

        print(f"[AdvancedScraper] 🚫 IP заблокирован (блокировка #{self.block_count})")

        # Закрываем текущий драйвер
        if self.driver:
            self.driver.quit()
            self.driver = None

        # Добавляем текущий прокси в заблокированные
        if hasattr(self, 'current_proxy'):
            proxy_string = f"{self.current_proxy['host']}:{self.current_proxy['port']}"
            self.blocked_proxies.add(proxy_string)
            print(f"[AdvancedScraper] ❌ Прокси {proxy_string} добавлен в черный список")

        # Возвращаем информацию о блокировке для уведомления
        return {
            'blocked': True,
            'block_count': self.block_count,
            'timestamp': datetime.now(),
            'blocked_proxies': len(self.blocked_proxies)
        }

    def get_apartments(self):
        """Главный метод получения квартир"""
        try:
            # Проверяем блокировку
            if self.ip_blocked and (time.time() - self.last_block_time) < 1800:  # 30 минут
                remaining = 1800 - (time.time() - self.last_block_time)
                print(f"[AdvancedScraper] ⏰ Ждем снятия блокировки: {remaining / 60:.1f} мин")
                return []

            # Настраиваем драйвер
            if not self.driver or self.ip_blocked:
                if not self.setup_driver():
                    print("[AdvancedScraper] ❌ Не удалось настроить драйвер, используем fallback")
                    return self.get_apartments_fallback()
                self.ip_blocked = False

            # Переходим на страницу
            url = AVITO_SEARCH_URL if AVITO_SEARCH_URL else "https://www.avito.ru/moskva/kvartiry/sdam"
            print(f"[AdvancedScraper] 🌐 Переход на: {url[:80]}...")

            self.driver.get(url)
            time.sleep(random.uniform(3, 5))

            # Проверяем на блокировку
            if self.check_blocking():
                return [self.handle_blocking()]

            # ✅ Упрощенное ожидание загрузки
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, '[data-marker="item"]')) > 0
                )
            except TimeoutException:
                print("[AdvancedScraper] ⚠️ Таймаут, пробуем парсить что есть")

            # Парсим
            apartments = self.parse_apartments()
            self.save_cookies()

            print(f"[AdvancedScraper] ✅ Найдено квартир: {len(apartments)}")
            return apartments

        except Exception as e:
            print(f"[AdvancedScraper] ❌ Ошибка: {e}")
            return self.get_apartments_fallback()

    def parse_apartments(self):
        """Парсинг квартир с помощью Selenium"""
        apartments = []

        try:
            # Получаем все карточки объявлений
            apartment_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-marker="item"]')
            print(f"[AdvancedScraper] 🏠 Найдено элементов: {len(apartment_elements)}")

            for i, element in enumerate(apartment_elements[:15]):  # Ограничиваем количество
                try:
                    print(f"[AdvancedScraper] 🔍 Обработка элемента {i + 1}")

                    # Заголовок
                    title_elem = element.find_element(By.CSS_SELECTOR, '[data-marker="item-title"]')
                    title = title_elem.text.strip() if title_elem else "Без названия"

                    # Ссылка
                    url = title_elem.get_attribute('href') if title_elem else ""

                    # Цена
                    try:
                        price_elem = element.find_element(By.CSS_SELECTOR, '[data-marker="item-price"]')
                        price = price_elem.text.strip()
                        price_num = self.extract_price_number(price)
                    except:
                        price = "Цена не указана"
                        price_num = 0

                    # Адрес
                    try:
                        address_elem = element.find_element(By.CSS_SELECTOR, '[data-marker="item-address"]')
                        location = address_elem.text.strip()
                    except:
                        location = "Адрес не указан"

                    # Описание
                    try:
                        desc_elem = element.find_element(By.CSS_SELECTOR, '[data-marker="item-specific-params"]')
                        description = desc_elem.text.strip()
                    except:
                        description = ""

                    # Извлекаем параметры
                    rooms, area = self.extract_apartment_params(title, description)
                    metro_info = self.extract_metro_info(element.text)

                    apartment_data = {
                        'title': title,
                        'price': price,
                        'price_num': price_num,
                        'location': location,
                        'metro_info': metro_info,
                        'url': url,
                        'description': description,
                        'rooms': rooms,
                        'area': area,
                        'listing_age': "📅 Недавно"
                    }

                    # Проверяем критерии
                    if self.meets_criteria(apartment_data):
                        apartments.append(apartment_data)
                        print(f"[AdvancedScraper] ✅ Добавлено: {title[:50]}...")

                    # Небольшая задержка между элементами
                    time.sleep(random.uniform(0.3, 0.8))

                except Exception as e:
                    print(f"[AdvancedScraper] ⚠️ Ошибка обработки элемента {i + 1}: {e}")
                    continue

        except Exception as e:
            print(f"[AdvancedScraper] ❌ Ошибка парсинга: {e}")

        return apartments

    def extract_price_number(self, price_text):
        """Извлечение числового значения цены"""
        try:
            numbers = re.findall(r'\d+', price_text.replace(' ', ''))
            if numbers:
                return int(''.join(numbers))
        except:
            pass
        return 0

    def extract_apartment_params(self, title, description):
        """Извлечение параметров квартиры"""
        rooms = None
        area = None

        # Комнаты
        if 'студия' in title.lower():
            rooms = 0
        else:
            room_match = re.search(r'(\d+)-к', title.lower())
            if room_match:
                rooms = int(room_match.group(1))

        # Площадь
        area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*м²', (title + ' ' + description))
        if area_match:
            area = float(area_match.group(1).replace(',', '.'))

        return rooms, area

    def extract_metro_info(self, text):
        """Извлечение информации о метро"""
        metro_info = {'stations': [], 'time': None}
        text_lower = text.lower()

        # Время до метро
        time_match = re.search(r'(\d+)\s*мин', text_lower)
        if time_match:
            metro_info['time'] = int(time_match.group(1))

        # Станции метро
        for station in TARGET_METRO_STATIONS:
            if station in text_lower:
                metro_info['stations'].append(station)

        return metro_info

    def meets_criteria(self, apartment_data):
        """Проверка критериев"""
        try:
            # Цена
            if apartment_data.get('price_num') and apartment_data['price_num'] > FILTER_CRITERIA['max_price']:
                return False

            # Площадь
            if apartment_data.get('area') and apartment_data['area'] < FILTER_CRITERIA['min_area']:
                return False

            # Комнаты
            if apartment_data.get('rooms') and apartment_data['rooms'] not in FILTER_CRITERIA['rooms']:
                return False

            # Время до метро
            metro_time = apartment_data['metro_info'].get('time')
            if metro_time and metro_time > FILTER_CRITERIA['max_metro_time']:
                return False

            # Станции метро
            metro_stations = apartment_data['metro_info'].get('stations', [])
            if metro_stations:
                return any(station in TARGET_METRO_STATIONS for station in metro_stations)

            # Поиск в тексте
            full_text = (apartment_data.get('title', '') + ' ' +
                         apartment_data.get('description', '') + ' ' +
                         apartment_data.get('location', '')).lower()

            return any(station in full_text for station in TARGET_METRO_STATIONS)

        except Exception as e:
            print(f"[AdvancedScraper] ❌ Ошибка проверки критериев: {e}")
            return False

    def cleanup(self):
        """Очистка ресурсов"""
        if self.driver:
            self.save_cookies()
            self.driver.quit()
            print("[AdvancedScraper] 🧹 Ресурсы очищены")

    def get_apartments_fallback(self):
        """Fallback на requests с авторизованным прокси"""
        print("[AdvancedScraper] 🔄 Fallback на requests с авторизацией...")

        try:
            url = AVITO_SEARCH_URL if AVITO_SEARCH_URL else "https://www.avito.ru/moskva/kvartiry/sdam"

            # ✅ Настройка авторизованного прокси для requests
            proxies_dict = None
            if self.proxies:
                proxy = self.get_next_proxy()
                if proxy:
                    proxy_url = self.format_proxy_url(proxy)
                    proxies_dict = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                    print(
                        f"[AdvancedScraper] 🌐 Requests прокси: {proxy['username']}:***@{proxy['host']}:{proxy['port']}")

            # Делаем запрос
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=proxies_dict,
                timeout=15
            )

            if response.status_code == 429:
                return [self.handle_blocking()]

            if response.status_code != 200:
                print(f"[AdvancedScraper] ❌ HTTP {response.status_code}")
                return []

            # Парсим через BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            cards = soup.find_all('div', {'data-marker': 'item'})

            apartments = []
            for card in cards[:5]:
                try:
                    apartment_data = self.parse_card_with_bs4(card)
                    if apartment_data and self.meets_criteria(apartment_data):
                        apartments.append(apartment_data)
                except:
                    continue

            print(f"[AdvancedScraper] 📊 Fallback результат: {len(apartments)} квартир")
            return apartments

        except Exception as e:
            print(f"[AdvancedScraper] ❌ Fallback ошибка: {e}")
            return []

    def parse_card_with_bs4(self, card):
        """Парсинг карточки через BeautifulSoup"""
        try:
            title_elem = card.find('a', {'data-marker': 'item-title'})
            title = title_elem.text.strip() if title_elem else "Без названия"

            price_elem = card.find('span', {'data-marker': 'item-price'})
            price = price_elem.text.strip() if price_elem else "Цена не указана"
            price_num = self.extract_price_number(price)

            address_elem = card.find('div', {'data-marker': 'item-address'})
            location = address_elem.text.strip() if address_elem else "Адрес не указан"

            url = title_elem.get('href', '') if title_elem else ''
            if url and not url.startswith('http'):
                url = self.base_url + url

            description = card.get_text()
            rooms, area = self.extract_apartment_params(title, description)
            metro_info = self.extract_metro_info(description)

            return {
                'title': title,
                'price': price,
                'price_num': price_num,
                'location': location,
                'metro_info': metro_info,
                'url': url,
                'description': description,
                'rooms': rooms,
                'area': area,
                'listing_age': "📅 Недавно"
            }
        except Exception as e:
            print(f"[AdvancedScraper] ❌ BS4 парсинг: {e}")
            return None
