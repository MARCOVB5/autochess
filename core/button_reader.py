"""Leitura não bloqueante dos botões físicos do robô."""

import queue
import threading
import time

import serial

import hardware_config as hardware


def parse_button_command(line):
    if not line.startswith(hardware.BUTTON_EVENT_PREFIX):
        return None
    command = line.removeprefix(hardware.BUTTON_EVENT_PREFIX)
    return command if command in {"0", "1", "2"} else None


class PhysicalButtonReader:
    def __init__(
        self,
        event_queue,
        port=hardware.BUTTONS_SERIAL_PORT,
        baudrate=hardware.BUTTONS_SERIAL_BAUDRATE,
        timeout=hardware.BUTTONS_SERIAL_TIMEOUT,
    ):
        self.event_queue = event_queue
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.running = False
        self.thread = None

    @property
    def enabled(self):
        return bool(self.port)

    def start(self):
        if not self.enabled:
            return False
        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout,
        )
        time.sleep(hardware.BUTTONS_STARTUP_DELAY)
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        return True

    def _read_loop(self):
        while self.running:
            try:
                line = self.serial.readline().decode(
                    "utf-8",
                    errors="ignore",
                ).strip()
                command = parse_button_command(line)
                if command is not None:
                    self.event_queue.put(("button", command))
                elif line:
                    self.event_queue.put(("button_log", line))
            except (OSError, serial.SerialException) as error:
                self.event_queue.put(("error", f"Botões: {error}"))
                self.running = False
            time.sleep(hardware.BUTTONS_POLL_INTERVAL)

    def close(self):
        self.running = False
        if self.serial and self.serial.is_open:
            self.serial.close()


def drain_events(event_queue):
    while True:
        try:
            yield event_queue.get_nowait()
        except queue.Empty:
            return
