import argparse
import logging
import sys
import traceback
from omnipcx.messages import MessageDetector, MessageBase
from omnipcx.proxy import Proxy
from omnipcx.logging import ColorStreamHandler, Loggable, LogWrapper
from omnipcx.sockets import Server

DEFAULT_OLD_PORT = 5010
DEFAULT_OPERA_PORT = 2561
DEFAULT_CDR_PORT = 6666
DEFAULT_PASSWORD = '8756'
DEFAULT_RETRY_TIMEOUT = 2.0
DEFAULT_RETRIES = 5
DEFAULT_FORMAT = '{"timestamp": %(timestamp)s, "file": "%(file)s", "line_no": "%(line_no)s", "function": "%(function)s", "message": "%(message)s"}'


class Application(Loggable):
    @staticmethod
    def log_levels(log_level):
        log_level = log_level.upper()
        choices = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARN": logging.WARNING,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
                "CRIT": logging.CRITICAL,
        }
        try:
            return choices[log_level]
        except KeyError:
            msg = ', '.join([choice.lower() for choice in choices.keys()])
            msg = 'LogLevels: use one of {%s}'%msg
            raise argparse.ArgumentTypeError(msg)

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(prog="proxy", description='Proxy between OLD and Opera')
        parser.add_argument("--log-level", type=Application.log_levels, default="INFO",
            help="Log level", dest="log_level")
        parser.add_argument('--old-port', type=int, dest='old_port', default=DEFAULT_OLD_PORT,
            help='Office Link Driver port (connect)')
        parser.add_argument('--old-address', dest='old_address', required=True,
            help='Office Link Driver address (connect)')
        parser.add_argument('--opera-port', type=int, dest='opera_port', default=DEFAULT_OPERA_PORT,
            help='Opera port (listen)')
        parser.add_argument('--cdr-port', type=int, dest='cdr_port', default=DEFAULT_CDR_PORT,
            help='CDR collection port (connect)')
        parser.add_argument('--cdr-address', dest='cdr_address', required=True,
            help='CDR collection address (connect)')
        parser.add_argument('--default-password', dest='default_password', default=DEFAULT_PASSWORD,
            help='Default voice mail password')
        return parser.parse_args()

    def __init__(self):
        self.args = Application.parse_args()
        self.init_logging()
        self.server = Server({
                'opera_port': self.args.opera_port,
                'old_port': self.args.old_port,
                'old_address': self.args.old_address,
                'cdr_port': self.args.cdr_port,
                'cdr_address': self.args.cdr_address,
                'retries': DEFAULT_RETRIES,
                'retry_sleep': DEFAULT_RETRY_TIMEOUT,
            })

    def init_logging(self, level=logging.DEBUG):
        logging.basicConfig(level=level)
        formatter = logging.Formatter(fmt=DEFAULT_FORMAT)
        streamHandler = logging.StreamHandler(sys.stderr)
        streamHandler.setFormatter(formatter)
        handler = ColorStreamHandler(streamHandler)
        lgr = logging.getLogger('omnipcx')
        lgr.addHandler(handler)
        lgr.setLevel(level)
        lgr.propagate = False
        logger = LogWrapper(lgr)
        for cls in [Server, MessageDetector, Proxy, MessageBase, Application]:
            cls.set_logger(logger)
        self.logger.info("Initialized logging")

    def start(self):
        args = self.parse_args()
        self.logger.info("Starting application")
        for skt_old, skt_opera, skt_cdr in self.server.socket_tuples():
            self.logger.info("Received Opera connection. Starting proxy operation")
            proxy = Proxy(skt_old, skt_opera, skt_cdr, self.args.default_password)
            try:
                proxy.run()
            finally:
                for skt in [skt_opera, skt_old, skt_cdr]:
                    skt.close()
