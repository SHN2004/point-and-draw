document.addEventListener('DOMContentLoaded', () => {
    // --- WebSocket Connection ---
    const socket = io();
    // --- Element References ---
    const canvas = document.getElementById('draw-canvas');
    const screenFeed = document.getElementById('screen-feed');
    // ... (rest of the element references are the same)
    const toolButtons = document.querySelectorAll('.tool-btn');
    const fadeModeButton = document.getElementById('mode-fade');
    const clearButton = document.getElementById('btn-clear');
    let isDrawing = false;
    // --- Canvas Synchronization Logic (no changes here) ---
    function syncCanvasToVideo() {
        const videoRect = screenFeed.getBoundingClientRect();
        const containerRect = screenFeed.parentElement.getBoundingClientRect();
        canvas.style.width = `${videoRect.width}px`;
        canvas.style.height = `${videoRect.height}px`;
        canvas.style.top = `${videoRect.top - containerRect.top}px`;
        canvas.style.left = `${videoRect.left - containerRect.left}px`;
        canvas.width = videoRect.width;
        canvas.height = videoRect.height;
    }
    // --- Drawing Functions (UPDATED FOR GESTURE CONTROL) ---
    function startDraw(e) {
        // Only prevent default and start drawing if it's a SINGLE finger touch.
        if (e.touches.length === 1) {
            e.preventDefault(); // Prevent page scroll for single-finger touch
            isDrawing = true;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const x = (touch.clientX - rect.left) / rect.width;
            const y = (touch.clientY - rect.top) / rect.height;
            if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
                socket.emit('draw_event', { x, y, new_stroke: true });
            }
        }
        // If there are more than 1 touches, we do nothing and let the browser handle scrolling.
    }
    function handleDraw(e) {
        // We only draw if the "isDrawing" state is active AND it's a single finger.
        if (!isDrawing || e.touches.length !== 1) {
            // If we are in a multi-touch gesture, ensure drawing is stopped.
            if (isDrawing) {
                isDrawing = false;
            }
            return;
        }
        e.preventDefault(); // Prevent page scroll while drawing
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        const x = (touch.clientX - rect.left) / rect.width;
        const y = (touch.clientY - rect.top) / rect.height;
        if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
            socket.emit('draw_event', { x, y, new_stroke: false });
        }
    }
    function stopDraw(e) {
        // Reset the drawing state when the last finger is lifted.
        if (isDrawing) {
            isDrawing = false;
            // Tell the server the stroke is complete so it can start fading if needed
            socket.emit('stroke_finished_event');
        }
    }
    // --- Event Listeners (no changes here) ---
    socket.on('connect', () => {
        console.log('Connected to server via WebSocket!');
        syncCanvasToVideo();
    });
    window.addEventListener('resize', syncCanvasToVideo);
    screenFeed.addEventListener('load', syncCanvasToVideo);
    canvas.addEventListener('touchstart', startDraw);
    canvas.addEventListener('touchend', stopDraw);
    canvas.addEventListener('touchcancel', stopDraw); // Also handle interruptions
    canvas.addEventListener('touchmove', handleDraw);
    toolButtons.forEach(button => {
        button.addEventListener('click', () => {
            toolButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            socket.emit('settings_event', { tool: button.id.split('-')[1] });
        });
    });
    fadeModeButton.addEventListener('click', () => {
        const isActive = fadeModeButton.classList.toggle('active');
        socket.emit('settings_event', { persistence: isActive ? 'fade' : 'permanent' });
    });
    clearButton.addEventListener('click', () => { socket.emit('clear_event'); });
    // Initial sync
    syncCanvasToVideo();
});