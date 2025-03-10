/**
 * WhatsApp Integration for VoxAgent
 * 
 * Connects the WhatsApp manager with VoxAgent to enable:
 * - Processing incoming messages from different WhatsApp clients
 * - Sending responses using the appropriate client
 * - Maintaining consistent memory context across all interactions
 */

const WhatsAppManager = require('./WhatsAppManager');
const Memory = require('../../core/Memory');
const path = require('path');

class WhatsAppIntegration {
  constructor(voxAgent, options = {}) {
    this.voxAgent = voxAgent;
    this.manager = null;
    this.options = {
      sessionsDir: options.sessionsDir || path.join(process.cwd(), '.whatsapp-sessions'),
      mediaDir: options.mediaDir || path.join(process.cwd(), 'media'),
      ...options
    };
    
    this.initialized = false;
  }
  
  /**
   * Initialize the WhatsApp integration
   */
  async initialize() {
    if (this.initialized) return this;
    
    // Create WhatsApp manager
    this.manager = new WhatsAppManager({
      sessionsDir: this.options.sessionsDir,
      mediaDir: this.options.mediaDir
    });
    
    // Set up event handling
    this._setupEventHandlers();
    
    // Add integration to VoxAgent
    this.voxAgent.modules.set('whatsapp', this);
    
    this.initialized = true;
    
    // Record initialization in memory
    Memory.updateEntityProfile(
      'whatsapp_integration',
      'system',
      {
        initialized: Date.now(),
        status: 'active',
        moduleType: 'messaging'
      }
    );
    
    return this;
  }
  
  /**
   * Set up event handlers for the WhatsApp manager
   */
  _setupEventHandlers() {
    // Handle messages that need VoxAgent processing
    this.manager.on('message_for_vox', async (event) => {
      try {
        // Forward to VoxAgent for processing
        const response = await this.voxAgent.processEvent(event);
        
        // If VoxAgent generated a response, send it back
        if (response) {
          const recipient = event.data.isGroup ? event.data.group : event.data.sender;
          await this.manager.sendMessage(recipient, response, event.clientId);
        }
      } catch (error) {
        console.error('Error processing WhatsApp message:', error);
        
        // Log error in memory
        Memory.addEvent(
          'whatsapp_integration',
          'system',
          'PROCESSING_ERROR',
          {
            error: error.message,
            event,
            timestamp: Date.now()
          }
        );
      }
    });
    
    // Handle client authentication events
    this.manager.on('client_qr', (data) => {
      console.log(`QR code generated for WhatsApp client ${data.clientId}`);
      
      // Add QR to memory for UI to access
      Memory.updateEntityProfile(
        data.clientId,
        'whatsapp_client',
        {
          qrCode: data.qr,
          qrTimestamp: Date.now(),
          status: 'authentication_needed'
        }
      );
    });
    
    // Handle client ready events
    this.manager.on('client_ready', (data) => {
      console.log(`WhatsApp client ${data.clientId} is ready`);
      
      // Update client status in memory
      Memory.updateEntityProfile(
        data.clientId,
        'whatsapp_client',
        {
          status: 'connected',
          connectedAt: Date.now()
        }
      );
    });
    
    // Handle client disconnected events
    this.manager.on('client_disconnected', (data) => {
      console.log(`WhatsApp client ${data.clientId} disconnected: ${data.reason}`);
      
      // Update client status in memory
      Memory.updateEntityProfile(
        data.clientId,
        'whatsapp_client',
        {
          status: 'disconnected',
          disconnectedAt: Date.now(),
          reason: data.reason
        }
      );
    });
    
    // Handle group participant updates
    this.manager.on('group_participants_update', (data) => {
      // Record in memory
      Memory.addEvent(
        data.id,
        'group',
        'PARTICIPANTS_UPDATED',
        {
          participants: data.participants,
          action: data.action,
          timestamp: Date.now()
        }
      );
    });
  }
  
  /**
   * Create a new WhatsApp client for group interactions (Baileys)
   * @param {String} clientId - Client identifier
   * @param {Object} options - Client options
   * @returns {Promise<Object>} The client instance
   */
  async createGroupClient(clientId, options = {}) {
    this._ensureInitialized();
    return this.manager.createBaileyClient(clientId, options);
  }
  
  /**
   * Create a new WhatsApp client for direct messaging (Web.js)
   * @param {String} clientId - Client identifier
   * @param {Object} options - Client options
   * @returns {Promise<Object>} The client instance
   */
  async createDirectClient(clientId, options = {}) {
    this._ensureInitialized();
    return this.manager.createWebJsClient(clientId, options);
  }
  
  /**
   * Send a message to a user or group
   * @param {String} to - Recipient ID or phone number
   * @param {String} text - Message text
   * @param {String} [preferredClientId] - Preferred client ID (optional)
   * @returns {Promise<Object>} Send result
   */
  async sendMessage(to, text, preferredClientId = null) {
    this._ensureInitialized();
    
    const result = await this.manager.sendMessage(to, text, preferredClientId);
    
    // Log in VoxAgent memory
    Memory.addEvent(
      to.includes('@g.us') ? to : to.split('@')[0],
      to.includes('@g.us') ? 'group' : 'user',
      'MESSAGE_SENT',
      {
        content: text,
        timestamp: new Date(),
        sentBy: 'vox',
        clientId: result.clientId,
        clientType: result.clientType
      }
    );
    
    return result;
  }
  
  /**
   * Send a media message
   * @param {String} to - Recipient ID or phone number
   * @param {Object} media - Media object
   * @param {String} [preferredClientId] - Preferred client ID (optional)
   * @returns {Promise<Object>} Send result
   */
  async sendMediaMessage(to, media, preferredClientId = null) {
    this._ensureInitialized();
    
    const result = await this.manager.sendMediaMessage(to, media, preferredClientId);
    
    // Log in VoxAgent memory
    Memory.addEvent(
      to.includes('@g.us') ? to : to.split('@')[0],
      to.includes('@g.us') ? 'group' : 'user',
      'MEDIA_SENT',
      {
        mediaType: media.type,
        caption: media.caption,
        timestamp: new Date(),
        sentBy: 'vox',
        clientId: result.clientId,
        clientType: result.clientType
      }
    );
    
    return result;
  }
  
  /**
   * Get all available clients
   * @returns {Array<Object>} List of clients
   */
  getAllClients() {
    this._ensureInitialized();
    return this.manager.getAllClients();
  }
  
  /**
   * Get a specific client's QR code
   * @param {String} clientId - Client ID
   * @returns {String|null} QR code or null if not available
   */
  getClientQR(clientId) {
    this._ensureInitialized();
    return this.manager.getClientQR(clientId);
  }
  
  /**
   * Disconnect a specific client
   * @param {String} clientId - Client ID
   * @returns {Promise<Boolean>} Success result
   */
  async disconnectClient(clientId) {
    this._ensureInitialized();
    return this.manager.disconnectClient(clientId);
  }
  
  /**
   * Disconnect all clients
   * @returns {Promise<Array>} Results
   */
  async disconnectAll() {
    this._ensureInitialized();
    return this.manager.disconnectAll();
  }
  
  /**
   * Ensure the integration is initialized
   */
  _ensureInitialized() {
    if (!this.initialized) {
      throw new Error('WhatsApp integration not initialized');
    }
  }
  
  /**
   * Shutdown the integration
   */
  async shutdown() {
    if (!this.initialized) return;
    
    try {
      // Disconnect all clients
      await this.manager.disconnectAll();
      
      // Update status in memory
      Memory.updateEntityProfile(
        'whatsapp_integration',
        'system',
        {
          status: 'shutdown',
          shutdownTime: Date.now()
        }
      );
      
      this.initialized = false;
    } catch (error) {
      console.error('Error shutting down WhatsApp integration:', error);
      throw error;
    }
  }
}

module.exports = WhatsAppIntegration;
