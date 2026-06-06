"""Exercise bench PC host profile measurements and artifact capture."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    col.config.load_config("examples/configs/bench.sim.toml")
    col.host.config.verify_bench_config_loaded(key="cfg")
    col.host.system.measure_memory_available_mb(key="mem_mb")
    col.host.system.verify_memory_available_mb(key="mem_mb", minimum=128.0)
    col.host.system.measure_disk_free_gb(key="disk_gb")
    col.host.system.verify_disk_free_gb(key="disk_gb", minimum=0.1)
    col.host.system.measure_python_version(key="py")
    col.host.system.measure_platform(key="plat")
    col.host.bench.measure_visa_backend(key="visa")
    col.host.bench.verify_visa_available(key="visa", allow_sim=True, optional=True)
    col.host.bench.measure_serial_ports(key="ports")
    col.host.config.capture_host_profile(path="host_profile.json")


if __name__ == "__main__":
    main()
    col.endex()
