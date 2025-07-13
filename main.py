import sys
import time
import io
import mss
from PIL import Image
import threading
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen

# --- Part 1: Thread-Safe Communication ---
# A helper object that will emit signals from the web thread to the GUI thread
class SignalBridge(QObject):
    # Define the signals we need. They will carry the data.
    point_added = pyqtSignal(dict)
    drawing_cleared = pyqtSignal()
    settings_changed = pyqtSignal(dict)

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
                'fade': self.persistence == 'fade' or self.draw_tool == 'pointer'
            }
            self.points.append(new_stroke)
        elif self.points:
            self.points[-1]['points'].append(point)
        
        self.update() # Now this is called safely in the GUI thread

    def clear_drawing(self):
        self.points = []
        self.update() # Safely called in the GUI thread

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
        if any(s['fade'] for s in self.points):
            self.points = [s for s in self.points if not s['fade'] or s['opacity'] > 0]
            for stroke in self.points:
                if stroke['fade']:
                    stroke['opacity'] -= 0.015
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

# --- Part 5: Main Application Execution ---
if __name__ == '__main__':
    # Start the Flask-SocketIO server in a background thread
    server_thread = threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=5000))
    server_thread.daemon = True
    server_thread.start()

    # Start the PyQt application in the main thread
    qt_app = QApplication(sys.argv)
    drawing_window = DrawingWindow()
    drawing_window.show()
    sys.exit(qt_app.exec())