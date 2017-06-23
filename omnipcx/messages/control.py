from omnipcx.messages.base import ControlMessage

class ACK(ControlMessage):
    @classmethod
    def get_type(cls):
        return b'\x06'


class NAK(ControlMessage):
    @classmethod
    def get_type(cls):
        return b'\x15'


class XON(ControlMessage):
    @classmethod
    def get_type(cls):
        return b'\x13'


class XOFF(ControlMessage):
    @classmethod
    def get_type(cls):
        return b'\x11'

CLASSES = [ACK, NAK, XON, XOFF]
