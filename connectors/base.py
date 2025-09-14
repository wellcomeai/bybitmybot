from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import asyncio
import logging

class BaseConnector(ABC):
    """Базовый класс для всех коннекторов"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_connected = False
        self.logger = logging.getLogger(f"Connector.{name}")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Установить соединение"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Закрыть соединение"""
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """Проверить состояние соединения"""
        pass

class BaseWebSocketConnector(BaseConnector):
    """Базовый WebSocket коннектор"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.websocket = None
        self.running = False
        self.reconnect_count = 0
        self.callbacks = {}
    
    def add_callback(self, event_type: str, callback: Callable):
        """Добавить callback для обработки событий"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
        self.logger.debug(f"Добавлен callback для события: {event_type}")
    
    async def _emit_event(self, event_type: str, data: Any):
        """Вызвать все callbacks для события"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Ошибка в callback {callback}: {e}")

class BaseNotificationConnector(BaseConnector):
    """Базовый коннектор для уведомлений"""
    
    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> bool:
        """Отправить сообщение"""
        pass
    
    def send_message_sync(self, message: str, **kwargs) -> bool:
        """Синхронная отправка сообщения (для shutdown)"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если цикл уже запущен, создаем задачу
                return asyncio.create_task(self.send_message(message, **kwargs))
            else:
                # Если цикла нет, запускаем синхронно
                return asyncio.run(self.send_message(message, **kwargs))
        except Exception as e:
            self.logger.error(f"Ошибка синхронной отправки: {e}")
            return False
