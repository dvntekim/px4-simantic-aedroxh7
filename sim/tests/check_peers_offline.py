"""Offline checks of the Simantic peers with a fake ctx (no simulator needed)."""
import importlib.util
import pathlib
import sys

PEERS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "peers"


def load(name):
    spec = importlib.util.spec_from_file_location(name, PEERS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self):
        self.logs, self.sent, self.periodic = [], [], None

    def info(self, msg):
        self.logs.append(msg)

    def send(self, can_id, data, extended=False, **kw):
        self.sent.append((can_id, bytes(data), extended))

    def schedule_periodic(self, us):
        self.periodic = us


def xfer(slave, tx):
    slave.on_select()
    rx = [slave.on_transmit(b) for b in tx]
    slave.on_deselect()
    return rx


# ICM-42688-P
icm = load("icm42688p_peer").Slave(Ctx())
assert xfer(icm, [0xF5, 0x00]) == [0x00, 0x47], "WHO_AM_I"
assert xfer(icm, [0xAD, 0x00])[1] == 0x10, "RESET_DONE after power-on"
assert xfer(icm, [0xAD, 0x00])[1] == 0x00, "INT_STATUS clears on read"
xfer(icm, [0x4F, 0x06])                       # GYRO_CONFIG0 write
assert xfer(icm, [0xCF, 0x00])[1] == 0x06, "readback"
xfer(icm, [0x76, 0x01])                       # bank 1
assert xfer(icm, [0xF6, 0x00])[1] == 0x01, "bank select readback"
assert xfer(icm, [0xCF, 0x00])[1] == 0x00, "bank 1 is separate"
xfer(icm, [0x76, 0x00])
xfer(icm, [0x11, 0x01])                       # soft reset
assert xfer(icm, [0xCF, 0x00])[1] == 0x00, "reset clears config"
assert xfer(icm, [0xF5, 0x00])[1] == 0x47, "WHO_AM_I survives reset"
assert xfer(icm, [0xF4, 0x00, 0x00])[1:] == [0x00, 0x47], "burst auto-increment"

# BMI088 accel: dummy byte
acc = load("bmi088_accel_peer").Slave(Ctx())
assert xfer(acc, [0x80, 0x00, 0x00]) == [0x00, 0xFF, 0x1E], "accel chip ID after dummy"
xfer(acc, [0x41, 0x03])
assert xfer(acc, [0xC1, 0x00, 0x00])[2] == 0x03, "accel readback"
xfer(acc, [0x7E, 0xB6])
assert xfer(acc, [0xC1, 0x00, 0x00])[2] == 0x00, "accel soft reset"

# BMI088 gyro: no dummy
gyr = load("bmi088_gyro_peer").Slave(Ctx())
assert xfer(gyr, [0x80, 0x00]) == [0x00, 0x0F], "gyro chip ID"
xfer(gyr, [0x0F, 0x01])
assert xfer(gyr, [0x8F, 0x00])[1] == 0x01
xfer(gyr, [0x14, 0xB6])
assert xfer(gyr, [0x8F, 0x00])[1] == 0x00, "gyro soft reset"

# DroneCAN NodeStatus
dc = load("dronecan_nodestatus_peer")
ctx = Ctx()
node = dc.Node(ctx)
assert ctx.periodic == 1_000_000
node.on_timer(); node.on_timer()
can_id, data, ext = ctx.sent[1]
assert ext and len(data) == 8
assert can_id == (16 << 24) | (341 << 8) | 42 == 0x1001552A
assert data[:4] == (1).to_bytes(4, "little") and data[7] == 0xC1
node.on_frame({"id": 0x10015501, "data": b"", "extended": True})
assert "node 1" in ctx.logs[0]

# DPS310 (I2C): pointer write, then read
dps = load("dps310_peer").Slave(Ctx())
dps.on_write(bytes([0x0D]))
assert dps.on_read(1) == bytes([0x10]), "DPS310 product ID"
dps.on_write(bytes([0x08]))
assert dps.on_read(1)[0] & 0xC0 == 0xC0, "ready flags set"
dps.on_write(bytes([0x06, 0x26, 0xA0]))       # PRS_CFG, TMP_CFG burst write
dps.on_write(bytes([0x06]))
assert dps.on_read(2) == bytes([0x26, 0xA0]), "burst readback"
dps.on_write(bytes([0x0C, 0x09]))             # soft reset
dps.on_write(bytes([0x06]))
assert dps.on_read(1) == bytes([0x00]), "reset clears config"
dps.on_write(bytes([0x0D]))
assert dps.on_read(1) == bytes([0x10]), "ID survives reset"
print("all peer checks passed")
