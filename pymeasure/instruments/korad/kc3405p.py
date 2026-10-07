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

from pymeasure.adapters import UDPAdapter
from pymeasure.instruments import Channel, Instrument
from pymeasure.instruments.validators import strict_discrete_set, strict_range
from pymeasure.units import ureg

#: Default UDP port of the KC3405P.
DEFAULT_PORT = 18190


def _quantity(unit):
    """Return a `get_process` function that attaches `unit` to a measured value."""
    return lambda value: ureg.Quantity(value, unit)


def _quantity_range(unit):
    """Return a validator that accepts a plain number (in `unit`) or a pint quantity of the
    same dimension and checks its magnitude in `unit` against a strict range."""
    def validator(value, values):
        if isinstance(value, ureg.Quantity):
            value = value.to(unit).magnitude
        return strict_range(value, values)
    return validator


class KC3405PChannel(Channel):
    """One output channel of the Korad KC3405P."""

    voltage = Channel.measurement(
        "VOUT{ch}?", """Measure the actual output voltage (:class:`pint.Quantity` in V).""",
        get_process=_quantity("V"),
    )

    current = Channel.measurement(
        "IOUT{ch}?", """Measure the actual output current (:class:`pint.Quantity` in A).""",
        get_process=_quantity("A"),
    )

    voltage_setpoint = Channel.control(
        "VSET{ch}?", "VSET{ch}:%.3f",
        """Control the output voltage setpoint
        (:class:`pint.Quantity` in V, strictly from 0 to 30 V).
        A plain number is taken as V.""",
        validator=_quantity_range("V"),
        get_process=_quantity("V"),
        values=[0, 30],
    )

    current_setpoint = Channel.control(
        "ISET{ch}?", "ISET{ch}:%.3f",
        """Control the output current setpoint
        (:class:`pint.Quantity` in A, strictly from 0 to 5 A).
        A plain number is taken as A.""",
        validator=_quantity_range("A"),
        get_process=_quantity("A"),
        values=[0, 5],
    )

    ocp_setpoint = Channel.control(
        "OCPSET{ch}?", "OCPSET{ch}:%.3f",
        """Control the overcurrent protection threshold (:class:`pint.Quantity` in A, strictly
        from 0 to 5.1 A). A plain number is taken as A.""",
        validator=_quantity_range("A"),
        get_process=_quantity("A"),
        values=[0, 5.1],
    )

    ovp_setpoint = Channel.control(
        "OVPSET{ch}?", "OVPSET{ch}:%.3f",
        """Control the overvoltage protection threshold (:class:`pint.Quantity` in V, strictly
        from 0 to 31 V). A plain number is taken as V.""",
        validator=_quantity_range("V"),
        get_process=_quantity("V"),
        values=[0, 31],
    )

    ocp_enabled = Channel.control(
        "OCP{ch}?", "OCP{ch}:%d",
        """Control whether the overcurrent protection is enabled (bool).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    ovp_enabled = Channel.control(
        "OVP{ch}?", "OVP{ch}:%d",
        """Control whether the overvoltage protection is enabled (bool).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    external_trigger_enabled = Channel.setting(
        "EXIT{ch}:%d",
        """Set whether the external trigger is enabled (bool, write-only).
        Enabling it disables the external switch of this channel.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    external_switch_enabled = Channel.setting(
        "EXON{ch}:%d",
        """Set whether the external switch is enabled (bool, write-only).
        Enabling it disables the external trigger of this channel.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    external_compensation_enabled = Channel.setting(
        "COMP{ch}:%d",
        """Set whether the external compensation is enabled (bool, write-only).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    output_enabled = Channel.setting(
        "OUT{ch}:%d",
        """Set whether the output of this channel is enabled (bool, write-only).
        Use :attr:`output_is_on` to read back the state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    # The status byte holds the regulation mode of channels 1-4 in bits 0-3
    # (set: constant voltage, cleared: constant current) and the output state in bits 4-7.
    @property
    def output_is_on(self) -> bool:
        """Get whether the output of this channel is enabled (bool)."""
        return bool(self.parent.status_byte >> (self.id + 3) & 1)

    @property
    def mode(self) -> str:
        """Get the regulation mode of this channel: 'cv' (constant voltage) or
        'cc' (constant current)."""
        return "cv" if self.parent.status_byte >> (self.id - 1) & 1 else "cc"


class KC3405P(Instrument):
    """Korad KC3405P four channel power supply, controlled via Ethernet (UDP).

    The channels are available as :attr:`ch_1` to :attr:`ch_4` and
    through the :attr:`channels` collection.

    Voltages and currents are :class:`pint.Quantity` objects (see :mod:`pymeasure.units`).

    .. code-block:: python

        from pymeasure.units import ureg

        psu = KC3405P("192.168.1.100")
        psu.ch_1.voltage_setpoint = 5  # plain numbers are taken as V (A for currents)
        psu.ch_1.current_setpoint = 500 * ureg.mA
        psu.ch_1.output_enabled = True
        print(psu.ch_1.voltage, psu.ch_1.current, psu.ch_1.mode)
        psu.shutdown()

    :param adapter: IP address (str) of the instrument or an
        :class:`~pymeasure.adapters.Adapter` instance. An IP address creates a
        :class:`~pymeasure.adapters.UDPAdapter`.
    :param name: Name of the instrument.
    :param port: UDP port of the instrument. The local socket is bound to the same port,
        as the instrument replies to it. Only used if `adapter` is an IP address.
    :param kwargs: Any valid key-word argument for
        :class:`~pymeasure.adapters.UDPAdapter` or :class:`Instrument`.
    """

    channels = Instrument.MultiChannelCreator(KC3405PChannel, (1, 2, 3, 4), prefix="ch_")

    def __init__(self, adapter, name="Korad KC3405P", port=DEFAULT_PORT, **kwargs):
        if isinstance(adapter, str):
            kwargs.setdefault("local_port", port)
            adapter = UDPAdapter(adapter, port, write_termination="\r\n",
                                 read_termination="\n", **kwargs)
            kwargs = {}
        super().__init__(adapter, name, includeSCPI=False, **kwargs)

    @property
    def status_byte(self) -> int:
        """Get the raw status byte (mode and output state of all channels)."""
        self.write("STATUS?")
        response = self.read_bytes(-1)
        if len(response) != 2:
            raise ConnectionError(f"Invalid status response received: {response!r}")
        return response[0]

    @property
    def device_info(self) -> dict:
        """Get the network and interface settings of the instrument (dict)."""
        self.write(":SYST:DEVINFO?")
        # The device answers with one datagram per entry, each as "<name>:<value>".
        entries = [self.read().split(":", 1)[1] for _ in range(8)]
        dhcp, ip, netmask, gateway, mac, port, baud_rate, gpib = entries
        return {
            "dhcp": int(dhcp),
            "ip_address": ip,
            "netmask": netmask,
            "gateway": gateway,
            "mac_address": mac,
            "udp_port": int(port),
            "baud_rate": int(baud_rate),
            "gpib_address": int(gpib),
        }

    buttons_locked = Instrument.setting(
        "LOCK:%d",
        """Set whether the front panel buttons are locked (bool, write-only).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    all_outputs_enabled = Instrument.setting(
        "OUT1234:%d",
        """Set whether the outputs of all channels are enabled (bool, write-only).""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    def shutdown(self):
        """Disable the outputs of all channels."""
        self.all_outputs_enabled = False
        super().shutdown()
