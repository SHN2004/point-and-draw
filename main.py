import sys
import time
import io
import mss
from PIL import Image
import threading
import random
import itertools
import os
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen

# Optional color support for Windows
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        GREEN = ''
        CYAN = ''
        MAGENTA = ''
        RED = ''
        YELLOW = ''
    class Style:
        RESET_ALL = ''

# --- Startup Animation Code ---

ASCII_BANNER = r"""
 ________               ___  ___              ________      
|\   ____\             |\  |\  \            |\   ___  \    
\ \  \___|_            \ \  \\\  \           \ \  \\ \  \   
 \ \_____  \            \ \   __  \           \ \  \\ \  \  
  \|____|\  \            \ \  \ \  \           \ \  \\ \  \ 
    ____\_\  \            \ \__\ \__\           \ \__\\ \__\
   |\_________\            \|__|\|__|            \|__| \|__|
   \|_________|                                              
"""

def type_out(text, delay=0.02):
    """Typing effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def flicker_line(text, times=10):
    """Simulate flickering daemon line"""
    for _ in range(times):
        flicker = random.choice(['', ' ', text[:len(text)//2], '█'*len(text)])
        sys.stdout.write('\r' + flicker.ljust(len(text)))
        sys.stdout.flush()
        time.sleep(random.uniform(0.05, 0.15))
    sys.stdout.write('\r' + text + '\n')

def loading_bar(duration=2):
    """Loading bar that actually fills"""
    bar_length = 30
    steps = int(duration / 0.05)
    for i in range(steps + 1):
        progress = i / steps
        filled = int(bar_length * progress)
        bar = Fore.CYAN + '█' * filled + Fore.CYAN + '-' * (bar_length - filled)
        sys.stdout.write(f'\r{Fore.CYAN}DEAMON LOADING [{bar}{Fore.CYAN}] {int(progress * 100)}%')
        sys.stdout.flush()
        time.sleep(0.05)
    print(Style.RESET_ALL)

def run_startup_animation():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + ASCII_BANNER + Style.RESET_ALL)
    time.sleep(0.3)
    print(Fore.CYAN, end='')
    flicker_line("[Initializing Daemon :: ████████████:: Active]")
    loading_bar(1.3)
    type_out(Fore.GREEN + "\n> SYSTEM ONLINE", 0.03)
    time.sleep(0.5)
    print(Style.RESET_ALL)


# --- Part 1: Thread-Safe Communication ---
# A helper object that will emit signals from the web thread to the GUI thread
class SignalBridge(QObject):
    # Define the signals we need. They will carry the data.
    point_added = pyqtSignal(dict)
    drawing_cleared = pyqtSignal()
    settings_changed = pyqtSignal(dict)
    stroke_finished = pyqtSignal()

# --- Part 2: Flask and SocketIO Setup ---
app = Flask(__name__) # Flask will now find templates/ and static/ automatically
app.config['SECRET_KEY'] = 'your-very-secret-key!'
socketio = SocketIO(app, async_mode='threading')

# Global state dictionary and signal bridge
app_state = { 'drawing_window': None }
signals = SignalBridge()

# --- Part 3: The Transparent Drawing Window ---
class DrawingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.points = []
        self.draw_tool = 'pen'
        self.persistence = 'permanent'
        self.initUI()
        self.init_signals() # Connect signals to handler methods

        # Timer for fade animations (this is safe as it's part of the GUI thread)
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.update_fades)
        self.fade_timer.start(30) # ~33 FPS

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()
        app_state['drawing_window'] = self # Make window accessible

    def init_signals(self):
        # Connect the signals from our bridge to the methods that do the work
        signals.point_added.connect(self._handle_point_added)
        signals.drawing_cleared.connect(self.clear_drawing)
        signals.settings_changed.connect(self._handle_settings_changed)
        signals.stroke_finished.connect(self.finish_stroke)

    # --- SLOTS (Thread-Safe Handlers) ---
    def _handle_point_added(self, data):
        screen_geom = QApplication.primaryScreen().geometry()
        point = QPoint(int(data['x'] * screen_geom.width()), int(data['y'] * screen_geom.height()))
        
        if data.get('new_stroke', False):
            if self.draw_tool == 'pen':
                color, width = (255, 0, 0, 255), 5
            elif self.draw_tool == 'highlighter':
                color, width = (255, 255, 0, 100), 25
            else: # Pointer
                color, width = (255, 0, 0, 255), 15
            
            new_stroke = {
                'points': [point], 'color': color, 'width': width, 'opacity': 1.0,
                'fade': self.persistence == 'fade' or self.draw_tool == 'pointer',
                'active': True  # Mark the new stroke as active
            }
            self.points.append(new_stroke)
        elif self.points:
            self.points[-1]['points'].append(point)
        
        self.update() # Now this is called safely in the GUI thread

    def clear_drawing(self):
        self.points = []
        self.update() # Safely called in the GUI thread

    def finish_stroke():
        """Deactivates the last drawn stroke, making it eligible for fading."""
        if self.points:
            self.points[-1]['active'] = False

    def _handle_settings_changed(self, data):
        self.draw_tool = data.get('tool', self.draw_tool)
        self.persistence = data.get('persistence', self.persistence)

    def paintEvent(self, event):
        with QPainter(self) as painter: # Using 'with' is safer
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for stroke in self.points:
                if len(stroke['points']) > 1:
                    color = QColor(*stroke['color'])
                    color.setAlpha(int(color.alpha() * stroke['opacity']))
                    pen = QPen(color, stroke['width'], Qt.PenStyle.SolidLine)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    for i in range(len(stroke['points']) - 1):
                        painter.drawLine(stroke['points'][i], stroke['points'][i+1])

    def update_fades(self):
        """
        Handles the gradual fading of strokes. This is called by a QTimer.
        """
        fading_occurred = False
        strokes_to_keep = []

        for stroke in self.points:
            # A stroke should fade if it's marked to fade AND it's not currently being drawn.
            is_eligible_for_fading = stroke['fade'] and not stroke.get('active', False)

            if is_eligible_for_fading:
                fading_occurred = True
                # Reduce the opacity for this frame.
                stroke['opacity'] -= 0.015 # Controls the speed of the fade
                
                # Only keep the stroke if it's still visible.
                if stroke['opacity'] > 0:
                    strokes_to_keep.append(stroke)
            else:
                # Keep all other strokes (permanent ones, or active ones).
                strokes_to_keep.append(stroke)
        
        # Replace the old list with the new one that has updated opacities.
        self.points = strokes_to_keep

        # Trigger a repaint only if something actually changed.
        if fading_occurred:
            self.update()

# --- Part 4: Screen Streaming and SocketIO Events ---
def generate_frames():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            resized_img = img.resize((800, int(800 * img.height / img.width)), Image.LANCZOS)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="JPEG", quality=65)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.getvalue() + b'\r\n')
            time.sleep(1/20) # Cap at 20 FPS

@app.route('/')
def index():
    return render_template('index.html') # Flask automatically looks in 'templates' folder

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# SocketIO events now EMIT SIGNALS instead of calling GUI functions directly
@socketio.on('connect')
def handle_connect():
    print('Client connected!')

@socketio.on('draw_event')
def handle_draw_event(data):
    signals.point_added.emit(data) # Emit the signal

@socketio.on('clear_event')
def handle_clear_event():
    signals.drawing_cleared.emit() # Emit the signal

@socketio.on('settings_event')
def handle_settings_event(data):
    signals.settings_changed.emit(data) # Emit the signal

@socketio.on('stroke_finished_event')
def handle_stroke_finished():
    signals.stroke_finished.emit()

# --- Part 5: Main Application Execution ---
if __name__ == '__main__':
    run_startup_animation()
    
    # Start the Flask-SocketIO server in a background thread
    server_thread = threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=5000))
    server_thread.daemon = True
    server_thread.start()

    # Start the PyQt application in the main thread
    qt_app = QApplication(sys.argv)
    drawing_window = DrawingWindow()
    drawing_window.show()
    sys.exit(qt_app.exec())