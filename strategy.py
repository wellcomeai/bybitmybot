import logging
from config import BUY_LEVEL, SELL_LEVEL

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self):
        self.last_signal = None
        self.last_price = None
        self.signal_count = 0
        
    def check_signal(self, price: float):
        """
        Простая стратегия с защитой от дублирования сигналов:
        - BUY, если цена выше BUY_LEVEL
        - SELL, если цена ниже SELL_LEVEL
        - Возвращает сигнал только если он отличается от предыдущего
        """
        current_signal = None
        
        if price > BUY_LEVEL:
            current_signal = "BUY"
        elif price < SELL_LEVEL:
            current_signal = "SELL"
        
        # Проверяем, изменился ли сигнал
        if current_signal and current_signal != self.last_signal:
            self.last_signal = current_signal
            self.signal_count += 1
            self.last_price = price
            
            logger.info(f"🎯 Новый сигнал: {current_signal} @ {price} (#{self.signal_count})")
            return current_signal
        
        return None
    
    def get_stats(self):
        """Возвращает статистику стратегии"""
        return {
            "last_signal": self.last_signal,
            "last_price": self.last_price,
            "total_signals": self.signal_count,
            "buy_level": BUY_LEVEL,
            "sell_level": SELL_LEVEL
        }
    
    def reset(self):
        """Сброс состояния стратегии"""
        self.last_signal = None
        self.last_price = None
        logger.info("🔄 Стратегия сброшена")

# Создаем глобальный экземпляр стратегии
strategy = TradingStrategy()
