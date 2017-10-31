import socket, signal, os.path, os, errno
from omnipcx.logging import Loggable


class ClientStream(Loggable):
    def __init__(self, address, port, timeout=0.5, ipv6=False):
        super(ClientStream, self).__init__()
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
            self.logger.info("Trying to open a connection to %s:%s" %(self.address, self.port))
            skt.connect((self.address, self.port),)
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


class CDRStream(ClientStream):
    def __init__(self, address, port, filename=None, timeout=0.5, ipv6=False):
        super(CDRStream, self).__init__(address, port, timeout, ipv6)
        self._filename = filename
        if self.file_mode:
            self._connected = True
            was_present = self.create_dir_for_file(self._filename)
            if not was_present:
                self.logger.warn("Created folder for CDR file")
        else:
            if address is None or port is None:
                raise Exception("You need to specify an address and a port")

    @property
    def file_mode(self):
        """ The stream works in file mode"""
        return self._filename is not None

    @property
    def temp_file(self):
        return self._filename

    @property
    def cdr_file(self):
        return self._filename + ".1"

    def connect(self):
        if self.cdr_file:
            return True
        else:
            return super(CDRStream, self).connect()

    def recv(self):
        self.logger.warn("Cannot read from a CDR socket")
        if self.cdr_file:
            return b""
        else:
            return super(CDRStream, self).recv()

    def create_dir_for_file(self, filename):
        directory = os.path.dirname(filename)
        try:
            os.makedirs(directory)
            return True
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            else:
                return False

    def send(self, message):
        if not self._connected:
            self.logger.error("Cannot send to a closed socket")
            return
        if self.file_mode:
            # File case
            try:
                with open(self.temp_file, "a+") as f:
                    # TODO: should it be ASCII?
                    f.write(message.serialize_cdr().decode("utf-8", "strict"))
                return True
            except PermissionError:
                self.logger.error("Failed writing CDR to file '%s': permission denied" % self.temp_file)
                return False
            except Exception as e:
                self.logger.exception("Failed writing CDR to file: " + str(e))
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

    def close(self):
        if not self.file_mode:
            super(CDRStream, self).close()


    def rotate(self):
        if not self.file_mode:
            return
        try:
            can_replace = not os.path.isfile(self.cdr_file) and os.path.isfile(self.temp_file)
            if can_replace:
                self.logger.info("Moving CDR file to its place")
                os.replace(self.temp_file, self.cdr_file)
            else:
                self.logger.info("CDR collecter didn't gather CDRs. Not replacing CDR file yet")
        except PermissionError as e:
            self.logger.exception(("Cannot rename CDR temp file %s to CDR file %s: " % (self.temp_file, self.cdr_file) )+ str(e))
            raise e


class ServerStream(Loggable):
    class SocketWrapper(Loggable):
        def __init__(self, skt):
            super(ServerStream.SocketWrapper, self).__init__()
            self._connected = True
            self._socket = skt

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

    def __init__(self, port, listen_timeout=5, timeout=0.5, ipv6=False, parallel_num=10):
        super(ServerStream, self).__init__()
        self.port = port
        self.ipv6 = socket.AF_INET6 if ipv6 else socket.AF_INET
        self.timeout = timeout
        self.listen_timeout = listen_timeout
        self.parallel_num = parallel_num
        self._listening = False

    @property
    def listening(self):
        return self._listening

    def listen(self):
        bind_fail = False
        try:
            server = socket.socket(self.ipv6, socket.SOCK_STREAM)
            address = "" # socket.gethostname()
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.settimeout(self.listen_timeout)
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
                skt, address = server.accept()
                skt.settimeout(self.timeout)
                yield ServerStream.SocketWrapper(skt)
            except KeyboardInterrupt:
                self.logger.warn("Stopped by Control+C")
                return
            except socket.timeout:
                yield None
