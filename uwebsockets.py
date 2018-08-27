"""
Websockets client for micropython

Based very heavily on
https://github.com/aaugustin/websockets/blob/master/websockets/client.py
"""

#import usocket as socket
import os
import ure as re
import urandom as random
import ustruct as struct
import usocket as socket
import ubinascii as binascii
from ucollections import namedtuple

# Opcodes
OP_CONT = const(0x0)
OP_TEXT = const(0x1)
OP_BYTES = const(0x2)
OP_CLOSE = const(0x8)
OP_PING = const(0x9)
OP_PONG = const(0xa)

# Close codes
CLOSE_OK = const(1000)
CLOSE_GOING_AWAY = const(1001)
CLOSE_PROTOCOL_ERROR = const(1002)
CLOSE_DATA_NOT_SUPPORTED = const(1003)
CLOSE_BAD_DATA = const(1007)
CLOSE_POLICY_VIOLATION = const(1008)
CLOSE_TOO_BIG = const(1009)
CLOSE_MISSING_EXTN = const(1010)
CLOSE_BAD_CONDITION = const(1011)

URL_RE = re.compile(r'ws://([A-Za-z0-9\-\.]+)(?:\:([0-9]+))?(/.+)?')
URI = namedtuple('URI', ('hostname', 'port', 'path'))

def urlparse(uri):
    match = URL_RE.match(uri)
    if match:
        return URI(match.group(1), int(match.group(2)), match.group(3))
    else:
        raise ValueError("Invalid URL: %s" % uri)

class Websocket:
    is_client = False

    def __init__(self, sock):
        self._sock = sock
        self.open = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def settimeout(self, timeout):
        self._sock.settimeout(timeout)

    def read_frame(self, max_size=None):
        # Frame header
        byte1, byte2 = struct.unpack('!BB', self._sock.read(2))

        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        fin = bool(byte1 & 0x80)
        opcode = byte1 & 0x0f

        # Byte 2: MASK(1) LENGTH(7)
        mask = bool(byte2 & (1 << 7))
        length = byte2 & 0x7f

        if length == 126:  # Magic number, length header is 2 bytes
            length, = struct.unpack('!H', self._sock.read(2))
        elif length == 127:  # Magic number, length header is 8 bytes
            length, = struct.unpack('!Q', self._sock.read(8))

        if mask:  # Mask is 4 bytes
            mask_bits = self._sock.read(4)

        try:
            data = self._sock.read(length)
        except MemoryError:
            # We can't receive this many bytes, close the socket
            self.close(code=CLOSE_TOO_BIG)
            return True, OP_CLOSE, None

        if mask:
            data = bytes(b ^ mask_bits[i % 4]
                         for i, b in enumerate(data))

        return fin, opcode, data

    def write_frame(self, opcode, data=b''):
        fin = True
        mask = self.is_client  # messages sent by client are masked

        length = len(data)

        # Frame header
        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        byte1 = 0x80 if fin else 0
        byte1 |= opcode

        # Byte 2: MASK(1) LENGTH(7)
        byte2 = 0x80 if mask else 0

        if length < 126:  # 126 is magic value to use 2-byte length header
            byte2 |= length
            self._sock.write(struct.pack('!BB', byte1, byte2))

        elif length < (1 << 16):  # Length fits in 2-bytes
            byte2 |= 126  # Magic code
            self._sock.write(struct.pack('!BBH', byte1, byte2, length))

        elif length < (1 << 64):
            byte2 |= 127  # Magic code
            self._sock.write(struct.pack('!BBQ', byte1, byte2, length))

        else:
            raise ValueError()

        if mask:  # Mask is 4 bytes
            mask_bits = struct.pack('!I', random.getrandbits(32))
            self._sock.write(mask_bits)

            data = bytes(b ^ mask_bits[i % 4]
                         for i, b in enumerate(data))

        self._sock.write(data)

    def recv(self):
        assert self.open

        while self.open:
            try:
                fin, opcode, data = self.read_frame()
            except ValueError:
                self._close()
                return

            if not fin:
                raise NotImplementedError()

            if opcode == OP_TEXT:
                return data
            elif opcode == OP_BYTES:
                return data
            elif opcode == OP_CLOSE:
                self._close()
                return
            elif opcode == OP_PONG:
                # Ignore this frame, keep waiting for a data frame
                continue
            elif opcode == OP_PING:
                # We need to send a pong frame
                self.write_frame(OP_PONG, data)
                # And then wait to receive
                continue
            elif opcode == OP_CONT:
                # This is a continuation of a previous frame
                raise NotImplementedError(opcode)
            else:
                raise ValueError(opcode)

    def send(self, buf):
        assert self.open

        if isinstance(buf, str):
            opcode = OP_TEXT
            buf = buf.encode('utf-8')
        elif isinstance(buf, bytes):
            opcode = OP_BYTES
        else:
            raise TypeError()

        self.write_frame(opcode, buf)

    def close(self, code=CLOSE_OK, reason=''):
        if not self.open:
            return

        buf = struct.pack('!H', code) + reason.encode('utf-8')

        self.write_frame(OP_CLOSE, buf)
        self._close()

    def _close(self):
        self.open = False
        self._sock.close()

class WebsocketClient(Websocket):
    is_client = True

def connect(uri):
    """
    Connect a websocket.
    """

    # Parse the given WebSocket URI
    uri = urlparse(uri)
    assert uri

    # Connect the socket
    sock = socket.socket()
    addr = socket.getaddrinfo(uri.hostname, uri.port)
    sock.connect(addr[0][4])

    # Sec-WebSocket-Key is 16 bytes of random base64 encoded
    key = binascii.b2a_base64(os.urandom(16))[:-1]

    # WebSocket initiation headers
    headers = [
    	b'GET %s HTTP/1.1' % uri.path or '/',
    	b'Upgrade: websocket',
    	b'Connection: Upgrade',
    	b'Host: %s:%s' % (uri.hostname, uri.port),
    	b'Origin: http://%s:%s' % (uri.hostname, uri.port),
    	b'Sec-WebSocket-Key: ' + key,
    	b'Sec-WebSocket-Version: 13',
    	b'',
    	b''
    ]

    # Concatenate the headers and add new lines
    data = b'\r\n'.join(headers)

    # Send the WebSocket initiation packet
    sock.send(data)

    # Check for the WebSocket response header
    header = sock.readline()[:-2]
    assert header == b'HTTP/1.1 101 Switching Protocols', header

    # We don't (currently) need these headers
    # FIXME: should we check the return key?
    while header:
        header = sock.readline()[:-2]

    return WebsocketClient(sock)
