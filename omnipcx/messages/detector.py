from socket import timeout as SocketTimeout
from omnipcx.logging import Loggable
from omnipcx.messages.control import CLASSES as _CONTROL_MSG_CLS
from omnipcx.messages.protocol import CLASSES as _PROTOCOL_MSG_CLS

from .base import ControlMessage, ProtocolMessage

RECV_SIZE = 150

class MessageDetector(Loggable):
    def __init__(self):
        self.is_initialized = False
        self.init_messages()
        self.reset()

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

    def reset(self):
        self.remainder = b""

    def detect(self, socket):
        message = socket.recv(RECV_SIZE)
        if len(message) == 0:
            self.logger.trace("Server closed connection")
            return None
        if message[0] in self._control_first_char:
            MessageClass = self._control_first_char[0]
            self.remainder += message[1:]
            return MessageClass()
        elif message[0] != ProtocolMessage.STX:
            self.logger.trace("Invalid character in communication: '%s'", message[0])
            return None
        for i, c in enumerate(message[1:]):
            if c == ProtocolMessage.ETX:
                i += 1
                self.remainder += message[i:]
                message = message[:i]
                break
            # TODO: here we should read more if we didn't find the end of message
        self.logger.debug("Message: '%s'", message)
