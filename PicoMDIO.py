from machine import Pin
from time import sleep_us

MDIO_PIN = 3        # Bidirectional MDIO
MDC_PIN  = 2        # Clock


class MDIO:
    def __init__(self):
        self._mdio = Pin(MDIO_PIN, Pin.OUT, value=1)
        self._mdc = Pin(MDC_PIN, Pin.OUT, value=0)

    def _delay(self):
        sleep_us(1)

    def _clock(self, bit: int):
        self._mdio.value(bit)
        self._delay(); self._mdc.value(1)
        self._delay(); self._mdc.value(0)

    def _clock_in(self) -> int:
        self._mdc.value(1)
        self._delay()
        bit = self._mdio.value()
        self._mdc.value(0)
        self._delay()
        return bit

    def _shift_out(self, value: int, width: int):
        for i in range(width - 1, -1, -1):
            self._clock((value >> i) & 1)

    def _preamble(self):
        self._mdio.init(Pin.OUT, value=1)
        for _ in range(33):
            self._clock(1)

    # Clause-22
    def read22(self, phy: int, reg: int) -> int:
        self._preamble()
        self._clock(0); self._clock(1)
        self._clock(1); self._clock(0)
        self._shift_out(phy, 5)
        self._shift_out(reg, 5)
        self._mdio.init(Pin.IN)
        self._clock(0)

        data = 0
        for _ in range(16):
            bit = self._clock_in()
            data = (data << 1) | bit
        self._clock(1)
        return data

    def write22(self, phy: int, reg: int, val: int):
        self._preamble()
        self._clock(0); self._clock(1)
        self._clock(0); self._clock(1)
        self._shift_out(phy, 5)
        self._shift_out(reg, 5)
        self._clock(1); self._clock(0)
        self._shift_out(val, 16)
        self._mdio.init(Pin.IN)

    # Clause-45
    def _address_frame(self, phy: int, dev: int, reg: int):
        self._preamble()
        self._clock(0); self._clock(0)
        self._clock(0); self._clock(0)
        self._shift_out(phy, 5)
        self._shift_out(dev, 5)
        self._clock(1); self._clock(0)
        self._shift_out(reg, 16)
        self._mdio.init(Pin.IN)

    def write45(self, phy: int, dev: int, reg: int, val: int):
        self._address_frame(phy, dev, reg)
        self._preamble()
        self._clock(0); self._clock(0)
        self._clock(0); self._clock(1)
        self._shift_out(phy, 5)
        self._shift_out(dev, 5)
        self._clock(1); self._clock(0)
        self._shift_out(val, 16)
        self._mdio.init(Pin.IN)

    def read45(self, phy: int, dev: int, reg: int) -> int:
        self._address_frame(phy, dev, reg)
        self._preamble()
        self._clock(0); self._clock(0)
        self._clock(1); self._clock(1)
        self._shift_out(phy, 5)
        self._shift_out(dev, 5)
        self._mdio.init(Pin.IN)
        self._clock(0)

        data = 0
        for _ in range(16):
            bit = self._clock_in()
            data = (data << 1) | bit
        self._clock(1)
        return data
