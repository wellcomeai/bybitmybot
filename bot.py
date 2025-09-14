import asyncio
import websockets
import json
import requests
import logging
import signal
import sys
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BYBIT_PUBLIC_WS, SYMBOL, 
    LOG_LEVEL, RECONNECT_DELAY, validate_config
)
from strategy import strategy

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Простой HTTP сервер для health check в Render"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            stats = strategy.get_stats()
            health_data = {
                "status": "healthy",
                "service": "crypto-bot",
                "symbol": SYMBOL,
                "total_signals": stats["total_signals"],
                "last_signal": stats["last_signal"],
                "last_price": stats["last_price"]
            }
            self.wfile.write(json.dumps(health_data).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Отключаем логи HTTP сервера чтобы не засорять вывод
        pass

def start_health_server():
    """Запуск HTTP сервера в отдельном потоке"""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"🏥 Health check сервер запущен на порту {port}")
    server.serve_forever()

class CryptoBot:
    def __init__(self):
        self.running = True
        self.reconnect_count = 0
        self.start_time = datetime.now()
        self.startup_message_sent = False
        
    def send_telegram_sync(self, message: str):
        """Синхронная отправка сообщения в Telegram для случаев завершения работы"""
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
    
    async def send_telegram(self, message: str):
        """Отправка сообщения в Telegram с retry логикой"""
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        for attempt in range(3):  # 3 попытки
            try:
                # Используем asyncio.to_thread для неблокирующего HTTP запроса
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
                if attempt < 2:  # Не ждем после последней попытки
                    await asyncio.sleep(2)
        
        logger.error(f"🚫 Не удалось отправить сообщение в Telegram: {message}")
        return False
    
    async def send_startup_message(self):
        """Отправляем сообщение о запуске бота"""
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
                    self.reconnect_count = 0  # Сбрасываем счетчик при успешном подключении
                    
                    # Отправляем сообщение о запуске (только один раз)
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
    
    async def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск крипто-бота...")
        
        # Проверяем конфигурацию
        try:
            validate_config()
        except ValueError as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return
        
        # Запускаем HTTP сервер для health check в отдельном потоке
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Настраиваем обработчики сигналов для graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"📡 Получен сигнал {signum}. Завершение работы...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
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

def main():
    bot = CryptoBot()
    try:
        asyncio.run(bot.run())
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
