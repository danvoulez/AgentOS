/**
 * Memory Model
 * Handles the storage and retrieval of user interactions with Vox
 */

const mongoose = require('mongoose');
const Schema = mongoose.Schema;

/**
 * Memory Schema
 * Stores interactions between users and Vox
 */
const MemorySchema = new Schema({
  userId: {
    type: String,
    required: true,
    index: true
  },
  type: {
    type: String,
    enum: ['individual', 'collective'],
    default: 'individual'
  },
  content: {
    prompt: {
      type: String,
      required: true
    },
    response: {
      type: String,
      required: true
    }
  },
  metadata: {
    source: {
      type: String,
      enum: ['text', 'voice'],
      default: 'text'
    },
    timestamp: {
      type: Date,
      default: Date.now
    },
    context: {
      type: Object,
      default: {}
    }
  },
  importance: {
    type: Number,
    min: 1,
    max: 10,
    default: 5
  },
  tags: [{
    type: String
  }]
}, {
  timestamps: true
});

// Add text search index
MemorySchema.index({ 'content.prompt': 'text', 'content.response': 'text' });

/**
 * Find memories by user ID
 * @param {String} userId - User ID to search for
 * @returns {Promise} - Promise resolving to array of memories
 */
MemorySchema.statics.findByUser = function(userId) {
  return this.find({ userId }).sort({ 'metadata.timestamp': -1 });
};

/**
 * Find memories by content search
 * @param {String} searchTerm - Term to search for in prompts and responses
 * @returns {Promise} - Promise resolving to array of memories
 */
MemorySchema.statics.findByContent = function(searchTerm) {
  return this.find(
    { $text: { $search: searchTerm } },
    { score: { $meta: 'textScore' } }
  ).sort({ score: { $meta: 'textScore' } });
};

/**
 * Find collective memories
 * @returns {Promise} - Promise resolving to array of collective memories
 */
MemorySchema.statics.findCollective = function() {
  return this.find({ type: 'collective' }).sort({ importance: -1 });
};

module.exports = mongoose.model('Memory', MemorySchema);
