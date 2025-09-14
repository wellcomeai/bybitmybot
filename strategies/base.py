from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

class BaseStrategy(ABC):
    """Базовый класс для всех торговых стратегий"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Strategy.{name}")
        
        # Статистика
        self.last_signal = None
        self.last_price = None
        self.signal_count = 0
        self.created_at = datetime.now()
        
        self.logger.info(f"🎯 Стратегия '{name}' инициализирована")
    
    @abstractmethod
    def check_signal(self, price: float) -> Optional[str]:
        """
        Проверить цену и вернуть сигнал если есть
        
        Args:
            price: Текущая цена
            
        Returns:
            str: 'BUY', 'SELL' или None
        """
        pass
    
    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """Получить информацию о стратегии (уровни, параметры)"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику стратегии"""
        uptime = datetime.now() - self.created_at
        
        return {
            "name": self.name,
            "last_signal": self.last_signal,
            "last_price": self.last_price,
            "total_signals": self.signal_count,
            "uptime": str(uptime),
            **self.get_strategy_info()
        }
    
    def reset(self):
        """Сброс состояния стратегии"""
        self.last_signal = None
        self.last_price = None
        self.signal_count = 0
        self.logger.info(f"🔄 Стратегия '{self.name}' сброшена")
    
    def _emit_signal(self, signal: str, price: float) -> str:
        """Внутренний метод для эмиссии сигнала"""
        self.last_signal = signal
        self.last_price = price
        self.signal_count += 1
        
        self.logger.info(f"🎯 Новый сигнал: {signal} @ ${price:,.2f} (#{self.signal_count})")
        return signal
