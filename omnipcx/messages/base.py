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
    STX = "\x02"
    ETX = "\x03"

    @classmethod
    def get_payload_size(cls):
        size = cls.get_size() - 3
        if cls.has_crc():
            size -= 2
        return size

    def __init__(self, payload):
        assert len(payload) == self.get_payload_size()
        self.payload = payload

    @staticmethod
    def crc(string):
        hexa = "0123456789ABCDEF"
        result = ord(self.get_type())
        for c in string:
            result = result ^ ord(c)
        return hexa[(result >> 4) & 0xF] + hexa[result & 0xF]

    def serialize(self):
        return ProtocolMessage.STX + self.payload + ProtocolMessage.crc(self.payload) + ProtocolMessage.ETX
