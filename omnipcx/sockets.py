import socket, time, signal
from omnipcx.logging import Loggable

class SocketWrapper(Loggable):
    def __init__(self, socket):
        super(SocketWrapper, self).__init__()
        self._open = True
        self._socket = socket

    def send(self, message):
        try:
            self._socket.send(message.serialize())
            return True
        except BrokenPipeError:
            self.logger.error("Remote end closed connection")
            return False

    def recv(self, size):
        try:
            return self._socket.recv(size)
        except socket.timeout:
            return b""

    def close(self):
        if not self._open:
            self.logger.warn("Trying to close a closed socket")
            return
        self._open = False
        self._socket.close()


class CDRSocketWrapper(SocketWrapper):
    def send(self, message):
        try:
            self._socket.send(message.serialize_cdr())
            return True
        except BrokenPipeError:
            self.logger.error("Remote end closed connection")
            return False
        except:
            self.logger.exception("Failed sending CDR to collector")
            return False


class Server(Loggable):
    def __init__(self, config):
        super(Server, self).__init__()
        self.ipv6 = socket.AF_INET6 if config['ipv6'] else socket.AF_INET
        self.opera_port = config['opera_port']
        self.old_port = config['old_port']
        self.cdr_port = config['cdr_port']
        self.old_address = config['old_address']
        self.cdr_address = config['cdr_address']
        self.timeout = 0.5
        self.retries = config['retries']
        self.retry_sleep = config['retry_sleep']

    def listen(self):
        bind_fail = False
        try:
            server = socket.socket(self.ipv6, socket.SOCK_STREAM)
            address = "" # socket.gethostname()
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((address, self.opera_port))
            server.listen(10)
        except OSError:
            bind_fail = True
        except Exception:
            self.logger.exception("Caught exception when listening for connections")
            bind_fail = True
        if bind_fail:
            self.logger.error("Cannot listen on port %s. Maybe there is another process listening to that port?" % self.opera_port)
            return
        self.logger.info("Listening on [%s]:%d ...", address, self.opera_port)
        while True:
            self.logger.info("Waiting for client connection ...")
            try:
                yield server.accept()
            except KeyboardInterrupt:
                self.logger.warn("Stopped by Control+C")
                return

    def connect(self, address, port):
        try:
            skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            skt.settimeout(self.timeout)
            self.logger.info("Trying to open a connection to %s:%s" %(address, port))
            skt.connect((address, port),)
            return skt
        except (socket.timeout, ConnectionRefusedError) as e:
            return None

    def socket_tuples(self):
        for skt_opera, address in self.listen():
            skt_opera.settimeout(self.timeout)
            retries = self.retries
            skt_cdr = None
            skt_old = None
            while retries > 0:
                if skt_cdr is None:
                    skt_cdr = self.connect(self.cdr_address, self.cdr_port)
                if skt_old is None:
                    skt_old = self.connect(self.old_address, self.old_port)
                if skt_old is None or skt_cdr is None:
                    retries -= 1
                    self.logger.warn("Couldn't open connection to " + "CDR" if skt_cdr is None else "OLD" + ". Waiting ...")
                    time.sleep(self.retry_sleep)
                    continue
                else:
                    retries = 0
            if skt_old is None or skt_cdr is None:
                if skt_old:
                    self.logger.trace("Closing connection to Opera")
                    self.logger.error("Couldn't connect to CDR collector. Giving up.")
                    skt_old.close()
                if skt_cdr:
                    self.logger.trace("Closing connection to CDR collector")
                    self.logger.error("Couldn't connect to OLD. Giving up.")
                    skt_cdr.close()
                skt_opera.close()
                continue
            yield SocketWrapper(skt_old), SocketWrapper(skt_opera), CDRSocketWrapper(skt_cdr)

