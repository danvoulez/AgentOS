/**
 * Memory Manager
 * Handles the storage and retrieval of user interactions with Vox
 */

const Memory = require('../models/memory');
const { logger } = require('../../../common/config/logger');

/**
 * Create a new memory entry
 * @param {String} userId - User ID
 * @param {String} prompt - User input
 * @param {String} response - Vox response
 * @param {Object} options - Additional options
 * @returns {Promise} - Promise resolving to created memory
 */
exports.createMemory = async (userId, prompt, response, options = {}) => {
  try {
    const {
      type = 'individual',
      source = 'text',
      importance = 5,
      tags = [],
      context = {}
    } = options;
    
    const memory = new Memory({
      userId,
      type,
      content: {
        prompt,
        response
      },
      metadata: {
        source,
        context
      },
      importance,
      tags
    });
    
    await memory.save();
    logger.info(`Memory created for user ${userId}`);
    
    return memory;
  } catch (error) {
    logger.error(`Error creating memory: ${error.message}`);
    throw error;
  }
};

/**
 * Retrieve memories for a specific user
 * @param {String} userId - User ID
 * @param {Number} limit - Maximum number of memories to retrieve
 * @returns {Promise} - Promise resolving to array of memories
 */
exports.getUserMemories = async (userId, limit = 10) => {
  try {
    const memories = await Memory.findByUser(userId).limit(limit);
    logger.info(`Retrieved ${memories.length} memories for user ${userId}`);
    
    return memories;
  } catch (error) {
    logger.error(`Error retrieving user memories: ${error.message}`);
    throw error;
  }
};

/**
 * Search memories by content
 * @param {String} searchTerm - Term to search for
 * @param {String} userId - Optional user ID to filter by
 * @returns {Promise} - Promise resolving to array of memories
 */
exports.searchMemories = async (searchTerm, userId = null) => {
  try {
    let query = Memory.findByContent(searchTerm);
    
    if (userId) {
      query = query.where('userId').equals(userId);
    }
    
    const memories = await query.exec();
    logger.info(`Found ${memories.length} memories matching "${searchTerm}"`);
    
    return memories;
  } catch (error) {
    logger.error(`Error searching memories: ${error.message}`);
    throw error;
  }
};

/**
 * Retrieve collective memories
 * @param {Number} limit - Maximum number of memories to retrieve
 * @returns {Promise} - Promise resolving to array of collective memories
 */
exports.getCollectiveMemories = async (limit = 10) => {
  try {
    const memories = await Memory.findCollective().limit(limit);
    logger.info(`Retrieved ${memories.length} collective memories`);
    
    return memories;
  } catch (error) {
    logger.error(`Error retrieving collective memories: ${error.message}`);
    throw error;
  }
};

/**
 * Update memory importance
 * @param {String} memoryId - Memory ID
 * @param {Number} importance - New importance value (1-10)
 * @returns {Promise} - Promise resolving to updated memory
 */
exports.updateImportance = async (memoryId, importance) => {
  try {
    const memory = await Memory.findByIdAndUpdate(
      memoryId,
      { importance },
      { new: true }
    );
    
    if (!memory) {
      throw new Error(`Memory with ID ${memoryId} not found`);
    }
    
    logger.info(`Updated importance for memory ${memoryId} to ${importance}`);
    
    return memory;
  } catch (error) {
    logger.error(`Error updating memory importance: ${error.message}`);
    throw error;
  }
};

/**
 * Delete a memory
 * @param {String} memoryId - Memory ID
 * @returns {Promise} - Promise resolving to deletion result
 */
exports.deleteMemory = async (memoryId) => {
  try {
    const result = await Memory.findByIdAndDelete(memoryId);
    
    if (!result) {
      throw new Error(`Memory with ID ${memoryId} not found`);
    }
    
    logger.info(`Deleted memory ${memoryId}`);
    
    return { success: true, id: memoryId };
  } catch (error) {
    logger.error(`Error deleting memory: ${error.message}`);
    throw error;
  }
};
