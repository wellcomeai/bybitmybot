import asyncio
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from ..base import BaseNotificationConnector

class TelegramConnector(BaseNotificationConnector):
    """Коннектор для отправки сообщений в Telegram"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Telegram", config)
        
        # Параметры подключения
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.timeout = config.get('timeout', 10)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 2)
        
        # Валидация обязательных параметров
        if not self.bot_token:
            raise ValueError("Telegram bot_token is required")
        if not self.chat_id:
            raise ValueError("Telegram chat_id is required")
            
        # Базовый URL API
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Статистика
        self.messages_sent = 0
        self.messages_failed = 0
        self.last_message_time = None
        
        self.logger.info(f"🤖 Telegram коннектор инициализирован для чата: {self.chat_id}")
    
    async def connect(self) -> bool:
        """Проверить подключение к Telegram API"""
        try:
            # Проверяем валидность токена
            response = await self._make_api_request('getMe')
            if response and response.get('ok'):
                bot_info = response.get('result', {})
                self.logger.info(f"✅ Подключение к Telegram успешно. Бот: @{bot_info.get('username', 'unknown')}")
                self.is_connected = True
                return True
            else:
                self.logger.error("❌ Неверный токен Telegram бота")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к Telegram: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Отключение (для Telegram API не требуется)"""
        self.is_connected = False
        self.logger.info("📱 Telegram коннектор отключен")
        return True
    
    async def is_healthy(self) -> bool:
        """Проверить состояние коннектора"""
        if not self.is_connected:
            return False
            
        try:
            # Проверяем доступность API
            response = await self._make_api_request('getMe')
            return response and response.get('ok', False)
        except:
            return False
    
    async def send_message(self, message: str, **kwargs) -> bool:
        """Отправить сообщение в Telegram"""
        try:
            # Подготавливаем данные для отправки
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': kwargs.get('parse_mode', 'HTML'),
                'disable_web_page_preview': kwargs.get('disable_preview', True)
            }
            
            # Отправляем с retry логикой
            success = await self._send_with_retry('sendMessage', data)
            
            if success:
                self.messages_sent += 1
                self.last_message_time = datetime.now()
                self.logger.debug(f"✅ Сообщение отправлено: {message[:50]}...")
            else:
                self.messages_failed += 1
                self.logger.error(f"❌ Не удалось отправить сообщение: {message[:50]}...")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения: {e}")
            self.messages_failed += 1
            return False
    
    def send_message_sync(self, message: str, **kwargs) -> bool:
        """Синхронная отправка сообщения (для shutdown)"""
        try:
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': kwargs.get('parse_mode', 'HTML'),
                'disable_web_page_preview': kwargs.get('disable_preview', True)
            }
            
            # Синхронная отправка с retry
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        f"{self.api_url}/sendMessage",
                        data=data,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    if result.get('ok'):
                        self.messages_sent += 1
                        self.logger.debug(f"✅ Синхронное сообщение отправлено: {message[:50]}...")
                        return True
                    else:
                        self.logger.warning(f"⚠️ Telegram API ответил с ошибкой: {result}")
                        
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"❌ Попытка {attempt + 1} неудачна: {e}")
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay)
            
            self.messages_failed += 1
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка синхронной отправки: {e}")
            return False
    
    async def _send_with_retry(self, method: str, data: Dict) -> bool:
        """Отправка с retry логикой"""
        for attempt in range(self.max_retries):
            try:
                response = await self._make_api_request(method, data)
                
                if response and response.get('ok'):
                    return True
                else:
                    self.logger.warning(f"⚠️ Попытка {attempt + 1}: Telegram API ответил с ошибкой: {response}")
                    
            except Exception as e:
                self.logger.warning(f"❌ Попытка {attempt + 1} неудачна: {e}")
                
            # Ждем перед следующей попыткой (кроме последней)
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        return False
    
    async def _make_api_request(self, method: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Выполнить запрос к Telegram API"""
        url = f"{self.api_url}/{method}"
        
        # Выполняем запрос в отдельном потоке чтобы не блокировать async loop
        response = await asyncio.to_thread(
            requests.post if data else requests.get,
            url,
            data=data,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику коннектора"""
        return {
            'name': self.name,
            'is_connected': self.is_connected,
            'messages_sent': self.messages_sent,
            'messages_failed': self.messages_failed,
            'success_rate': (
                self.messages_sent / (self.messages_sent + self.messages_failed) 
                if (self.messages_sent + self.messages_failed) > 0 else 0
            ),
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'chat_id': self.chat_id,
            'api_url': self.api_url.replace(self.bot_token, '*****')  # Скрываем токен
        }
    
    # Дополнительные методы для разных типов сообщений
    
    async def send_startup_message(self, symbol: str, buy_level: float, sell_level: float, websocket_url: str) -> bool:
        """Отправить сообщение о запуске бота"""
        message = (
            f"🤖 <b>Крипто-бот запущен!</b>\n\n"
            f"📊 Символ: <code>{symbol}</code>\n"
            f"📈 Уровень покупки: <code>${buy_level:,.2f}</code>\n"
            f"📉 Уровень продажи: <code>${sell_level:,.2f}</code>\n"
            f"⏰ Время запуска: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
            f"🌐 WebSocket: <code>{websocket_url}</code>"
        )
        return await self.send_message(message)
    
    async def send_signal_message(self, symbol: str, action: str, price: float) -> bool:
        """Отправить торговый сигнал"""
        emoji = "📈" if action == "BUY" else "📉"
        message = (
            f"{emoji} <b>СИГНАЛ по {symbol}</b>\n\n"
            f"📊 Действие: <b>{action}</b>\n"
            f"💰 Цена: <code>${price:,.2f}</code>\n"
            f"⏰ Время: <code>{datetime.now().strftime('%H:%M:%S')}</code>"
        )
        return await self.send_message(message)
    
    async def send_shutdown_message(self, uptime: str, reconnect_count: int, total_signals: int, last_signal: Optional[str]) -> bool:
        """Отправить сообщение о завершении работы"""
        message = (
            f"🛑 <b>Крипто-бот остановлен</b>\n\n"
            f"⏱️ Время работы: <code>{uptime}</code>\n"
            f"🔄 Переподключений: <code>{reconnect_count}</code>\n"
            f"📊 Всего сигналов: <code>{total_signals}</code>\n"
            f"🎯 Последний сигнал: <code>{last_signal or 'Нет'}</code>"
        )
        # Используем синхронную отправку при завершении
        return self.send_message_sync(message)
