from omnipcx.messages.base import ControlMessage

class ACK(ControlMessage):
    @classmethod
    def get_type(cls):
        return '\x06'


class NAK(ControlMessage):
    @classmethod
    def get_type(cls):
        return '\x15'


class XON(ControlMessage):
    @classmethod
    def get_type(cls):
        return '\x13'


class XOFF(ControlMessage):
    @classmethod
    def get_type(cls):
        return '\x11'

CLASSES = [ACK, NAK, XON, XOFF]
