from typing import Dict, Any, Optional
from .base import BaseStrategy

class SimpleLevelsStrategy(BaseStrategy):
    """
    Простая стратегия на основе уровней поддержки/сопротивления
    
    - BUY сигнал, если цена выше уровня покупки
    - SELL сигнал, если цена ниже уровня продажи  
    - Защита от дублирования сигналов
    """
    
    def __init__(self, buy_level: float = None, sell_level: float = None):
        super().__init__("SimpleLevels")
        
        # Импортируем конфиг только если параметры не переданы
        if buy_level is None or sell_level is None:
            from config import BUY_LEVEL, SELL_LEVEL
            self.buy_level = buy_level or BUY_LEVEL
            self.sell_level = sell_level or SELL_LEVEL
        else:
            self.buy_level = buy_level
            self.sell_level = sell_level
        
        # Валидация
        if self.buy_level <= self.sell_level:
            raise ValueError("BUY_LEVEL должен быть больше SELL_LEVEL")
        
        self.logger.info(f"📈 Уровень покупки: ${self.buy_level:,.2f}")
        self.logger.info(f"📉 Уровень продажи: ${self.sell_level:,.2f}")
    
    def check_signal(self, price: float) -> Optional[str]:
        """
        Проверить цену и вернуть сигнал
        
        Логика:
        - BUY, если цена > buy_level
        - SELL, если цена < sell_level  
        - None если цена между уровнями или сигнал дублируется
        """
        current_signal = None
        
        if price > self.buy_level:
            current_signal = "BUY"
        elif price < self.sell_level:
            current_signal = "SELL"
        
        # Проверяем, изменился ли сигнал (защита от дублирования)
        if current_signal and current_signal != self.last_signal:
            return self._emit_signal(current_signal, price)
        
        return None
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Получить информацию о параметрах стратегии"""
        return {
            "buy_level": self.buy_level,
            "sell_level": self.sell_level,
            "spread": self.buy_level - self.sell_level,
            "spread_percent": ((self.buy_level - self.sell_level) / self.sell_level) * 100
        }
    
    def update_levels(self, buy_level: float, sell_level: float):
        """Обновить торговые уровни"""
        if buy_level <= sell_level:
            raise ValueError("BUY_LEVEL должен быть больше SELL_LEVEL")
        
        old_buy, old_sell = self.buy_level, self.sell_level
        self.buy_level = buy_level
        self.sell_level = sell_level
        
        self.logger.info(f"🔄 Уровни обновлены:")
        self.logger.info(f"  📈 Покупка: ${old_buy:,.2f} → ${self.buy_level:,.2f}")
        self.logger.info(f"  📉 Продажа: ${old_sell:,.2f} → ${self.sell_level:,.2f}")
        
        # Сбрасываем состояние чтобы избежать ложных сигналов
        self.reset()
