import sqlite3
import hashlib
from datetime import datetime, timedelta


class ApartmentDB:
    def __init__(self, db_name='apartments.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apartments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apartment_id TEXT UNIQUE,
                avito_id TEXT,
                title TEXT,
                price TEXT,
                price_num INTEGER,
                location TEXT,
                url TEXT,
                image_url TEXT,
                description TEXT,
                rooms INTEGER,
                area REAL,
                metro_stations TEXT,
                metro_time INTEGER,
                date_published TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def generate_apartment_id(self, apartment_data):
        """Генерация уникального ID для квартиры"""
        # Используем несколько параметров для уникальности
        unique_string = f"{apartment_data.get('id', '')}{apartment_data['title']}{apartment_data.get('price_num', 0)}{apartment_data['location']}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def is_new_apartment(self, apartment_data):
        """Проверка, является ли квартира новой"""
        apartment_id = self.generate_apartment_id(apartment_data)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Проверяем по ID и по Avito ID (если есть)
        if apartment_data.get('id'):
            cursor.execute(
                'SELECT id FROM apartments WHERE apartment_id = ? OR avito_id = ?',
                (apartment_id, apartment_data['id'])
            )
        else:
            cursor.execute('SELECT id FROM apartments WHERE apartment_id = ?', (apartment_id,))

        result = cursor.fetchone()
        conn.close()

        return result is None

    def add_apartment(self, apartment_data):
        """Добавление новой квартиры в базу"""
        apartment_id = self.generate_apartment_id(apartment_data)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Подготавливаем данные
        metro_stations_str = ','.join(apartment_data['metro_info'].get('stations', []))
        date_published = None

        if apartment_data.get('date_published'):
            try:
                date_published = datetime.fromtimestamp(apartment_data['date_published'])
            except:
                pass

        cursor.execute('''
            INSERT OR IGNORE INTO apartments 
            (apartment_id, avito_id, title, price, price_num, location, url, image_url, 
             description, rooms, area, metro_stations, metro_time, date_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            apartment_id,
            apartment_data.get('id'),
            apartment_data['title'],
            apartment_data['price'],
            apartment_data.get('price_num'),
            apartment_data['location'],
            apartment_data['url'],
            apartment_data['image_url'],
            apartment_data['description'],
            apartment_data.get('rooms'),
            apartment_data.get('area'),
            metro_stations_str,
            apartment_data['metro_info'].get('time'),
            date_published
        ))

        conn.commit()
        conn.close()

    def clean_old_apartments(self, days_old=7):
        """Удаление старых записей из базы"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM apartments WHERE created_at < ?', (cutoff_date,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        return deleted
