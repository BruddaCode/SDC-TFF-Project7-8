"""
Standalone LiDAR viewer voor Ubuntu/Linux met objectdetectie, tracking en logging.

Vereisten:
    pip install rplidar-roboticia numpy matplotlib pyserial
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
# Probeer rplidar te importeren
# ---------------------------------------------------------------------------
try:
    from rplidar import RPLidar
except ImportError:
    print("\n[FOUT] rplidar ontbreekt. Installeer met: pip install rplidar-roboticia\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_PORT = "/dev/ttyUSB0"
MIN_DISTANCE_MM = 500
PLOT_RANGE = 10_000
BAUD_RATE = 115200

# ---------------------------------------------------------------------------
# Auto-detectie van LiDAR poort
# ---------------------------------------------------------------------------
def find_lidar_port() -> str | None:
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc = (port.description or "").lower()
            dev = port.device.lower()

            if (
                "ttyusb" in dev
                or "ttyacm" in dev
                or "cp210" in desc
                or "ch340" in desc
                or "ftdi" in desc
                or "silicon labs" in desc
            ):
                print(f"[AUTO-DETECT] LiDAR gevonden op {port.device}")
                return port.device

        return None

    except ImportError:
        return None

# ---------------------------------------------------------------------------
# LiDAR uitleesklasse
# ---------------------------------------------------------------------------
class StandaloneLidar:
    def __init__(self, port: str, min_distance: float = MIN_DISTANCE_MM) -> None:
        self.min_distance = min_distance
        self.scan_data = np.full(360, np.inf)
        self._running = False

        print(f"[LIDAR] Verbinden met {port} …")
        try:
            self.lidar = RPLidar(port, timeout=3)
        except Exception as e:
            print(f"[FOUT] Kan niet verbinden: {e}")
            print("Controleer rechten: sudo usermod -a -G dialout $USER")
            sys.exit(1)

        self.lidar.stop_motor()
        self._thread = Thread(target=self._listen, daemon=True)

    def start(self) -> None:
        self._running = True
        if not self._thread.is_alive():
            self._thread.start()
        print("[LIDAR] Gestart.")

    def stop(self) -> None:
        self._running = False
        try:
            self.lidar.stop()
            self.lidar.stop_motor()
            self.lidar.disconnect()
        except Exception:
            pass
        print("[LIDAR] Gestopt.")

    def _capture(self) -> None:
        self.lidar.start_motor()
        for scan in self._iter_scans():
            if not self._running:
                break

            for _, angle, distance in scan:
                idx = min(359, floor(angle))
                self.scan_data[idx] = distance if distance >= self.min_distance else np.inf

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
                logging.error("Leesfout: %s", e)
                time.sleep(1)

# ---------------------------------------------------------------------------
# Objectdetectie
# ---------------------------------------------------------------------------
def detect_objects(distances, angles, max_distance=3000, min_cluster_size=3):
    objects = []
    cluster = []

    for i in range(len(distances)):
        d = distances[i]

        if not np.isinf(d) and d < max_distance:
            cluster.append(i)
        else:
            if len(cluster) >= min_cluster_size:
                objects.append(cluster)
            cluster = []

    if len(cluster) >= min_cluster_size:
        objects.append(cluster)

    centroids = []
    for cluster in objects:
        xs = [distances[i] * np.cos(angles[i]) for i in cluster]
        ys = [distances[i] * np.sin(angles[i]) for i in cluster]
        centroids.append((np.mean(xs), np.mean(ys)))

    return centroids

# ---------------------------------------------------------------------------
# Objecttracking
# ---------------------------------------------------------------------------
class ObjectTracker:
    def __init__(self, max_distance=400):
        self.objects = {}          # id → (x, y)
        self.next_id = 1
        self.max_distance = max_distance

    def update(self, detections):
        updated = {}

        for (x, y) in detections:
            best_id = None
            best_dist = 999999

            for oid, (ox, oy) in self.objects.items():
                dist = np.hypot(x - ox, y - oy)
                if dist < best_dist and dist < self.max_distance:
                    best_dist = dist
                    best_id = oid

            if best_id is None:
                best_id = self.next_id
                self.next_id += 1

            updated[best_id] = (x, y)

        self.objects = updated
        return updated

# ---------------------------------------------------------------------------
# Visualisatie + tracking + logging
# ---------------------------------------------------------------------------
def view_lidar(port: str, min_distance: float) -> None:
    lidar = StandaloneLidar(port=port, min_distance=min_distance)
    lidar.start()

    # Open logbestand
    logfile = open("lidar_object_log.txt", "a")
    logfile.write("\n--- Nieuwe sessie gestart ---\n")

    time.sleep(1)

    plt.ion()
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.canvas.manager.set_window_title("LiDAR Viewer")

    angles = np.linspace(0, 2 * np.pi, 360) - np.pi/2

    tracker = ObjectTracker()

    print("[PLOT] Viewer gestart.")

    try:
        while True:
            data = lidar.scan_data.copy()
            plot_data = np.where(np.isinf(data), 0, data)

            x = plot_data * np.cos(angles)
            y = plot_data * np.sin(angles)

            # Detecteer objecten
            detections = detect_objects(plot_data, angles)

            # Update tracking
            tracked = tracker.update(detections)

            ax.clear()
            ax.scatter(x, y, s=2, c="lime")

            # Teken objecten + log ze
            for oid, (ox, oy) in tracked.items():
                print(f"[OBJECT {oid}] x={ox:.1f} mm, y={oy:.1f} mm")

                # Log naar txt-bestand
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                logfile.write(f"{timestamp}, ID={oid}, x={ox:.1f}, y={oy:.1f}\n")

                ax.plot(ox, oy, "ro", markersize=8)
                ax.text(ox, oy, f"ID {oid}", color="white")

            ax.set_xlim(-PLOT_RANGE, PLOT_RANGE)
            ax.set_ylim(-1000, PLOT_RANGE)
            ax.set_facecolor("black")
            ax.set_aspect("equal")
            ax.grid(True, alpha=0.3, color="gray")
            ax.set_title("LiDAR Scan + Objecttracking", color="white")
            fig.patch.set_facecolor("black")
            ax.tick_params(colors="white")

            ax.plot(0, 0, "r+", markersize=15)

            plt.pause(0.05)

            if not plt.fignum_exists(fig.number):
                break

    except KeyboardInterrupt:
        print("\n[STOP] Ctrl+C ontvangen.")
    finally:
        lidar.stop()
        plt.close("all")
        logfile.close()
        print("[LOG] Data opgeslagen in lidar_object_log.txt")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global PLOT_RANGE

    parser = argparse.ArgumentParser(description="LiDAR viewer met objecttracking")
    parser.add_argument("--port", type=str, default=None)
    parser.add_argument("--min-distance", type=float, default=MIN_DISTANCE_MM)
    parser.add_argument("--range", type=float, default=PLOT_RANGE)

    args = parser.parse_args()
    PLOT_RANGE = args.range

    port = args.port or find_lidar_port() or DEFAULT_PORT

    print("=" * 50)
    print("  LiDAR Viewer + Objecttracking")
    print(f"  Poort: {port}")
    print(f"  Min afstand: {args.min_distance} mm")
    print(f"  Plot bereik: ±{PLOT_RANGE} mm")
    print("=" * 50)

    view_lidar(port=port, min_distance=args.min_distance)

if __name__ == "__main__":
    main()
