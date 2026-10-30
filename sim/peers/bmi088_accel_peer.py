"""BMI088 accelerometer SPI peer for Simantic.

Bosch BMI088 datasheet:
  ACC_CHIP_ID   0x00 -> 0x1E
  ACC_SOFTRESET 0x7E, write 0xB6
SPI read quirk: after the address byte the accelerometer sends ONE dummy
byte before the first data byte. Drivers that forget it read garbage, so
the peer models it; this is a real check on the PX4 bmi088 driver path.

Scope: identity, soft reset and register read-back only. No sample data.
"""

ACC_CHIP_ID = 0x00
ACC_CHIP_ID_VALUE = 0x1E
ACC_SOFTRESET = 0x7E
SOFTRESET_CMD = 0xB6


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self._power_on()
        self._new_frame()

    def _power_on(self):
        self.regs = bytearray(128)
        self.regs[ACC_CHIP_ID] = ACC_CHIP_ID_VALUE

    def _new_frame(self):
        self.addr = None
        self.is_read = False
        self.dummy_pending = False

    def on_select(self):
        self._new_frame()

    def on_deselect(self):
        self._new_frame()

    def on_transmit(self, b):
        if self.addr is None:
            self.is_read = bool(b & 0x80)
            self.addr = b & 0x7F
            self.dummy_pending = self.is_read
            return 0x00
        if self.is_read:
            if self.dummy_pending:
                self.dummy_pending = False
                return 0xFF  # dummy byte, value undefined on silicon
            value = self.regs[self.addr]
        else:
            value = 0x00
            if self.addr == ACC_SOFTRESET and b == SOFTRESET_CMD:
                self.ctx.info("accel soft reset")
                self._power_on()
            elif self.addr != ACC_CHIP_ID:
                self.regs[self.addr] = b
        self.addr = (self.addr + 1) & 0x7F
        return value
