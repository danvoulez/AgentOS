/**
 * AgentOS Core Memory System
 * 
 * A unified memory system for the entire application,
 * enabling context preservation across all interactions,
 * platforms, and interfaces.
 */

const mongoose = require('mongoose');
const { EventEmitter } = require('events');

class Memory extends EventEmitter {
  constructor() {
    super();
    this.shortTermMemory = new Map();
    this.contextMap = new Map();
    this.entityProfiles = new Map();
    this.longTermStorage = null;
    this.initialized = false;
  }

  /**
   * Initialize the memory system and connect to long-term storage
   */
  async initialize(mongoConnection) {
    if (this.initialized) return;
    
    this.longTermStorage = mongoConnection;
    
    // Set up automatic cleanup
    setInterval(() => this.cleanup(), 3600000); // Cleanup every hour
    
    this.initialized = true;
    this.emit('initialized');
    
    return this;
  }

  /**
   * Get or create a context for any entity (user, group, system, etc.)
   * @param {String} entityId - Entity identifier
   * @param {String} entityType - Type of entity (user, group, system, etc.)
   * @returns {Object} The entity context
   */
  getContext(entityId, entityType = 'user') {
    const key = `${entityType}:${entityId}`;
    
    if (!this.contextMap.has(key)) {
      this.contextMap.set(key, {
        id: entityId,
        type: entityType,
        history: [],
        lastInteraction: Date.now(),
        metadata: {},
        state: 'idle'
      });
    }
    
    return this.contextMap.get(key);
  }

  /**
   * Add an event to an entity's history
   * @param {String} entityId - Entity identifier
   * @param {String} entityType - Type of entity
   * @param {String} eventType - Type of event
   * @param {Object} data - Event data
   * @param {Object} metadata - Additional event metadata
   */
  addEvent(entityId, entityType, eventType, data = {}, metadata = {}) {
    const context = this.getContext(entityId, entityType);
    
    const event = {
      entityId,
      entityType,
      eventType,
      data,
      timestamp: Date.now(),
      metadata
    };
    
    context.history.push(event);
    context.lastInteraction = Date.now();
    
    // Limit history size to prevent memory issues
    if (context.history.length > 200) {
      context.history = context.history.slice(-200);
    }
    
    this.emit('newEvent', event, context);
    return event;
  }

  /**
   * Store information about any entity
   * @param {String} entityId - Entity identifier
   * @param {String} entityType - Type of entity
   * @param {Object} profileData - Information to store
   */
  updateEntityProfile(entityId, entityType, profileData) {
    const key = `${entityType}:${entityId}`;
    const existingProfile = this.entityProfiles.get(key) || {};
    
    this.entityProfiles.set(key, {
      ...existingProfile,
      ...profileData,
      id: entityId,
      type: entityType,
      lastUpdated: Date.now()
    });
    
    this.emit('profileUpdated', entityId, entityType, this.entityProfiles.get(key));
  }

  /**
   * Retrieve stored entity profile
   * @param {String} entityId - Entity identifier
   * @param {String} entityType - Type of entity
   * @returns {Object} Entity profile or null if not found
   */
  getEntityProfile(entityId, entityType) {
    const key = `${entityType}:${entityId}`;
    return this.entityProfiles.get(key) || null;
  }

  /**
   * Store a memory item temporarily
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
   * Persist information to long-term storage
   * @param {String} collection - Storage collection name
   * @param {Object} data - Data to store
   * @returns {Promise<Object>} Stored document
   */
  async persistToLongTerm(collection, data) {
    if (!this.longTermStorage) {
      throw new Error('Long-term storage not initialized');
    }
    
    try {
      const model = this.longTermStorage.model(collection);
      const document = new model({
        ...data,
        timestamp: Date.now()
      });
      
      await document.save();
      this.emit('dataPersisted', collection, document);
      return document;
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Query information from long-term storage
   * @param {String} collection - Storage collection name
   * @param {Object} query - MongoDB query
   * @returns {Promise<Array>} Query results
   */
  async queryLongTerm(collection, query) {
    if (!this.longTermStorage) {
      throw new Error('Long-term storage not initialized');
    }
    
    try {
      const model = this.longTermStorage.model(collection);
      return await model.find(query).lean().exec();
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Clean up expired memories and old contexts
   */
  cleanup() {
    const now = Date.now();
    
    // Clean up short-term memory
    for (const [key, memory] of this.shortTermMemory.entries()) {
      if (memory.expiry < now) {
        this.shortTermMemory.delete(key);
      }
    }
    
    // Clean up very old contexts (older than 90 days)
    const ninetyDaysAgo = now - (90 * 24 * 60 * 60 * 1000);
    for (const [key, context] of this.contextMap.entries()) {
      if (context.lastInteraction < ninetyDaysAgo) {
        // Backup to long-term storage before deletion if needed
        this.emit('contextArchived', key, context);
        this.contextMap.delete(key);
      }
    }
  }
}

// Create a singleton instance
const memory = new Memory();

module.exports = memory;
