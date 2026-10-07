#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2026 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
import socket
from typing import Optional

from .adapter import Adapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class UDPAdapter(Adapter):
    """Adapter class for instruments that communicate via UDP datagrams.

    UDP is message based: every :meth:`write_bytes` call sends exactly one datagram and
    every read call receives exactly one datagram. If an instrument answers with several
    datagrams, call read once per datagram.

    :param host: IP address or host name of the instrument.
    :param port: UDP port of the instrument.
    :param local_port: UDP port to bind the local socket to. Some instruments reply to a fixed
        port instead of the port the request came from, which makes binding necessary.
        If None, the operating system chooses a free port.
    :param local_address: Local interface address to bind to (only used with `local_port`).
    :param timeout: Time in seconds to wait for a datagram. None waits forever.
    :param write_termination: String appended to messages before writing them.
    :param read_termination: String removed from the end of read messages.
    :param buffer_size: Maximum datagram size in bytes that can be received.
    """

    connection: socket.socket

    def __init__(
        self,
        host: str,
        port: int,
        local_port: Optional[int] = None,
        local_address: str = "0.0.0.0",
        timeout: Optional[float] = 1.0,
        write_termination: str = "",
        read_termination: str = "",
        buffer_size: int = 1024,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.write_termination = write_termination
        self.read_termination = read_termination
        self.buffer_size = buffer_size
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connection.settimeout(timeout)
        if local_port is not None:
            self.connection.bind((local_address, local_port))

    @property
    def timeout(self) -> Optional[float]:
        """Time in seconds to wait for a datagram. None waits forever."""
        return self.connection.gettimeout()

    @timeout.setter
    def timeout(self, value: Optional[float]) -> None:
        self.connection.settimeout(value)

    def _write(self, command: str, **kwargs) -> None:
        """Write a string command to the instrument appending `write_termination`.

        :param str command: Command string to be sent to the instrument
            (without termination).
        :param \\**kwargs: Keyword arguments for the connection itself.
        """
        self._write_bytes((command + self.write_termination).encode(), **kwargs)

    def _write_bytes(self, content: bytes, **kwargs) -> None:
        """Send `content` as one datagram to the instrument.

        :param bytes content: The bytes to write to the instrument.
        :param \\**kwargs: Keyword arguments for the connection itself.
        """
        self.connection.sendto(content, (self.host, self.port), **kwargs)

    def _read(self, **kwargs) -> str:
        """Receive one datagram and return it as string without `read_termination`.

        :param \\**kwargs: Keyword arguments for the connection itself.
        :returns str: ASCII response of the instrument (read_termination is removed first).
        """
        read = self._read_bytes(-1, **kwargs).decode()
        return read.removesuffix(self.read_termination) if self.read_termination else read

    def _read_bytes(self, count: int, break_on_termchar: bool = False, **kwargs) -> bytes:
        """Receive one datagram.

        :param int count: Maximum number of bytes to return. A value of -1 returns the whole
            datagram. As UDP is message based, the remainder of a longer datagram is discarded.
        :param bool break_on_termchar: Has no effect, a datagram is always read as a whole.
        :param \\**kwargs: Keyword arguments for the connection itself.
        :returns bytes: Bytes response of the instrument (including termination).
        """
        data = self.connection.recv(self.buffer_size, **kwargs)
        return data if count < 0 else data[:count]

    def flush_read_buffer(self) -> None:
        """Discard all datagrams that are waiting to be read."""
        timeout = self.connection.gettimeout()
        self.connection.settimeout(0)
        try:
            while True:
                self.connection.recv(self.buffer_size)
        except BlockingIOError:
            pass
        finally:
            self.connection.settimeout(timeout)

    def __repr__(self) -> str:
        return f"<UDPAdapter(host='{self.host}', port={self.port})>"
