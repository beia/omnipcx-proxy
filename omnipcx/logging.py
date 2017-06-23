import time
import logging
import inspect

import platform
if platform.system() != 'Windows':
    class ColorStreamHandler(logging.StreamHandler):
        DEFAULT = '\x1b[0m'
        RED     = '\x1b[31m'
        GREEN   = '\x1b[32m'
        YELLOW  = '\x1b[33m'
        CYAN    = '\x1b[36m'

        CRITICAL = RED
        ERROR    = RED
        WARNING  = YELLOW
        INFO     = GREEN
        DEBUG    = CYAN

        level = logging.DEBUG

        def __init__(self, streamHandler):
            super(ColorStreamHandler, self).__init__(streamHandler.stream)
            self.downstreamHandler = streamHandler

        @property
        def is_tty(self):
            isatty = getattr(self.downstreamHandler.stream, 'isatty', None)
            return isatty and isatty()

        @classmethod
        def _get_color(cls, level):
            if level >= logging.CRITICAL:  return cls.CRITICAL
            elif level >= logging.ERROR:   return cls.ERROR
            elif level >= logging.WARNING: return cls.WARNING
            elif level >= logging.INFO:    return cls.INFO
            elif level >= logging.DEBUG:   return cls.DEBUG
            else:                          return cls.DEFAULT

        def format(self, record):
            text = self.downstreamHandler.format(record)
            if self.is_tty:
                color = self._get_color(record.levelno)
                return color + text + self.DEFAULT
            else:
                return text
else:
    class ColorStreamHandler(logging.StreamHandler):
        # wincon.h
        FOREGROUND_BLACK     = 0x0000
        FOREGROUND_BLUE      = 0x0001
        FOREGROUND_GREEN     = 0x0002
        FOREGROUND_CYAN      = 0x0003
        FOREGROUND_RED       = 0x0004
        FOREGROUND_MAGENTA   = 0x0005
        FOREGROUND_YELLOW    = 0x0006
        FOREGROUND_GREY      = 0x0007
        FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.
        FOREGROUND_WHITE     = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED

        BACKGROUND_BLACK     = 0x0000
        BACKGROUND_BLUE      = 0x0010
        BACKGROUND_GREEN     = 0x0020
        BACKGROUND_CYAN      = 0x0030
        BACKGROUND_RED       = 0x0040
        BACKGROUND_MAGENTA   = 0x0050
        BACKGROUND_YELLOW    = 0x0060
        BACKGROUND_GREY      = 0x0070
        BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

        DEFAULT  = FOREGROUND_WHITE
        CRITICAL = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
        ERROR    = FOREGROUND_RED | FOREGROUND_INTENSITY
        WARNING  = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        INFO     = FOREGROUND_GREEN
        DEBUG    = FOREGROUND_CYAN

        @classmethod
        def _get_color(cls, level):
            if level >= logging.CRITICAL:  return cls.CRITICAL
            elif level >= logging.ERROR:   return cls.ERROR
            elif level >= logging.WARNING: return cls.WARNING
            elif level >= logging.INFO:    return cls.INFO
            elif level >= logging.DEBUG:   return cls.DEBUG
            else:                          return cls.DEFAULT

        def _set_color(self, code):
            import ctypes
            ctypes.windll.kernel32.SetConsoleTextAttribute(self._outhdl, code)

        def __init__(self, streamHandler):
            super(ColorStreamHandler, self).__init__(streamHandler.stream)
            self.downstreamHandler = streamHandler
            # get file handle for the stream
            import ctypes, ctypes.util
            # for some reason find_msvcrt() sometimes doesn't find msvcrt.dll on my system?
            crtname = ctypes.util.find_msvcrt()
            if not crtname:
                crtname = ctypes.util.find_library("msvcrt")
            crtlib = ctypes.cdll.LoadLibrary(crtname)
            self._outhdl = crtlib._get_osfhandle(self.downstreamHandler.stream.fileno())

        def emit(self, record):
            color = self._get_color(record.levelno)
            self._set_color(color)
            self.downstreamHandler.emit(record)
            self._set_color(self.FOREGROUND_WHITE)


class LogWrapper(object):
    def __init__(self, logger):
        self._logger = logger

    @property
    def _logging_extra(self):
        frame = inspect.currentframe()
        try:
            frame_info = inspect.getouterframes(frame)[2]
            try:
                return {
                    'file': str(frame_info[1]),
                    'line_no': str(frame_info[2]),
                    'function': frame_info[3],
                    'timestamp': int(time.time()),
                }
            finally:
                del frame_info
        finally:
            del frame

    def trace(self, message, *args):
        self._logger.debug(message, *args, extra=self._logging_extra)

    def debug(self, message, *args):
        self._logger.debug(message, *args, extra=self._logging_extra)

    def info(self, message, *args):
        self._logger.info(message, *args, extra=self._logging_extra)

    def warn(self, message, *args):
        self._logger.warn(message, *args, extra=self._logging_extra)

    def error(self, message, *args):
        self._logger.error(message, *args, extra=self._logging_extra)


class Loggable(object):
    @property
    def logger(self):
        return self._logger

    @classmethod
    def set_logger(cls, logger):
        cls._logger = logger
