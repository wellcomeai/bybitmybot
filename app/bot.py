import asyncio
import websockets
import json
import requests
import logging
import signal
import sys
import threading
from datetime import datetime

from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BYBIT_PUBLIC_WS, SYMBOL, 
    LOG_LEVEL, RECONNECT_DELAY, validate_config
)
from strategy import strategy
from .health import start_health_server

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class CryptoBot:
    """Основной класс криптобота"""
    
    def __init__(self):
        self.running = True
        self.reconnect_count = 0
        self.start_time = datetime.now()
        self.startup_message_sent = False
        
    def send_telegram_sync(self, message: str) -> bool:
        """Синхронная отправка сообщения в Telegram"""
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        for attempt in range(3):
            try:
                response = requests.post(
                    url, 
                    data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
                    timeout=10
                )
                response.raise_for_status()
                logger.debug(f"✅ Сообщение отправлено в Telegram: {message[:50]}...")
                return True
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ Попытка {attempt + 1} отправки в Telegram неудачна: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2)
        
        logger.error(f"🚫 Не удалось отправить сообщение в Telegram: {message}")
        return False
    
    async def send_telegram(self, message: str) -> bool:
        """Асинхронная отправка сообщения в Telegram"""
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    requests.post,
                    url, 
                    data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
                    timeout=10
                )
                response.raise_for_status()
                logger.debug(f"✅ Сообщение отправлено в Telegram: {message[:50]}...")
                return True
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ Попытка {attempt + 1} отправки в Telegram неудачна: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        
        logger.error(f"🚫 Не удалось отправить сообщение в Telegram: {message}")
        return False
    
    async def send_startup_message(self):
        """Отправка сообщения о запуске бота"""
        stats = strategy.get_stats()
        message = (
            f"🤖 Крипто-бот запущен!\n\n"
            f"📊 Символ: {SYMBOL}\n"
            f"📈 Уровень покупки: {stats['buy_level']}\n"
            f"📉 Уровень продажи: {stats['sell_level']}\n"
            f"⏰ Время запуска: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🌐 WebSocket: {BYBIT_PUBLIC_WS}"
        )
        await self.send_telegram(message)
    
    async def handle_websocket_data(self, data):
        """Обработка данных от WebSocket"""
        try:
            if "data" in data and isinstance(data["data"], dict):
                price_str = data["data"].get("lastPrice")
                if not price_str:
                    return
                    
                price = float(price_str)
                logger.debug(f"📊 {SYMBOL}: {price}")
                
                signal = strategy.check_signal(price)
                if signal:
                    message = (
                        f"🚀 СИГНАЛ по {SYMBOL}\n\n"
                        f"📊 Действие: {signal}\n"
                        f"💰 Цена: ${price:,.2f}\n"
                        f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    logger.info(message.replace('\n', ' | '))
                    await self.send_telegram(message)
                    
        except (ValueError, KeyError) as e:
            logger.error(f"❌ Ошибка обработки данных: {e}")
    
    async def websocket_handler(self):
        """Основной обработчик WebSocket соединения"""
        while self.running:
            try:
                logger.info(f"🔗 Подключение к {BYBIT_PUBLIC_WS}...")
                
                async with websockets.connect(
                    BYBIT_PUBLIC_WS,
                    ping_interval=20,
                    ping_timeout=10
                ) as ws:
                    # Подписываемся на тикеры
                    sub_msg = {"op": "subscribe", "args": [f"tickers.{SYMBOL}"]}
                    await ws.send(json.dumps(sub_msg))
                    
                    logger.info(f"✅ Подписка на тикеры {SYMBOL} успешна")
                    self.reconnect_count = 0
                    
                    # Отправляем сообщение о запуске
                    if not self.startup_message_sent:
                        await self.send_startup_message()
                        self.startup_message_sent = True
                    
                    # Основной цикл получения данных
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            await self.handle_websocket_data(data)
                            
                        except asyncio.TimeoutError:
                            logger.warning("⏱️ Таймаут получения данных, отправляем ping...")
                            await ws.ping()
                            
            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    self.reconnect_count += 1
                    logger.warning(f"🔌 Соединение закрыто. Переподключение #{self.reconnect_count} через {RECONNECT_DELAY}с...")
                    await asyncio.sleep(RECONNECT_DELAY)
                    
            except Exception as e:
                if self.running:
                    self.reconnect_count += 1
                    logger.error(f"❌ Ошибка WebSocket: {e}. Переподключение #{self.reconnect_count} через {RECONNECT_DELAY}с...")
                    await asyncio.sleep(RECONNECT_DELAY)
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Получен сигнал {signum}. Завершение работы...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск крипто-бота...")
        
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
            await self.websocket_handler()
        except KeyboardInterrupt:
            logger.info("⌨️ Получен Ctrl+C. Завершение работы...")
        finally:
            # Отправляем сообщение о завершении работы
            uptime = datetime.now() - self.start_time
            stats = strategy.get_stats()
            message = (
                f"🛑 Крипто-бот остановлен\n\n"
                f"⏱️ Время работы: {uptime}\n"
                f"🔄 Переподключений: {self.reconnect_count}\n"
                f"📊 Всего сигналов: {stats['total_signals']}\n"
                f"🎯 Последний сигнал: {stats['last_signal'] or 'Нет'}"
            )
            self.send_telegram_sync(message)
            logger.info("👋 Бот завершил работу")
