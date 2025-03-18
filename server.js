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
const users = {}; // { socketId: { username, defaultUsername, isAdmin, isAvailable, role } }
const privateChats = {}; // { roomId: [socketId1, socketId2] }

// Special user sign-in credentials
const SPECIAL_USERS = [
    { username: 'zac :D', password: 'zaxc1122', role: 'Server Owner' },
    { username: 'lily', password: 'lily1', role: 'Developer' },
    { username: 'izzy', password: 'izzy', role: 'Server Owner' },
    { username: 'JW', password: 'JW', role: 'Developer' },
    { username: 'issac', password: 'issac1', role: 'Server Owner' },
    { username: 'Milly<3', password: 'milly', role: 'Developer' },
];

// Handle connections
io.on('connection', (socket) => {
    console.log(`User connected: ${socket.id}`);

    // Assign a default username and initialize user data
    const defaultUsername = `User${Math.floor(Math.random() * 10000)}`;
    users[socket.id] = {
        username: defaultUsername,
        defaultUsername,
        isAvailable: true,
        role: null // Default to no special role
    };

    // Notify all clients of the updated user list
    io.emit('update users', users);

    // Handle special user sign-in
    socket.on('sign in', ({ username, password }) => {
        const specialUser = SPECIAL_USERS.find(user => user.username === username && user.password === password);
        if (specialUser) {
            // Grant special role
            users[socket.id].role = specialUser.role;
            users[socket.id].username = `[${specialUser.role}] ${username}`;
            console.log(`User ${socket.id} signed in as ${specialUser.role}.`);

            // Notify all clients of updated user list
            io.emit('update users', users);
        } else {
            console.log(`Invalid sign-in attempt by ${socket.id}.`);
            socket.emit('sign in error', 'Invalid username or password'); // Notify the client
        }
    });

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id].username = username || users[socket.id].defaultUsername;
        io.emit('update users', users); // Notify all users
    });

    // Handle general chat messages
    socket.on('chat message', (msg) => {
        const user = users[socket.id] || {};
        const formattedMessage = {
            username: user.username || `User${socket.id}`,
            text: msg,
            role: user.role || null // Attach role if available
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

    // Admin-only actions
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
        io.emit('chat message', { username: 'SERVERHOST', text: announcement, role: null });
        console.log('Announcement sent by admin.');
    });

    // Handle Developer Chat room access
    socket.on('join dev', (confirmed) => {
        if (confirmed && users[socket.id]?.role) {
            console.log(`User ${socket.id} joined Developer Chat.`);
            socket.emit('dev message', `Welcome to the Developer Chat!`);
        } else {
            console.log(`User ${socket.id} declined access or unauthorized attempt.`);
        }
    });

    // Handle Developer Chat messages
    socket.on('dev chat message', (msg) => {
        if (users[socket.id]?.role) {
            io.to('Developer Chat').emit('dev chat message', {
                username: users[socket.id].username,
                text: msg
            });
        } else {
            console.log(`Unauthorized message attempt by ${socket.id}.`);
        }
    });

    // Handle disconnections
    socket.on('disconnect', () => {
        console.log(`User disconnected: ${socket.id}`);
        delete users[socket.id];
        io.emit('update users', users); // Notify all clients
    });
});

// Dynamic route for private chat rooms
app.get('/DM:roomId', (req, res) => {
    const { roomId } = req.params;
    res.sendFile(__dirname + '/public/private_chat.html'); // Serve private chat interface
});

// Serve admin page
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html'); // Path to your admin page
});

// Start the server
server.listen(3000, () => {
    console.log('LCS - lantern chat service version 1.6E made by pancakes and learnhelp.cc | opened on http://localhost:3000');
});
