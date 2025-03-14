/**
 * WhatsApp Manager for AgentOS
 * 
 * Provides a unified interface for both WhatsApp clients:
 * - Baileys for group interactions
 * - Web.js for direct messaging
 */

const { EventEmitter } = require('events');
const path = require('path');
const fs = require('fs');
const BaileysWhatsAppClient = require('./baileys/client');
const WebJsWhatsAppClient = require('./webjs/client');
const { isGroupId, formatPhoneNumber } = require('./common/utils');
const VoxMemory = require('../../core/Memory');

class WhatsAppManager extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      sessionsDir: options.sessionsDir || path.join(process.cwd(), '.whatsapp-sessions'),
      mediaDir: options.mediaDir || path.join(process.cwd(), 'media'),
      ...options
    };
    
    // Clients collection
    this.baileyClients = new Map();
    this.webjsClients = new Map();
    
    // Ensure directories exist
    if (!fs.existsSync(this.options.sessionsDir)) {
      fs.mkdirSync(this.options.sessionsDir, { recursive: true });
    }
    
    if (!fs.existsSync(this.options.mediaDir)) {
      fs.mkdirSync(this.options.mediaDir, { recursive: true });
    }
    
    // Save to memory
    VoxMemory.updateEntityProfile(
      'whatsapp_manager',
      'system',
      {
        type: 'whatsapp_manager',
        initialized: new Date(),
        baileyClients: 0,
        webjsClients: 0,
        status: 'initialized'
      }
    );
  }
  
  /**
   * Create a new Baileys client for group interactions
   * @param {String} clientId - Client identifier
   * @param {Object} options - Client options
   * @returns {Promise<BaileysWhatsAppClient>} The client instance
   */
  async createBaileyClient(clientId, options = {}) {
    if (this.baileyClients.has(clientId)) {
      return this.baileyClients.get(clientId);
    }
    
    try {
      const client = new BaileysWhatsAppClient({
        clientId,
        sessionsDir: this.options.sessionsDir,
        ...options
      });
      
      // Set up event forwarding
      this._setupClientEvents(client, clientId, 'bailey');
      
      // Initialize the client
      await client.initialize();
      
      // Store the client
      this.baileyClients.set(clientId, client);
      
      // Update manager profile
      VoxMemory.updateEntityProfile(
        'whatsapp_manager',
        'system',
        {
          baileyClients: this.baileyClients.size,
          lastClientAdded: new Date(),
          lastClientType: 'bailey'
        }
      );
      
      return client;
    } catch (error) {
      console.error(`Error creating Baileys client ${clientId}:`, error);
      throw error;
    }
  }
  
  /**
   * Create a new Web.js client for direct messaging
   * @param {String} clientId - Client identifier
   * @param {Object} options - Client options
   * @returns {Promise<WebJsWhatsAppClient>} The client instance
   */
  async createWebJsClient(clientId, options = {}) {
    if (this.webjsClients.has(clientId)) {
      return this.webjsClients.get(clientId);
    }
    
    try {
      const client = new WebJsWhatsAppClient({
        clientId,
        sessionsDir: this.options.sessionsDir,
        ...options
      });
      
      // Set up event forwarding
      this._setupClientEvents(client, clientId, 'webjs');
      
      // Initialize the client
      await client.initialize();
      
      // Store the client
      this.webjsClients.set(clientId, client);
      
      // Update manager profile
      VoxMemory.updateEntityProfile(
        'whatsapp_manager',
        'system',
        {
          webjsClients: this.webjsClients.size,
          lastClientAdded: new Date(),
          lastClientType: 'webjs'
        }
      );
      
      return client;
    } catch (error) {
      console.error(`Error creating Web.js client ${clientId}:`, error);
      throw error;
    }
  }
  
  /**
   * Set up event forwarding from a client
   * @param {Object} client - Client instance
   * @param {String} clientId - Client identifier
   * @param {String} type - Client type ('bailey' or 'webjs')
   */
  _setupClientEvents(client, clientId, type) {
    // Forward ready event
    client.on('ready', (data) => {
      this.emit('client_ready', { 
        clientId, 
        type, 
        data 
      });
    });
    
    // Forward QR event
    client.on('qr', (qr) => {
      this.emit('client_qr', { 
        clientId, 
        type, 
        qr 
      });
    });
    
    // Forward disconnect event
    client.on('disconnected', (reason) => {
      this.emit('client_disconnected', { 
        clientId, 
        type, 
        reason 
      });
    });
    
    // Forward vox-process event
    client.on('vox-process', (processData) => {
      this.emit('message_for_vox', {
        ...processData,
        clientId,
        clientType: type
      });
    });
    
    // Client-specific events
    if (type === 'bailey') {
      // Forward group-participants event
      client.on('group-participants', (update) => {
        this.emit('group_participants_update', {
          ...update,
          clientId
        });
      });
    }
  }
  
  /**
   * Get the appropriate client for a given recipient
   * @param {String} to - Recipient ID
   * @returns {Object} Client and ID to use
   */
  _getClientForRecipient(to) {
    const isGroup = isGroupId(to);
    
    if (isGroup) {
      // Use Baileys for groups
      if (this.baileyClients.size === 0) {
        throw new Error('No Baileys clients available for group messaging');
      }
      
      // Use first available client for now
      // In a more complex implementation, we'd use a smarter selection strategy
      const clientId = this.baileyClients.keys().next().value;
      const client = this.baileyClients.get(clientId);
      
      return { client, clientId, type: 'bailey' };
    } else {
      // Use Web.js for direct messaging
      if (this.webjsClients.size === 0) {
        // Fall back to Baileys if no Web.js clients
        if (this.baileyClients.size === 0) {
          throw new Error('No WhatsApp clients available');
        }
        
        const clientId = this.baileyClients.keys().next().value;
        const client = this.baileyClients.get(clientId);
        
        return { client, clientId, type: 'bailey' };
      }
      
      // Use first available client for now
      const clientId = this.webjsClients.keys().next().value;
      const client = this.webjsClients.get(clientId);
      
      return { client, clientId, type: 'webjs' };
    }
  }
  
  /**
   * Send a text message to a user or group
   * @param {String} to - Recipient ID or phone number
   * @param {String} text - Message text
   * @param {String} [preferredClientId] - Preferred client ID (optional)
   * @returns {Promise<Object>} Send result
   */
  async sendMessage(to, text, preferredClientId = null) {
    // Format phone number if needed
    if (!to.includes('@')) {
      to = formatPhoneNumber(to);
    }
    
    try {
      let clientInfo;
      
      if (preferredClientId) {
        // Try to use preferred client
        if (this.baileyClients.has(preferredClientId)) {
          clientInfo = {
            client: this.baileyClients.get(preferredClientId),
            clientId: preferredClientId,
            type: 'bailey'
          };
        } else if (this.webjsClients.has(preferredClientId)) {
          clientInfo = {
            client: this.webjsClients.get(preferredClientId),
            clientId: preferredClientId,
            type: 'webjs'
          };
        } else {
          throw new Error(`Preferred client ${preferredClientId} not found`);
        }
      } else {
        // Select appropriate client based on recipient
        clientInfo = this._getClientForRecipient(to);
      }
      
      // Send message
      const result = await clientInfo.client.sendTextMessage(to, text);
      
      // Log in memory
      VoxMemory.addEvent(
        clientInfo.clientId,
        'whatsapp_client',
        'MESSAGE_SENT',
        {
          to,
          content: text,
          timestamp: new Date(),
          messageId: result.id || result.key?.id
        }
      );
      
      return {
        success: true,
        messageId: result.id || result.key?.id,
        clientId: clientInfo.clientId,
        clientType: clientInfo.type,
        to,
        timestamp: new Date()
      };
    } catch (error) {
      console.error('Error sending WhatsApp message:', error);
      
      // Log failure
      VoxMemory.addEvent(
        'whatsapp_manager',
        'system',
        'MESSAGE_SEND_FAILED',
        {
          to,
          content: text,
          error: error.message,
          timestamp: new Date()
        }
      );
      
      throw error;
    }
  }
  
  /**
   * Send a media message
   * @param {String} to - Recipient ID or phone number
   * @param {Object} media - Media object
   * @param {String} [preferredClientId] - Preferred client ID (optional)
   * @returns {Promise<Object>} Send result
   */
  async sendMediaMessage(to, media, preferredClientId = null) {
    // Format phone number if needed
    if (!to.includes('@')) {
      to = formatPhoneNumber(to);
    }
    
    try {
      let clientInfo;
      
      if (preferredClientId) {
        // Try to use preferred client
        if (this.baileyClients.has(preferredClientId)) {
          clientInfo = {
            client: this.baileyClients.get(preferredClientId),
            clientId: preferredClientId,
            type: 'bailey'
          };
        } else if (this.webjsClients.has(preferredClientId)) {
          clientInfo = {
            client: this.webjsClients.get(preferredClientId),
            clientId: preferredClientId,
            type: 'webjs'
          };
        } else {
          throw new Error(`Preferred client ${preferredClientId} not found`);
        }
      } else {
        // Select appropriate client based on recipient
        clientInfo = this._getClientForRecipient(to);
      }
      
      // Send media message
      const result = await clientInfo.client.sendMediaMessage(to, media);
      
      // Log in memory
      VoxMemory.addEvent(
        clientInfo.clientId,
        'whatsapp_client',
        'MEDIA_SENT',
        {
          to,
          mediaType: media.type,
          caption: media.caption,
          timestamp: new Date(),
          messageId: result.id || result.key?.id
        }
      );
      
      return {
        success: true,
        messageId: result.id || result.key?.id,
        clientId: clientInfo.clientId,
        clientType: clientInfo.type,
        to,
        timestamp: new Date()
      };
    } catch (error) {
      console.error('Error sending WhatsApp media message:', error);
      
      // Log failure
      VoxMemory.addEvent(
        'whatsapp_manager',
        'system',
        'MEDIA_SEND_FAILED',
        {
          to,
          mediaType: media.type,
          error: error.message,
          timestamp: new Date()
        }
      );
      
      throw error;
    }
  }
  
  /**
   * Get all available clients
   * @returns {Array<Object>} List of clients
   */
  getAllClients() {
    const clients = [];
    
    // Add Baileys clients
    for (const [id, client] of this.baileyClients.entries()) {
      clients.push({
        id,
        type: 'bailey',
        connected: client.isAuthenticated(),
        hasQr: !!client.getQR(),
        primaryUse: 'groups'
      });
    }
    
    // Add Web.js clients
    for (const [id, client] of this.webjsClients.entries()) {
      clients.push({
        id,
        type: 'webjs',
        connected: client.isAuthenticated(),
        hasQr: !!client.getQR(),
        primaryUse: 'direct'
      });
    }
    
    return clients;
  }
  
  /**
   * Get a specific client by ID
   * @param {String} clientId - Client ID
   * @returns {Object|null} Client or null if not found
   */
  getClient(clientId) {
    if (this.baileyClients.has(clientId)) {
      return {
        client: this.baileyClients.get(clientId),
        type: 'bailey'
      };
    }
    
    if (this.webjsClients.has(clientId)) {
      return {
        client: this.webjsClients.get(clientId),
        type: 'webjs'
      };
    }
    
    return null;
  }
  
  /**
   * Get the QR code for a client
   * @param {String} clientId - Client ID
   * @returns {String|null} QR code or null if not available
   */
  getClientQR(clientId) {
    const clientInfo = this.getClient(clientId);
    if (!clientInfo) return null;
    
    return clientInfo.client.getQR();
  }
  
  /**
   * Disconnect a specific client
   * @param {String} clientId - Client ID
   * @returns {Promise<Boolean>} Success result
   */
  async disconnectClient(clientId) {
    const clientInfo = this.getClient(clientId);
    if (!clientInfo) return false;
    
    try {
      await clientInfo.client.disconnect();
      
      if (clientInfo.type === 'bailey') {
        this.baileyClients.delete(clientId);
      } else {
        this.webjsClients.delete(clientId);
      }
      
      // Update manager profile
      VoxMemory.updateEntityProfile(
        'whatsapp_manager',
        'system',
        {
          baileyClients: this.baileyClients.size,
          webjsClients: this.webjsClients.size,
          lastClientRemoved: new Date(),
          lastClientRemovedType: clientInfo.type
        }
      );
      
      return true;
    } catch (error) {
      console.error(`Error disconnecting client ${clientId}:`, error);
      return false;
    }
  }
  
  /**
   * Disconnect all clients
   * @returns {Promise<Array>} Results
   */
  async disconnectAll() {
    const results = [];
    
    // Disconnect Baileys clients
    for (const [id, client] of this.baileyClients.entries()) {
      try {
        await client.disconnect();
        results.push({
          clientId: id,
          type: 'bailey',
          success: true
        });
      } catch (error) {
        results.push({
          clientId: id,
          type: 'bailey',
          success: false,
          error: error.message
        });
      }
    }
    
    // Disconnect Web.js clients
    for (const [id, client] of this.webjsClients.entries()) {
      try {
        await client.disconnect();
        results.push({
          clientId: id,
          type: 'webjs',
          success: true
        });
      } catch (error) {
        results.push({
          clientId: id,
          type: 'webjs',
          success: false,
          error: error.message
        });
      }
    }
    
    // Clear client maps
    this.baileyClients.clear();
    this.webjsClients.clear();
    
    // Update manager profile
    VoxMemory.updateEntityProfile(
      'whatsapp_manager',
      'system',
      {
        baileyClients: 0,
        webjsClients: 0,
        lastDisconnectAll: new Date()
      }
    );
    
    return results;
  }
}

module.exports = WhatsAppManager;
