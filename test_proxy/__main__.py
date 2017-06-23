import socket
import sys
from omnipcx.messages.control import ACK
from omnipcx.messages.protocol import TCPConnection

DEFAULT_OLD_PORT = 5010
DEFAULT_OPERA_PORT = 2561
DEFAULT_CDR_PORT = 6666
ADDR = "localhost"
RECV_SIZE = 150

def dumb_ack():
    server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    address = "::" # socket.gethostname()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, 5010))
    server.listen(1)
    while True:
        sock, addr = server.accept()
        sock.settimeout(5.0)
        while True:
            sock.send(b'\x02@FFFF\x03')
            msg = sock.recv(RECV_SIZE)
            print("Message received %s" % msg)
            sock.send(b'\x02J24271640Z000000113112992359 9995912345678           0066989202161FF\x03')
            msg = sock.recv(RECV_SIZE)
            print("Message received %s" % msg)
            msg = sock.recv(RECV_SIZE)
            print("Message received %s" % msg)
            sock.send(b'\x06')
            print("Sent ACK")



def simple_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5000)
    print("Trying to open a connection to %s:%s" %(ADDR, DEFAULT_OPERA_PORT))
    sock.connect((ADDR, DEFAULT_OPERA_PORT),)
    while True:
        msg = sock.recv(RECV_SIZE)
        print("Message received %s" % msg)
        sock.send(b'\x06')
        print("Sent ACK")
        msg = sock.recv(RECV_SIZE)
        print("Message received %s" % msg)
        sock.send(b'\x06')
        print("Sent ACK")
        sock.send(b'\x02A24271640 VldPoenaru          1    1234039999999.11230 2FF\x03')
        msg = sock.recv(RECV_SIZE)
        print("Message received %s" % msg)

if __name__ == "__main__":
    if int(sys.argv[1]) == 1:
        dumb_ack()
    elif int(sys.argv[1]) == 2:
        simple_client()
