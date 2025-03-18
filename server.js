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
let messageHistory = []; // Store messages
const users = {}; // { socketId: { username, defaultUsername, isAvailable, role } }
const privateChats = {}; // { roomId: [socketId1, socketId2] }
const SPECIAL_USERS = [
    { username: 'zac : D', password: 'zaxc1122', role: 'Server Owner' },
    { username: 'lily', password: 'lily1', role: 'Developer' },
    { username: 'izzy', password: 'izzy', role: 'Server Owner' },
    { username: 'JW', password: 'JW', role: 'Developer' },
    { username: 'issac', password: 'issac1', role: 'Server Owner' },
    { username: 'Milly<3', password: 'milly', role: 'Developer' },
];

// Server state for multi-server support
let servers = {
    "default": {
        name: "Default Server",
        users: {},
        chatrooms: {
            "general": [], // Default chatroom
            "random": [], // Additional chatroom
        },
    },
};

// Helper function to update server list
const updateServerList = () => {
    io.emit('update servers', Object.keys(servers));
};

// Handle connections
io.on('connection', (socket) => {
    console.log(`User connected: ${socket.id}`);

    // Assign default server and username
    const defaultServer = "default";
    const defaultUsername = `User${Math.floor(Math.random() * 10000)}`;
    users[socket.id] = {
        username: defaultUsername,
        defaultUsername,
        isAvailable: true,
        role: null,
    };
    servers[defaultServer].users[socket.id] = { ...users[socket.id] };

    // Notify all clients of the updated server list
    socket.emit('update servers', Object.keys(servers));
    socket.emit('update users', servers[defaultServer].users);

    // Handle special user sign-in
    socket.on('sign in', ({ username, password }) => {
        const specialUser = SPECIAL_USERS.find(
            user => user.username === username && user.password === password
        );
        if (specialUser) {
            users[socket.id].role = specialUser.role;
            users[socket.id].username = `[${specialUser.role}] ${username}`;
            servers[defaultServer].users[socket.id] = { ...users[socket.id] };

            console.log(`User ${socket.id} signed in as ${specialUser.role}.`);
            io.emit('update users', servers[defaultServer].users);
        } else {
            console.log(`Invalid sign-in attempt by ${socket.id}.`);
            socket.emit('sign in error', 'Invalid username or password');
        }
    });

    // Handle server creation
    socket.on('create server', (serverName) => {
        if (!serverName || servers[serverName]) {
            socket.emit('server error', 'Server already exists or invalid name.');
            return;
        }

        servers[serverName] = {
            name: serverName,
            users: {}, // New user list
            chatrooms: {
                "general": [], // Default chatroom
            },
        };
        console.log(`Server created: ${serverName}`);
        updateServerList();
    });

    // Handle joining a server
    socket.on('join server', (serverName) => {
        if (!servers[serverName]) {
            socket.emit('server error', 'Server does not exist.');
            return;
        }

        // Add user to the server
        servers[serverName].users[socket.id] = users[socket.id];
        console.log(`User ${socket.id} joined server: ${serverName}`);
        socket.emit('server joined', serverName);
        updateUsersInServer(serverName);
    });

    // Helper to update user list in a specific server
    const updateUsersInServer = (serverName) => {
        const usersInServer = Object.values(servers[serverName].users);
        io.emit('update server users', { serverName, users: usersInServer });
    };

    // Handle general chat messages
    socket.on('chat message', (msg) => {
        const user = users[socket.id] || {};
        const formattedMessage = {
            username: user.username || `User${socket.id}`,
            text: msg,
            role: user.role || null,
        };

        console.log(`Message from ${socket.id}: ${msg}`);
        messageHistory.push(formattedMessage);
        io.emit('chat message', formattedMessage);
    });

    // Handle sending messages in server chatrooms
    socket.on('send message', ({ serverName, chatroom, message }) => {
        if (!servers[serverName] || !servers[serverName].chatrooms[chatroom]) {
            socket.emit('server error', 'Invalid server or chatroom.');
            return;
        }

        const user = servers[serverName].users[socket.id];
        const formattedMessage = {
            username: user.username,
            text: message,
            timestamp: new Date().toISOString(),
        };

        servers[serverName].chatrooms[chatroom].push(formattedMessage);
        io.emit('new message', { serverName, chatroom, message: formattedMessage });
    });

    // Handle direct message requests
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

    // Handle disconnections
    socket.on('disconnect', () => {
        for (const serverName in servers) {
            if (servers[serverName].users[socket.id]) {
                delete servers[serverName].users[socket.id];
                updateUsersInServer(serverName);
                break;
            }
        }
        console.log(`User disconnected: ${socket.id}`);
    });
});

// Dynamic route for private chat rooms
app.get('/DM:roomId', (req, res) => {
    const { roomId } = req.params;
    res.sendFile(__dirname + '/public/private_chat.html');
});

// Serve admin page
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html');
});

// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
