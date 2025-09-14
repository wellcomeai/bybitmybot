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
        self.recv_timeout = config.get('recv_timeout', 60)  # Увеличиваем таймаут
        
        # Статистика
        self.last_price = None
        self.last_update = None
        self.total_messages = 0
        self.consecutive_errors = 0  # Счетчик последовательных ошибок
        self.max_consecutive_errors = 5  # Максимум ошибок подряд
    
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
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.debug(f"Ошибка при закрытии WebSocket: {e}")
                
        self.is_connected = False
        return True
    
    async def is_healthy(self) -> bool:
        """Проверить состояние соединения - ИСПРАВЛЕНО"""
        if not self.running:
            return False
            
        if not self.is_connected:
            return False
            
        # Более мягкая проверка - данные должны обновляться чаще раза в 5 минут
        if self.last_update:
            time_since_update = (datetime.now() - self.last_update).seconds
            return time_since_update < 300  # 5 минут вместо 60 секунд
            
        return False
    
    async def _connection_loop(self):
        """Основной цикл подключения с переподключениями"""
        while self.running:
            try:
                await self._handle_websocket_connection()
                # Если дошли сюда без исключения, сбрасываем счетчик ошибок
                self.consecutive_errors = 0
                
            except Exception as e:
                if self.running:
                    self.consecutive_errors += 1
                    self.reconnect_count += 1
                    
                    # Увеличиваем задержку при последовательных ошибках
                    delay = min(self.reconnect_delay * self.consecutive_errors, 60)
                    
                    self.logger.error(f"❌ Ошибка соединения #{self.consecutive_errors}: {e}")
                    self.logger.info(f"🔄 Переподключение #{self.reconnect_count} через {delay}с...")
                    
                    self.is_connected = False
                    
                    # Если слишком много ошибок подряд, увеличиваем паузу
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        self.logger.warning(f"⚠️ Слишком много ошибок подряд ({self.consecutive_errors}), увеличиваем паузу")
                        await asyncio.sleep(120)  # 2 минуты паузы
                        self.consecutive_errors = 0  # Сбрасываем счетчик
                    else:
                        await asyncio.sleep(delay)
    
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
        """Основной цикл получения сообщений - УЛУЧШЕНО"""
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
                # При таймауте не считаем это критической ошибкой
                self.logger.debug("⏱️ Таймаут получения данных, отправляем ping...")
                try:
                    await self.websocket.ping()
                except Exception as ping_error:
                    self.logger.warning(f"❌ Ошибка ping: {ping_error}")
                    break  # Выходим из цикла, произойдет переподключение
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("🔌 WebSocket соединение закрыто")
                self.is_connected = False
                break
                
    async def _handle_message(self, message: str):
        """Обработка входящего сообщения - УЛУЧШЕННАЯ ДИАГНОСТИКА"""
        try:
            data = json.loads(message)
            self.total_messages += 1
            self.last_update = datetime.now()
            
            # Диагностическое логирование для первых 5 сообщений
            if self.total_messages <= 5:
                self.logger.info(f"📨 Сообщение #{self.total_messages} от Bybit:")
                self.logger.info(f"    📋 Тип: {type(data)}")
                self.logger.info(f"    📋 Ключи: {list(data.keys()) if isinstance(data, dict) else 'не словарь'}")
                self.logger.info(f"    📋 Размер: {len(message)} символов")
                if isinstance(data, dict):
                    if "topic" in data:
                        self.logger.info(f"    🎯 Topic: {data['topic']}")
                    if "type" in data:
                        self.logger.info(f"    🔄 Type: {data['type']}")
                    if "op" in data:
                        self.logger.info(f"    ⚙️ Operation: {data['op']}")
                
            # Логируем сырые данные только для тикер сообщений при DEBUG уровне
            if self.logger.isEnabledFor(10) and isinstance(data, dict):
                if "topic" in data and "tickers" in data.get("topic", ""):
                    self.logger.debug(f"📨 Тикер сообщение: {message[:200]}...")
                elif "op" in data:
                    self.logger.debug(f"📨 Операционное сообщение: {message}")
            
            # Обрабатываем данные тикеров
            if self._is_ticker_data(data):
                await self._handle_ticker_data(data)
            else:
                # Логируем другие типы сообщений для диагностики
                if isinstance(data, dict):
                    if "op" in data:
                        op = data.get("op")
                        if op == "pong":
                            self.logger.debug("🏓 Получен pong от Bybit")
                        elif op == "subscribe":
                            success = data.get("success", False)
                            ret_msg = data.get("ret_msg", "")
                            if success:
                                self.logger.info(f"✅ Подписка подтверждена: {ret_msg}")
                            else:
                                self.logger.error(f"❌ Ошибка подписки: {ret_msg}")
                        else:
                            self.logger.debug(f"📩 Операционное сообщение: {op}")
                    else:
                        # Неизвестный формат сообщения
                        self.logger.warning(f"❓ Неизвестный формат сообщения: {list(data.keys())}")
                        if self.total_messages <= 10:  # Логируем первые 10 для диагностики
                            self.logger.warning(f"    📋 Содержимое: {data}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Ошибка декодирования JSON: {e}")
            self.logger.error(f"📋 Сырое сообщение: {message[:200]}...")
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки сообщения: {e}")
            self.logger.error(f"📋 Тип: {type(message)}, длина: {len(message) if hasattr(message, '__len__') else 'unknown'}")
            if hasattr(message, '__len__') and len(message) < 1000:
                self.logger.error(f"📋 Содержимое: {message}")
    
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
            
            # Логируем цену только при DEBUG уровне
            if self.logger.isEnabledFor(10):  # DEBUG level
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
            'reconnect_count': self.reconnect_count,
            'total_messages': self.total_messages,
            'consecutive_errors': self.consecutive_errors,
            'last_price': self.last_price,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'symbol': self.symbol,
            'websocket_url': self.websocket_url,
            'health_timeout': 300  # В секундах
        }
