import serial
import threading
import logging
from typing import Optional, Callable

# Configure basic logging for better feedback and debugging
# logging.basicConfig(
#     level=logging.INFO, 
#     format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
# )

class ScannerManager:
    """
    Manages a serial port scanner in a dedicated thread.

    This class encapsulates the logic for reading data from a scanner,
    handling callbacks, and ensuring that only "fresh" scans are delivered
    to consumers after certain events. It is thread-safe.
    """

    def __init__(self, port: str = "/dev/ttyACM0", baud_rate: int = 9600):
        """
        Initializes the ScannerManager.

        Args:
            port (str): The serial port to connect to (e.g., "/dev/ttyACM0" on Linux or "COM3" on Windows).
            baud_rate (int): The baud rate for serial communication.
        """
        self.port = port
        self.baud_rate = baud_rate
        self.last_scanned_value: Optional[str] = None

        self._update_callback: Optional[Callable[[str], None]] = None
        self._active_page_context: Optional[str] = None  # For logging context

        # --- Sequence Gate Mechanism to prevent stale scans ---
        self._scan_sequence = 0
        self._min_seq_to_deliver = 0
        self._lock = threading.Lock()

        # --- Threading Control ---
        self._thread: Optional[threading.Thread] = None
        self._is_running = threading.Event()

    def start(self):
        """Starts the scanner reading thread. Safe to call if already running."""
        if self._is_running.is_set():
            logging.warning("Scanner thread is already running.")
            return

        logging.info(f"Starting scanner on port {self.port}...")
        self._is_running.set()
        self._thread = threading.Thread(target=self._read_loop, name="ScannerThread", daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the scanner reading thread gracefully."""
        if not self._is_running.is_set():
            logging.warning("Scanner thread is not running.")
            return

        logging.info("Stopping scanner thread...")
        self._is_running.clear()
        if self._thread:
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                logging.error("Scanner thread did not stop in time.")

    def _read_loop(self):
        """The main loop that runs in a thread to read from the serial port."""
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=1) as ser:
                logging.info(f"Successfully connected to scanner on {self.port}.")
                while self._is_running.is_set():
                    if ser.in_waiting > 0:
                        self._process_data(ser.readline())
        except serial.SerialException as e:
            logging.error(f"Scanner error on {self.port}: {e}. Thread stopping.")
        except Exception as e:
            logging.error(f"An unexpected error occurred in scanner loop: {e}")
        finally:
            logging.info("Scanner thread has finished.")

    def _process_data(self, raw_data: bytes):
        """Decodes, validates, and delivers scanned data."""
        if not (decoded_data := raw_data.decode(errors='ignore').strip()):
            return

        with self._lock:
            self._scan_sequence += 1
            # Gate: Ignore any scan older than the armed requirement
            if self._scan_sequence <= self._min_seq_to_deliver:
                logging.debug(f"[{self._active_page_context}] Ignored stale scan: {decoded_data}")
                return
            
            # This is a fresh scan; deliver it
            self.last_scanned_value = decoded_data
            callback = self._update_callback

        logging.info(f"[{self._active_page_context}] Delivered new scan: '{decoded_data}'")
        
        # Execute callback outside the lock to avoid blocking the scanner thread
        if callback:
            try:
                callback(decoded_data)
            except Exception as e:
                logging.error(f"Error in scanner update callback: {e}")

    def clear_last_scan(self):
        """Manually clears the last scanned value."""
        with self._lock:
            self.last_scanned_value = None
            logging.debug("Last scanned value cleared.")

    def require_fresh_scan(self):
        """
        Arms a gate so only the *next* new scan is delivered.
        
        This is useful when a UI screen needs new input, ignoring any previous
        scans that might have occurred.
        """
        with self._lock:
            self._min_seq_to_deliver = self._scan_sequence
            self.last_scanned_value = None
            logging.info("Gate armed. Waiting for a fresh scan.")

    def set_update_callback(self,
                            callback: Optional[Callable[[str], None]] = None,
                            page_context: Optional[str] = None,
                            require_fresh: bool = False):
        """
        Sets the callback function to be executed on each new scan.

        Args:
            callback: A function that takes a string argument (the scanned data).
            page_context: An optional string to provide context in logs.
            require_fresh: If True, ignores all past scans and waits for a new one.
        """
        with self._lock:
            self._update_callback = callback
            self._active_page_context = page_context
        
        if require_fresh:
            self.require_fresh_scan()