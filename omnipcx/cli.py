import argparse, logging, sys, traceback, time
from omnipcx.messages import MessageDetector, MessageBase
from omnipcx.proxy import Proxy
from omnipcx.logging import ColorStreamHandler, Loggable, LogWrapper
from omnipcx.streams import CDRStream, ClientStream, ServerStream
from omnipcx.cdr_buffer import CDRBuffer

DEFAULT_OLD_PORT = 5010
DEFAULT_OPERA_PORT = 2561
DEFAULT_CDR_PORT = 6666
DEFAULT_PASSWORD = '8756'
DEFAULT_RETRY_TIMEOUT = 2.0
DEFAULT_RETRIES = 5
DEFAULT_BUFFER_FILE = 'cdr_buffer.db'
DEFAULT_FORMAT = '{"timestamp": %(timestamp)s, "file": "%(file)s", "line_no": "%(line_no)s", "function": "%(function)s", "message": "%(message)s"}'


class Application(Loggable):
    @staticmethod
    def log_levels(log_level):
        from argparse import ArgumentTypeError
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
        choices_msg = 'LogLevels: use one of' + ', '.join([choice.lower() for choice in choices.keys()])
        try:
            return choices[log_level]
        except KeyError:
            raise ArgumentTypeError(choices_msg)

    def parse_args(self):
        parser = argparse.ArgumentParser(prog="proxy", description='Proxy between OLD and Opera')
        parser.add_argument("--log-level", type=Application.log_levels, default="INFO",
            help="Log level", dest="log_level")
        parser.add_argument('--old-port', type=int, dest='old_port', default=DEFAULT_OLD_PORT,
            help='Office Link Driver port (connect)')
        parser.add_argument('--old-address', dest='old_address', required=True,
            help='Office Link Driver address (connect)')
        parser.add_argument('--opera-port', type=int, dest='opera_port', default=DEFAULT_OPERA_PORT,
            help='Opera port (listen)')
        parser.add_argument('--cdr-file', type=str, dest='cdr_file_name', default=None,
            help='Save CDRs to a file instead of sending them over the network. If set, other CDR settings are ignored.')
        parser.add_argument('--cdr-port', type=int, dest='cdr_port', default=DEFAULT_CDR_PORT,
            help='CDR collection port (connect)')
        parser.add_argument('--cdr-address', dest='cdr_address',
            help='CDR collection address (connect)')
        parser.add_argument('--cdr-buffer-db-file', dest='buffer_db_file', default=DEFAULT_BUFFER_FILE,
            help='Default CDR buffer database file')
        parser.add_argument('--ipv6', type=bool, dest='ipv6', help='Use IPv6')
        parser.add_argument('--default-password', dest='default_password', default=DEFAULT_PASSWORD,
            help='Default voice mail password')
        parser.add_argument('--retry-sleep', dest='retry_sleep', default=5,
            help='Default sleep between connection attempts')
        self.args = parser.parse_args()

    def __init__(self):
        self.parse_args()
        self.init_logging()
        self.init_cdr_buffer()

    def init_cdr_buffer(self):
        self.cdr_buffer = CDRBuffer(file=self.args.buffer_db_file)
        self.cdr_buffer.load()

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
        Loggable.set_logger(logger=LogWrapper(lgr))
        self.logger.info("Initialized logging")

    def socket_tuples(self):
        opera_listener = ServerStream(self.args.opera_port, ipv6=self.args.ipv6)
        cdr_stream = CDRStream(self.args.cdr_address, self.args.cdr_port, self.args.cdr_file_name, ipv6=self.args.ipv6)
        old_stream = ClientStream(self.args.old_address, self.args.old_port, ipv6=self.args.ipv6)
        for opera_stream in opera_listener.listen():
            retries = DEFAULT_RETRIES
            old_connected = False
            cdr_connected = False
            while retries > 0:
                if not cdr_connected:
                    cdr_connected = cdr_stream.connect()
                if not old_connected:
                    old_connected = old_stream.connect()

                if not old_connected:
                    retries -= 1
                    self.logger.warn("Couldn't open connection to OLD. Waiting ...")
                    time.sleep(self.args.retry_sleep)
                    continue
                elif not cdr_connected:
                    retries -= 1
                    self.logger.warn("Couldn't open connection to CDR. Waiting ...")
                    time.sleep(self.args.retry_sleep)
                    continue
                else:
                    break
            if not old_connected or not cdr_connected:
                if old_connected:
                    self.logger.trace("Closing connection to Opera")
                    self.logger.error("Couldn't connect to CDR collector. Giving up.")
                    old_stream.close()
                if cdr_connected:
                    self.logger.trace("Closing connection to CDR collector")
                    self.logger.error("Couldn't connect to OLD. Giving up.")
                    cdr_stream.close()
                opera_stream.close()
                continue
            yield old_stream, opera_stream, cdr_stream


    def start(self):
        self.logger.info("Starting application")
        for old_stream, opera_stream, cdr_stream in self.socket_tuples():
            self.logger.info("Received Opera connection. Starting proxy operation")
            proxy = Proxy(old_stream, opera_stream, cdr_stream, self.args.default_password, self.cdr_buffer)
            try:
                proxy.run()
            except KeyboardInterrupt:
                self.logger.warn("Stopped by Ctrl+C / Ctrl+Break")
                break
            except Exception:
                self.logger.exception("Caught an exception in the main loop of the proxy")
                traceback.print_exc()
            finally:
                for stream in [opera_stream, old_stream, cdr_stream]:
                    stream.close()
        self.cdr_buffer.save()
