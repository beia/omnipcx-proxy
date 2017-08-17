from omnipcx.logging import Loggable
from omnipcx.messages.control import CLASSES as _CONTROL_MSG_CLS
from omnipcx.messages.protocol import CLASSES as _PROTOCOL_MSG_CLS

from omnipcx.messages.base import ControlMessage, ProtocolMessage

RECV_SIZE = 150

class MessageDetector(Loggable):
    is_initialized = False

    def __init__(self, socket):
        self.init_message_classes()
        self.socket = socket
        self.remainder = b""

    @classmethod
    def init_message_classes(cls):
        if cls.is_initialized:
            return
        cls.ctrl_msg_classes = dict( (clss.get_type()[0],clss) for clss in _CONTROL_MSG_CLS)
        cls.proto_classes = dict( (clss.get_type()[0],clss) for clss in _PROTOCOL_MSG_CLS)
        cls.is_initialized = True

    def messages(self):
        while True:
            message = self.socket.recv(RECV_SIZE)
            self.remainder += message
            if len(self.remainder) == 0:
                yield None
                continue
            if self.remainder[0] == ProtocolMessage.STX[0]:
                # eat up all the message until ProtocolMessage.ETX
                i = 1
                while self.remainder[i] != ProtocolMessage.ETX[0]:
                    i += 1
                # TODO: here we should probably check if we arrived at the end of remainder and read more :(
                payload = self.remainder[:i+1]
                self.remainder = self.remainder[i+1:]
                ProtoClass = self.proto_classes.get(payload[1], None)
                if ProtoClass is None:
                    self.logger.error("Invalid message type")
                    return
                yield ProtoClass(payload)
            elif self.ctrl_msg_classes.get(self.remainder[0], None) is not None:
                CtrlMsgClass = self.ctrl_msg_classes[self.remainder[0]]
                self.remainder = self.remainder[1:]
                yield CtrlMsgClass()
            else:
                self.logger.error("Invalid character in stream ord(%s)" % self.remainder[0])
                return
