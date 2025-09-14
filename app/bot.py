import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime
from typing import Optional

from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BYBIT_PUBLIC_WS, SYMBOL, 
    LOG_LEVEL, RECONNECT_DELAY, validate_config, BUY_LEVEL, SELL_LEVEL
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
        
        # Инициализируем коннекторы
        self._init_connectors()
        
        # Настраиваем callbacks
        self._setup_callbacks()
        
    def _init_connectors(self):
        """Инициализация коннекторов"""
        try:
            # Конфигурация для Bybit WebSocket
            bybit_config = {
                'websocket_url': BYBIT_PUBLIC_WS,
                'symbol': SYMBOL,
                'reconnect_delay': RECONNECT_DELAY,
                'ping_interval': 20,
                'ping_timeout': 10,
                'recv_timeout': 30
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
            self.bybit_connector = BybitWebSocketConnector(bybit_config)
            self.telegram_connector = TelegramConnector(telegram_config)
            
            logger.info("✅ Коннекторы инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации коннекторов: {e}")
            raise
    
    def _setup_callbacks(self):
        """Настройка callbacks для событий коннекторов"""
        
        # Подписываемся на события подключения
        self.bybit_connector.add_callback('connected', self._on_bybit_connected)
        
        # Подписываемся на обновления цен
        self.bybit_connector.add_callback('price_update', self._on_price_update)
        
        logger.debug("✅ Callbacks настроены")
    
    async def _on_bybit_connected(self, data):
        """Обработчик события подключения к Bybit"""
        logger.info(f"🔗 Подключен к Bybit: {data['symbol']} @ {data['websocket_url']}")
        
        # Отправляем сообщение о запуске (только один раз)
        if not self.startup_message_sent:
            await self._send_startup_message()
            self.startup_message_sent = True
    
    async def _on_price_update(self, price_event):
        """Обработчик обновления цены"""
        symbol = price_event['symbol']
        price = price_event['price']
        
        logger.debug(f"📊 {symbol}: ${price:,.2f}")
        
        # Проверяем стратегию
        signal = strategy.check_signal(price)
        if signal:
            await self._send_signal_message(symbol, signal, price)
    
    async def _send_startup_message(self):
        """Отправка сообщения о запуске"""
        try:
            stats = strategy.get_stats()
            success = await self.telegram_connector.send_startup_message(
                symbol=SYMBOL,
                buy_level=stats['buy_level'],
                sell_level=stats['sell_level'],
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
    
    async def _connect_all(self) -> bool:
        """Подключение всех коннекторов"""
        logger.info("🔗 Подключение коннекторов...")
        
        try:
            # Подключаем Telegram
            telegram_connected = await self.telegram_connector.connect()
            if not telegram_connected:
                logger.error("❌ Не удалось подключиться к Telegram")
                return False
            
            # Подключаем Bybit WebSocket
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
                await self.bybit_connector.disconnect()
            
            if hasattr(self, 'telegram_connector'):
                await self.telegram_connector.disconnect()
            
            logger.info("✅ Все коннекторы отключены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отключения коннекторов: {e}")
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Получен сигнал {signum}. Завершение работы...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _send_shutdown_message(self):
        """Отправка сообщения о завершении работы"""
        try:
            uptime = str(datetime.now() - self.start_time)
            stats = strategy.get_stats()
            
            # Получаем статистику коннекторов
            reconnect_count = getattr(self.bybit_connector, 'reconnect_count', 0)
            
            success = await self.telegram_connector.send_shutdown_message(
                uptime=uptime,
                reconnect_count=reconnect_count,
                total_signals=stats['total_signals'],
                last_signal=stats['last_signal']
            )
            
            if success:
                logger.info("📱 Сообщение о завершении отправлено")
            
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
                    'startup_message_sent': self.startup_message_sent
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
    
    async def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск криптобота (модульная версия)...")
        
        try:
            # Проверяем конфигурацию
            validate_config()
        except ValueError as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return
        
        # Запускаем HTTP сервер для health check
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Настраиваем обработчики сигналов
        self._setup_signal_handlers()
        
        try:
            # Подключаем все коннекторы
            if not await self._connect_all():
                logger.error("❌ Не удалось подключить коннекторы")
                return
            
            # Основной цикл работы
            logger.info("🟢 Бот запущен и готов к работе")
            while self.running:
                try:
                    # Проверяем состояние коннекторов
                    if not await self.bybit_connector.is_healthy():
                        logger.warning("⚠️ Bybit коннектор не здоров")
                    
                    if not await self.telegram_connector.is_healthy():
                        logger.warning("⚠️ Telegram коннектор не здоров")
                    
                    # Спим между проверками
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка в основном цикле: {e}")
                    await asyncio.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("⌨️ Получен Ctrl+C. Завершение работы...")
        
        finally:
            # Отправляем сообщение о завершении
            await self._send_shutdown_message()
            
            # Отключаем все коннекторы
            await self._disconnect_all()
            
            logger.info("👋 Бот завершил работу")
