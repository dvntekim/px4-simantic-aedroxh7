"""ICM-42688-P SPI peer for Simantic: a banked register file.

Datasheet DS-000347 (TDK InvenSense):
  WHO_AM_I      bank 0, 0x75 -> 0x47
  REG_BANK_SEL  0x76, visible from every bank
  DEVICE_CONFIG bank 0, 0x11, bit 0 = SOFT_RESET_CONFIG
  INT_STATUS    bank 0, 0x2D, bit 4 = RESET_DONE_INT (clears on read)
SPI framing: first byte is the address, bit 7 set = read; the address
auto-increments for burst access.

Scope: enough for PX4's icm42688p driver to probe, reset and configure the
part (register writes read back what was written). The FIFO is not modelled:
FIFO_COUNTH/L read 0, so the driver finds the IMU but gets no samples.
Next step: fill FIFO packets at the ODR the driver writes to GYRO_CONFIG0.
"""

WHO_AM_I = 0x75
WHO_AM_I_VALUE = 0x47
REG_BANK_SEL = 0x76
DEVICE_CONFIG = 0x11
SOFT_RESET = 0x01
INT_STATUS = 0x2D
RESET_DONE = 0x10
NUM_BANKS = 5


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self._power_on()
        self._new_frame()

    def _power_on(self):
        self.banks = [bytearray(128) for _ in range(NUM_BANKS)]
        self.bank = 0
        self.banks[0][WHO_AM_I] = WHO_AM_I_VALUE
        self.banks[0][INT_STATUS] = RESET_DONE

    def _new_frame(self):
        self.addr = None
        self.is_read = False

    def on_select(self):
        self._new_frame()

    def on_deselect(self):
        self._new_frame()

    def on_transmit(self, b):
        if self.addr is None:  # command byte
            self.is_read = bool(b & 0x80)
            self.addr = b & 0x7F
            return 0x00
        out = self._read() if self.is_read else self._write(b)
        self.addr = (self.addr + 1) & 0x7F
        return out

    def _read(self):
        if self.addr == REG_BANK_SEL:
            return self.bank
        regs = self.banks[self.bank]
        value = regs[self.addr]
        if self.bank == 0 and self.addr == INT_STATUS:
            regs[INT_STATUS] = 0  # read-to-clear
        return value

    def _write(self, b):
        if self.addr == REG_BANK_SEL:
            self.bank = b & 0x07 if (b & 0x07) < NUM_BANKS else 0
            return 0x00
        if self.bank == 0 and self.addr == DEVICE_CONFIG and b & SOFT_RESET:
            self.ctx.info("soft reset")
            self._power_on()
            return 0x00
        if self.bank == 0 and self.addr == WHO_AM_I:
            return 0x00  # read-only
        self.banks[self.bank][self.addr] = b
        return 0x00
