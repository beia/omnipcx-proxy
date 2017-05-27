from socket import timeout as SocketTimeout
from omnipcx.logging import Loggable
from omnipcx.messages.control import CLASSES as _CONTROL_MSG_CLS
from omnipcx.messages.protocol import CLASSES as _PROTOCOL_MSG_CLS

from .base import ControlMessage, ProtocolMessage

class MessageDetector(Loggable):
    def __init__(self):
        self.is_initialized = False
        self.init_messages()

    def init_messages(self):
        self._control_first_char = dict((c.get_type(), c) for c in _CONTROL_MSG_CLS)
        self._second_char = {}
        for cls in _PROTOCOL_MSG_CLS:
            c = cls.get_type()
            if c not in self._second_char:
                self._second_char[c] = []
            self._second_char[c].append(cls)
            # a bit inneficient, but ...
            self._second_char[c].sort(key=lambda cls: cls.get_size())

    def detect(self, socket):
        # First char
        try:
            c = socket.recv(1)
        except SocketTimeout:
            self.logger.debug("timeout waiting for the first char")
            return None
        if c in self._control_first_char:
            MessageClass = self._control_first_char[c]
            return MessageClass()
        elif c != ProtocolMessage.STX:
            raise ValueError("Unexpected character in the data stream '%s'" % c)
        # Second char
        try:
            c = socket.recv(1)
        except SocketTimeout:
            self.logger.debug("timeout waiting for the second char")
            return None
        read_size = 2
        if c not in self._second_char:
            raise ValueError("Invalid message type '%s'" % c)
        if len(self._second_char[c]) == 1:
            MessageClass = self._second_char[c][0]
            try:
                message = socket.recv(MessageClass.get_size() - read_size) # size - what was read so far
            except SocketTimeout:
                self.logger.debug("timeout waiting for the payload")
                return None
        else:
            message = ""
            # We use the fact that classes are ordered by the size of message
            for cls in self._second_char[c]:
                try:
                    message = message + socket.recv(cls.get_size() - read_size) # size - what was read so far
                except SocketTimeout:
                    self.logger.debug("timeout waiting for the payload")
                    return None
                read_size = cls.get_size()
                if message[-1] == ProtocolMessage.ETX:
                    # We found the correct message size/class
                    MessageClass = cls
                    break
        payload = message[:-4]
        crc = message[-3:-2]
        if ProtocolMessage.crc(payload) != crc:
            raise ValueError("CRC failed when checking message")
        return MessageClass(payload)
