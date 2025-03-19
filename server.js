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
let isChatLocked = false;
let messageHistory = [];
const users = {};
const privateChats = {};
const SPECIAL_USERS = [
    { username: 'zac : D', password: 'zaxc1122', role: 'Server Owner' },
    { username: 'lily', password: 'lily1', role: 'Developer' },
    { username: 'izzy', password: 'izzy', role: 'Server Owner' },
    { username: 'JW', password: 'JW', role: 'Developer' },
    { username: 'issac', password: 'issac1', role: 'Server Owner' },
    { username: 'Milly<3', password: 'milly', role: 'Developer' },
];

// Handle connections
io.on('connection', (socket) => {
    console.log(`User connected: ${socket.id}`);

    // Assign a default username
    const defaultUsername = `User${Math.floor(Math.random() * 10000)}`;
    users[socket.id] = {
        username: defaultUsername,
        defaultUsername,
        isAvailable: true,
        role: null,
    };

    // Notify all clients of the updated user list
    io.emit('update users', Object.values(users));

    // Handle user sign-in
    socket.on('sign in', ({ username, password }) => {
        const specialUser = SPECIAL_USERS.find(user => user.username === username && user.password === password);
        if (specialUser) {
            users[socket.id].role = specialUser.role;
            users[socket.id].username = `[${specialUser.role}] ${username}`;
            console.log(`User ${socket.id} signed in as ${specialUser.role}.`);
            io.emit('update users', Object.values(users));
        } else {
            console.log(`Invalid sign-in attempt by ${socket.id}.`);
            socket.emit('sign in error', 'Invalid username or password');
        }
    });

    // Handle username updates
    socket.on('set username', (username) => {
        if (username) {
            users[socket.id].username = username;
            console.log(`User ${socket.id} updated their username to ${username}.`);
        } else {
            users[socket.id].username = users[socket.id].defaultUsername;
        }
        io.emit('update users', Object.values(users));
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        const user = users[socket.id] || {};
        const formattedMessage = {
            username: user.username,
            text: msg,
            role: user.role || null,
        };
        console.log(`Message from ${socket.id}: ${msg}`);
        messageHistory.push(formattedMessage);
        io.emit('chat message', formattedMessage);
    });

    // Handle private chat requests
    socket.on('request dm', (targetSocketId) => {
        const roomId = `DM${String(Math.floor(Math.random() * 1e15)).padStart(15, '0')}`;
        privateChats[roomId] = [socket.id, targetSocketId];
        io.to(targetSocketId).emit('dm request', { from: socket.id, roomId });
    });

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
        io.emit('chat message', { username: 'SERVERHOST', text: announcement, role: null });
        console.log('Announcement sent by admin.');
    });

    // Handle developer chat messages
    socket.on('join dev', (confirmed) => {
        if (confirmed && users[socket.id]?.role) {
            console.log(`User ${socket.id} joined Developer Chat.`);
            socket.emit('dev message', `Welcome to the Developer Chat!`);
        } else {
            console.log(`Unauthorized Developer Chat access attempt by ${socket.id}.`);
        }
    });

    socket.on('dev chat message', (msg) => {
        if (users[socket.id]?.role) {
            io.emit('dev chat message', {
                username: users[socket.id].username,
                text: msg,
            });
        } else {
            console.log(`Unauthorized Developer Chat message attempt by ${socket.id}.`);
        }
    });

    // Handle disconnections
    socket.on('disconnect', () => {
        console.log(`User disconnected: ${socket.id}`);
        delete users[socket.id];
        io.emit('update users', Object.values(users));
    });
});

// Serve static files
app.get('/DM:roomId', (req, res) => {
    res.sendFile(__dirname + '/public/private_chat.html');
});

app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html');
});

// Start the server
server.listen(3000, () => {
    console.log('Server running at http://localhost:3000');
});
