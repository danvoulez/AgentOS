/**
 * VoxAgent Advanced Memory System
 * 
 * This module provides a centralized memory storage for VoxAgent to maintain context
 * across different messaging platforms and interaction methods.
 * 
 * Enhanced features:
 * - Semantic indexing for message retrieval
 * - Intelligent categorization of memories
 * - Controlled forgetting system with relevance scoring
 * - Importance-based memory retention
 */

const mongoose = require('mongoose');
const { EventEmitter } = require('events');
const natural = require('natural'); // Natural language processing library
const { TfIdf } = natural; // Term frequency-inverse document frequency for semantic indexing

class VoxMemory extends EventEmitter {
  constructor() {
    super();
    this.shortTermMemory = new Map();
    this.conversationContexts = new Map();
    this.userProfiles = new Map();
    this.groupContexts = new Map();
    
    // Semantic Memory Components
    this.semanticIndex = new TfIdf();
    this.documentMap = new Map(); // Maps document IDs to actual messages/memories
    this.documentCounter = 0;
    
    // Memory Categorization
    this.categories = {
      CRITICAL: { weight: 1.0, decayRate: 0.0001 }, // Almost no decay for critical info
      IMPORTANT: { weight: 0.8, decayRate: 0.001 },
      STANDARD: { weight: 0.5, decayRate: 0.01 },
      TRANSIENT: { weight: 0.2, decayRate: 0.1 }
    };
    
    // Memory Relevance Tracking
    this.relevanceScores = new Map(); // Tracks relevance of each memory item
  }

  /**
   * Get or create a conversation context for a specific user or group
   * @param {String} id - User or group ID
   * @param {String} type - 'user' or 'group'
   * @returns {Object} The conversation context
   */
  getContext(id, type = 'user') {
    const key = `${type}:${id}`;
    if (!this.conversationContexts.has(key)) {
      this.conversationContexts.set(key, {
        id,
        type,
        history: [],
        lastInteraction: Date.now(),
        metadata: {},
        state: 'idle'
      });
    }
    return this.conversationContexts.get(key);
  }

  /**
   * Add a message to conversation history with semantic indexing and categorization
   * @param {String} senderId - User or group ID of the sender
   * @param {String} senderType - 'user' or 'group'
   * @param {String} content - Message content
   * @param {Object} metadata - Additional message metadata
   * @param {String} category - Memory category (CRITICAL, IMPORTANT, STANDARD, TRANSIENT)
   */
  addMessage(senderId, senderType, content, metadata = {}, category = 'STANDARD') {
    const context = this.getContext(senderId, senderType);
    const docId = `msg_${++this.documentCounter}`;
    
    // Create the message with additional semantic metadata
    const message = {
      id: docId,
      senderId,
      senderType,
      content,
      timestamp: Date.now(),
      metadata,
      category: this.categories[category] ? category : 'STANDARD',
      relevanceScore: this.categories[category]?.weight || this.categories['STANDARD'].weight
    };
    
    // Add to context history
    context.history.push(message);
    context.lastInteraction = Date.now();
    
    // Index the message content for semantic retrieval
    this.indexMessageSemantics(docId, content, senderId, senderType);
    
    // Store relevance score
    this.relevanceScores.set(docId, message.relevanceScore);
    
    // Apply intelligent forgetting - keep relevant messages based on relevance scores
    if (context.history.length > 100) {
      this.intelligentPrune(context);
    }
    
    this.emit('newMessage', message, context);
    return message;
  }
  
  /**
   * Index message content for semantic search
   * @param {String} docId - Document ID
   * @param {String} content - Message content
   * @param {String} senderId - Sender ID
   * @param {String} senderType - Sender type
   */
  indexMessageSemantics(docId, content, senderId, senderType) {
    // Add document to semantic index
    this.semanticIndex.addDocument(content, docId);
    
    // Map document ID to original content and metadata
    this.documentMap.set(docId, {
      content,
      senderId,
      senderType,
      timestamp: Date.now()
    });
  }
  
  /**
   * Intelligently prune conversation history based on relevance scores
   * @param {Object} context - Conversation context
   */
  intelligentPrune(context) {
    // Apply decay to all messages based on their category and age
    const now = Date.now();
    
    // Update relevance scores with decay factor
    context.history.forEach(message => {
      if (!message.id) return; // Skip messages without ID
      
      const age = (now - message.timestamp) / (1000 * 60 * 60); // Age in hours
      const category = this.categories[message.category] || this.categories.STANDARD;
      const decayFactor = Math.exp(-category.decayRate * age);
      const newScore = this.relevanceScores.get(message.id) * decayFactor;
      
      this.relevanceScores.set(message.id, newScore);
    });
    
    // Sort by relevance score and keep top messages
    context.history.sort((a, b) => {
      const scoreA = this.relevanceScores.get(a.id) || 0;
      const scoreB = this.relevanceScores.get(b.id) || 0;
      return scoreB - scoreA; // Descending order
    });
    
    // Keep top 100 most relevant messages
    context.history = context.history.slice(0, 100);
  }

  /**
   * Update the user profile with new information
   * @param {String} userId - User ID
   * @param {Object} profileData - Profile information to update
   */
  updateUserProfile(userId, profileData) {
    const existingProfile = this.userProfiles.get(userId) || {};
    this.userProfiles.set(userId, {
      ...existingProfile,
      ...profileData,
      lastUpdated: Date.now()
    });
  }

  /**
   * Retrieve stored user profile
   * @param {String} userId - User ID
   * @returns {Object} User profile or null if not found
   */
  getUserProfile(userId) {
    return this.userProfiles.get(userId) || null;
  }

  /**
   * Associate a temporary memory item with a key
   * @param {String} key - Memory key
   * @param {any} value - Memory value
   * @param {Number} ttl - Time to live in milliseconds (default: 1 hour)
   */
  remember(key, value, ttl = 3600000) {
    this.shortTermMemory.set(key, {
      value,
      expiry: Date.now() + ttl
    });
    
    // Schedule cleanup
    setTimeout(() => {
      if (this.shortTermMemory.has(key)) {
        this.shortTermMemory.delete(key);
      }
    }, ttl);
  }

  /**
   * Retrieve a memory item by key
   * @param {String} key - Memory key
   * @returns {any} Memory value or null if not found or expired
   */
  recall(key) {
    if (!this.shortTermMemory.has(key)) return null;
    
    const memory = this.shortTermMemory.get(key);
    if (memory.expiry < Date.now()) {
      this.shortTermMemory.delete(key);
      return null;
    }
    
    return memory.value;
  }

  /**
   * Store memory in the database for long-term persistence with semantic metadata
   * @param {String} contextId - Context ID (user or group)
   * @param {String} memoryType - Type of memory to store
   * @param {Object} data - Memory data to store
   * @param {String} category - Memory category (CRITICAL, IMPORTANT, STANDARD, TRANSIENT)
   */
  async persistMemory(contextId, memoryType, data, category = 'STANDARD') {
    // Enhance data with semantic metadata
    const enrichedData = {
      ...data,
      category,
      relevanceScore: this.categories[category]?.weight || this.categories['STANDARD'].weight,
      timestamp: Date.now(),
      semanticMetadata: {
        createdAt: Date.now(),
        lastAccessed: Date.now(),
        accessCount: 1
      }
    };
    
    // This would connect to the MongoDB database to store long-term memories
    // Implementation will use the MongoDB connection
    this.emit('persistMemory', { contextId, memoryType, data: enrichedData });
    
    return enrichedData;
  }
  
  /**
   * Search for semantically similar messages
   * @param {String} query - Search query
   * @param {Number} limit - Maximum number of results
   * @returns {Array} Array of semantically similar messages
   */
  semanticSearch(query, limit = 5) {
    const results = [];
    
    // Get similar documents based on TF-IDF
    this.semanticIndex.tfidfs(query, (i, measure, docId) => {
      if (this.documentMap.has(docId)) {
        const doc = this.documentMap.get(docId);
        results.push({
          docId,
          similarity: measure,
          content: doc.content,
          metadata: doc,
          relevanceScore: this.relevanceScores.get(docId) || 0
        });
      }
    });
    
    // Sort by similarity score
    results.sort((a, b) => b.similarity - a.similarity);
    
    // Record access to increase relevance
    results.slice(0, limit).forEach(result => {
      if (this.relevanceScores.has(result.docId)) {
        // Boost relevance when retrieved
        const currentScore = this.relevanceScores.get(result.docId);
        this.relevanceScores.set(result.docId, currentScore * 1.2); // Boost by 20%
      }
    });
    
    return results.slice(0, limit);
  }
  
  /**
   * Categorize memory based on content and context
   * @param {String} content - Message content
   * @param {Object} metadata - Additional metadata
   * @returns {String} Detected category
   */
  categorizeMemory(content, metadata = {}) {
    // Simple keyword-based categorization - this would be enhanced with ML in production
    const lowercaseContent = content.toLowerCase();
    
    // Keywords suggesting critical information
    const criticalKeywords = ['urgent', 'emergency', 'critical', 'immediately', 'asap'];
    if (criticalKeywords.some(keyword => lowercaseContent.includes(keyword))) {
      return 'CRITICAL';
    }
    
    // Keywords suggesting important information
    const importantKeywords = ['important', 'significant', 'deadline', 'required', 'needed'];
    if (importantKeywords.some(keyword => lowercaseContent.includes(keyword))) {
      return 'IMPORTANT';
    }
    
    // Keywords suggesting transient information
    const transientKeywords = ['fyi', 'just so you know', 'by the way', 'btw'];
    if (transientKeywords.some(keyword => lowercaseContent.includes(keyword))) {
      return 'TRANSIENT';
    }
    
    // Default category
    return 'STANDARD';
  }

  /**
   * Clean up expired memories and old conversation contexts
   * Uses intelligent forgetting with category-based retention
   */
  cleanup() {
    const now = Date.now();
    
    // Clean up short-term memory
    for (const [key, memory] of this.shortTermMemory.entries()) {
      if (memory.expiry < now) {
        this.shortTermMemory.delete(key);
      }
    }
    
    // Clean up conversation contexts based on relevance and category
    for (const [contextKey, context] of this.conversationContexts.entries()) {
      // Apply intelligent forgetting to each context
      if (context.history && context.history.length > 0) {
        this.intelligentPrune(context);
      }
      
      // Remove very old contexts (older than 30 days for standard items)
      const thirtyDaysAgo = now - (30 * 24 * 60 * 60 * 1000);
      if (context.lastInteraction < thirtyDaysAgo) {
        // Before removing, check if there are any CRITICAL memories to keep
        const hasCriticalMemories = context.history.some(msg => 
          msg.category === 'CRITICAL' && this.relevanceScores.get(msg.id) > 0.5
        );
        
        if (!hasCriticalMemories) {
          this.conversationContexts.delete(contextKey);
          
          // Clean up associated document mappings and relevance scores
          context.history.forEach(msg => {
            if (msg.id) {
              this.documentMap.delete(msg.id);
              this.relevanceScores.delete(msg.id);
            }
          });
        }
      }
    }
    
    // Emit cleanup event with statistics
    this.emit('cleanup', {
      timestamp: now,
      shortTermMemorySize: this.shortTermMemory.size,
      conversationContextsSize: this.conversationContexts.size,
      semanticIndexSize: this.documentMap.size
    });
  }
  
  /**
   * Get memory statistics and health metrics
   * @returns {Object} Memory system statistics
   */
  getMemoryStats() {
    const categoryCounts = {};
    let totalRelevance = 0;
    let messageCount = 0;
    
    // Initialize category counts
    Object.keys(this.categories).forEach(category => {
      categoryCounts[category] = 0;
    });
    
    // Count items by category and calculate average relevance
    for (const context of this.conversationContexts.values()) {
      if (context.history) {
        context.history.forEach(msg => {
          messageCount++;
          if (msg.category) {
            categoryCounts[msg.category] = (categoryCounts[msg.category] || 0) + 1;
          }
          if (msg.id && this.relevanceScores.has(msg.id)) {
            totalRelevance += this.relevanceScores.get(msg.id);
          }
        });
      }
    }
    
    return {
      timestamp: Date.now(),
      shortTermMemorySize: this.shortTermMemory.size,
      conversationContextsCount: this.conversationContexts.size,
      semanticIndexSize: this.documentMap.size,
      totalMessages: messageCount,
      averageRelevance: messageCount > 0 ? totalRelevance / messageCount : 0,
      categoryCounts
    };
  }
}

// Create a singleton instance
const voxMemory = new VoxMemory();

// Run cleanup every hour
setInterval(() => voxMemory.cleanup(), 3600000);

module.exports = voxMemory;
