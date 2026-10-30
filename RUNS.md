# Simantic runs

One row per commit made by `scripts/sim-commit.sh`. Raw output for each run is in `results/` at that commit.

| When | Commit | PX4 patches | Simantic |
| --- | --- | --- | --- |
| 2026-10-30 13:04 | Run stock PX4 AEDROXH7 firmware on Simantic | none (stock PX4) | **FAIL** |
| 2026-10-30 13:05 | aedroxh7: mount /etc ROMFS so startup scripts run | 0001-aedroxh7-mount-etc-romfs.patch | **PASS** |
