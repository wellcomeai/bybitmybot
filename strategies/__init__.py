"""
Торговые стратегии
"""
from .simple_levels import SimpleLevelsStrategy

# Для обратной совместимости создаем глобальный экземпляр
strategy = SimpleLevelsStrategy()

__all__ = ['SimpleLevelsStrategy', 'strategy']
