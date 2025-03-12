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
const users = {}; // { socketId: { username, defaultUsername, isAdmin, isAvailable, isServerOwner } }
const privateChats = {}; // { roomId: [socketId1, socketId2] }

// Sign-in credentials
const SERVER_OWNER_CREDENTIALS = { username: 'zac', password: 'zaxc1122' };

// Handle connections
io.on('connection', (socket) => {
    console.log(`User connected: ${socket.id}`);

    // Assign a default username and determine if the user is an admin
    const defaultUsername = `User${Math.floor(Math.random() * 10000)}`;
    const isAdmin = socket.handshake.headers.cookie?.includes('ADMINSERVERSERVICEPERMSEC3256') || false;
    users[socket.id] = { 
        username: defaultUsername, 
        defaultUsername, 
        isAvailable: true, 
        isAdmin,
        isServerOwner: false // Default to not being a server owner
    };

    // Notify all users of the updated user list
    io.emit('update users', users);

    // Handle Sign-In
    socket.on('sign in', ({ username, password }) => {
        if (
            username === SERVER_OWNER_CREDENTIALS.username &&
            password === SERVER_OWNER_CREDENTIALS.password
        ) {
            // Mark user as server owner
            users[socket.id].isServerOwner = true;
            users[socket.id].username = `[Server Owner] ${username}`;
            console.log(`User ${socket.id} signed in as Server Owner.`);

            // Notify all clients to update the user list
            io.emit('update users', users);
        } else {
            console.log(`Invalid sign-in attempt by ${socket.id}.`);
        }
    });

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id].username = username || users[socket.id].defaultUsername;
        io.emit('update users', users); // Notify all users
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        const user = users[socket.id] || {};
        const isServerOwner = user.isServerOwner || false;

        const formattedMessage = {
            username: user.username || `User${socket.id}`,
            text: msg,
            isServerOwner,
        };

        console.log(`Message from ${socket.id}: ${msg}`);
        messageHistory.push(formattedMessage);

        io.emit('chat message', formattedMessage); // Broadcast to all clients
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
        io.emit('chat message', { username: 'SERVERHOST', text: announcement, isServerOwner: false });
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
