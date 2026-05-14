import sys
import threading
import time
import subprocess
import ctypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QSpinBox,
                            QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

try:
    from version import VERSION
except ImportError:
    VERSION = "dev"


class _CGPoint(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]


def _setup_cg():
    cg = ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics'
    )
    cg.CGEventCreate.restype = ctypes.c_void_p
    cg.CGEventCreate.argtypes = [ctypes.c_void_p]
    cg.CGEventGetLocation.restype = _CGPoint
    cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
    cg.CGEventSourceCreate.restype = ctypes.c_void_p
    cg.CGEventSourceCreate.argtypes = [ctypes.c_int]
    cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, _CGPoint, ctypes.c_uint32
    ]
    cg.CGEventPost.restype = None
    cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cg.CFRelease.restype = None
    cg.CFRelease.argtypes = [ctypes.c_void_p]
    return cg


def _setup_iopm():
    iokit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
    cf = ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
    )
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    iokit.IOPMAssertionDeclareUserActivity.restype = ctypes.c_uint32
    iokit.IOPMAssertionDeclareUserActivity.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    return iokit, cf


_cg = _setup_cg() if sys.platform == 'darwin' else None
_iokit, _cf = _setup_iopm() if sys.platform == 'darwin' else (None, None)

_kCGEventSourceStateCombinedSessionState = 1
_kCGEventMouseMoved = 5
_kCGHIDEventTap = 0
_kIOPMUserActiveLocal = 0
_kCFStringEncodingUTF8 = 0x08000100


def _post_activity_event():
    """
    Declare IOKit user activity + post synthetic mouse-moved event.
    IOPMAssertionDeclareUserActivity resets the IOKit-level idle state Teams monitors.
    CGEventPost resets the CGEvent idle timer as a secondary signal.
    """
    if _cg is None or _iokit is None:
        raise RuntimeError("CoreGraphics/IOKit not available on this platform")

    # Primary: declare user activity at IOKit level (what Teams actually monitors)
    name = _cf.CFStringCreateWithCString(None, b"MSTeamsWaker", _kCFStringEncodingUTF8)
    if name:
        try:
            assertion_id = ctypes.c_uint32(0)
            _iokit.IOPMAssertionDeclareUserActivity(
                name, _kIOPMUserActiveLocal, ctypes.byref(assertion_id)
            )
        finally:
            _cf.CFRelease(name)

    # Secondary: reset CGEvent idle timer
    source = _cg.CGEventSourceCreate(_kCGEventSourceStateCombinedSessionState)
    if not source:
        raise RuntimeError("CGEventSourceCreate returned NULL")
    try:
        temp = _cg.CGEventCreate(None)
        if not temp:
            raise RuntimeError("CGEventCreate returned NULL")
        point = _cg.CGEventGetLocation(temp)
        _cg.CFRelease(temp)

        event = _cg.CGEventCreateMouseEvent(source, _kCGEventMouseMoved, point, 0)
        if not event:
            raise RuntimeError("CGEventCreateMouseEvent returned NULL")
        try:
            _cg.CGEventPost(_kCGHIDEventTap, event)
        finally:
            _cg.CFRelease(event)
    finally:
        _cg.CFRelease(source)


class WorkerSignals(QObject):
    log_update = pyqtSignal(str)


class TeamsWakerWorker(threading.Thread):
    def __init__(self, interval_minutes, signals):
        threading.Thread.__init__(self)
        self.interval_minutes = interval_minutes
        self.running = True
        self.signals = signals

    def run(self):
        self.log("Teams waker started")
        while self.running:
            try:
                _post_activity_event()
                self.log("Activity signal sent")
                for _ in range(self.interval_minutes * 60):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(60)
        self.log("Teams waker stopped")

    def stop(self):
        self.running = False

    def log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.signals.log_update.emit(f"[{timestamp}] {message}")


class TeamsWakerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.caffeinate_process = None
        self.worker_signals = WorkerSignals()
        self.worker_signals.log_update.connect(self.update_log)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"MS Teams Waker v{VERSION}")
        self.setMinimumSize(500, 400)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        version_label = QLabel(f"Version: {VERSION}")
        version_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(version_label)

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Wake frequency (minutes):")
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(5)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        main_layout.addLayout(interval_layout)

        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_waker)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_waker)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        log_label = QLabel("Activity Log:")
        main_layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        self.statusBar().showMessage("Ready")

    def start_waker(self):
        interval = self.interval_spinbox.value()
        self.worker = TeamsWakerWorker(interval, self.worker_signals)
        self.worker.start()

        try:
            self.caffeinate_process = subprocess.Popen(['caffeinate', '-d'])
            self.update_log(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] System sleep prevention activated"
            )
        except Exception as e:
            self.update_log(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to prevent sleep: {e}"
            )

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.interval_spinbox.setEnabled(False)
        self.statusBar().showMessage("Running")

    def stop_waker(self):
        if self.caffeinate_process:
            self.caffeinate_process.terminate()
            self.caffeinate_process = None
            self.update_log(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] System sleep prevention deactivated"
            )

        if self.worker:
            self.worker.stop()
            self.worker.join(timeout=5)
            self.worker = None

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.interval_spinbox.setEnabled(True)
        self.statusBar().showMessage("Stopped")

    def update_log(self, message):
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        if self.worker:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                "The Teams waker is still running. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_waker()
                event.accept()
            else:
                event.ignore()


def main():
    app = QApplication(sys.argv)
    window = TeamsWakerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
