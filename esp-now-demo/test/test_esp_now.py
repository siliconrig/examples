import re
from pathlib import Path
import pytest
from siliconrig import Board

_DIR = Path(__file__).resolve().parent.parent
SENDER_FW = str(_DIR / "sender" / "build" / "sender-merged.bin")
RECEIVER_FW = str(_DIR / "receiver" / "build" / "receiver-merged.bin")


@pytest.fixture(scope="module")
def sender():
    with Board("esp32-s3", firmware=SENDER_FW) as b:
        b.expect("TX: seq=", timeout=60)
        b.flush()
        yield b


@pytest.fixture(scope="module")
def receiver():
    with Board("esp32-s3", firmware=RECEIVER_FW) as b:
        b.expect("RX: seq=", timeout=60)
        b.flush()
        yield b


def test_sender_transmits(sender):
    """Sender should produce TX lines."""
    output = sender.read_until("TX: seq=", timeout=10)
    assert "TX: seq=" in output


def test_receiver_gets_packets(sender, receiver):
    """Receiver should receive packets over ESP-NOW."""
    output = receiver.read_until("RX: seq=", timeout=15)
    assert "RX: seq=" in output


def test_rssi_in_range(sender, receiver):
    """RSSI should be between -100 and 0 dBm."""
    output = receiver.read(timeout=5)
    match = re.search(r"rssi=(-?\d+)", output)
    assert match, f"no RSSI value found: {output!r}"
    rssi = int(match.group(1))
    assert -100 <= rssi <= 0, f"RSSI {rssi} out of range"


def test_no_excessive_packet_loss(sender, receiver):
    """Loss rate should be below 50%."""
    output = receiver.read_until("SUMMARY:", timeout=30)
    output += receiver.read_until("SUMMARY:", timeout=30)
    match = re.search(r"loss=([\d.]+)%", output)
    assert match, f"no loss value found: {output!r}"
    loss = float(match.group(1))
    assert loss < 50.0, f"packet loss {loss}% exceeds threshold"
