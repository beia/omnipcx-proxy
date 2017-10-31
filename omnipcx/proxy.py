import threading
import time
from omnipcx.logging import Loggable
from omnipcx.messages import MessageDetector
from omnipcx.messages.protocol import SMDR, CheckInBase
from omnipcx.messages.control import NACK

MAX_TIME = 60.0

class Proxy(Loggable):
    def __init__(self, pbx, hotel, cdr, default_password, buf):
        super(Proxy, self).__init__()
        self.pbx = pbx
        self.hotel = hotel
        self.cdr = cdr
        self.upstream = MessageDetector(self.pbx)
        self.downstream = MessageDetector(self.hotel)
        self.default_password = default_password
        self.buffer = buf

    def send_missing_cdr(self):
        if self.buffer.is_empty:
            return True
        self.logger.info("Sending buffered CDRs")
        count = 0
        while True:
            # TODO: try to do some kind of flow control ...
            message = self.buffer.get()
            if not self.cdr.send(message):
                self.logger.error("CDR sending failed")
                self.buffer.put(message)
                return False
            count += 1
            if self.buffer.is_empty:
                break
        self.logger.info("Sent all CDRs to the collector")
        return True

    def send_nack_to_pbx(self, log_msg):
        if not self.pbx.send(NACK()):
            self.logger.error("Failed sending NACK to PBX")
        else:
            self.logger.info("Sent NACK to PBX to force the CDR to be resent")
        if log_msg != "":
            self.logger.error(log_msg)

    def run(self):
        time_last_recv =  {
            "upstream": time.time(),
            "downstream": time.time()
        }
        upstream_g = self.upstream.messages()
        downstream_g = self.downstream.messages()
        if not self.send_missing_cdr():
            return
        while True:
            # Try to read from PBX
            u_msg = next(upstream_g)
            if u_msg:
                time_last_recv["upstream"] = time.time()
                self.logger.trace("Recv %s from pbx" % u_msg.serialize())
                if isinstance(u_msg, SMDR):
                    if not self.cdr.send(u_msg):
                        self.buffer.put(u_msg)
                        return self.send_nack_to_pbx(log_msg="CDR collector closed connection. Reseting all others")
                self.logger.trace("Send %s to hotel" % u_msg.serialize())
                if not self.hotel.send(u_msg):
                    return self.send_nack_to_pbx(log_msg="Opera closed connection. Reseting all others")
                d_msg = next(downstream_g)
                if not d_msg:
                    return self.logger.error("Timeout when waiting for message from Opera")
                time_last_recv["downstream"] = time.time()
                if not self.pbx.send(d_msg):
                    return self.logger.error("PBX closed connection. Reseting all others")
            # Try to read from Hotel
            d_msg = next(downstream_g)
            if d_msg:
                time_last_recv["downstream"] = time.time()
                self.logger.trace("Recv %s from hotel" % d_msg.serialize())
                if isinstance(d_msg, CheckInBase):
                    if d_msg.password == b"    ":
                        d_msg.password = self.default_password
                self.logger.trace("Send %s to pbx" % d_msg.serialize())
                if not self.pbx.send(d_msg):
                    return self.logger.error("PBX closed connection. Reseting all others")
                u_msg = next(upstream_g)
                if not u_msg:
                    return self.logger.error("Timeout when waiting for message from OLD/Hotel Driver")
                time_last_recv["upstream"] = time.time()
                if not self.hotel.send(u_msg):
                    return self.logger.error("Opera closed connection. Reseting all others")
            if time.time() - max(time_last_recv.values()) > MAX_TIME:
                return self.logger.warn("The connections were innactive for too long. We are probably disconnected ...")
            # rotate the CDR file
            self.cdr.rotate()
