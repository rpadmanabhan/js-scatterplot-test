
const express = require('express');
const path = require('path');


const server_filename = path.resolve(__filename)
const server_dirname = path.dirname(server_filename);

var app = express();

// Middleware to serve static files from 'node_modules'
app.use('/node_modules', express.static(path.join(server_dirname, 'node_modules'), {
}));

// Middleware to serve static files from 'dist' with the same headers
app.use(express.static(path.join(server_dirname, 'dist'), {
}));


// Other server configurations...
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}`);
});


