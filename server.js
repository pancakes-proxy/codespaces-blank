const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files from the public directory
app.use(express.static('public'));

// Store usernames for connected clients
const users = {}; // Format: { socketId: username }

io.on('connection', (socket) => {
    console.log('A user connected:', socket.id);

    // Set a default username when the user connects
    users[socket.id] = "Anonymous";

    // Handle username updates from clients
    socket.on('set username', (username) => {
        users[socket.id] = username || "Anonymous"; // Update username or default to "Anonymous"
        console.log(`User ${socket.id} set their username to: ${users[socket.id]}`);
    });

    // Handle chat messages
    socket.on('chat message', (msg) => {
        const username = users[socket.id] || "Anonymous"; // Get the username for this socket
        const formattedMessage = `${username}: ${msg}`; // Format message as "username: message"
        io.emit('chat message', formattedMessage); // Broadcast the message to all clients
    });

    // Handle user disconnection
    socket.on('disconnect', () => {
        console.log('A user disconnected:', socket.id);
        delete users[socket.id]; // Remove the user from the list
    });
});

const { exec } = require('child_process');

// Function to run idle.sh
function runIdleScript() {
    exec('bash idle.sh', (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing idle.sh: ${error.message}`);
            return;
        }
        if (stderr) {
            console.error(`Script error: ${stderr}`);
            return;
        }
        console.log(`Idle script output: ${stdout}`);
    });
}

// Schedule idle.sh to run every 5 minutes (300,000 ms)
setInterval(runIdleScript, 300000); // Adjust the interval as needed


// Start the server
server.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
