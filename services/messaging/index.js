const express = require('express');
const cors = require('cors');
const routes = require('./routes');
const { connectToDatabase } = require('../../src/database/config/mongodb');

const app = express();
const PORT = process.env.MESSAGING_SERVICE_PORT || 3003;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/messaging', routes);

// Health check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'messaging-service' });
});

// Connect to database and start server
async function startServer() {
  try {
    await connectToDatabase();
    app.listen(PORT, () => {
      console.log(`Messaging service running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start messaging service:', error);
    process.exit(1);
  }
}

startServer();
