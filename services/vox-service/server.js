/**
 * Vox Hybrid Service - Central Guardian of AgentOS
 * Processes text and voice commands, integrating with OpenAI APIs
 */

const express = require('express');
const bodyParser = require('body-parser');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const morgan = require('morgan');
const compression = require('compression');
const { Configuration, OpenAIApi } = require('openai');
const { logger } = require('../../common/config/logger');
const { errorHandler, requestLogger } = require('../../common/middleware');

// Load environment variables
require('dotenv').config();

const app = express();

// Production middleware
app.use(compression());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(morgan('combined', {
  stream: fs.createWriteStream(path.join(__dirname, '../../logs/vox.log'), { flags: 'a' })
}));
app.use(requestLogger);

// Serve static files (frontend)
app.use(express.static(path.join(__dirname, 'public')));

// Configure multer for voice uploads
const upload = multer({ 
  dest: path.join(__dirname, 'uploads/'),
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

// Configure OpenAI API
const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY
});
const openai = new OpenAIApi(configuration);

// Import routes
const voxRoutes = require('./routes');

// Apply routes
app.use('/api/vox', voxRoutes);

// Error handling middleware
app.use(errorHandler);

// Start server
const PORT = process.env.VOX_PORT || 3030;
const server = app.listen(PORT, () => {
  logger.info(`Vox hybrid service running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received. Closing HTTP server.');
  server.close(() => {
    logger.info('HTTP server closed.');
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received. Closing HTTP server.');
  server.close(() => {
    logger.info('HTTP server closed.');
  });
});

module.exports = app;
