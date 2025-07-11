""""
Contains logging configuration (levels, formatters, handlers, colors, ...)
"""

import logging
from colorama import Fore, Style

# Logging related stuffclass ColoredFormatter(logging.Formatter):
COLORS = {
    'DEBUG': Fore.BLUE,
    'INFO': Fore.WHITE,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.MAGENTA
}

def __init__(self, *, format, use_color):
    logging.Formatter.__init__(self, fmt=format)
    self.use_color = use_color

def format(self, record):
    msg = super().format(record)
    if self.use_color:
        levelname = record.levelname
        if hasattr(record, 'color'):
            return f'{record.color}{msg}{Style.RESET_ALL}'
        if levelname in self.COLORS:
            return f'{self.COLORS[levelname]}{msg}{Style.RESET_ALL}'
    return msg

# creating a Logger to track events
log = logging.getLogger(__name__)
