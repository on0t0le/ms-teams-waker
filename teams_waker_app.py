import sys
import threading
import time
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSpinBox, 
                            QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

# Try to import version information
try:
    from version import VERSION
except ImportError:
    VERSION = "dev"

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
                self.wake_teams()
                self.log("Teams refreshed")

                for _ in range(self.interval_minutes * 60):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(60)

        self.log("Teams waker stopped")
    
    def wake_teams(self):
        script = '''
        tell application "Microsoft Teams"
            activate
            tell application "System Events"
                keystroke "2" using command down
            end tell
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
    
    def stop(self):
        self.running = False
    
    def log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.signals.log_update.emit(log_message)

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
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Version label
        version_label = QLabel(f"Version: {VERSION}")
        version_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(version_label)
        
        # Interval setting
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Wake frequency (minutes):")
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(5)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        main_layout.addLayout(interval_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_waker)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_waker)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)
        
        # Log area
        log_label = QLabel("Activity Log:")
        main_layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def start_waker(self):
        interval = self.interval_spinbox.value()
        self.worker = TeamsWakerWorker(interval, self.worker_signals)
        self.worker.start()

        try:
            self.caffeinate_process = subprocess.Popen(['caffeinate', '-d'])
            self.update_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] System sleep prevention activated")
        except Exception as e:
            self.update_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to prevent sleep: {e}")

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.interval_spinbox.setEnabled(False)
        self.statusBar().showMessage("Running")

    def stop_waker(self):
        if self.caffeinate_process:
            self.caffeinate_process.terminate()
            self.caffeinate_process = None
            self.update_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] System sleep prevention deactivated")

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
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        if self.worker:
            reply = QMessageBox.question(self, 'Confirm Exit',
                "The Teams waker is still running. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
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
