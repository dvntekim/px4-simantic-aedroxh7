"""BMI088 gyroscope SPI peer for Simantic.

Bosch BMI088 datasheet:
  GYRO_CHIP_ID   0x00 -> 0x0F
  GYRO_SOFTRESET 0x14, write 0xB6
Unlike the accelerometer, the gyro has no dummy byte on SPI reads.

Scope: identity, soft reset and register read-back only. No sample data.
"""

GYRO_CHIP_ID = 0x00
GYRO_CHIP_ID_VALUE = 0x0F
GYRO_SOFTRESET = 0x14
SOFTRESET_CMD = 0xB6


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self._power_on()
        self._new_frame()

    def _power_on(self):
        self.regs = bytearray(128)
        self.regs[GYRO_CHIP_ID] = GYRO_CHIP_ID_VALUE

    def _new_frame(self):
        self.addr = None
        self.is_read = False

    def on_select(self):
        self._new_frame()

    def on_deselect(self):
        self._new_frame()

    def on_transmit(self, b):
        if self.addr is None:
            self.is_read = bool(b & 0x80)
            self.addr = b & 0x7F
            return 0x00
        if self.is_read:
            value = self.regs[self.addr]
        else:
            value = 0x00
            if self.addr == GYRO_SOFTRESET and b == SOFTRESET_CMD:
                self.ctx.info("gyro soft reset")
                self._power_on()
            elif self.addr != GYRO_CHIP_ID:
                self.regs[self.addr] = b
        self.addr = (self.addr + 1) & 0x7F
        return value
