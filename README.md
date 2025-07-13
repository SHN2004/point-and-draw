# PyPointer 🎯

A real-time screen annotation tool that allows you to draw on your screen from any device with a web browser. Perfect for presentations, teaching, remote assistance, and collaborative screen sharing.

## ✨ Features

- **Cross-Device Control**: Draw on your computer screen from any mobile device or tablet
- **Real-Time Screen Streaming**: Live video feed of your desktop with minimal latency
- **Multiple Drawing Tools**:
  - 🖊️ **Pen**: Standard drawing tool with red ink
  - 🖍️ **Highlighter**: Semi-transparent yellow highlighting
  - 👆 **Pointer**: Temporary pointer that auto-fades
- **Smart Persistence**: Choose between permanent drawings or auto-fading annotations
- **Transparent Overlay**: Annotations appear directly on your screen without interfering with applications
- **Touch-Optimized**: Responsive touch controls with gesture support (single-finger draw, multi-finger scroll)

## 🚀 Quick Start

### Prerequisites

```bash
uv add PyQt6 flask flask-socketio mss pillow colorama
```

### Installation & Usage

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/pypointer.git
   cd pypointer
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

3. **Connect from your mobile device**:
   - Open a web browser on your phone/tablet
   - Navigate to `http://[your-computer-ip]:5000`
   - Start drawing on the screen feed!

## 🎮 Controls

### Drawing Tools
- **Pen**: Standard drawing tool for permanent annotations
- **Highlighter**: Semi-transparent highlighting for emphasis
- **Pointer**: Temporary pointer that fades away automatically

### Modes
- **Fade Away**: Toggle to make all drawings gradually disappear
- **Clear All**: Remove all annotations instantly

### Touch Gestures
- **Single finger**: Draw/annotate
- **Multi-finger**: Scroll and zoom the interface (drawing disabled during gestures)

## 🏗️ Architecture

PyPointer uses a hybrid architecture combining:

- **PyQt6**: Transparent fullscreen overlay for desktop annotations
- **Flask + SocketIO**: Real-time web interface and communication
- **MSS**: High-performance screen capture
- **Threading**: Separate threads for GUI and web server

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Mobile Web    │ ◄─────────────► │   Flask Server  │
│   Interface     │                 │   (Background   │
└─────────────────┘                 │    Thread)      │
                                    └─────────────────┘
                                            │
                                       Signal Bridge
                                            │
                                    ┌─────────────────┐
                                    │   PyQt6 GUI     │
                                    │  (Main Thread)  │
                                    └─────────────────┘
                                            │
                                    ┌─────────────────┐
                                    │ Transparent     │
                                    │ Screen Overlay  │
                                    └─────────────────┘
```

## 🔧 Configuration

### Network Setup
By default, the server runs on `0.0.0.0:5000`. To find your computer's IP address:

**Windows**: `ipconfig`
**Mac/Linux**: `ifconfig` or `ip addr show`

### Performance Tuning
- **Frame Rate**: Adjust `time.sleep(1/20)` in `generate_frames()` for higher/lower FPS
- **Image Quality**: Modify `quality=65` in JPEG compression for better quality vs. bandwidth
- **Fade Speed**: Change `stroke['opacity'] -= 0.015` in `update_fades()` for faster/slower fading

## 🛠️ Technical Details

### Thread Safety
PyPointer uses Qt's signal-slot mechanism to ensure thread-safe communication between the web server and GUI:

```python
class SignalBridge(QObject):
    point_added = pyqtSignal(dict)
    drawing_cleared = pyqtSignal()
    settings_changed = pyqtSignal(dict)
```

### Screen Coordinate Mapping
Touch coordinates are normalized (0-1) and mapped to screen coordinates:

```python
screen_geom = QApplication.primaryScreen().geometry()
point = QPoint(int(data['x'] * screen_geom.width()), 
               int(data['y'] * screen_geom.height()))
```

### Fade Animation System
Smooth fading is achieved through a 33 FPS timer that gradually reduces opacity:

```python
def update_fades(self):
    for stroke in self.points:
        if stroke['fade'] and not stroke.get('active', False):
            stroke['opacity'] -= 0.015
```

## 📱 Mobile Interface

The web interface is fully responsive and optimized for touch devices:

- **Touch-action manipulation**: Allows pinch-to-zoom while preserving drawing functionality
- **Gesture detection**: Distinguishes between single-finger drawing and multi-finger navigation
- **Canvas synchronization**: Automatically aligns the drawing canvas with the video feed

## 🔒 Security Considerations

- **Local Network Only**: Designed for trusted local networks
- **No Authentication**: Currently no user authentication (consider adding for production use)
- **Screen Access**: Captures entire screen content

## 🐛 Troubleshooting

### Common Issues

**"Can't connect to server"**
- Ensure both devices are on the same network
- Check firewall settings (port 5000)
- Verify IP address is correct

**"Drawing appears offset"**
- Refresh the web page to resync canvas positioning
- Check if screen resolution changed

**"Lag in drawing"**
- Reduce video quality in `generate_frames()`
- Check network bandwidth
- Close unnecessary applications

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Additional drawing tools
- UI improvements
- Performance optimizations
- Security enhancements
- Documentation updates

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyQt6** for the robust GUI framework
- **Flask-SocketIO** for real-time web communication
- **MSS** for efficient screen capture
- **Pillow** for image processing

---

**Made with ❤️ for seamless screen collaboration**
