/**
 * OpenAI Helper
 * Utility functions for interacting with OpenAI APIs
 */

const { Configuration, OpenAIApi } = require('openai');
const { logger } = require('../../../common/config/logger');

// Configure OpenAI API
const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY
});
const openai = new OpenAIApi(configuration);

/**
 * Generate a text completion using OpenAI
 * @param {String} prompt - Input prompt
 * @param {Object} options - Configuration options
 * @returns {Promise<String>} - Promise resolving to generated text
 */
exports.generateCompletion = async (prompt, options = {}) => {
  try {
    const {
      model = 'text-davinci-003',
      maxTokens = 150,
      temperature = 0.7,
      topP = 1,
      presencePenalty = 0,
      frequencyPenalty = 0
    } = options;
    
    logger.info(`Generating completion for prompt: "${prompt.substring(0, 50)}..."`);
    
    const completion = await openai.createCompletion({
      model,
      prompt,
      max_tokens: maxTokens,
      temperature,
      top_p: topP,
      presence_penalty: presencePenalty,
      frequency_penalty: frequencyPenalty
    });
    
    const responseText = completion.data.choices[0].text.trim();
    
    logger.info(`Generated completion: "${responseText.substring(0, 50)}..."`);
    
    return responseText;
  } catch (error) {
    logger.error(`Error generating completion: ${error.message}`);
    throw error;
  }
};

/**
 * Transcribe audio to text using OpenAI Whisper
 * @param {ReadStream} audioStream - Audio file read stream
 * @param {Object} options - Configuration options
 * @returns {Promise<String>} - Promise resolving to transcribed text
 */
exports.transcribeAudio = async (audioStream, options = {}) => {
  try {
    const {
      model = 'whisper-1',
      language = null,
      prompt = null
    } = options;
    
    logger.info('Transcribing audio file');
    
    const transcriptionOptions = {
      model
    };
    
    if (language) transcriptionOptions.language = language;
    if (prompt) transcriptionOptions.prompt = prompt;
    
    const transcriptionResponse = await openai.createTranscription(
      audioStream,
      model,
      prompt,
      'json',
      1,
      language
    );
    
    const transcription = transcriptionResponse.data.text;
    
    logger.info(`Transcription result: "${transcription.substring(0, 50)}..."`);
    
    return transcription;
  } catch (error) {
    logger.error(`Error transcribing audio: ${error.message}`);
    throw error;
  }
};

/**
 * Generate a chat completion using OpenAI
 * @param {Array} messages - Array of message objects
 * @param {Object} options - Configuration options
 * @returns {Promise<String>} - Promise resolving to generated text
 */
exports.generateChatCompletion = async (messages, options = {}) => {
  try {
    const {
      model = 'gpt-3.5-turbo',
      temperature = 0.7,
      topP = 1,
      maxTokens = 150
    } = options;
    
    logger.info(`Generating chat completion with ${messages.length} messages`);
    
    const chatCompletion = await openai.createChatCompletion({
      model,
      messages,
      temperature,
      top_p: topP,
      max_tokens: maxTokens
    });
    
    const responseText = chatCompletion.data.choices[0].message.content.trim();
    
    logger.info(`Generated chat completion: "${responseText.substring(0, 50)}..."`);
    
    return responseText;
  } catch (error) {
    logger.error(`Error generating chat completion: ${error.message}`);
    throw error;
  }
};
