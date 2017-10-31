import socket, time, signal
from omnipcx.logging import Loggable


class ClientStream(Loggable):
    def __init__(self, address, port, timeout=0.5, ipv6=False):
        self(ClientStream, self).__init__()
        self.port = port
        self.address = address
        self.ipv6 = socket.AF_INET6 if ipv6 else socket.AF_INET
        self.timeout = timeout
        self._connected = False

    @property
    def connected(self):
        return self._connected

    def connect(self):
        if self._connected:
            self.logger.warn("Stream is already connected")
            return self._connected
        try:
            skt = socket.socket(self.ipv6, socket.SOCK_STREAM)
            skt.settimeout(self.timeout)
            self.logger.info("Trying to open a connection to %s:%s" %(address, port))
            skt.connect((address, port),)
            self._socket = skt
            self._connected = True
        except (socket.timeout, ConnectionRefusedError) as e:
            self._socket = None
            self._connected = False
        return self._connected

    def send(self, message):
        if not self._connected:
            self.logger.error("Cannot send to a closed socket")
            return
        try:
            self._socket.send(message.serialize())
            return True
        except BrokenPipeError:
            self.logger.error("Remote end closed connection")
            return False

    def recv(self, size):
        if not self._connected:
            self.logger.error("Cannot recv from a closed socket")
            return
        try:
            return self._socket.recv(size)
        except socket.timeout:
            return b""

    def close(self):
        if not self._connected:
            self.logger.warn("Trying to close a closed socket")
            return
        self._connected = False
        self._socket.close()


class CDRClientStream(ClientStream):
    def __init__(self, address, port, filename=None, timeout=0.5, ipv6=False):
        self(CDRClientStream, self).__init__(address, port, timeout, ipv6)
        self.cdr_file = filename
        if self.cdr_file:
            self._connected = True

    @property
    def temp_file(self):
        return self.cdr_file + ".1"

    def connect(self):
        if self.cdr_file:
            return True
        else:
            return super(CDRClientStream, self).connect()

    def recv(self):
        self.logger.warn("Cannot read from a CDR socket")
        if self.cdr_file:
            return b""
        else:
            return super(CDRClientStream, self).recv()

    def send(self, message):
        if not self._connected:
            self.logger.error("Cannot send to a closed socket")
            return
        if self.cdr_file:
            # File case
            try:
                with open(self.temp_file, "a+") as f:
                    f.write(message.serialize_cdr())
                return True
            except Exception as e:
                self.logger.exception("Failed writing CDR to file: " + e)
                return False
        else:
            # Network case
            try:
                self._socket.send(message.serialize_cdr())
                return True
            except BrokenPipeError:
                self.logger.error("Remote end closed connection")
                return False
            except:
                self.logger.exception("Failed sending CDR to collector")
                return False

    def rotate(self):
        if not self.cdr_file:
            return
        if not os.path.isfile(self.cdr_file):
            self.logger.info("Moving CDR file to its place")
            os.replace(self.temp_file, self.cdr_file)
        else:
            self.logger.info("CDR collecter didn't gather CDRs. Not replacing CDR file yet")


class ServerStream(Loggable):
    class SocketWrapper(Loggable):
        def __init__(self, socket):
            super(SocketWrapper, self).__init__()
            self._connected = True
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
            if not self._connected:
                self.logger.warn("Trying to close a closed socket")
                return
            self._connected = False
            self._socket.close()

    def __init__(self, port, timeout=0.5, ipv6=False, parallel_num=10):
        self(ServerStream, self).__init__()
        self.port = port
        self.ipv6 = socket.AF_INET6 if ipv6 else socket.AF_INET
        self.timeout = timeout
        self.parallel_num = parallel_num
        self._listening = False

    @property
    def listening(self):
        retrun self._listening

    def listen(self):
        bind_fail = False
        try:
            server = socket.socket(self.ipv6, socket.SOCK_STREAM)
            address = "" # socket.gethostname()
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((address, self.port))
            self._listening = True
            server.listen(self.parallel_num)
        except OSError:
            bind_fail = True
        except Exception:
            self.logger.exception("Caught exception when listening for connections")
            bind_fail = True
        if bind_fail:
            self.logger.error("Cannot listen on port %s. Maybe there is another process listening to that port?" % self.port)
            return
        self.logger.info("Listening on [%s]:%d ...", address, self.port)
        while True:
            self.logger.info("Waiting for client connection ...")
            try:
                socket, address = server.accept()
                socket.settimeout(self.timeout)
                yield SocketWrapper(socket)
            except KeyboardInterrupt:
                self.logger.warn("Stopped by Control+C")
                return
