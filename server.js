const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cookieParser = require('cookie-parser'); // Middleware for cookies

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files and parse cookies
app.use(express.static('public'));
app.use(cookieParser());

// Chat state
let isChatLocked = false; // Lock state
let messageHistory = []; // Store messages
const users = {}; // { socketId: username }

// Serve admin panel
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html');
});

// Handle connections
io.on('connection', (socket) => {
    console.log('User connected:', socket.id);

    // Set a default username
    users[socket.id] = "Anonymous";

    // Check if the user has the admin cookie
    const cookies = socket.handshake.headers.cookie || '';
    const isAdmin = cookies.includes('ADMINSERVERSERVICEPERMSEC3256');

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id] = username || "Anonymous";
        console.log(`User ${socket.id} set their username to: ${users[socket.id]}`);
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        if (!isChatLocked || isAdmin) { // Admins bypass lock
            const username = users[socket.id] || "Anonymous";
            const prefix = isAdmin ? `[Admin] ${username}` : username; // Add admin tag if applicable
            const formattedMessage = `${prefix}: ${msg}`;
            messageHistory.push(formattedMessage); // Save message history
            io.emit('chat message', formattedMessage); // Broadcast to all clients
        } else {
            socket.emit('chat locked'); // Notify regular users if the chat is locked
        }
    });

    // Handle admin actions
    socket.on('admin lock', () => {
        isChatLocked = true;
        io.emit('chat lock status', isChatLocked);
        console.log('Chat locked by admin');
    });

    socket.on('admin unlock', () => {
        isChatLocked = false;
        io.emit('chat lock status', isChatLocked);
        console.log('Chat unlocked by admin');
    });

    socket.on('admin clear messages', () => {
        messageHistory = [];
        io.emit('chat history', messageHistory);
        console.log('Messages cleared by admin');
    });

    socket.on('admin announcement', (announcement) => {
        const adminMessage = `SERVERHOST (admin): ${announcement}`;
        io.emit('chat message', adminMessage);
        console.log('Announcement sent:', adminMessage);
    });

    // Handle disconnection
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        delete users[socket.id];
    });
});

// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
