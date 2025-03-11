const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files
app.use(express.static('public'));

// Chat state
let isChatLocked = false; // Lock state
let messageHistory = []; // Store messages
const users = {}; // { socketId: username }
const admins = {}; // { socketId: adminUsername }

// Serve admin panel
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html');
});

// Handle connections
io.on('connection', (socket) => {
    console.log('User connected:', socket.id);

    // Set a default username for regular users
    users[socket.id] = "Anonymous";

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id] = username || "Anonymous";
        console.log(`User ${socket.id} set their username to: ${users[socket.id]}`);
    });

    // Handle admin login
    socket.on('admin login', (adminUsername) => {
        admins[socket.id] = adminUsername; // Add admin to admin list
        console.log(`Admin logged in: ${adminUsername}`);
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        if (!isChatLocked || admins[socket.id]) { // Bypass lock for admins
            const isAdmin = !!admins[socket.id];
            const username = isAdmin ? `${admins[socket.id]} {admin}` : users[socket.id] || "Anonymous";
            const formattedMessage = `${username}: ${msg}`;

            messageHistory.push(formattedMessage); // Add to message history
            io.emit('chat message', formattedMessage); // Broadcast to all clients
        } else {
            socket.emit('chat locked'); // Notify regular users if the chat is locked
        }
    });

    // Handle admin-specific actions
    socket.on('admin lock', () => {
        isChatLocked = true;
        io.emit('chat lock status', isChatLocked); // Notify all clients
        console.log('Chat has been locked by admin');
    });

    socket.on('admin unlock', () => {
        isChatLocked = false;
        io.emit('chat lock status', isChatLocked); // Notify all clients
        console.log('Chat has been unlocked by admin');
    });

    socket.on('admin clear messages', () => {
        messageHistory = []; // Clear message history
        io.emit('chat history', messageHistory); // Notify all clients to clear chat
        console.log('Chat messages have been cleared by admin');
    });

    socket.on('admin announcement', (announcement) => {
        const adminMessage = `SERVERHOST (admin): ${announcement}`;
        io.emit('chat message', adminMessage); // Broadcast announcement to all users
        console.log('Announcement sent:', adminMessage);
    });

    // Handle disconnection
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        delete users[socket.id];
        delete admins[socket.id]; // Remove from admins if applicable
    });
});

// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
