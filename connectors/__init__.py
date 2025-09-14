"""
Коннекторы для подключения к внешним сервисам
"""
from .bybit.websocket import BybitWebSocketConnector
from .telegram.bot import TelegramConnector

__all__ = ['BybitWebSocketConnector', 'TelegramConnector']
