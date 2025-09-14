"""
Кастомные исключения для криптобота
"""

class BotException(Exception):
    """Базовое исключение для бота"""
    pass

class ConfigurationError(BotException):
    """Ошибка конфигурации"""
    pass

class ConnectionError(BotException):
    """Ошибка подключения"""
    pass

class StrategyError(BotException):
    """Ошибка стратегии"""
    pass

class NotificationError(BotException):
    """Ошибка уведомления"""
    pass
