import schedule
import time
from datetime import datetime
from avito_scraper import AvitoScraper
from telegram_bot import TelegramBot
from database import ApartmentDB
from config import CHECK_INTERVAL


class ApartmentMonitor:
    def __init__(self):
        self.scraper = AvitoScraper()
        self.bot = TelegramBot()
        self.db = ApartmentDB()

    def check_new_apartments(self):
        """Основная функция проверки новых квартир"""
        current_time = datetime.now()
        print(f"[{current_time}] 🔍 Проверка новых квартир за сегодня и вчера...")

        try:
            apartments = self.scraper.get_apartments()
            new_apartments_count = 0

            for apartment in apartments:
                if self.db.is_new_apartment(apartment):
                    print(
                        f"✅ Найдена новая квартира: {apartment['title'][:50]}... ({apartment.get('listing_age', 'недавно')})")

                    self.bot.send_apartment_notification(apartment)
                    self.db.add_apartment(apartment)

                    new_apartments_count += 1
                    time.sleep(3)

            if new_apartments_count > 0:
                print(f"📊 Найдено новых квартир: {new_apartments_count}")
                self.bot.send_status_message(f"✅ Найдено {new_apartments_count} новых квартир")
            else:
                print("📭 Новых квартир не найдено")

            self.scraper.add_random_delay()

        except Exception as e:
            error_msg = f"❌ Ошибка при проверке: {str(e)}"
            print(error_msg)
            self.bot.send_message(error_msg)

    def daily_cleanup(self):
        """Ежедневная очистка базы данных"""
        try:
            deleted = self.db.clean_old_apartments(days_old=7)
            if deleted > 0:
                print(f"🗑️ Удалено старых записей: {deleted}")
        except Exception as e:
            print(f"Ошибка при очистке базы: {e}")

    def start_monitoring(self):
        """Запуск мониторинга"""
        print("🚀 Запуск мониторинга квартир на Avito...")
        print("📅 Режим работы: отслеживаются СЕГОДНЯШНИЕ И ВЧЕРАШНИЕ объявления")

        self.bot.send_status_message("🚀 Мониторинг запущен ✅\n📅 Режим тестирования: сегодня + вчера")

        schedule.every(CHECK_INTERVAL).seconds.do(self.check_new_apartments)
        schedule.every().day.at("06:00").do(self.daily_cleanup)

        # Первоначальная проверка
        self.check_new_apartments()

        # Основной цикл
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    monitor = ApartmentMonitor()
    monitor.start_monitoring()
