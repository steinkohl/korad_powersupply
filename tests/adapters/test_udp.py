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

import socket

import pytest

from pymeasure.adapters import UDPAdapter


@pytest.fixture
def server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(1)
    yield sock
    sock.close()


@pytest.fixture
def adapter(server):
    adapter = UDPAdapter("127.0.0.1", server.getsockname()[1], timeout=0.5,
                         write_termination="\r\n", read_termination="\n")
    yield adapter
    adapter.close()


def test_write_appends_termination(adapter, server):
    adapter.write("VOUT1?")
    assert server.recvfrom(128)[0] == b"VOUT1?\r\n"


def test_write_bytes(adapter, server):
    adapter.write_bytes(b"\x01\x02")
    assert server.recvfrom(128)[0] == b"\x01\x02"


def test_read_strips_termination(adapter, server):
    adapter.write("x")
    server.sendto(b"1.234\n", server.recvfrom(128)[1])
    assert adapter.read() == "1.234"


def test_each_read_returns_one_datagram(adapter, server):
    adapter.write("x")
    client = server.recvfrom(128)[1]
    server.sendto(b"a\n", client)
    server.sendto(b"b\n", client)
    assert adapter.read() == "a"
    assert adapter.read() == "b"


def test_read_bytes_count(adapter, server):
    adapter.write("x")
    server.sendto(b"abc\n", server.recvfrom(128)[1])
    assert adapter.read_bytes(2) == b"ab"


def test_read_timeout(adapter):
    with pytest.raises(TimeoutError):
        adapter.read()


def test_flush_read_buffer(adapter, server):
    adapter.write("x")
    client = server.recvfrom(128)[1]
    server.sendto(b"stale\n", client)
    server.sendto(b"stale\n", client)
    adapter.flush_read_buffer()
    with pytest.raises(TimeoutError):
        adapter.read()
    assert adapter.timeout == 0.5


def test_bind_local_port(server):
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    adapter = UDPAdapter("127.0.0.1", server.getsockname()[1], local_port=port,
                         local_address="127.0.0.1")
    adapter.write("x")
    assert server.recvfrom(128)[1][1] == port
    adapter.close()
