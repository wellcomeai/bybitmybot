#!/usr/bin/env python3
"""
Криптобот - основная точка входа
"""
import asyncio
import sys
import os
import signal
import logging
import platform
from datetime import datetime
from app.bot import CryptoBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class CryptoBotLauncher:
    """Класс для запуска криптобота"""
    
    def __init__(self):
        self.bot = None
        self.start_time = datetime.now()
        self.shutdown_initiated = False
        
        # Настройка простого обработчика сигналов
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Упрощенная настройка обработчика сигналов"""
        
        def graceful_shutdown_handler(signum, frame):
            if self.shutdown_initiated:
                logger.warning("⚠️ Повторный сигнал завершения игнорируется")
                return
                
            self.shutdown_initiated = True
            signal_names = {2: 'SIGINT', 15: 'SIGTERM', 1: 'SIGHUP'}
            signal_name = signal_names.get(signum, f'Signal {signum}')
            
            logger.warning(f"🚨 Получен {signal_name} - инициируется graceful shutdown...")
            
            # Останавливаем бота если он есть
            if self.bot:
                logger.info("🛑 Остановка бота...")
                self.bot.running = False
            else:
                logger.warning("⚠️ Объект бота недоступен")
            
        # Регистрируем обработчики
        signal.signal(signal.SIGINT, graceful_shutdown_handler)
        signal.signal(signal.SIGTERM, graceful_shutdown_handler)
        signal.signal(signal.SIGHUP, graceful_shutdown_handler)
        
        logger.info("📡 Обработчики сигналов настроены")

    def run(self):
        """Запуск бота"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК КРИПТОБОТА")
        logger.info("=" * 60)
        logger.info(f"📦 PID: {os.getpid()}")
        logger.info(f"🖥️ Платформа: {platform.platform()}")
        logger.info(f"🐍 Python: {sys.version.split()[0]}")
        logger.info(f"⏰ Время запуска: {self.start_time}")
        
        # Проверим доступные ресурсы при старте
        try:
            import psutil
            memory = psutil.virtual_memory()
            logger.info(f"💾 Доступно памяти: {memory.available / 1024 / 1024:.1f} MB")
        except ImportError:
            logger.debug("psutil недоступен для мониторинга ресурсов")
        except Exception as e:
            logger.debug(f"Не удалось получить информацию о ресурсах: {e}")
        
        try:
            # Создаем и запускаем бота
            logger.info("🤖 Создание экземпляра CryptoBot...")
            self.bot = CryptoBot()
            
            logger.info("🏁 Запуск основного цикла бота...")
            asyncio.run(self.bot.run())
            
        except KeyboardInterrupt:
            logger.warning("⌨️ Получен KeyboardInterrupt")
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА")
            logger.error(f"📊 Тип: {type(e).__name__}")
            logger.error(f"📝 Сообщение: {str(e)}")
            
            # Сокращенный traceback - только последние 3 строки
            import traceback
            tb_lines = traceback.format_exc().splitlines()
            logger.error("📋 Последние строки traceback:")
            for line in tb_lines[-3:]:
                logger.error(f"    {line}")
            logger.error("=" * 60)
            
            return 1
            
        finally:
            final_uptime = datetime.now() - self.start_time
            logger.info("=" * 60)
            logger.info("👋 ЗАВЕРШЕНИЕ РАБОТЫ")
            logger.info(f"⏱️ Общее время работы: {final_uptime}")
            logger.info("=" * 60)
            
        return 0

def main():
    """Основная функция"""
    launcher = CryptoBotLauncher()
    exit_code = launcher.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
