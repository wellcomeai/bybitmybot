#!/usr/bin/env python3
"""
Криптобот - основная точка входа
"""
import asyncio
import sys
import logging
from app.bot import CryptoBot

def main():
    """Основная функция запуска"""
    try:
        # Создаем и запускаем бота
        bot = CryptoBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("⌨️ Получен сигнал завершения")
        sys.exit(0)
    except Exception as e:
        logging.error(f"💥 Критическая ошибка при запуске: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
