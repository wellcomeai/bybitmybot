import asyncio
import websockets
import json
from typing import Dict, Any
from datetime import datetime
from ..base import BaseWebSocketConnector

class BybitWebSocketConnector(BaseWebSocketConnector):
    """WebSocket коннектор для Bybit"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("BybitWS", config)
        
        # Параметры подключения
        self.websocket_url = config.get('websocket_url', 'wss://stream.bybit.com/v5/public/spot')
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.reconnect_delay = config.get('reconnect_delay', 5)
        self.ping_interval = config.get('ping_interval', 20)
        self.ping_timeout = config.get('ping_timeout', 10)
        self.recv_timeout = config.get('recv_timeout', 30)
        
        # Статистика
        self.last_price = None
        self.last_update = None
        self.total_messages = 0
    
    async def connect(self) -> bool:
        """Установить WebSocket соединение"""
        if self.running:
            self.logger.warning("Коннектор уже запущен")
            return True
            
        self.logger.info(f"🔗 Подключение к {self.websocket_url}...")
        self.running = True
        
        # Запускаем основной цикл подключения
        asyncio.create_task(self._connection_loop())
        return True
    
    async def disconnect(self) -> bool:
        """Закрыть соединение"""
        self.logger.info("🔌 Отключение WebSocket...")
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
            
        self.is_connected = False
        return True
    
    async def is_healthy(self) -> bool:
        """Проверить состояние соединения"""
        if not self.running:
            return False
            
        if not self.is_connected:
            return False
            
        # Проверяем, получали ли мы данные недавно
        if self.last_update:
            time_since_update = (datetime.now() - self.last_update).seconds
            return time_since_update < 60  # Данные должны обновляться чаще раза в минуту
            
        return False
    
    async def _connection_loop(self):
        """Основной цикл подключения с переподключениями"""
        while self.running:
            try:
                await self._handle_websocket_connection()
            except Exception as e:
                if self.running:
                    self.reconnect_count += 1
                    self.logger.error(f"❌ Ошибка соединения: {e}. Переподключение #{self.reconnect_count} через {self.reconnect_delay}с...")
                    self.is_connected = False
                    await asyncio.sleep(self.reconnect_delay)
    
    async def _handle_websocket_connection(self):
        """Обработка одного WebSocket соединения"""
        async with websockets.connect(
            self.websocket_url,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout
        ) as ws:
            self.websocket = ws
            
            # Подписываемся на тикеры
            await self._subscribe_to_tickers()
            
            self.logger.info(f"✅ Подписка на тикеры {self.symbol} успешна")
            self.is_connected = True
            self.reconnect_count = 0
            
            # Эмитим событие успешного подключения
            await self._emit_event('connected', {
                'symbol': self.symbol,
                'websocket_url': self.websocket_url
            })
            
            # Основной цикл получения данных
            await self._message_loop()
    
    async def _subscribe_to_tickers(self):
        """Подписка на тикеры"""
        subscription_message = {
            "op": "subscribe", 
            "args": [f"tickers.{self.symbol}"]
        }
        
        await self.websocket.send(json.dumps(subscription_message))
        self.logger.debug(f"📡 Отправлена подписка: {subscription_message}")
    
    async def _message_loop(self):
        """Основной цикл получения сообщений"""
        while self.running and self.is_connected:
            try:
                # Получаем сообщение с таймаутом
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=self.recv_timeout
                )
                
                # Обрабатываем сообщение
                await self._handle_message(message)
                
            except asyncio.TimeoutError:
                self.logger.warning("⏱️ Таймаут получения данных, отправляем ping...")
                await self.websocket.ping()
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("🔌 WebSocket соединение закрыто")
                self.is_connected = False
                break
                
    async def _handle_message(self, message: str):
        """Обработка входящего сообщения"""
        try:
            data = json.loads(message)
            self.total_messages += 1
            self.last_update = datetime.now()
            
            # Логируем сырые данные для дебага
            self.logger.debug(f"📨 Получено сообщение: {message[:100]}...")
            
            # Обрабатываем данные тикеров
            if self._is_ticker_data(data):
                await self._handle_ticker_data(data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Ошибка декодирования JSON: {e}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    def _is_ticker_data(self, data: Dict) -> bool:
        """Проверить, является ли сообщение данными тикера"""
        return (
            isinstance(data, dict) and 
            "data" in data and 
            isinstance(data["data"], dict) and
            "lastPrice" in data["data"]
        )
    
    async def _handle_ticker_data(self, data: Dict):
        """Обработка данных тикера"""
        try:
            ticker_data = data["data"]
            price_str = ticker_data.get("lastPrice")
            
            if not price_str:
                return
                
            price = float(price_str)
            self.last_price = price
            
            # Подготавливаем данные для события
            price_event = {
                'symbol': self.symbol,
                'price': price,
                'timestamp': datetime.now(),
                'raw_data': ticker_data
            }
            
            # Логируем цену
            self.logger.debug(f"📊 {self.symbol}: ${price:,.2f}")
            
            # Эмитим событие новой цены
            await self._emit_event('price_update', price_event)
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"❌ Ошибка обработки тикер данных: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику коннектора"""
        return {
            'name': self.name,
            'is_connected': self.is_connected,
            'is_healthy': asyncio.create_task(self.is_healthy()) if self.running else False,
            'reconnect_count': self.reconnect_count,
            'total_messages': self.total_messages,
            'last_price': self.last_price,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'symbol': self.symbol,
            'websocket_url': self.websocket_url
        }
