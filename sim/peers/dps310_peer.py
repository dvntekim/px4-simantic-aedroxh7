"""Infineon DPS310 barometer I2C peer for Simantic.

DPS310 datasheet register map:
  PRODUCT_ID 0x0D -> 0x10
  MEAS_CFG   0x08: bit 7 COEF_RDY, bit 6 SENSOR_RDY (set from power-on here)
  RESET      0x0C: low nibble 0x9 = soft reset
I2C framing: a write's first byte sets the register pointer; further bytes
are written from there. Reads return from the pointer, auto-incrementing.

Scope: identity, ready flags and register read-back. Pressure and
temperature registers read 0 and the coefficients are all zero, so the
driver probes and starts but reports meaningless altitude.
"""

PRODUCT_ID = 0x0D
PRODUCT_ID_VALUE = 0x10
MEAS_CFG = 0x08
READY_FLAGS = 0xC0  # COEF_RDY | SENSOR_RDY
RESET = 0x0C
SOFT_RESET = 0x09


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.ptr = 0
        self._power_on()

    def _power_on(self):
        self.regs = bytearray(64)
        self.regs[PRODUCT_ID] = PRODUCT_ID_VALUE
        self.regs[MEAS_CFG] = READY_FLAGS

    def on_write(self, data):
        if not data:
            return
        self.ptr = data[0] & 0x3F
        for b in data[1:]:
            if self.ptr == RESET and (b & 0x0F) == SOFT_RESET:
                self.ctx.info("soft reset")
                self._power_on()
            elif self.ptr == MEAS_CFG:
                self.regs[MEAS_CFG] = READY_FLAGS | (b & 0x07)  # keep ready bits
            elif self.ptr != PRODUCT_ID:
                self.regs[self.ptr] = b
            self.ptr = (self.ptr + 1) & 0x3F

    def on_read(self, count):
        out = bytearray()
        for _ in range(count):
            out.append(self.regs[self.ptr])
            self.ptr = (self.ptr + 1) & 0x3F
        return bytes(out)
