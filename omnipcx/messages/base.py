from omnipcx.logging import Loggable


class MessageBase(Loggable):
    @classmethod
    def get_size(cls):
        raise NotImplementedError

    @classmethod
    def get_type(cls):
        raise NotImplementedError

    @classmethod
    def has_crc(cls):
        raise NotImplementedError

    @classmethod
    def get_first_char(cls):
        raise NotImplementedError

    def serialize(self):
        raise NotImplementedError


class ControlMessage(MessageBase):
    @classmethod
    def get_size(self):
        return 1

    @classmethod
    def has_crc(cls):
        return False

    def serialize(self):
        return self.get_type()


class ProtocolMessage(MessageBase):
    STX = b'\x02'
    ETX = b'\x03'

    def __init__(self, payload, with_ends=True):
        # Not valid anymore
        # assert len(payload) == self.get_payload_size()
        if with_ends:
            self.payload = payload[1:-1]
        else:
            self.payload = payload

    @classmethod
    def crc(cls, string):
        hexa = '0123456789ABCDEF'
        if string == b"":
            return b""
        result = string[0]
        for c in string[1:]:
            result = result ^ c
        return hexa[(result >> 4) & 0xF] + hexa[result & 0xF]

    def serialize(self):
        return ProtocolMessage.STX + self.payload + ProtocolMessage.ETX
