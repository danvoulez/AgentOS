/**
 * WhatsApp Web.js Client for AgentOS
 * Used primarily for direct messaging interactions
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const { EventEmitter } = require('events');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const mime = require('mime-types');

// Get core VoxAgent memory reference
const VoxMemory = require('../../../core/Memory');

class WebJsWhatsAppClient extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      clientId: options.clientId || 'default',
      sessionsDir: options.sessionsDir || path.join(process.cwd(), '.whatsapp-sessions'),
      headless: options.headless !== false,
      ...options
    };
    
    this.client = null;
    this.connected = false;
    this.qrCode = null;
    this.clientInfo = {
      id: this.options.clientId,
      type: 'webjs',
      primaryUse: 'direct'
    };
  }

  /**
   * Initialize the WhatsApp client
   */
  async initialize() {
    try {
      // Ensure sessions directory exists
      const sessionPath = path.join(this.options.sessionsDir, this.options.clientId);
      if (!fs.existsSync(sessionPath)) {
        fs.mkdirSync(sessionPath, { recursive: true });
      }
      
      // Create the client
      this.client = new Client({
        authStrategy: new LocalAuth({ 
          clientId: this.options.clientId,
          dataPath: this.options.sessionsDir
        }),
        puppeteer: {
          headless: this.options.headless,
          args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-extensions']
        }
      });
      
      // Set up event handlers
      this._setupEventListeners();
      
      // Initialize the client
      await this.client.initialize();
      
      // Store initialization in VoxMemory
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        {
          ...this.clientInfo,
          initTime: Date.now(),
          status: 'initializing'
        }
      );
      
      return this;
    } catch (error) {
      console.error('Failed to initialize WhatsApp Web.js client:', error);
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        {
          status: 'error',
          error: error.message
        }
      );
      throw error;
    }
  }
  
  /**
   * Set up event listeners for the WhatsApp client
   */
  _setupEventListeners() {
    // Handle QR code generation
    this.client.on('qr', (qr) => {
      this.qrCode = qr;
      
      // Display QR in terminal for testing
      if (this.options.showQrInTerminal) {
        qrcode.generate(qr, { small: true });
      }
      
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        { qrCode: qr, status: 'authentication_needed' }
      );
      
      this.emit('qr', qr);
    });
    
    // Handle ready event
    this.client.on('ready', () => {
      this.connected = true;
      
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        { 
          status: 'connected',
          connectedAt: Date.now()
        }
      );
      
      this.emit('ready');
    });
    
    // Handle authentication failures
    this.client.on('auth_failure', (msg) => {
      this.connected = false;
      
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        { 
          status: 'auth_failed',
          error: msg
        }
      );
      
      this.emit('auth_failure', msg);
    });
    
    // Handle disconnects
    this.client.on('disconnected', (reason) => {
      this.connected = false;
      
      VoxMemory.updateEntityProfile(
        this.options.clientId,
        'whatsapp_client',
        { 
          status: 'disconnected',
          disconnectedAt: Date.now(),
          reason
        }
      );
      
      this.emit('disconnected', reason);
    });
    
    // Handle incoming messages
    this.client.on('message', (msg) => {
      // Skip messages from groups
      if (msg.isGroup) return;
      
      this._processIncomingMessage(msg);
    });
    
    // Handle client info update
    this.client.on('authenticated', () => {
      this.client.getInfo().then(info => {
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { 
            phoneNumber: info.wid._serialized.split('@')[0]
          }
        );
      }).catch(err => {
        console.error('Error getting client info:', err);
      });
    });
  }
  
  /**
   * Process an incoming WhatsApp message
   * @param {Object} msg - WhatsApp Web.js Message object
   */
  async _processIncomingMessage(msg) {
    try {
      const isGroup = msg.isGroup;
      
      // Skip group messages as those are handled by Baileys client
      if (isGroup) return;
      
      const sender = msg.from;
      const content = msg.body;
      const contact = await msg.getContact();
      const senderName = contact.pushname || contact.name || sender.split('@')[0];
      
      // Extract media if present
      let media = null;
      if (msg.hasMedia) {
        const msgMedia = await msg.downloadMedia();
        media = {
          type: this._getMediaType(msgMedia.mimetype),
          mimetype: msgMedia.mimetype,
          data: msgMedia.data,
          filename: msgMedia.filename || null,
          caption: content
        };
      }
      
      // Create standardized message object
      const message = {
        id: msg.id.id,
        content,
        sender,
        senderName,
        isGroup: false,
        timestamp: msg.timestamp ? new Date(msg.timestamp * 1000) : new Date(),
        media,
        clientType: 'webjs',
        raw: msg
      };
      
      // Store in memory
      VoxMemory.addEvent(
        sender,
        'user',
        'MESSAGE_RECEIVED',
        message
      );
      
      // Update sender profile
      VoxMemory.updateEntityProfile(
        sender,
        'user',
        {
          name: senderName,
          lastMessage: message.timestamp,
          messageCount: (VoxMemory.getEntityProfile(sender, 'user')?.messageCount || 0) + 1,
          contactInfo: {
            pushname: contact.pushname,
            name: contact.name,
            number: contact.number
          }
        }
      );
      
      // Emit message event
      this.emit('message', message);
      
      // Forward to VoxAgent for processing
      this._forwardToVoxAgent(message);
    } catch (error) {
      console.error('Error processing message:', error);
    }
  }
  
  /**
   * Determine media type from mimetype
   * @param {String} mimetype - MIME type
   * @returns {String} Media type (image, video, document, audio)
   */
  _getMediaType(mimetype) {
    if (mimetype.startsWith('image/')) {
      return 'image';
    } else if (mimetype.startsWith('video/')) {
      return 'video';
    } else if (mimetype.startsWith('audio/')) {
      return 'audio';
    } else {
      return 'document';
    }
  }
  
  /**
   * Forward message to VoxAgent for processing
   * @param {Object} message - Standardized message object
   */
  _forwardToVoxAgent(message) {
    // This would typically be a call to the VoxAgent processEvent method
    // For now, we'll just emit an event
    this.emit('vox-process', {
      type: 'WHATSAPP_MESSAGE',
      data: message,
      source: 'user',
      sourceId: message.sender
    });
  }
  
  /**
   * Send a text message
   * @param {String} to - Recipient ID
   * @param {String} text - Message text
   * @returns {Promise<Object>} Send result
   */
  async sendTextMessage(to, text) {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      const result = await this.client.sendMessage(to, text);
      
      // Record in memory
      VoxMemory.addEvent(
        to,
        'user',
        'MESSAGE_SENT',
        {
          id: result.id.id,
          content: text,
          timestamp: new Date(),
          clientType: 'webjs'
        }
      );
      
      return result;
    } catch (error) {
      console.error('Error sending text message:', error);
      throw error;
    }
  }
  
  /**
   * Send a media message
   * @param {String} to - Recipient ID
   * @param {Object} media - Media object
   * @returns {Promise<Object>} Send result
   */
  async sendMediaMessage(to, media) {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      let messageMedia;
      
      if (typeof media.data === 'string' && fs.existsSync(media.data)) {
        // It's a file path
        messageMedia = MessageMedia.fromFilePath(media.data);
      } else if (Buffer.isBuffer(media.data)) {
        // It's a buffer
        const base64Data = media.data.toString('base64');
        messageMedia = new MessageMedia(
          media.mimetype,
          base64Data,
          media.filename || 'file'
        );
      } else if (typeof media.data === 'string') {
        // It's already a base64 string
        messageMedia = new MessageMedia(
          media.mimetype,
          media.data,
          media.filename || 'file'
        );
      } else {
        throw new Error('Invalid media data format');
      }
      
      const result = await this.client.sendMessage(to, messageMedia, {
        caption: media.caption || '',
        sendMediaAsDocument: media.type === 'document'
      });
      
      // Record in memory
      VoxMemory.addEvent(
        to,
        'user',
        'MEDIA_SENT',
        {
          id: result.id.id,
          mediaType: media.type,
          caption: media.caption,
          timestamp: new Date(),
          clientType: 'webjs'
        }
      );
      
      return result;
    } catch (error) {
      console.error('Error sending media message:', error);
      throw error;
    }
  }
  
  /**
   * Get all chats
   * @returns {Promise<Array>} List of chats
   */
  async getChats() {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      const chats = await this.client.getChats();
      
      // Filter to only include non-group chats
      const directChats = chats.filter(chat => !chat.isGroup);
      
      return directChats.map(chat => ({
        id: chat.id._serialized,
        name: chat.name,
        unreadCount: chat.unreadCount,
        timestamp: chat.timestamp ? new Date(chat.timestamp * 1000) : null,
        lastMessage: chat.lastMessage ? {
          content: chat.lastMessage.body,
          sender: chat.lastMessage.from,
          timestamp: chat.lastMessage.timestamp ? new Date(chat.lastMessage.timestamp * 1000) : null
        } : null
      }));
    } catch (error) {
      console.error('Error fetching chats:', error);
      throw error;
    }
  }
  
  /**
   * Disconnect the client
   */
  async disconnect() {
    if (this.client) {
      try {
        await this.client.destroy();
        this.connected = false;
        
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { 
            status: 'disconnected',
            disconnectedAt: Date.now()
          }
        );
        
        this.emit('disconnected', 'manual');
      } catch (error) {
        console.error('Error disconnecting client:', error);
      }
    }
  }
  
  /**
   * Get authentication QR code
   * @returns {String|null} QR code or null if not available
   */
  getQR() {
    return this.qrCode;
  }
  
  /**
   * Check if client is authenticated
   * @returns {Boolean} Whether client is authenticated
   */
  isAuthenticated() {
    return this.connected;
  }
}

module.exports = WebJsWhatsAppClient;
