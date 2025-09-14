import asyncio
import logging
import sys
import os
import platform
import threading
from datetime import datetime
from typing import Optional

from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BYBIT_PUBLIC_WS, SYMBOL, 
    LOG_LEVEL, RECONNECT_DELAY, validate_config
)
from strategy import strategy
from connectors import BybitWebSocketConnector, TelegramConnector
from .health import start_health_server

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class CryptoBot:
    """Основной класс криптобота с модульной архитектурой"""
    
    def __init__(self):
        self.running = True
        self.start_time = datetime.now()
        self.startup_message_sent = False
        self.loop_iterations = 0
        self.last_heartbeat = datetime.now()
        self.last_health_check = datetime.now()
        
        logger.info("🏗️ Инициализация CryptoBot...")
        logger.info(f"🏷️ Версия бота: 1.0.0 (модульная архитектура)")
        logger.info(f"🖥️ Платформа: {platform.platform()}")
        logger.info(f"🐍 Python: {sys.version}")
        logger.info(f"📦 PID: {os.getpid()}")
        
        # Инициализируем коннекторы
        self._init_connectors()
        
        # Настраиваем callbacks
        self._setup_callbacks()
        
        logger.info("🤖 CryptoBot инициализирован с модульной архитектурой")
        
    def _init_connectors(self):
        """Инициализация коннекторов"""
        try:
            logger.info("🔧 Инициализация коннекторов...")
            
            # Конфигурация для Bybit WebSocket
            bybit_config = {
                'websocket_url': BYBIT_PUBLIC_WS,
                'symbol': SYMBOL,
                'reconnect_delay': RECONNECT_DELAY,
                'ping_interval': 20,
                'ping_timeout': 10,
                'recv_timeout': 60  # Увеличиваем таймаут
            }
            
            # Конфигурация для Telegram
            telegram_config = {
                'bot_token': TELEGRAM_TOKEN,
                'chat_id': TELEGRAM_CHAT_ID,
                'timeout': 10,
                'max_retries': 3,
                'retry_delay': 2
            }
            
            # Создаем коннекторы
            logger.debug("🔗 Создание Bybit WebSocket коннектора...")
            self.bybit_connector = BybitWebSocketConnector(bybit_config)
            
            logger.debug("📱 Создание Telegram коннектора...")
            self.telegram_connector = TelegramConnector(telegram_config)
            
            logger.info("✅ Коннекторы инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации коннекторов: {e}")
            logger.error(f"📊 Детали ошибки: {type(e).__name__}: {str(e)}")
            raise
    
    def _setup_callbacks(self):
        """Настройка callbacks для событий коннекторов"""
        logger.debug("⚙️ Настройка event callbacks...")
        
        # Подписываемся на события подключения
        self.bybit_connector.add_callback('connected', self._on_bybit_connected)
        
        # Подписываемся на обновления цен
        self.bybit_connector.add_callback('price_update', self._on_price_update)
        
        logger.debug("✅ Event callbacks настроены")
    
    async def _on_bybit_connected(self, data):
        """Обработчик события подключения к Bybit"""
        logger.info(f"🔗 Подключен к Bybit: {data['symbol']} @ {data['websocket_url']}")
        logger.debug(f"🔍 Детали подключения: {data}")
        
        # Отправляем сообщение о запуске (только один раз)
        if not self.startup_message_sent:
            logger.info("📤 Отправка стартового сообщения...")
            await self._send_startup_message()
            self.startup_message_sent = True
    
    async def _on_price_update(self, price_event):
        """Обработчик обновления цены"""
        symbol = price_event['symbol']
        price = price_event['price']
        
        # Логируем цену только при DEBUG уровне
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"📊 {symbol}: ${price:,.2f}")
        
        # Проверяем стратегию
        try:
            signal_result = strategy.check_signal(price)
            if signal_result:
                logger.info(f"🎯 Стратегия сгенерировала сигнал: {signal_result}")
                await self._send_signal_message(symbol, signal_result, price)
        except Exception as e:
            logger.error(f"❌ Ошибка в стратегии: {e}")
            logger.error(f"📊 Цена на момент ошибки: ${price:,.2f}")
    
    async def _send_startup_message(self):
        """Отправка сообщения о запуске"""
        try:
            logger.debug("📤 Подготовка стартового сообщения...")
            stats = strategy.get_stats()
            success = await self.telegram_connector.send_startup_message(
                symbol=SYMBOL,
                buy_level=stats.get('buy_level', 0),
                sell_level=stats.get('sell_level', 0),
                websocket_url=BYBIT_PUBLIC_WS
            )
            
            if success:
                logger.info("📱 Сообщение о запуске отправлено")
            else:
                logger.warning("⚠️ Не удалось отправить сообщение о запуске")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения о запуске: {e}")
    
    async def _send_signal_message(self, symbol: str, action: str, price: float):
        """Отправка торгового сигнала"""
        try:
            logger.info(f"📤 Отправка сигнала: {action} {symbol} @ ${price:,.2f}")
            success = await self.telegram_connector.send_signal_message(
                symbol=symbol,
                action=action,
                price=price
            )
            
            if success:
                logger.info(f"🚀 Сигнал отправлен: {action} {symbol} @ ${price:,.2f}")
            else:
                logger.warning(f"⚠️ Не удалось отправить сигнал: {action} {symbol}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сигнала: {e}")
            logger.error(f"📊 Детали: {action} {symbol} @ ${price:,.2f}")
    
    async def _connect_all(self) -> bool:
        """Подключение всех коннекторов"""
        logger.info("🔗 Подключение коннекторов...")
        
        try:
            # Подключаем Telegram
            logger.info("📱 Подключение к Telegram...")
            telegram_connected = await self.telegram_connector.connect()
            if not telegram_connected:
                logger.error("❌ Не удалось подключиться к Telegram")
                return False
            
            # Подключаем Bybit WebSocket
            logger.info("🔗 Подключение к Bybit WebSocket...")
            bybit_connected = await self.bybit_connector.connect()
            if not bybit_connected:
                logger.error("❌ Не удалось подключиться к Bybit")
                return False
            
            logger.info("✅ Все коннекторы подключены")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения коннекторов: {e}")
            return False
    
    async def _disconnect_all(self):
        """Отключение всех коннекторов"""
        logger.info("🔌 Отключение коннекторов...")
        
        try:
            # Отключаем коннекторы
            if hasattr(self, 'bybit_connector'):
                logger.debug("🔌 Отключение Bybit...")
                await self.bybit_connector.disconnect()
            
            if hasattr(self, 'telegram_connector'):
                logger.debug("🔌 Отключение Telegram...")
                await self.telegram_connector.disconnect()
            
            logger.info("✅ Все коннекторы отключены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отключения коннекторов: {e}")
    
    async def _send_shutdown_message(self):
        """Отправка сообщения о завершении работы"""
        try:
            logger.info("📤 Подготовка сообщения о завершении работы...")
            uptime = str(datetime.now() - self.start_time)
            stats = strategy.get_stats()
            
            # Получаем статистику коннекторов
            reconnect_count = getattr(self.bybit_connector, 'reconnect_count', 0)
            
            success = await self.telegram_connector.send_shutdown_message(
                uptime=uptime,
                reconnect_count=reconnect_count,
                total_signals=stats.get('total_signals', 0),
                last_signal=stats.get('last_signal')
            )
            
            if success:
                logger.info("📱 Сообщение о завершении отправлено")
            else:
                logger.warning("⚠️ Не удалось отправить сообщение о завершении")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения о завершении: {e}")
    
    def get_bot_stats(self) -> dict:
        """Получить статистику бота для health check"""
        try:
            strategy_stats = strategy.get_stats()
            
            bybit_stats = {}
            if hasattr(self, 'bybit_connector'):
                bybit_stats = self.bybit_connector.get_stats()
            
            telegram_stats = {}
            if hasattr(self, 'telegram_connector'):
                telegram_stats = self.telegram_connector.get_stats()
            
            return {
                'bot': {
                    'running': self.running,
                    'uptime': str(datetime.now() - self.start_time),
                    'startup_message_sent': self.startup_message_sent,
                    'loop_iterations': self.loop_iterations,
                    'last_heartbeat': self.last_heartbeat.isoformat()
                },
                'strategy': strategy_stats,
                'connectors': {
                    'bybit': bybit_stats,
                    'telegram': telegram_stats
                }
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'error': str(e)}
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья коннекторов - УЛУЧШЕНО"""
        logger.info("🏥 Запуск health check цикла...")
        check_interval = 30  # Проверяем каждые 30 секунд
        recovery_attempts = 0
        max_recovery_attempts = 3
        
        while self.running:
            try:
                logger.debug("🩺 Выполняется health check...")
                self.last_health_check = datetime.now()
                
                # Проверяем Bybit коннектор
                bybit_healthy = await self.bybit_connector.is_healthy()
                telegram_healthy = await self.telegram_connector.is_healthy()
                
                if not bybit_healthy:
                    logger.warning("⚠️ Bybit коннектор не здоров")
                    bybit_stats = self.bybit_connector.get_stats()
                    logger.warning(f"🔍 Bybit диагностика: {bybit_stats}")
                    
                    # НОВАЯ ЛОГИКА: Попытка восстановления
                    if recovery_attempts < max_recovery_attempts:
                        recovery_attempts += 1
                        logger.info(f"🔄 Попытка восстановления Bybit коннектора #{recovery_attempts}")
                        
                        try:
                            # Переподключаем Bybit коннектор
                            await self.bybit_connector.disconnect()
                            await asyncio.sleep(5)
                            await self.bybit_connector.connect()
                            logger.info("✅ Восстановление Bybit коннектора завершено")
                            
                        except Exception as recovery_error:
                            logger.error(f"❌ Ошибка восстановления Bybit: {recovery_error}")
                    else:
                        logger.error(f"🚨 Исчерпаны попытки восстановления Bybit коннектора ({max_recovery_attempts})")
                
                if not telegram_healthy:
                    logger.warning("⚠️ Telegram коннектор не здоров")
                    telegram_stats = self.telegram_connector.get_stats()
                    logger.warning(f"🔍 Telegram диагностика: {telegram_stats}")
                    
                    # Попытка переподключения Telegram
                    try:
                        await self.telegram_connector.connect()
                        logger.info("✅ Восстановление Telegram коннектора")
                    except Exception as e:
                        logger.error(f"❌ Ошибка восстановления Telegram: {e}")
                
                # Если оба коннектора здоровы, сбрасываем счетчик попыток
                if bybit_healthy and telegram_healthy:
                    if recovery_attempts > 0:
                        logger.info("✅ Все коннекторы восстановлены")
                        recovery_attempts = 0
                    
                    # Логируем только каждые 10 минут при нормальной работе
                    if self.loop_iterations % (10 * 60 // check_interval) == 0:
                        logger.debug("✅ Все коннекторы здоровы")
                
                # Спим между проверками
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в health check: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Запуск бота с детальным логированием"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК КРИПТОБОТА (МОДУЛЬНАЯ ВЕРСИЯ)")
        logger.info("=" * 60)
        
        # Логируем системную информацию при старте
        logger.info(f"🖥️ Платформа: {platform.platform()}")
        logger.info(f"🐍 Python версия: {sys.version.split()[0]}")
        logger.info(f"📦 Process ID: {os.getpid()}")
        logger.info(f"📂 Рабочая директория: {os.getcwd()}")
        logger.info(f"🎯 Торговый символ: {SYMBOL}")
        logger.info(f"🔗 WebSocket URL: {BYBIT_PUBLIC_WS}")
        
        try:
            # Проверяем конфигурацию
            logger.info("🔍 Проверка конфигурации...")
            validate_config()
            logger.info("✅ Конфигурация валидна")
        except ValueError as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return
        
        # Запускаем HTTP сервер для health check в отдельном потоке
        logger.info("🏥 Запуск health check сервера...")
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        logger.info("🏥 Health check сервер запущен в отдельном потоке")
        
        # УБРАЛИ ДУБЛИРУЮЩИЕ ОБРАБОТЧИКИ СИГНАЛОВ - они будут только в main.py
        
        try:
            # Подключаем все коннекторы
            logger.info("🔌 Начинаем подключение коннекторов...")
            if not await self._connect_all():
                logger.error("❌ Не удалось подключить коннекторы - завершение работы")
                return
            
            # Запускаем health check в отдельной задаче
            logger.info("🏥 Запуск health check задачи...")
            health_task = asyncio.create_task(self._health_check_loop())
            
            # Основной цикл работы
            logger.info("🟢 Бот запущен и готов к работе!")
            logger.info("⏳ Вход в основной цикл ожидания...")
            logger.info("=" * 60)
            
            try:
                # Ждем завершения работы
                while self.running:
                    self.loop_iterations += 1
                    
                    # Каждые 5 минут логируем heartbeat
                    if self.loop_iterations % 300 == 0:  # 300 секунд = 5 минут
                        uptime = datetime.now() - self.start_time
                        strategy_stats = strategy.get_stats()
                        bybit_reconnects = getattr(self.bybit_connector, 'reconnect_count', 0)
                        
                        logger.info(f"💓 Heartbeat: бот работает {uptime}, "
                                  f"сигналов: {strategy_stats.get('total_signals', 0)}, "
                                  f"переподключений: {bybit_reconnects}")
                        
                        self.last_heartbeat = datetime.now()
                    
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                logger.warning("⏹️ Получен сигнал отмены основного цикла")
            finally:
                logger.info("🔄 Завершение основного цикла...")
                # Отменяем health check задачу
                health_task.cancel()
                try:
                    await health_task
                except asyncio.CancelledError:
                    logger.debug("✅ Health check задача отменена")
            
        except KeyboardInterrupt:
            logger.warning("⌨️ Получен Ctrl+C. Завершение работы...")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в основном цикле: {e}")
            logger.error(f"📊 Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        finally:
            logger.info("=" * 60)
            logger.info("🏁 НАЧАЛО ПРОЦЕДУРЫ ЗАВЕРШЕНИЯ РАБОТЫ")
            logger.info("=" * 60)
            
            # Отправляем сообщение о завершении
            try:
                logger.info("📤 Отправка уведомления о завершении...")
                await self._send_shutdown_message()
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке сообщения завершения: {e}")
            
            # Отключаем все коннекторы
            try:
                await self._disconnect_all()
            except Exception as e:
                logger.error(f"❌ Ошибка при отключении коннекторов: {e}")
            
            # Финальная статистика
            final_uptime = datetime.now() - self.start_time
            final_stats = strategy.get_stats() if hasattr(strategy, 'get_stats') else {}
            
            logger.info("=" * 60)
            logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
            logger.info(f"⏱️ Общее время работы: {final_uptime}")
            logger.info(f"🔄 Итераций главного цикла: {self.loop_iterations}")
            logger.info(f"🎯 Всего сигналов: {final_stats.get('total_signals', 'N/A')}")
            logger.info(f"📈 Последний сигнал: {final_stats.get('last_signal', 'Нет')}")
            logger.info("=" * 60)
            logger.info("👋 Криптобот завершил работу")
            logger.info("=" * 60)
