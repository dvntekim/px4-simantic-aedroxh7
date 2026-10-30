# PX4 AEDROXH7 on Simantic

PX4 firmware (`aedrox_aedroxh7_default`, STM32H743VI) run on [Simantic](https://simantic.com)'s
STM32H743 model with simulated sensors on the board's real buses:

| Part | Bus | Peer |
| --- | --- | --- |
| ICM-42688-P IMU | SPI2, CS PB12 | `sim/peers/icm42688p_peer.py` |
| DPS310 baro | I2C2, 0x76 | `sim/peers/dps310_peer.py` |

Every commit is made by `scripts/sim-commit.sh`, which builds PX4 at the pinned commit
(`px4/PX4_COMMIT`) plus the patches in `px4/patches/`, runs it on Simantic, and commits the
change together with Simantic's unedited output:

- `results/sim-output.txt`: what `sim run` printed, and its exit code in the commit message
- `results/console.txt`: the firmware's UART8 console
- `results/sensor-bus.txt`: the first SPI/I2C frames to the simulated IMU and baro

`RUNS.md` lists every run. Compare two commits' `results/console.txt` to see what a change did.

## Reproduce

Needs PX4 cloned at `../PX4-Autopilot` (checked out at the pinned commit, `.venv` set up),
the ARM toolchain, and `sim` signed in.

```
scripts/sim-commit.sh "what you changed"
```

The script resets `boards/aedrox/aedroxh7` in the PX4 tree before applying the patches, and
does a clean NuttX build whenever the patch set changes (NuttX builds in-tree, so a stale
`.config` survives deleting `build/`).

## Not tested here

Power, analog noise, layout, D-cache/DMA coherency, and sensor data: the peers answer
identity and register read-back only, so PX4 starts the drivers but gets no IMU samples.
