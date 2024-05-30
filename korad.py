import socket
import math
import json


def _convert_response(data: bytes):
    try:
        return data.decode("utf-8").strip('\n')
    except:
        return data


def _split_response(data):
    try:
        data = _convert_response(data)
        return data.split(':')[1]
    except:
        return data


def _check_channel(channel: int) -> int:
    channel = int(channel)
    if 1 > channel > 4:
        raise ValueError("Channel must be between 1 and 4")
    return channel


class KC3405P:
    _default_voltage = 0.0
    _default_current = 0.0
    _default_ocp = 5.1
    _default_ovp = 31.0
    def __init__(self, ip_address: str, port: int = 18190):
        self.serverAddressPort = (ip_address, port)
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpSocket.bind(('0.0.0.0', port))

    def _send_command(self, cmd: str):
        data = f"{cmd}\r\n"
        self.udpSocket.sendto(str.encode(data), self.serverAddressPort)
        return self

    def _get_response(self):
        return self.udpSocket.recv(128)

    def _get_response_str(self):
        return _convert_response(self._get_response())

    def get_device_info(self) -> dict:
        self._send_command(":SYST:DEVINFO?")
        dhcp = self._get_response_str()
        ip = self._get_response_str()
        netmask = self._get_response_str()
        gateway = self._get_response_str()
        mac = self._get_response_str()
        port = self._get_response_str()
        baudrate = self._get_response_str()
        gpib = self._get_response_str()
        data = {
            "system_dhcp": int(_split_response(dhcp)),
            "system_ip_address": str(_split_response(ip)),
            "system_netmask": str(_split_response(netmask)),
            "system_gateway": str(_split_response(gateway)),
            "system_mac_address": str(_split_response(mac)),
            "system_udp_port": int(_split_response(port)),
            "system_baud_rate": int(_split_response(baudrate)),
            "system_gpib_address": int(_split_response(gpib)),
        }
        return data

    def _get_status_byte(self) -> int:
        self._send_command("STATUS?")
        response = self._get_response()
        if len(response) != 2:
            raise ValueError("Invalid response received")
        return response[0]

    def get_status(self) -> dict:
        status = f"{self._get_status_byte():08b}"[::-1]
        status_dict = {
            "ch1_mode": "cv" if status[0] == "1" else "cc",
            "ch2_mode": "cv" if status[1] == "1" else "cc",
            "ch3_mode": "cv" if status[2] == "1" else "cc",
            "ch4_mode": "cv" if status[3] == "1" else "cc",
            "ch1_output": "on" if status[4] == "1" else "off",
            "ch2_output": "on" if status[5] == "1" else "off",
            "ch3_output": "on" if status[6] == "1" else "off",
            "ch4_output": "on" if status[7] == "1" else "off",
        }
        return status_dict

    def get_voltage(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"VOUT{channel}?")
        voltage = float(self._get_response_str())
        return voltage

    def get_current(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"IOUT{channel}?")
        current = float(self._get_response_str())
        return current

    def get_voltage_setting(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"VSET{channel}?")
        voltage = float(self._get_response_str())
        return voltage

    def get_current_setting(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"ISET{channel}?")
        current = float(self._get_response_str())
        return current

    def set_voltage(self, channel: int, voltage: float) -> None:
        channel = _check_channel(channel)
        self._send_command(f"VSET{channel}:{voltage:.3f}")
        setting = self.get_voltage_setting(channel)
        if not math.isclose(voltage, setting, abs_tol=1e-2):
            raise ValueError(f"Voltage should be close to {voltage:.3f}V, "
                             f"but was {setting:.3f}V. "
                             f"Not able to set voltage on channel {channel}!")
        return

    def set_current(self, channel: int, current: float) -> None:
        channel = _check_channel(channel)
        self._send_command(f"ISET{channel}:{current:.3f}")
        setting = self.get_current_setting(channel)
        if not math.isclose(current, setting, abs_tol=1e-2):
            raise ValueError("Current should be close to {voltage:.3f}A, "
                             f"but was {setting:.3f}A. "
                             f"Not able to set current on channel {channel}!")
        return

    def lock_buttons(self):
        self._send_command("LOCK:1")
        return

    def unlock_buttons(self):
        self._send_command("LOCK:0")
        return

    def enable_output(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, "
                             "or 0 for triggering all channels")
        elif channel == 0:
            self._send_command("OUT1234:1")
            status = f"{self._get_status_byte():08b}"[::-1]
            if not status[4:] == "1111":
                raise ValueError(f"Could not enable all channels! "
                                 f"CH1: {status[4]}, CH2: {status[5]}, "
                                 f"CH3: {status[6]}, CH4: {status[7]}")
        else:
            self._send_command(f"OUT{channel}:1")
            status = f"{self._get_status_byte():08b}"[::-1]
            if not status[3+channel] == "1":
                raise ValueError(f"Could not enable channel {channel}!")
        return

    def disable_output(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, "
                             "or 0 for triggering all channels")
        elif channel == 0:
            self._send_command(f"OUT1234:0")
            status = f"{self._get_status_byte():08b}"[::-1]
            if not status[4:] == "0000":
                raise ValueError("Could not disable all channels! "
                                 f"CH1: {status[4]}, CH2: {status[5]}, "
                                 f"CH3: {status[6]}, CH4: {status[7]}")
        else:
            self._send_command(f"OUT{channel}:0")
            status = f"{self._get_status_byte():08b}"[::-1]
            if not status[3+channel] == "0":
                raise ValueError(f"Could not disable channel {channel}!")
        return

    def get_overcurrent_protection_setting(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"OCPSET{channel}?")
        current = float(self._get_response_str())
        return current

    def set_overcurrent_protection(self, channel: int, current: float):
        channel = _check_channel(channel)
        self._send_command(f"OCPSET{channel}:{current:.3f}")
        setting = self.get_current_setting(channel)
        if math.isclose(current, setting, abs_tol=1e-2):
            raise ValueError("Current should be close to setting, "
                             "not able to set current on device!")
        return

    def get_overvoltage_protection_setting(self, channel: int) -> float:
        channel = _check_channel(channel)
        self._send_command(f"OVPSET{channel}?")
        voltage = float(self._get_response_str())
        return voltage

    def set_overvoltage_protection(self, channel: int, voltage: float):
        channel = _check_channel(channel)
        self._send_command(f"OVPSET{channel}:{voltage:.3f}")
        setting = self.get_voltage_setting(channel)
        if math.isclose(voltage, setting, abs_tol=1e-2):
            raise ValueError("Voltage should be close to setting, "
                             "not able to set voltage on device!")
        return

    def get_ocp_status(self, channel: int) -> bool:
        channel = _check_channel(channel)
        self._send_command(f"OCP{channel}?")
        ocp_status = self._get_response_str()
        return bool(int(ocp_status))

    def enable_overcurrent_protection(self, channel: int):
        channel = _check_channel(channel)
        self._send_command(f"OCP{channel}:1")
        if not self.get_ocp_status(channel):
            raise ValueError(f"Could not enable overcurrent protection "
                             f"on channel {channel}!")
        return

    def disable_overcurrent_protection(self, channel: int):
        channel = _check_channel(channel)
        self._send_command(f"OCP{channel}:0")
        if self.get_ocp_status(channel):
            raise ValueError(f"Could not disable overcurrent protection "
                             f"on channel {channel}!")
        return

    def get_ovp_status(self, channel: int) -> bool:
        channel = _check_channel(channel)
        self._send_command(f"OVP{channel}?")
        ovp_status = self._get_response_str()
        return bool(int(ovp_status))

    def enable_overvoltage_protection(self, channel: int):
        channel = _check_channel(channel)
        self._send_command(f"OVP{channel}:1")
        if not self.get_ovp_status(channel):
            raise ValueError(f"Could not enable overvoltage protection "
                             f"on channel {channel}!")
        return

    def disable_overvoltage_protection(self, channel: int):
        channel = _check_channel(channel)
        self._send_command(f"OVP{channel}:0")
        if self.get_ovp_status(channel):
            raise ValueError(f"Could not disable overvoltage protection "
                             f"on channel {channel}!")
        return

    def enable_external_trigger(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "enabling external triggers for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"EXIT{i}:1")
        else:
            self._send_command(f"EXIT{channel}:1")
        return

    def disable_external_trigger(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "disabling external triggers for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"EXIT{i}:0")
        else:
            self._send_command(f"EXIT{channel}:0")
        return

    def enable_external_switch(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "enabling external switches for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"EXON{i}:1")
        else:
            self._send_command(f"EXON{channel}:1")
        return

    def disable_external_switch(self, channel: int = 0):
        # channel=0 sets all channels
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "disabling external switches for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"EXON{i}:0")
        else:
            self._send_command(f"EXON{channel}:0")
        return

    def enable_external_compensation(self, channel: int = 0):
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "enabling external compensation for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"COMP{i}:1")
        else:
            self._send_command(f"COMP{channel}:1")
        return

    def disable_external_compensation(self, channel: int = 0):
        channel = int(channel)
        if 0 > channel > 4:
            raise ValueError("Channel must be between 1 and 4, or 0 for "
                             "disabling external compensation for all channels")
        elif channel == 0:
            for i in range(1, 5):
                self._send_command(f"COMP{i}:0")
        else:
            self._send_command(f"COMP{channel}:0")
        return

    def get_settings(self) -> dict:
        settings = {}
        settings.update(self.get_device_info())
        settings.update(self.get_status())
        for channel in range(1, 5):
            settings.update({
                f"ch{channel}_ocp_value":
                    self.get_overcurrent_protection_setting(channel),
                f"ch{channel}_ocp":
                    "on" if self.get_ocp_status(channel) else "off",
                f"ch{channel}_ovp_value":
                    self.get_overvoltage_protection_setting(channel),
                f"ch{channel}_ovp":
                    "on" if self.get_ovp_status(channel) else "off",
                f"ch{channel}_voltage_setting":
                    self.get_voltage_setting(channel),
                f"ch{channel}_voltage":
                    self.get_voltage(channel),
                f"ch{channel}_current_setting":
                    self.get_current_setting(channel),
                f"ch{channel}_current":
                    self.get_current(channel),
            })
        return settings

    def print_settings(self):
        print(json.dumps(self.get_settings(), sort_keys=True, indent=4))

    def reset_settings(self):
        self.lock_buttons()
        self.disable_output()
        self.disable_external_switch()
        self.disable_external_trigger()
        self.disable_external_compensation()
        for channel in range(1, 5):
            self.set_overcurrent_protection(channel, self._default_ocp)
            self.enable_overcurrent_protection(channel)
            self.set_overvoltage_protection(channel, self._default_ovp)
            self.enable_overvoltage_protection(channel)
            self.set_voltage(channel, self._default_voltage)
            self.set_current(channel, self._default_current)


    # TODO
    """    
    EXIT<X>:<Boolean>
        Description: turning ON/OFF the external trigger; and turning ON it can 
        actively turn off the external switch functions of according channels.
        Example:EXIT1:1
        Turning ON the external trigger of CH1.

    COMP<X>:<Boolean>
        Description: turning ON/OFF the external compensation.
        Example:COMP1:1
        Turning ON the external compensation on CH1.

    EXON<X>:<Boolean>
        Description: turning ON/OFF the external switch; and turning ON it can 
        actively turn off the external trigger functions of according channels.
        
    VASTEP<X>:<NR2>,<NR2>,<NR2>,<NR2>
        Description:automatically outputting step voltage; before sending this 
        command, you need to turn ON the output; if the output is turned off, 
        this command will be invalid.
        Example:VASTEP1:2,30,0.1,0.2
        The automatic voltage stepping is set to be:the starting voltage is 2V,
        the ending voltage is 30V,the stepping voltage is 0.1V,and the stepping 
        time is 0.2S.
        
    VASTOP<X>
        Description:stop automatic voltage after VASTEP command.
        Example:VASTOP1
        stop zhe automatic voltage of CH1
    
    IASTEP<X>:<NR2>,<NR2>,<NR2>,<NR2>
        Description:automatically outputting step current; before sending this 
        command, you need to turn ON the
         output; if the output is turned off, this command will be
        invalid.
        Example:IASTEP1:0.2,3,0.1,0.2
        The automatic current stepping is set to be:the starting current is 
        0.2A, the ending current is 3A,the stepping current is 0.1A, 
        and the stepping time is 0.2S

    IASTOP<X>
        Description:stop automatic current after IASTEP command.
        Example:IASTOP1
        stop zhe automatic current of CH1
    
    VSTEP<X>:<NR2>
        Description:set manual step voltage
        Example:VSTEP1:0.5
        set CH1 manual step voltage

    VUP<X>
        Description:manually increase the voltage set by VSTEP and use the 
        command VSTEP before using this command
        Example:VUP1
        manually increase the voltage set by VSTEP1 on CH1
    
    VDOWN<X>
        Description:manually reduce the voltage set by VSTEP and use the command
        VSTEP before using this command
        Example:VDOWN1
        manually reduces the voltage set by VSTEP1 on CH1
    
    ISTEP<X>:<NR2>
        Description:set manual step current
        Example:ISTEP1:0.5 set CH1 manual step current

    IUP<X>
        Description:manually increase the current set by ISTEP and use the 
        command ISTEP before using this command
        Example:IUP1 manually increase the current set by ISTEP1 on CH1
    
    IDOWN<X>
        Description:manually reduce the current set by ISTEP and use the command
        ISTEP before using this command
        Example:IDOWN1 manually reduces the current set by ISTEP1 on CH1
        
    LISTCH<X>:<NR1>,<NR1>,<NR2>,<NR2>,<NR2>
        Description: modifying LIST value of the channels.
        Example:LISTCH1:2,3,12.5,2.2,1.5
        modifying the voltage of the 3rd step of LIST2 to be 12.5V, 
        current 2.2A and time 1.5s.

    LISTLCH<X>:<NR1>,<NR1>
        Description: modifying the LIST length of the channel.
        Example:LISTLCH1:3,56
        Modifying the length of CH1 LIST3 to be 56.
        
    LISTCCH<X>:<NR1>,<NR1>
        Description: modifying the LIST recycling times of the channel.
        Example:LISTCCH1:3,100
        Modifying the LIST3 recycling times on CH1 to be 100.
    
    LISTSCH<X>:<NR1>
        Description: saving LIST.
        Example:LISTSCH1:2
        Saving LIST2 on CH1.

    """