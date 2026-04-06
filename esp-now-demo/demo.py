#!/usr/bin/env python3
"""ESP-NOW HIL test demo."""

import re
import time
from pathlib import Path

from siliconrig import Board
from siliconrig.exceptions import SerialTimeout

DIR = Path(__file__).resolve().parent
SENDER_FW = str(DIR / "sender" / "build" / "sender-merged.bin")
RECEIVER_FW = str(DIR / "receiver" / "build" / "receiver-merged.bin")

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"

SAMPLES = 10


def main():
    print()

    with Board("esp32-s3", firmware=SENDER_FW) as sender:
        print(f"{DIM}Flashing sender...{RESET}", end="", flush=True)
        sender.expect("TX: seq=", timeout=60)
        sender.flush()
        sender.read_until("TX: seq=", timeout=10)  # wait for stable TX
        sender.flush()
        print(f" {DIM}done{RESET}")

        with Board("esp32-s3", firmware=RECEIVER_FW) as receiver:
            print(f"{DIM}Flashing receiver...{RESET}", end="", flush=True)
            receiver.expect("RX: seq=", timeout=60)
            receiver.flush()
            print(f" {DIM}done{RESET}")
            print()

            rssi_values = []
            dt_values = []
            rx_count = 0
            last_rx_seq = 0
            last_rx_time = None
            missed = 0

            while rx_count < SAMPLES:
                try:
                    rx_out = receiver.read(timeout=5)
                except SerialTimeout:
                    continue

                for line in rx_out.strip().splitlines():
                    line = line.strip()
                    if not line.startswith("RX:"):
                        continue
                    m = re.match(r"RX: seq=(\d+) rssi=(-?\d+)", line)
                    if not m:
                        continue

                    now = time.monotonic()
                    seq = int(m.group(1))
                    rssi = int(m.group(2))

                    if last_rx_seq > 0 and seq > last_rx_seq + 1:
                        missed += seq - last_rx_seq - 1
                    last_rx_seq = seq
                    rx_count += 1
                    rssi_values.append(rssi)

                    dt_ms = (now - last_rx_time) * 1000 if last_rx_time else None
                    if dt_ms is not None:
                        dt_values.append(dt_ms)
                    last_rx_time = now

                    dt_str = f"  dt={dt_ms:.0f}ms" if dt_ms is not None else ""
                    print(f"  {YELLOW}RX{RESET}  seq={seq}  rssi={rssi} dBm{dt_str}", flush=True)

                    if rx_count >= SAMPLES:
                        break

            print()

            total = rx_count + missed
            loss = (missed / total * 100) if total > 0 else 0

            print(f"  packets  {rx_count}/{total} received, {loss:.1f}% loss")
            print(f"  rssi     min={min(rssi_values)} max={max(rssi_values)} avg={sum(rssi_values)/len(rssi_values):.0f} dBm")
            if dt_values:
                jitter = max(dt_values) - min(dt_values)
                print(f"  timing   avg={sum(dt_values)/len(dt_values):.0f}ms jitter={jitter:.0f}ms")
            print()

            all_ok = loss < 50 and -100 <= min(rssi_values) <= 0 and rx_count == SAMPLES
            print(f"  {GREEN}PASS{RESET}" if all_ok else f"  {RED}FAIL{RESET}")
            print()


if __name__ == "__main__":
    main()
