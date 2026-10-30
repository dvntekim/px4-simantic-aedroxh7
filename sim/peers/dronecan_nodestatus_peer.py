"""Minimal DroneCAN node for Simantic: proves CAN1 wiring and bit timing.

Sends uavcan.protocol.NodeStatus (data type ID 341) once per second from a
static node ID, as a single-frame DroneCAN v0 transfer, and logs the first
frame it hears from the flight controller.

DroneCAN v0 frame layout (29-bit extended ID, message transfer):
  priority (5 bits) << 24 | data type ID (16 bits) << 8 | 0 << 7 | source node ID (7 bits)
NodeStatus payload (7 bytes): uptime_sec uint32 LE,
  then one byte health(2) | mode(3) | sub_mode(3), then vendor status uint16 LE.
Tail byte: start=1, end=1, toggle=0, transfer ID (5 bits) -> 0xC0 | tid.

Pass condition on the FC: `uavcan status` lists node 42. This is NOT a flow
sensor: it carries no flow or range data. A full optical-flow peer needs
dynamic node allocation, GetNodeInfo and multi-frame transfers; start from
Simantic's sim-fixtures dronecan_peer.py (tests/warg/zp4-h753) for that.
"""

NODE_ID = 42
PRIORITY = 16
NODE_STATUS_DTID = 341
PERIOD_US = 1_000_000


def node_status_can_id(node_id=NODE_ID, priority=PRIORITY):
    return (priority << 24) | (NODE_STATUS_DTID << 8) | (node_id & 0x7F)


def node_status_frame(uptime_s, tid, health=0, mode=0, sub_mode=0, vendor=0):
    payload = uptime_s.to_bytes(4, "little")
    payload += bytes([((health & 0x3) << 6) | ((mode & 0x7) << 3) | (sub_mode & 0x7)])
    payload += vendor.to_bytes(2, "little")
    tail = 0xC0 | (tid & 0x1F)
    return payload + bytes([tail])


class Node:
    def __init__(self, ctx):
        self.ctx = ctx
        self.uptime_s = 0
        self.tid = 0
        self.heard_fc = False
        self.ctx.schedule_periodic(PERIOD_US)

    def on_timer(self):
        data = node_status_frame(self.uptime_s, self.tid)
        self.ctx.send(node_status_can_id(), data, extended=True)
        self.uptime_s += 1
        self.tid = (self.tid + 1) & 0x1F

    def on_frame(self, frame):
        if not self.heard_fc and frame.get("extended"):
            src = frame["id"] & 0x7F
            self.ctx.info("first DroneCAN frame from node %d, id=0x%08X" % (src, frame["id"]))
            self.heard_fc = True
