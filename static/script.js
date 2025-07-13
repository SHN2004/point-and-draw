document.addEventListener('DOMContentLoaded', () => {
    // --- WebSocket Connection ---
    const socket = io();

    // --- Element References ---
    const canvas = document.getElementById('draw-canvas');
    const screenFeed = document.getElementById('screen-feed');
    const toolButtons = document.querySelectorAll('.tool-btn');
    const fadeModeButton = document.getElementById('mode-fade');
    const clearButton = document.getElementById('btn-clear');

    let isDrawing = false;

    // --- THE FIX: Canvas Synchronization ---
    function syncCanvasToVideo() {
        // Get the actual, rendered dimensions and position of the video image
        const videoRect = screenFeed.getBoundingClientRect();
        const containerRect = screenFeed.parentElement.getBoundingClientRect();

        // Set the canvas to the exact same size and position as the video image
        canvas.style.width = `${videoRect.width}px`;
        canvas.style.height = `${videoRect.height}px`;
        canvas.style.top = `${videoRect.top - containerRect.top}px`;
        canvas.style.left = `${videoRect.left - containerRect.left}px`;

        // IMPORTANT: Also set the internal resolution of the canvas
        canvas.width = videoRect.width;
        canvas.height = videoRect.height;
    }

    // --- Drawing Functions ---
    function handleDraw(e) {
        if (!isDrawing) return;
        e.preventDefault();
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect(); // Use the canvas's own rect

        // Normalize coordinates based on the correctly sized canvas
        const x = (touch.clientX - rect.left) / rect.width;
        const y = (touch.clientY - rect.top) / rect.height;

        if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
            socket.emit('draw_event', { x, y, new_stroke: false });
        }
    }

    function startDraw(e) {
        isDrawing = true;
        e.preventDefault();
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        const x = (touch.clientX - rect.left) / rect.width;
        const y = (touch.clientY - rect.top) / rect.height;

        if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
            socket.emit('draw_event', { x, y, new_stroke: true });
        }
    }

    function stopDraw() {
        isDrawing = false;
    }

    // --- Event Listeners ---
    socket.on('connect', () => {
        console.log('Connected to server via WebSocket!');
        // Sync canvas once connected and video is likely loading
        syncCanvasToVideo();
    });

    // Sync canvas when the window is resized or video loads
    window.addEventListener('resize', syncCanvasToVideo);
    screenFeed.addEventListener('load', syncCanvasToVideo);

    canvas.addEventListener('touchstart', startDraw);
    canvas.addEventListener('touchend', stopDraw);
    canvas.addEventListener('touchmove', handleDraw);

    // Button Listeners
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

    clearButton.addEventListener('click', () => {
        socket.emit('clear_event');
    });

    // Run once on load just in case
    syncCanvasToVideo();
});