import threading
from omnipcx.logging import Loggable
from omnipcx.messages import MessageDetector
from omnipcx.messages.protocol import SMDR, CheckInBase


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
        upstream_g = self.upstream.messages()
        downstream_g = self.downstream.messages()
        while True:
            # Try to read from PBX
            u_msg = next(upstream_g)
            if u_msg:
                self.logger.trace("Recv %s from pbx" % u_msg.serialize())
                if isinstance(u_msg, SMDR):
                    self.cdr.send(u_msg.serialize_cdr())
                self.logger.trace("Send %s to hotel" % u_msg.serialize())
                self.hotel.send(u_msg.serialize())
                d_msg = next(downstream_g)
                if not d_msg:
                    self.logger.error("Timeout when waiting for message from Opera")
                    return
                self.pbx.send(d_msg.serialize())
            # Try to read from Hotel
            d_msg = next(downstream_g)
            if d_msg:
                self.logger.trace("Recv %s from hotel" % d_msg.serialize())
                if isinstance(d_msg, CheckInBase):
                    d_msg.password = self.default_password
                self.logger.trace("Send %s to pbx" % d_msg.serialize())
                self.pbx.send(d_msg.serialize())
                u_msg = next(upstream_g)
                if not u_msg:
                    self.logger.error("Timeout when waiting for message from OLD/Hotel Driver")
                    return
                self.hotel.send(u_msg.serialize())
