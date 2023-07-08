"""
    Read values from SPS30 Particulate Matter Sensor over UART
    Tested on RP2040 Pico W
    https://www.sparkfun.com/products/15103
    https://cdn.sparkfun.com/assets/4/e/e/f/8/Sensirion_PM_Sensors_Datasheet_SPS30.pdf
    https://github.com/Sensirion/embedded-uart-sps
    https://github.com/dvsu/sps30
    https://docs.micropython.org/en/latest/library/machine.UART.html
"""
from time import sleep
import struct

import machine

led_pin = machine.Pin("LED", machine.Pin.OUT)

class SPS30:
    def __init__(self, uart):
        self.uart = uart


    def start(self):
        buf = [0x7E, 0x00, 0x00, 0x02, 0x01, 0x03, 0xF9, 0x7E]
        self.uart.write(bytes(buf))
        self.uart.flush()
    

    def stop(self):
        buf = [0x7E, 0x00, 0x01, 0x00, 0xFE, 0x7E]
        self.uart.write(bytes(buf))
        self.uart.flush()


    def flush_input(self):
        """ Clear any bytes pending"""
        if self.uart.any():
            self.uart.read()
    
    def reverse_byte_stuffing(self, raw):
        """
        Reverse byte-stuffing
        """
        if b'\x7D\x5E' in raw:
            raw = raw.replace(b'\x7D\x5E', b'\x7E')
        if b'\x7D\x5D' in raw:
            raw = raw.replace(b'\x7D\x5D', b'\x7D')
        if b'\x7D\x31' in raw:
            raw = raw.replace(b'\x7D\x31', b'\x11')
        if b'\x7D\x33' in raw:
            raw = raw.replace(b'\x7D\x33', b'\x13')
        return raw


    def read(self, length):
        """
        Read length bytes from uart.  Keep reading if we haven't read all the expected bytes

        Handles times when byte stuffing occurs and thus we read too few bytes
        """
        data = bytearray()
        while length > 0:
            raw = self.uart.read(length)
            if raw is None:
                print("read_values: Timeout")
                return None

            # Reverse byte-stuffing
            raw = self.reverse_byte_stuffing(raw)
            data.extend(raw)

            length = length - len(raw)

        return data


    def read_values(self):
        """
        PM1,PM2.5,PM4,PM10,0.3÷0.5,0.3÷1,0.3÷2.5,0.3÷4,0.3÷10,typical size

        Empty response frame:
        0x7E 0x00 0x03 0x00 0x00 0xFC 0x7E
        Or response frame with new measurement values:
        0x7E 0x00 0x03 0x00 0x28 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0xD4 0x7E
        """
        self.flush_input()

        # Ask for data
        self.uart.write(bytes([0x7E, 0x00, 0x03, 0x00, 0xFC, 0x7E]))

        # We want 47 bytes
        raw = self.read(47)
        if raw is None:
            print("read_values: Timeout")
            return None

        # print(len(raw))
        # import binascii
        # print(binascii.hexlify(bytearray(raw)))

        # Discard header and tail
        raw_data = raw[5:-2]

        try:
            data = struct.unpack(">ffffffffff", raw_data)
        except Exception:
            data = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return data


    def read_product_type(self):
        """
        Read product type as string
        Expect: 00080000
        """
        self.flush_input()

        self.uart.write(bytes([0x7E, 0x00, 0xD0, 0x01, 0x00, 0x2E, 0x7E]))

        raw = self.uart.read(24)
        if raw is None:
            print("read_serial: Timeout")
            return None

        # Reverse byte-stuffing
        raw = self.reverse_byte_stuffing(raw)

        # Discard header, tail and decode
        product_type = raw[5:-3].decode('ascii')
        return product_type


    def read_serial_number(self):
        """
        Read serial number as string
        """
        self.flush_input()

        self.uart.write(bytes([0x7E, 0x00, 0xD0, 0x01, 0x03, 0x2B, 0x7E]))

        raw = self.uart.read(24)
        if raw is None:
            print("read_serial: Timeout")
            return None
        
        # Reverse byte-stuffing
        raw = self.reverse_byte_stuffing(raw)
        
        # Discard header, tail and decode
        serial_number = raw[5:-3].decode('ascii')
        return serial_number


    def read_firmware_version(self):
        """
        Read firmware version as string
        """
        self.flush_input()

        self.uart.write(bytes([0x7E, 0x00, 0xD1, 0x00, 0x2E, 0x7E]))

        raw = self.uart.read(14)
        if raw is None:
            print("read_firmware_version: TIMEOUT")
            return None
        
        # print(raw)
        
        # Reverse byte-stuffing
        raw = self.reverse_byte_stuffing(raw)
        
        # Discard header and tail
        data = raw[5:-2]
        # Unpack data
        data = struct.unpack(">bbbbbbb", data)
        firmware_version = str(data[0]) + "." + str(data[1])
        return firmware_version


def connect_sps30():
    """
    Connect to SPS30 sensor on UART0
    """
    uart = machine.UART(0, 115200, tx=machine.Pin(0), rx=machine.Pin(1), timeout=2000)
    uart.init(bits=8, parity=None, stop=1)

    return SPS30(uart)


if __name__ == "__main__":
    led_pin.toggle()
    print("Run")

    sensor = connect_sps30()

    print(f"SPS30")
    sensor.start()
    sleep(1)

    print(f"Product type: {sensor.read_product_type()}")
    # print(f"Firmware: {sensor.read_firmware_version()}")
    # print(f"Serial Number: {sensor.read_serial_number()}")

    while True:
        
        # Average 30s of readings
        readings = []
        for i in range(30):
            readings.append(sensor.read_values())
            sleep(1)

        sum_readings = [sum(i) for i in zip(*readings)]
        avg_readings = [i / 30 for i in sum_readings]
        print(avg_readings)

    led_pin.toggle()
    print("Done")
