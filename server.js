socket.on('chat message', (msg) => {
    console.log(`Message received: ${msg}`);
    io.emit('chat message', msg);
});
