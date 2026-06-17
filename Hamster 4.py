##############################################################################
#
# Hamster 4: Hamster control back to buttons for easier real-time control.
# Hamster 4.0: only high speed. Turning is just one wheel turn for easier control.
# Potential Hamster 4.1: lower speed option (other buttons)
#
#############################################################################

from machine import Pin, Timer, SoftI2C
from time import sleep_ms
import ubluetooth

from machine import PWM
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

            # 1. Try to decode it as standard text (for your 'led' command)
            message = buffer.decode('UTF-8').strip()
            print('Text received:', message)

            if message == 'led':
                led.value(not led.value())
                print('led', led.value())
                self.send('led' + str(led.value()))

            if message == '!B516':
                # Up start
                L1.duty(1023)
                L2.duty(0)
                R1.duty(1023)
                R2.duty(0)

            elif message == '!B507':
                # Up end
                L1.duty(0)
                R1.duty(0)
            
            elif message == '!B813':
                # right start
                R1.duty(1023)
                R2.duty(0)

            elif message == '!B804':
                # right end
                R1.duty(0)

            elif message == '!B615':
                # Down start
                L1.duty(0)
                L2.duty(1023)
                R1.duty(0)
                R2.duty(1023)

            elif message == '!B606':
                # Down end
                L2.duty(0)
                R2.duty(0)

            elif message == '!B714':
                # left start
                L1.duty(1023)
                L2.duty(0)

            elif message == '!B705':
                # left end
                L1.duty(0)


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
