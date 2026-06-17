##############################################################################
#
# Hamster 3.1: Attempt to control hamster with color wheel
#
#############################################################################

from machine import Pin, Timer, SoftI2C, PWM
from time import sleep_ms
import ubluetooth
import math

# driver output A
L1 = PWM(Pin(17), freq = 1000)
L2 = PWM(Pin(16), freq = 1000)

# driver output B
R1 = PWM(Pin(12), freq = 1000)
R2 = PWM(Pin(13), freq = 1000)


class BLE():
    def __init__(self, name):
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)

# Change the pin from 2 to 25 to flash the white on-board LED while connected (using it below for another reason).
        self.led = Pin(2, Pin.OUT)
        self.timer1 = Timer(0)
        self.timer2 = Timer(1)

        self.disconnected()
        self.ble.irq(self.ble_irq)
        self.register()
        self.advertiser()


    def connected(self):
        self.timer1.deinit()
        self.timer2.deinit()

    def convert(self,red, green, blue):
        print('converting')
        # Normalize RGB to 0.0 - 1.0
        red, green, blue = red / 255.0, green / 255.0, blue / 255.0

        c_max = max(red, green, blue)
        c_min = min(red, green, blue)
        delta = c_max - c_min

        #Value
        l = (c_max + c_min) / 2.0

        # Saturation
        if delta == 0:
            s = 0
        else:
            s = delta / (1.0 - abs(2.0 * l - 1.0))

    # Hue
        if delta == 0:
            h = 0
        elif c_max == red:
            h = 60.0 * (((green - blue) / delta) % 6)
        elif c_max == green:
            h = 60.0 * (((blue - red) / delta) + 2.0)
        else: # c_max == b
            h = 60.0 * (((red - green) / delta) + 4.0)

        if h < 0:
            h += 360.0

        print(f"Hue:{h},Saturation:{s},Lightness:{l}")
        coords = [h,s]
        return coords

    def drive(self, h, s):
        print(f"Hue:{h},Saturation:{s}")

        # Char's Logic: Saturation (s) controls "intensity" multiplier (0 to 1)
        intensity = s

        # Convert Hue (h) to cartesian coords, using radius of 1
        angle_rad = math.radians(h)
        x = math.sin(angle_rad)
        y = math.cos(angle_rad)

        # Proportion of x to y determines the "proportion" multiplier
        # y is our forward/backward axis, x is our left/right axis????
        left_proportion = y + x
        right_proportion = y - x

        # Normalize proportions so the maximum multiplier never exceeds 1.0
        max_prop = max(abs(left_proportion), abs(right_proportion), 1.0)
        left_proportion = left_proportion / max_prop
        right_proportion = right_proportion / max_prop

        # LEFT MOTOR
        if left_proportion >= 0:
            # Moving Forward
            L1.duty(int(intensity * left_proportion * 1023))
            L2.duty(0)
        else:
            # Moving Backward
            L1.duty(0)
            L2.duty(int(intensity * abs(left_proportion) * 1023))

        # RIGHT MOTOR
        if right_proportion >= 0:
            # Moving Forward
            R1.duty(int(intensity * right_proportion * 1023))
            R2.duty(0)
        else:
            # Moving Backward
            R1.duty(0)
            R2.duty(int(intensity * abs(right_proportion) * 1023))


    def disconnected(self):
        self.timer1.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: self.led(1))
        sleep_ms(200)
        self.timer2.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: self.led(0))

    def ble_irq(self, event, data):
        if event == 1:
            '''Central disconnected'''
            self.connected()
            self.led(1)

        elif event == 2:
            '''Central disconnected'''
            self.advertiser()
            self.disconnected()

        elif event == 3:
            '''New message received'''
            buffer = self.ble.gatts_read(self.rx)

            try:
                # 1. Try to decode it as standard text (for your 'led' command)
                message = buffer.decode('UTF-8').strip()
                print('Text received:', message)

                if message == 'led':
                    led.value(not led.value())
                    print('led', led.value())
                    self.send('led' + str(led.value()))

            except UnicodeError:
                # 2. If it crashes, it's raw binary! Handle the color data here.
                print('Raw bytes received:', buffer)

                # Check if it's the standard Adafruit Bluefruit Color Packet
                # The app sends 6 bytes: '!' (33), 'C' (67), Red, Green, Blue, Checksum
                if len(buffer) >= 6 and buffer[0] == ord('!') and buffer[1] == ord('C'):
                    red = buffer[2]
                    green = buffer[3]
                    blue = buffer[4]
                    print(f"Adafruit Color Picker - R:{red} G:{green} B:{blue}")
                    # You can now send these RGB values to your LED strip!

                # Alternative: Check if it's just a raw 3-byte RGB sequence
                elif len(buffer) == 3:
                    red, green, blue = buffer[0], buffer[1], buffer[2]
                    print(f"Raw RGB Data - R:{red} G:{green} B:{blue}")

                coords = self.convert(red, green, blue)

                self.drive(coords[0], coords[1])


    def register(self):
        NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
        RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
        TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

        BLE_NUS = ubluetooth.UUID(NUS_UUID)
        BLE_RX = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
        BLE_TX = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_NOTIFY)

        BLE_UART = (BLE_NUS, (BLE_TX, BLE_RX,))
        SERVICES = (BLE_UART, )
        ((self.tx, self.rx,), ) = self.ble.gatts_register_services(SERVICES)

    def send(self, data):
        self.ble.gatts_notify(0, self.tx, data + '\n')

    def advertiser(self):
        name = bytes(self.name, 'UTF-8')
        self.ble.gap_advertise(100, bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name)

# test
led = Pin(25, Pin.OUT)
# You should change this line of code to name your own ESP32 - otherwise, chaos! :)
ble = BLE("Hamster's ESP32")
