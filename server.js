const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cookieParser = require('cookie-parser');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Middleware
app.use(express.static('public'));
app.use(cookieParser());

// Chat state
let isChatLocked = false; // Lock state
let messageHistory = []; // Store messages
const users = {}; // { socketId: { username, defaultUsername, isAdmin, isAvailable } }
const privateChats = {}; // { roomId: [socketId1, socketId2] }

// Handle connections
io.on('connection', (socket) => {
    console.log('User connected:', socket.id);

    // Assign a default username and determine if the user is an admin
    const defaultUsername = `User${Math.floor(Math.random() * 10000)}`;
    const isAdmin = socket.handshake.headers.cookie?.includes('ADMINSERVERSERVICEPERMSEC3256') || false;
    users[socket.id] = { 
        username: defaultUsername, 
        defaultUsername, 
        isAvailable: true, 
        isAdmin 
    };

    // Notify all users of the updated user list
    io.emit('update users', users);

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id].username = username || users[socket.id].defaultUsername;
        io.emit('update users', users); // Notify all users
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        if (!isChatLocked || users[socket.id].isAdmin) { // Admins bypass lock
            const username = users[socket.id].username;
            const prefix = users[socket.id].isAdmin ? `[Admin] ${username}` : username;
            const formattedMessage = `${prefix}: ${msg}`;
            messageHistory.push(formattedMessage);

            io.emit('chat message', formattedMessage); // Broadcast to all clients
        } else {
            socket.emit('chat locked'); // Notify users if chat is locked
        }
    });

    // Handle direct message requests
    socket.on('request dm', (targetSocketId) => {
        const roomId = `DM${String(Math.floor(Math.random() * 1e15)).padStart(15, '0')}`;
        privateChats[roomId] = [socket.id, targetSocketId];

        // Notify the recipient
        io.to(targetSocketId).emit('dm request', { from: socket.id, roomId });
    });

    // Handle DM acceptance
    socket.on('accept dm', (roomId) => {
        const participants = privateChats[roomId];
        if (participants && participants.includes(socket.id)) {
            io.to(participants[0]).emit('redirect dm', roomId);
            io.to(participants[1]).emit('redirect dm', roomId);
        }
    });

    // Admin actions
    socket.on('admin lock', () => {
        isChatLocked = true;
        io.emit('chat lock status', isChatLocked);
        console.log('Chat locked by admin.');
    });

    socket.on('admin unlock', () => {
        isChatLocked = false;
        io.emit('chat lock status', isChatLocked);
        console.log('Chat unlocked by admin.');
    });

    socket.on('admin clear messages', () => {
        messageHistory = [];
        io.emit('chat history', messageHistory);
        console.log('Messages cleared by admin.');
    });

    socket.on('admin announcement', (announcement) => {
        const adminMessage = `SERVERHOST (admin): ${announcement}`;
        io.emit('chat message', adminMessage);
        console.log('Announcement sent by admin.');
    });

    // Handle disconnection
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        delete users[socket.id];
        io.emit('update users', users); // Notify all clients
    });
});

// Dynamic route for private chat rooms
app.get('/DM:roomId', (req, res) => {
    const { roomId } = req.params;
    res.sendFile(__dirname + '/public/private_chat.html'); // Serve private chat interface
});

// Serve admin page (use your existing admin page)
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html'); // Path to your admin page
});

// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
