import threading
from omnipcx.logging import Loggable


class Pipeline(threading.Thread, Loggable):
    def __init__(self, in_skt, out_skt, extra_skt, detector, default_password, finished):
        super(Pipeline, self).__init__()
        self.in_skt = in_skt
        self.out_skt = out_skt
        self.extra_skt = extra_skt
        self.detector = detector
        self.default_password = default_password
        self.finished = finished

    def run(self):
        self.logger.info("(%s) Starting protocol thread", self.name)
        while not self.finished.is_set():
            message = None
            try:
                message = self.detector.detect(self.in_skt)
            except ValueError:
                self.logger.error("(%s) Protocol error. Quiting", self.name)
                self.finished.set()
                return
            if message is None:
                continue
            self.logger.debug("(%s) Received message '%s'", self.name, message.serialize())
            if hasattr(message, 'serialize_cdr'):
                self.extra_skt.send(message.serialize_cdr())
            elif hasattr(message, 'password'):
                message.password = self.default_password
            self.out_skt.send(message.serialize())
        self.logger.warn("(%s) thread signaled to finish", self.name)


class Proxy(Loggable):
    def __init__(self, pbx, hotel, cdr, detector, default_password):
        super(Proxy, self).__init__()
        self.pbx = pbx
        self.hotel = hotel
        self.cdr = cdr
        self.detector = detector
        self.default_password = default_password

    def start(self):
        finished = threading.Event()
        thread1 = Pipeline(self.pbx, self.hotel, self.cdr, self.detector, self.default_password, finished)
        thread2 = Pipeline(self.hotel, self.pbx, self.cdr, self.detector, self.default_password, finished)
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
