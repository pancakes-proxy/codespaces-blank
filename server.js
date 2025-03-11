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

// Store usernames for connected users
const users = {}; // Format: { socketId: username }

// Serve the admin page
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/public/admin.html');
});

// Handle socket connections
io.on('connection', (socket) => {
    console.log('A user connected:', socket.id);

    // Set a default username when a user connects
    users[socket.id] = "Anonymous";

    // Send lock status and message history to the connected client
    socket.emit('chat lock status', isChatLocked);
    socket.emit('chat history', messageHistory);

    // Handle username updates
    socket.on('set username', (username) => {
        users[socket.id] = username || "Anonymous"; // Update username or default to "Anonymous"
        console.log(`User ${socket.id} set their username to: ${users[socket.id]}`);
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        if (!isChatLocked) {
            const username = users[socket.id] || "Anonymous"; // Get the sender's username
            const formattedMessage = `${username}: ${msg}`; // Format as "username: message"
            messageHistory.push(formattedMessage); // Add to message history
            io.emit('chat message', formattedMessage); // Broadcast to all clients
        } else {
            socket.emit('chat locked'); // Notify sender if chat is locked
        }
    });

    // Handle admin actions
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
        console.log('A user disconnected:', socket.id);
        delete users[socket.id]; // Remove the user from the list
    });
});

// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});

