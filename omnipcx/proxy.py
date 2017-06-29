import threading
import time
from omnipcx.logging import Loggable
from omnipcx.messages import MessageDetector
from omnipcx.messages.protocol import SMDR, CheckInBase

MAX_TIME = 60.0

class Proxy(Loggable):
    def __init__(self, pbx, hotel, cdr, default_password):
        super(Proxy, self).__init__()
        self.pbx = pbx
        self.hotel = hotel
        self.cdr = cdr
        self.upstream = MessageDetector(self.pbx)
        self.downstream = MessageDetector(self.hotel)
        self.default_password = default_password

    def run(self):
        time_last_recv =  {
            "upstream": time.time(),
            "downstream": time.time()
        }
        upstream_g = self.upstream.messages()
        downstream_g = self.downstream.messages()
        while True:
            # Try to read from PBX
            u_msg = next(upstream_g)
            if u_msg:
                time_last_recv["upstream"] = time.time()
                self.logger.trace("Recv %s from pbx" % u_msg.serialize())
                if isinstance(u_msg, SMDR):
                    self.cdr.send(u_msg.serialize_cdr())
                self.logger.trace("Send %s to hotel" % u_msg.serialize())
                self.hotel.send(u_msg.serialize())
                d_msg = next(downstream_g)
                if not d_msg:
                    self.logger.error("Timeout when waiting for message from Opera")
                    return
                time_last_recv["downstream"] = time.time()
                self.pbx.send(d_msg.serialize())
            # Try to read from Hotel
            d_msg = next(downstream_g)
            if d_msg:
                time_last_recv["downstream"] = time.time()
                self.logger.trace("Recv %s from hotel" % d_msg.serialize())
                if isinstance(d_msg, CheckInBase):
                    if d_msg.password == b"    ":
                        d_msg.password = self.default_password
                self.logger.trace("Send %s to pbx" % d_msg.serialize())
                self.pbx.send(d_msg.serialize())
                u_msg = next(upstream_g)
                if not u_msg:
                    self.logger.error("Timeout when waiting for message from OLD/Hotel Driver")
                    return
                time_last_recv["upstream"] = time.time()
                self.hotel.send(u_msg.serialize())
            if time.time() - max(time_last_recv.values()) > MAX_TIME:
                self.logger.warn("The connections were innactive for too long. We are probably disconnected ...")
                return
