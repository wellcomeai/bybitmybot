#!/usr/bin/env python3
"""
Криптобот - основная точка входа с детальным логированием
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

class DetailedMain:
    """Главный класс с детальным логированием"""
    
    def __init__(self):
        self.bot = None
        self.start_time = datetime.now()
        self.shutdown_initiated = False
        
        # Настройка обработчика сигналов на уровне main
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Настройка детального обработчика сигналов в main.py"""
        
        def detailed_signal_handler(signum, frame):
            if self.shutdown_initiated:
                return
                
            self.shutdown_initiated = True
            signal_names = {
                2: 'SIGINT (Ctrl+C)',
                15: 'SIGTERM (Graceful shutdown)',
                9: 'SIGKILL (Force kill)',
                1: 'SIGHUP (Hangup)',
            }
            
            signal_name = signal_names.get(signum, f'Unknown signal ({signum})')
            uptime = datetime.now() - self.start_time
            
            logger.error("=" * 70)
            logger.error(f"🚨 MAIN.PY: ПОЛУЧЕН СИГНАЛ ЗАВЕРШЕНИЯ!")
            logger.error(f"📡 Сигнал: {signal_name}")
            logger.error(f"📍 Место: {frame.f_code.co_filename}:{frame.f_lineno}")
            logger.error(f"📦 PID: {os.getpid()}")
            logger.error(f"⏱️ Uptime: {uptime}")
            logger.error(f"🖥️ Платформа: {platform.platform()}")
            logger.error(f"🐍 Python: {sys.version.split()[0]}")
            
            # Системная информация
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                logger.error(f"💾 Память: {memory_mb:.1f} MB")
                logger.error(f"🖥️ CPU: {cpu_percent:.1f}%")
                
                # Проверим общие ресурсы системы
                system_memory = psutil.virtual_memory()
                logger.error(f"🌐 Система - Память: {system_memory.percent}% использовано")
                logger.error(f"🌐 Система - Доступно: {system_memory.available / 1024 / 1024:.1f} MB")
                
            except ImportError:
                logger.error("📊 psutil недоступен")
            except Exception as e:
                logger.error(f"❌ Ошибка получения системной информации: {e}")
            
            # Проверим состояние бота
            if self.bot:
                try:
                    bot_stats = self.bot.get_bot_stats()
                    logger.error(f"🤖 Бот запущен: {bot_stats.get('bot', {}).get('running', 'unknown')}")
                    logger.error(f"🔄 Итераций: {bot_stats.get('bot', {}).get('loop_iterations', 'unknown')}")
                    logger.error(f"🎯 Сигналов стратегии: {bot_stats.get('strategy', {}).get('total_signals', 'unknown')}")
                except Exception as e:
                    logger.error(f"❌ Не удалось получить статистику бота: {e}")
            else:
                logger.error("🤖 Объект бота недоступен")
            
            # Проверим активные соединения
            try:
                import psutil
                connections = process.connections()
                logger.error(f"🌐 Активных соединений: {len(connections)}")
                for conn in connections[:5]:  # Первые 5
                    logger.error(f"   📡 {conn.laddr} -> {conn.raddr if conn.raddr else 'N/A'} ({conn.status})")
            except Exception as e:
                logger.error(f"❌ Не удалось получить информацию о соединениях: {e}")
            
            logger.error("🏁 Инициация graceful shutdown из main.py...")
            logger.error("=" * 70)
            
            # Если есть бот, останавливаем его gracefully
            if self.bot:
                self.bot.running = False
            
        # Регистрируем обработчики
        signal.signal(signal.SIGINT, detailed_signal_handler)
        signal.signal(signal.SIGTERM, detailed_signal_handler)
        signal.signal(signal.SIGHUP, detailed_signal_handler)
        
        logger.info("📡 Детальные обработчики сигналов настроены в main.py")

    def run(self):
        """Запуск с детальным логированием"""
        logger.info("=" * 70)
        logger.info("🚀 MAIN.PY: ЗАПУСК КРИПТОБОТА")
        logger.info("=" * 70)
        logger.info(f"📦 PID: {os.getpid()}")
        logger.info(f"📂 Рабочая директория: {os.getcwd()}")
        logger.info(f"🖥️ Платформа: {platform.platform()}")
        logger.info(f"🐍 Python: {sys.version}")
        logger.info(f"⏰ Время запуска: {self.start_time}")
        
        # Проверим доступные ресурсы при старте
        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            logger.info(f"💾 Доступно памяти: {memory.available / 1024 / 1024:.1f} MB")
            logger.info(f"💿 Доступно диска: {disk.free / 1024 / 1024 / 1024:.1f} GB")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить информацию о ресурсах: {e}")
        
        try:
            # Создаем и запускаем бота
            logger.info("🤖 Создание экземпляра CryptoBot...")
            self.bot = CryptoBot()
            
            logger.info("🏁 Запуск основного цикла бота...")
            asyncio.run(self.bot.run())
            
        except KeyboardInterrupt:
            logger.warning("⌨️ MAIN.PY: Получен KeyboardInterrupt")
            
        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"💥 MAIN.PY: КРИТИЧЕСКАЯ ОШИБКА")
            logger.error(f"📊 Тип: {type(e).__name__}")
            logger.error(f"📝 Сообщение: {str(e)}")
            
            # Полный traceback
            import traceback
            logger.error("📋 Traceback:")
            for line in traceback.format_exc().splitlines():
                logger.error(f"    {line}")
            logger.error("=" * 70)
            
            sys.exit(1)
            
        finally:
            final_uptime = datetime.now() - self.start_time
            logger.info("=" * 70)
            logger.info("👋 MAIN.PY: ЗАВЕРШЕНИЕ РАБОТЫ")
            logger.info(f"⏱️ Общее время работы: {final_uptime}")
            logger.info("=" * 70)

def main():
    """Основная функция"""
    app = DetailedMain()
    app.run()

if __name__ == "__main__":
    main()
