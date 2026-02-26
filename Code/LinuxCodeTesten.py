"""
Standalone LiDAR viewer voor Ubuntu/Linux.

Dit script bevat ALLES wat nodig is om de LiDAR uit te lezen en te visualiseren.
Geen imports uit de rest van de codebase nodig.

Vereisten (pip install):
    pip install rplidar-roboticia numpy matplotlib pyserial

Gebruik:
    python3 view_lidar_standalone_linux.py                     # auto-detectie
    python3 view_lidar_standalone_linux.py --port /dev/ttyUSB0
    python3 view_lidar_standalone_linux.py --min-distance 500
"""

import argparse
import logging
import sys
import time
from math import floor
from threading import Thread

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Probeer rplidar te importeren; geef duidelijke foutmelding als het mist
# ---------------------------------------------------------------------------
try:
    from rplidar import RPLidar
except ImportError:
    print(
        "\n[FOUT] rplidar is niet geïnstalleerd.\n"
        "Installeer het met:  pip install rplidar-roboticia\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config – Linux defaults
# ---------------------------------------------------------------------------
DEFAULT_PORT = "/dev/ttyUSB0"   # Ubuntu/Linux standaard
MIN_DISTANCE_MM = 50              # Lowered to detect objects closer
PLOT_RANGE = 8000                 # Increased to 8m range
MAX_DISTANCE_MM = 8000            # Maximum distance filter for scanning
BAUD_RATE = 115200

# ---------------------------------------------------------------------------
# Linux/Ubuntu serial auto-detectie
# ---------------------------------------------------------------------------
def find_lidar_port() -> str | None:
    """Probeer automatisch de seriële poort van de LiDAR te vinden op Linux/Ubuntu."""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc = (port.description or "").lower()
            dev = port.device.lower()

            # Linux device namen + bekende USB-serial chips
            if (
                "ttyusb" in dev
                or "ttyacm" in dev
                or "cp210" in desc
                or "ch340" in desc
                or "ftdi" in desc
                or "silicon labs" in desc
                or "lidar" in desc
            ):
                print(f"[AUTO-DETECT] LiDAR gevonden op {port.device} ({port.description})")
                return port.device

        if ports:
            print("[AUTO-DETECT] Geen bekende LiDAR-chip gevonden. Beschikbare poorten:")
            for p in ports:
                print(f"  - {p.device}: {p.description}")
            return None

    except ImportError:
        pass

    return None

# ---------------------------------------------------------------------------
# Lidar klasse – alles-in-één, geen externe dependencies uit het project
# ---------------------------------------------------------------------------
class StandaloneLidar:
    """Leest data van een RPLiDAR sensor in een achtergrond-thread."""

    def __init__(self, port: str, min_distance: float = MIN_DISTANCE_MM) -> None:
        self.min_distance = min_distance
        self.scan_data = np.full(360, np.inf)
        self._running = False

        print(f"[LIDAR] Verbinden met poort {port} …")
        try:
            self.lidar = RPLidar(port, timeout=3)
        except Exception as e:
            print(f"[FOUT] Kan niet verbinden met LiDAR op {port}: {e}")
            print("\nTips voor Linux:")
            print("  1. Controleer of de LiDAR zichtbaar is met:")
            print("       ls /dev/ttyUSB* /dev/ttyACM*")
            print("  2. Voeg jezelf toe aan de 'dialout' groep:")
            print("       sudo usermod -a -G dialout $USER")
            print("  3. Log daarna opnieuw in.")
            sys.exit(1)

        self.lidar.stop_motor()
        self._thread = Thread(target=self._listen, daemon=True)

    def start(self) -> None:
        self._running = True
        if not self._thread.is_alive():
            self._thread.start()
        print("[LIDAR] Gestart – wacht op data …")

    def stop(self) -> None:
        self._running = False
        try:
            self.lidar.stop()
            self.lidar.stop_motor()
            self.lidar.disconnect()
        except Exception:
            pass
        print("[LIDAR] Gestopt.")

    # ----- interne methodes -----

    def _capture(self) -> None:
        self.lidar.start_motor()
        for scan in self._iter_scans():
            if not self._running:
                break
            for _, angle, distance in scan:
                angle_idx = min(359, floor(angle))
                if distance < self.min_distance:
                    self.scan_data[angle_idx] = np.inf
                else:
                    self.scan_data[angle_idx] = distance

    def _iter_scans(self):
        scan_list = []
        for new_scan, quality, angle, distance in self.lidar.iter_measures():
            if not self._running:
                break
            if new_scan:
                if len(scan_list) > 5:
                    yield scan_list
                scan_list = []
            scan_list.append((quality, angle, distance))

    def _listen(self) -> None:
        while self._running:
            try:
                self._capture()
            except Exception as e:
                logging.error("Fout bij het uitlezen van de LiDAR: %s", e)
                try:
                    self.lidar.stop()
                    self.lidar.stop_motor()
                except Exception:
                    pass
                if self._running:
                    time.sleep(1)

# ---------------------------------------------------------------------------
# Visualisatie
# ---------------------------------------------------------------------------
def view_lidar(port: str, min_distance: float) -> None:
    lidar = StandaloneLidar(port=port, min_distance=min_distance)
    lidar.start()

    time.sleep(1)

    plt.ion()
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.canvas.manager.set_window_title("LiDAR Viewer")

    angles = np.linspace(0, 2 * np.pi, 360)

    print("[PLOT] Live weergave gestart. Sluit het venster of druk Ctrl+C om te stoppen.")

    try:
        while True:
            data = lidar.scan_data.copy()
            plot_data = np.where(np.isinf(data), 0, data)

            x = plot_data * np.cos(angles)
            y = plot_data * np.sin(angles)

            ax.clear()
            ax.scatter(x, y, s=2, c="lime")
            ax.set_xlim(-PLOT_RANGE, PLOT_RANGE)
            ax.set_ylim(-PLOT_RANGE, PLOT_RANGE)
            ax.set_facecolor("black")
            ax.set_aspect("equal")
            ax.grid(True, alpha=0.3, color="gray")
            ax.set_title("LiDAR Scan (afstand in mm)", color="white")
            fig.patch.set_facecolor("black")
            ax.tick_params(colors="white")

            ax.plot(0, 0, "r+", markersize=15, markeredgewidth=2)

            plt.pause(0.05)

            if not plt.fignum_exists(fig.number):
                break

    except KeyboardInterrupt:
        print("\n[STOP] Ctrl+C ontvangen.")
    finally:
        lidar.stop()
        plt.close("all")

# ---------------------------------------------------------------------------
# Argument parsing & main
# ---------------------------------------------------------------------------
def main() -> None:
    global PLOT_RANGE

    parser = argparse.ArgumentParser(
        description="Standalone LiDAR viewer voor Ubuntu/Linux (RPLiDAR)"
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help=f"Seriële poort van de LiDAR (bijv. /dev/ttyUSB0). Standaard: auto-detect of {DEFAULT_PORT}",
    )
    parser.add_argument(
        "--min-distance",
        type=float,
        default=MIN_DISTANCE_MM,
        help=f"Minimale afstand in mm. Standaard: {MIN_DISTANCE_MM}",
    )
    parser.add_argument(
        "--range",
        type=float,
        default=PLOT_RANGE,
        dest="plot_range",
        help=f"Plot bereik in mm. Standaard: {PLOT_RANGE}",
    )
    args = parser.parse_args()

    PLOT_RANGE = args.plot_range

    port = args.port
    if port is None:
        port = find_lidar_port()
    if port is None:
        print(f"[INFO] Geen LiDAR-poort gedetecteerd, gebruik standaard: {DEFAULT_PORT}")
        port = DEFAULT_PORT

    print("=" * 50)
    print("  LiDAR Standalone Viewer (Linux)")
    print(f"  Poort:           {port}")
    print(f"  Min afstand:     {args.min_distance} mm")
    print(f"  Plot bereik:     ±{PLOT_RANGE} mm")
    print("=" * 50)

    view_lidar(port=port, min_distance=args.min_distance)

if __name__ == "__main__":
    main()