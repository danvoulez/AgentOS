/**
 * Vox Controller
 * Handles the business logic for text and voice command processing
 */

const fs = require('fs');
const { logger } = require('../../../common/config/logger');
const { AppError } = require('../../../common/utils/errorHandler');
const openaiHelper = require('../utils/openaiHelper');
const memoryManager = require('../utils/memoryManager');

/**
 * Process text commands
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 */
exports.processTextCommand = async (req, res, next) => {
  try {
    const { prompt, userId } = req.body;
    
    if (!prompt || !userId) {
      throw new AppError('Missing prompt or userId', 400, 'INVALID_REQUEST');
    }
    
    logger.info(`Processing text command for user ${userId}: ${prompt}`);
    
    const responseText = await openaiHelper.generateCompletion(prompt, {
      model: 'text-davinci-003',
      maxTokens: 150,
      temperature: 0.7
    });
    
    // Store the interaction in memory
    await memoryManager.createMemory(userId, prompt, responseText, {
      source: 'text',
      importance: 5
    });
    
    logger.info(`Generated response for user ${userId}: ${responseText}`);
    
    res.json({
      success: true,
      response: responseText
    });
  } catch (error) {
    logger.error(`Error processing text command: ${error.message}`);
    next(error);
  }
};

/**
 * Process voice commands
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 */
exports.processVoiceCommand = async (req, res, next) => {
  try {
    const { userId } = req.body;
    
    if (!req.file || !userId) {
      throw new AppError('Missing audio file or userId', 400, 'INVALID_REQUEST');
    }
    
    logger.info(`Processing voice command for user ${userId}`);
    
    // Transcribe audio using OpenAI Whisper API
    const transcription = await openaiHelper.transcribeAudio(
      fs.createReadStream(req.file.path),
      { model: 'whisper-1' }
    );
    
    logger.info(`Transcription for user ${userId}: ${transcription}`);
    
    // Generate response based on transcription
    const responseText = await openaiHelper.generateCompletion(transcription, {
      model: 'text-davinci-003',
      maxTokens: 150,
      temperature: 0.7
    });
    
    // Clean up temporary file
    fs.unlink(req.file.path, err => {
      if (err) logger.error(`Error deleting uploaded file: ${err.message}`);
    });
    
    // Store the interaction in memory
    await memoryManager.createMemory(userId, transcription, responseText, {
      source: 'voice',
      importance: 6
    });
    
    logger.info(`Generated response for user ${userId}: ${responseText}`);
    
    res.json({
      success: true,
      transcription,
      response: responseText
    });
  } catch (error) {
    logger.error(`Error processing voice command: ${error.message}`);
    
    // Clean up temporary file if it exists
    if (req.file && req.file.path) {
      fs.unlink(req.file.path, err => {
        if (err) logger.error(`Error deleting uploaded file: ${err.message}`);
      });
    }
    
    next(error);
  }
};
