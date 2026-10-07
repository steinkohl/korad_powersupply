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

import pint
import pytest

from pymeasure.test import expected_protocol
from pymeasure.instruments.korad import KC3405P
from pymeasure.units import ureg


def test_voltage():
    with expected_protocol(KC3405P, [("VOUT2?", "5.001")]) as inst:
        assert inst.ch_2.voltage == 5.001 * ureg.V


def test_current():
    with expected_protocol(KC3405P, [("IOUT4?", "0.123")]) as inst:
        assert inst.ch_4.current == 0.123 * ureg.A


def test_voltage_setpoint():
    with expected_protocol(KC3405P, [("VSET1:12.500", None), ("VSET1?", "12.500")]) as inst:
        inst.ch_1.voltage_setpoint = 12.5
        assert inst.ch_1.voltage_setpoint == 12.5 * ureg.V


def test_current_setpoint():
    with expected_protocol(KC3405P, [("ISET3:1.250", None)]) as inst:
        inst.ch_3.current_setpoint = 1.25


def test_setpoints_accept_quantities_in_other_units():
    with expected_protocol(KC3405P, [("VSET1:0.500", None), ("ISET1:0.250", None),
                                     ("OCPSET1:2.000", None),
                                     ("OVPSET1:0.015", None)]) as inst:
        inst.ch_1.voltage_setpoint = 500 * ureg.mV
        inst.ch_1.current_setpoint = 250 * ureg.mA
        inst.ch_1.ocp_setpoint = 2 * ureg.A
        inst.ch_1.ovp_setpoint = 15 * ureg.mV


def test_setpoint_wrong_dimension():
    with expected_protocol(KC3405P, []) as inst:
        with pytest.raises(pint.DimensionalityError):
            inst.ch_1.voltage_setpoint = 1 * ureg.A


def test_setpoint_quantity_out_of_range():
    with expected_protocol(KC3405P, []) as inst:
        with pytest.raises(ValueError):
            inst.ch_1.voltage_setpoint = 31000 * ureg.mV


@pytest.mark.parametrize("prop, value", [("voltage_setpoint", 31), ("voltage_setpoint", -1),
                                         ("current_setpoint", 5.5), ("ocp_setpoint", 6),
                                         ("ovp_setpoint", 32)])
def test_setpoint_out_of_range(prop, value):
    with expected_protocol(KC3405P, []) as inst:
        with pytest.raises(ValueError):
            setattr(inst.ch_1, prop, value)


def test_protection_setpoints():
    with expected_protocol(KC3405P, [("OCPSET1:5.100", None), ("OCPSET1?", "5.100"),
                                     ("OVPSET2:31.000", None), ("OVPSET2?", "31.000")]) as inst:
        inst.ch_1.ocp_setpoint = 5.1
        assert inst.ch_1.ocp_setpoint == 5.1 * ureg.A
        inst.ch_2.ovp_setpoint = 31
        assert inst.ch_2.ovp_setpoint == 31 * ureg.V


def test_protection_enabled():
    with expected_protocol(KC3405P, [("OCP1:1", None), ("OCP1?", "1"),
                                     ("OVP4:0", None), ("OVP4?", "0")]) as inst:
        inst.ch_1.ocp_enabled = True
        assert inst.ch_1.ocp_enabled is True
        inst.ch_4.ovp_enabled = False
        assert inst.ch_4.ovp_enabled is False


def test_external_settings():
    with expected_protocol(KC3405P, [("EXIT1:1", None), ("EXON2:0", None),
                                     ("COMP3:1", None)]) as inst:
        inst.ch_1.external_trigger_enabled = True
        inst.ch_2.external_switch_enabled = False
        inst.ch_3.external_compensation_enabled = True


def test_output_enabled():
    with expected_protocol(KC3405P, [("OUT2:1", None), ("OUT2:0", None)]) as inst:
        inst.ch_2.output_enabled = True
        inst.ch_2.output_enabled = False


def test_status():
    # CH1 and CH3 in constant voltage, outputs of CH1 and CH4 on: 0b10010101
    status = bytes([0b10010101, 0x0A])
    with expected_protocol(KC3405P, [("STATUS?", status)] * 8) as inst:
        assert inst.ch_1.mode == "cv"
        assert inst.ch_2.mode == "cc"
        assert inst.ch_3.mode == "cv"
        assert inst.ch_4.mode == "cc"
        assert inst.ch_1.output_is_on is True
        assert inst.ch_2.output_is_on is False
        assert inst.ch_3.output_is_on is False
        assert inst.ch_4.output_is_on is True


def test_invalid_status():
    with expected_protocol(KC3405P, [("STATUS?", b"\x00")]) as inst:
        with pytest.raises(ConnectionError):
            inst.status_byte


def test_device_info():
    with expected_protocol(KC3405P, [(":SYST:DEVINFO?", "DHCP:1"),
                                     (None, "IP:192.168.1.100"),
                                     (None, "NETMASK:255.255.255.0"),
                                     (None, "GATEWAY:192.168.1.1"),
                                     (None, "MAC:aa-bb-cc-dd-ee-ff"),
                                     (None, "PORT:18190"),
                                     (None, "BAUDRATE:115200"),
                                     (None, "GPIB:1")]) as inst:
        assert inst.device_info == {
            "dhcp": 1, "ip_address": "192.168.1.100", "netmask": "255.255.255.0",
            "gateway": "192.168.1.1", "mac_address": "aa-bb-cc-dd-ee-ff",
            "udp_port": 18190, "baud_rate": 115200, "gpib_address": 1,
        }


def test_lock_buttons():
    with expected_protocol(KC3405P, [("LOCK:1", None), ("LOCK:0", None)]) as inst:
        inst.buttons_locked = True
        inst.buttons_locked = False


def test_all_outputs():
    with expected_protocol(KC3405P, [("OUT1234:1", None)]) as inst:
        inst.all_outputs_enabled = True


def test_shutdown():
    with expected_protocol(KC3405P, [("OUT1234:0", None)]) as inst:
        inst.shutdown()
