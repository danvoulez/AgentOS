/**
 * Vox Controller Tests
 */

const { processTextCommand, processVoiceCommand } = require('../controllers/voxController');
const openaiHelper = require('../utils/openaiHelper');
const memoryManager = require('../utils/memoryManager');
const fs = require('fs');

// Mock dependencies
jest.mock('../utils/openaiHelper');
jest.mock('../utils/memoryManager');
jest.mock('fs');
jest.mock('../../../common/config/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn()
  }
}));

describe('Vox Controller', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('processTextCommand', () => {
    it('should process text command and return response', async () => {
      // Arrange
      const req = {
        body: {
          prompt: 'Hello Vox',
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();
      
      const mockResponse = 'Hello! How can I help you today?';
      openaiHelper.generateCompletion.mockResolvedValue(mockResponse);
      memoryManager.createMemory.mockResolvedValue({ _id: 'memory123' });

      // Act
      await processTextCommand(req, res, next);

      // Assert
      expect(openaiHelper.generateCompletion).toHaveBeenCalledWith('Hello Vox', expect.any(Object));
      expect(memoryManager.createMemory).toHaveBeenCalledWith('user123', 'Hello Vox', mockResponse, expect.any(Object));
      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        response: mockResponse
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should handle errors and pass to next middleware', async () => {
      // Arrange
      const req = {
        body: {
          prompt: 'Hello Vox',
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();
      
      const error = new Error('OpenAI API error');
      openaiHelper.generateCompletion.mockRejectedValue(error);

      // Act
      await processTextCommand(req, res, next);

      // Assert
      expect(next).toHaveBeenCalledWith(error);
      expect(res.status).not.toHaveBeenCalled();
      expect(res.json).not.toHaveBeenCalled();
    });

    it('should validate required fields', async () => {
      // Arrange
      const req = {
        body: {
          // Missing prompt
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();

      // Act
      await processTextCommand(req, res, next);

      // Assert
      expect(next).toHaveBeenCalled();
      expect(next.mock.calls[0][0].message).toContain('prompt is required');
      expect(openaiHelper.generateCompletion).not.toHaveBeenCalled();
    });
  });

  describe('processVoiceCommand', () => {
    it('should process voice command and return response', async () => {
      // Arrange
      const req = {
        file: {
          path: '/tmp/audio.mp3'
        },
        body: {
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();
      
      const mockTranscription = 'Hello Vox from voice';
      const mockResponse = 'I heard you! How can I help?';
      
      fs.createReadStream.mockReturnValue('audioStream');
      openaiHelper.transcribeAudio.mockResolvedValue(mockTranscription);
      openaiHelper.generateCompletion.mockResolvedValue(mockResponse);
      memoryManager.createMemory.mockResolvedValue({ _id: 'memory123' });
      fs.unlink.mockImplementation((path, callback) => callback(null));

      // Act
      await processVoiceCommand(req, res, next);

      // Assert
      expect(openaiHelper.transcribeAudio).toHaveBeenCalledWith('audioStream', expect.any(Object));
      expect(openaiHelper.generateCompletion).toHaveBeenCalledWith(mockTranscription, expect.any(Object));
      expect(memoryManager.createMemory).toHaveBeenCalledWith('user123', mockTranscription, mockResponse, expect.any(Object));
      expect(fs.unlink).toHaveBeenCalledWith('/tmp/audio.mp3', expect.any(Function));
      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        transcription: mockTranscription,
        response: mockResponse
      });
    });

    it('should handle errors and pass to next middleware', async () => {
      // Arrange
      const req = {
        file: {
          path: '/tmp/audio.mp3'
        },
        body: {
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();
      
      fs.createReadStream.mockReturnValue('audioStream');
      const error = new Error('Transcription error');
      openaiHelper.transcribeAudio.mockRejectedValue(error);
      fs.unlink.mockImplementation((path, callback) => callback(null));

      // Act
      await processVoiceCommand(req, res, next);

      // Assert
      expect(next).toHaveBeenCalledWith(error);
      expect(fs.unlink).toHaveBeenCalledWith('/tmp/audio.mp3', expect.any(Function));
    });

    it('should validate required file upload', async () => {
      // Arrange
      const req = {
        // Missing file
        body: {
          userId: 'user123'
        }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };
      const next = jest.fn();

      // Act
      await processVoiceCommand(req, res, next);

      // Assert
      expect(next).toHaveBeenCalled();
      expect(next.mock.calls[0][0].message).toContain('Audio file is required');
      expect(openaiHelper.transcribeAudio).not.toHaveBeenCalled();
    });
  });
});
