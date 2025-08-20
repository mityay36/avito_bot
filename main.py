import schedule
import time
from datetime import datetime
from avito_scraper import AdvancedAvitoScraper
from telegram_bot import TelegramBot
from database import ApartmentDB
from config import CHECK_INTERVAL


class AdvancedApartmentMonitor:
    def __init__(self):
        self.scraper = AdvancedAvitoScraper()
        self.bot = TelegramBot()
        self.db = ApartmentDB()
        self.last_block_notification = 0
        self.consecutive_blocks = 0

    def check_new_apartments(self):
        """Основная функция проверки новых квартир"""
        current_time = datetime.now()
        print(f"[{current_time}] 🔍 Расширенная проверка квартир...")

        try:
            results = self.scraper.get_apartments()
            new_apartments_count = 0

            # Проверяем на блокировку
            for result in results:
                if isinstance(result, dict) and result.get('blocked'):
                    self.handle_block_notification(result)
                    return  # Прекращаем обработку при блокировке

                # Обычная обработка квартир
                if self.db.is_new_apartment(result):
                    print(f"✅ Новая квартира: {result['title'][:50]}...")

                    self.bot.send_apartment_notification(result)
                    self.db.add_apartment(result)

                    new_apartments_count += 1
                    time.sleep(2)

            # Сброс счетчика блокировок при успешной работе
            self.consecutive_blocks = 0

            if new_apartments_count > 0:
                print(f"📊 Найдено новых квартир: {new_apartments_count}")
                self.bot.send_status_message(f"✅ Найдено {new_apartments_count} новых квартир")
            else:
                print("📭 Новых квартир не найдено")

        except Exception as e:
            error_msg = f"❌ Критическая ошибка: {str(e)}"
            print(error_msg)
            self.bot.send_message(error_msg)

    def handle_block_notification(self, block_info):
        """Обработка уведомлений о блокировке"""
        self.consecutive_blocks += 1
        current_time = time.time()

        # Отправляем уведомление не чаще чем раз в 30 минут
        if current_time - self.last_block_notification > 1800:  # 30 минут

            block_message = f"""
🚫 **AVITO БЛОКИРУЕТ IP АДРЕС**

⏰ **Время блокировки:** {block_info['timestamp'].strftime('%H:%M:%S')}
🔢 **Номер блокировки:** #{block_info['block_count']}
🎯 **Подряд блокировок:** {self.consecutive_blocks}
🌐 **Заблокировано прокси:** {block_info['blocked_proxies']}

🔄 **Действия:**
• Переключение на новый прокси
• Очистка cookies и сессии  
• Пауза на 1 час для снятия блокировки

⚠️ **Рекомендации:**
• Проверьте качество прокси
• Увеличьте интервалы между запросами
• Рассмотрите использование мобильных прокси

🤖 Бот продолжит работу автоматически
            """

            self.bot.send_message(block_message.strip())
            self.last_block_notification = current_time

            print(f"[Monitor] 📨 Отправлено уведомление о блокировке #{block_info['block_count']}")

    def daily_cleanup(self):
        """Ежедневная очистка"""
        try:
            deleted = self.db.clean_old_apartments(days_old=7)
            if deleted > 0:
                print(f"🗑️ Удалено старых записей: {deleted}")

            # Сброс статистики блокировок
            self.consecutive_blocks = 0

        except Exception as e:
            print(f"Ошибка при очистке базы: {e}")

    def start_monitoring(self):
        """Запуск расширенного мониторинга"""
        print("🚀 Запуск расширенного мониторинга Avito...")
        print("🛡️ Активна защита от блокировок с прокси и cookies")

        self.bot.send_status_message("""
🚀 **Расширенный мониторинг запущен!**

🛡️ **Новые возможности:**
• Selenium с маскировкой под браузер
• Автоматическая ротация прокси
• Управление cookies
• Умная обработка блокировок IP
• Уведомления о статусе работы

⚡ Готов к работе в усложненных условиях!
        """)

        # Увеличиваем интервал для стабильной работы
        interval = max(CHECK_INTERVAL, 1800)  # Минимум 30 минут
        schedule.every(interval).seconds.do(self.check_new_apartments)
        schedule.every().day.at("06:00").do(self.daily_cleanup)

        # Первоначальная проверка
        self.check_new_apartments()

        # Основной цикл
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем расписание каждую минуту
            except KeyboardInterrupt:
                print("\n🛑 Получен сигнал остановки...")
                self.cleanup()
                break
            except Exception as e:
                print(f"❌ Ошибка основного цикла: {e}")
                time.sleep(300)  # Пауза 5 минут при ошибке

    def cleanup(self):
        """Очистка ресурсов при завершении"""
        print("🧹 Очистка ресурсов...")
        self.scraper.cleanup()
        self.bot.send_status_message("🛑 Мониторинг остановлен")


if __name__ == "__main__":
    monitor = AdvancedApartmentMonitor()
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.cleanup()
