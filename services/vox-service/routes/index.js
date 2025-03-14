/**
 * Vox Service Routes
 * Defines all endpoints for the Vox hybrid service
 */

const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const voxController = require('../controllers/voxController');

// Configure multer for voice uploads
const upload = multer({ 
  dest: path.join(__dirname, '../uploads/'),
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

/**
 * @route   POST /api/vox/text
 * @desc    Process text commands
 * @access  Public
 */
router.post('/text', voxController.processTextCommand);

/**
 * @route   POST /api/vox/voice
 * @desc    Process voice commands (audio file upload)
 * @access  Public
 */
router.post('/voice', upload.single('audio'), voxController.processVoiceCommand);

/**
 * @route   GET /api/vox/health
 * @desc    Health check endpoint
 * @access  Public
 */
router.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'vox-hybrid' });
});

module.exports = router;
