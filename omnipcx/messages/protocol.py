from omnipcx.messages.decorator import MessageParameters
from omnipcx.messages.base import ProtocolMessage

@MessageParameters('@', 7, False)
class TCPConnection(ProtocolMessage):
    pass


@MessageParameters('$', 7, False)
class KeepAlive(ProtocolMessage):
    pass


@MessageParameters('J', 74)
class SMDR(ProtocolMessage):
    def serialize_cdr(self):
        return self.payload + '\x0d\x0a'


class CheckInBase(ProtocolMessage):
    @property
    def password(self):
        return self.payload[self.PASSWORD_OFFSET:self.PASSWORD_OFFSET + self.PASSWORD_LEN]

    @password.setter
    def password(self, value):
        if len(value) > self.PASSWORD_LEN:
            raise ValueError("'password' needs to be less than %d characters long" % self.PASSWORD_LEN)
        password = " " * (self.PASSWORD_LEN - len(value)) + value
        self.payload = self.payload[:self.PASSWORD_OFFSET] + password + self.payload[self.PASSWORD_OFFSET + self.PASSWORD_LEN:]


@MessageParameters('A', 61)
class CheckIn(CheckInBase):
    PASSWORD_OFFSET = 34
    PASSWORD_LEN = 4


@MessageParameters('H', 22)
class PhoneAllocation(ProtocolMessage):
    pass


@MessageParameters('M', 61)
class VoiceMailAttribution(ProtocolMessage):
    pass


@MessageParameters('D', 13)
class CheckOut(ProtocolMessage):
    pass


@MessageParameters('C', 17)
class RoomStatusChange(ProtocolMessage):
    pass


@MessageParameters('T', 44)
class GuestTelephoneAccount(ProtocolMessage):
    pass


@MessageParameters('P', 49)
class WakeUpEvent(ProtocolMessage):
    pass


@MessageParameters('U', 96)
class FullReinit(ProtocolMessage):
    pass


@MessageParameters('U', 26)
class PartialReinit(ProtocolMessage):
    pass


@MessageParameters('R', 19)
class Reply(ProtocolMessage):
    pass


# Hotel Aplication to Hotel Driver messages

@MessageParameters('I', 13)
class Interogation(ProtocolMessage):
    pass


@MessageParameters('Z', 14)
class ReinitRequest(ProtocolMessage):
    pass


# New messages for support of 6 digits password

@MessageParameters('B', 63)
class CheckinSixDigit(CheckInBase):
    PASSWORD_OFFSET = 34
    PASSWORD_LEN = 6


@MessageParameters('N', 63)
class ModificationSixDigit(ProtocolMessage):
    pass


@MessageParameters('V', 98)
class FullReinitSixDigit(ProtocolMessage):
    pass


@MessageParameters('V', 28)
class PartialReinitSixDigit(ProtocolMessage):
    pass


@MessageParameters('S', 21)
class ReplySixDigit(ProtocolMessage):
    pass


CLASSES = [
TCPConnection,
KeepAlive,
SMDR,
CheckIn,
PhoneAllocation,
VoiceMailAttribution,
CheckOut,
RoomStatusChange,
GuestTelephoneAccount,
WakeUpEvent,
FullReinit,
PartialReinit,
Reply,
Interogation,
ReinitRequest,
CheckinSixDigit,
ModificationSixDigit,
FullReinitSixDigit,
PartialReinitSixDigit,
ReplySixDigit
]

"""[CheckOut, CheckinSixDigit, FullReinit, FullReinitSixDigit,
    GuestTelephoneAccount, Interogation, KeepAlive, MessageParameters, ModificationSixDigit,
    PartialReinit, PartialReinitSixDigit, PhoneAllocation, ReinitRequest,
    Reply, ReplySixDigit, RoomStatusChange, SMDR, TCPConnection, VoiceMailAttribution,
    WakeUpEvent]
"""
