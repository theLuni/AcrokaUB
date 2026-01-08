"""
Acroka UserBot Core Package
"""

__version__ = "3.0.0"
__author__ = "Acroka Team"

# Экспортируем основные классы
from .bot_manager import BotManager
from .modules import Module, ModuleManager, load_modules
from .commands import CoreCommands

__all__ = [
    'BotManager',
    'Module',
    'ModuleManager', 
    'load_modules',
    'CoreCommands'
]