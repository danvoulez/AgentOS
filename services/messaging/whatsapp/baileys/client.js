/**
 * Baileys WhatsApp Client for AgentOS
 * Used primarily for group interactions
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const { Boom } = require('@hapi/boom');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');
const logger = pino({ level: 'warn' });

// Get core VoxAgent memory reference
const VoxMemory = require('../../../core/Memory');

class BaileysWhatsAppClient extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      clientId: options.clientId || 'default',
      sessionsDir: options.sessionsDir || path.join(process.cwd(), '.whatsapp-sessions'),
      ...options
    };
    
    this.client = null;
    this.authState = null;
    this.connected = false;
    this.qrCode = null;
    this.clientInfo = {
      id: this.options.clientId,
      type: 'baileys',
      primaryUse: 'groups'
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
      
      // Load auth state
      this.authState = await useMultiFileAuthState(sessionPath);
      
      // Create the client
      this.client = makeWASocket({
        auth: this.authState.state,
        printQRInTerminal: false,
        logger
      });
      
      // Set up event handlers
      this._setupEventListeners();
      
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
      console.error('Failed to initialize Baileys WhatsApp client:', error);
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
    // Handle connection events
    this.client.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;
      
      if (qr) {
        // New QR code received
        this.qrCode = qr;
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { qrCode: qr, status: 'authentication_needed' }
        );
        this.emit('qr', qr);
      }
      
      if (connection === 'close') {
        const shouldReconnect = 
          (lastDisconnect?.error instanceof Boom)? 
          lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut : true;
        
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { 
            status: shouldReconnect ? 'disconnected' : 'logged_out',
            lastDisconnect: Date.now()
          }
        );
        
        this.connected = false;
        this.emit('disconnected', { shouldReconnect, reason: lastDisconnect?.error?.message });
        
        if (shouldReconnect) {
          // Reconnect if the connection closed due to error
          setTimeout(() => this.initialize(), 5000);
        }
      } else if (connection === 'open') {
        this.connected = true;
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { 
            status: 'connected',
            connectedAt: Date.now(),
            phoneNumber: this.client.user?.id?.split(':')[0]
          }
        );
        this.emit('ready', this.client.user);
      }
    });
    
    // Handle authentication updates
    this.client.ev.on('creds.update', async () => {
      await this.authState.saveCreds();
    });
    
    // Handle incoming messages
    this.client.ev.on('messages.upsert', ({ messages }) => {
      if (!messages || !messages.length) return;
      
      for (const message of messages) {
        // Skip status messages and own messages
        if (message.key.fromMe || message.key.remoteJid === 'status@broadcast') continue;
        
        // Process the message
        this._processIncomingMessage(message);
      }
    });
    
    // Handle group participant updates
    this.client.ev.on('group-participants.update', (update) => {
      VoxMemory.addEvent(
        update.id,
        'group',
        'PARTICIPANTS_UPDATED',
        {
          participants: update.participants,
          action: update.action
        }
      );
      
      this.emit('group-participants', update);
    });
  }
  
  /**
   * Process an incoming WhatsApp message
   * @param {Object} rawMessage - Raw Baileys message object
   */
  _processIncomingMessage(rawMessage) {
    try {
      const isGroup = rawMessage.key.remoteJid.endsWith('@g.us');
      const sender = rawMessage.key.participant || rawMessage.key.remoteJid;
      const senderName = rawMessage.pushName || sender.split('@')[0];
      const groupId = isGroup ? rawMessage.key.remoteJid : null;
      
      // Extract text content
      let content = '';
      if (rawMessage.message?.conversation) {
        content = rawMessage.message.conversation;
      } else if (rawMessage.message?.extendedTextMessage?.text) {
        content = rawMessage.message.extendedTextMessage.text;
      } else if (rawMessage.message?.imageMessage?.caption) {
        content = rawMessage.message.imageMessage.caption;
      } else if (rawMessage.message?.videoMessage?.caption) {
        content = rawMessage.message.videoMessage.caption;
      }
      
      // Extract media if present
      let media = null;
      if (rawMessage.message?.imageMessage) {
        media = {
          type: 'image',
          mimetype: rawMessage.message.imageMessage.mimetype,
          caption: rawMessage.message.imageMessage.caption || '',
          messageId: rawMessage.key.id
        };
      } else if (rawMessage.message?.videoMessage) {
        media = {
          type: 'video',
          mimetype: rawMessage.message.videoMessage.mimetype,
          caption: rawMessage.message.videoMessage.caption || '',
          messageId: rawMessage.key.id
        };
      } else if (rawMessage.message?.documentMessage) {
        media = {
          type: 'document',
          mimetype: rawMessage.message.documentMessage.mimetype,
          filename: rawMessage.message.documentMessage.fileName || 'document',
          messageId: rawMessage.key.id
        };
      } else if (rawMessage.message?.audioMessage) {
        media = {
          type: 'audio',
          mimetype: rawMessage.message.audioMessage.mimetype,
          messageId: rawMessage.key.id
        };
      }
      
      // Create standardized message object
      const message = {
        id: rawMessage.key.id,
        content,
        sender,
        senderName,
        group: groupId,
        isGroup,
        timestamp: new Date(rawMessage.messageTimestamp * 1000),
        media,
        clientType: 'baileys',
        raw: rawMessage
      };
      
      // Store in memory
      VoxMemory.addEvent(
        isGroup ? groupId : sender,
        isGroup ? 'group' : 'user',
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
          messageCount: (VoxMemory.getEntityProfile(sender, 'user')?.messageCount || 0) + 1
        }
      );
      
      // Update group profile if it's a group message
      if (isGroup) {
        VoxMemory.updateEntityProfile(
          groupId,
          'group',
          {
            lastActivity: message.timestamp,
            messageCount: (VoxMemory.getEntityProfile(groupId, 'group')?.messageCount || 0) + 1
          }
        );
      }
      
      // Emit message event
      this.emit('message', message);
      
      // Forward to VoxAgent for processing
      this._forwardToVoxAgent(message);
    } catch (error) {
      console.error('Error processing message:', error);
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
      source: message.isGroup ? 'group' : 'user',
      sourceId: message.isGroup ? message.group : message.sender
    });
  }
  
  /**
   * Send a text message
   * @param {String} to - Recipient ID (user or group)
   * @param {String} text - Message text
   * @returns {Promise<Object>} Send result
   */
  async sendTextMessage(to, text) {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      const result = await this.client.sendMessage(to, { text });
      
      // Record in memory
      VoxMemory.addEvent(
        to,
        to.endsWith('@g.us') ? 'group' : 'user',
        'MESSAGE_SENT',
        {
          id: result.key.id,
          content: text,
          timestamp: new Date(),
          clientType: 'baileys'
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
   * @param {String} to - Recipient ID (user or group)
   * @param {Object} media - Media object
   * @returns {Promise<Object>} Send result
   */
  async sendMediaMessage(to, media) {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      let messageContent;
      
      switch (media.type) {
        case 'image':
          messageContent = {
            image: media.data,
            caption: media.caption || '',
            mimetype: media.mimetype || 'image/jpeg'
          };
          break;
          
        case 'video':
          messageContent = {
            video: media.data,
            caption: media.caption || '',
            mimetype: media.mimetype || 'video/mp4'
          };
          break;
          
        case 'document':
          messageContent = {
            document: media.data,
            mimetype: media.mimetype || 'application/octet-stream',
            fileName: media.filename || 'document'
          };
          break;
          
        case 'audio':
          messageContent = {
            audio: media.data,
            mimetype: media.mimetype || 'audio/mp4'
          };
          break;
          
        default:
          throw new Error(`Unsupported media type: ${media.type}`);
      }
      
      const result = await this.client.sendMessage(to, messageContent);
      
      // Record in memory
      VoxMemory.addEvent(
        to,
        to.endsWith('@g.us') ? 'group' : 'user',
        'MEDIA_SENT',
        {
          id: result.key.id,
          mediaType: media.type,
          caption: media.caption,
          timestamp: new Date(),
          clientType: 'baileys'
        }
      );
      
      return result;
    } catch (error) {
      console.error('Error sending media message:', error);
      throw error;
    }
  }
  
  /**
   * Get list of available groups
   * @returns {Promise<Array>} List of groups
   */
  async getGroups() {
    if (!this.connected || !this.client) {
      throw new Error('Client not connected');
    }
    
    try {
      const groups = await this.client.groupFetchAllParticipating();
      return Object.entries(groups).map(([id, group]) => ({
        id,
        name: group.subject,
        participants: group.participants.map(p => ({
          id: p.id,
          admin: p.admin ? true : false,
          superAdmin: p.admin === 'superadmin'
        })),
        creation: group.creation,
        desc: group.desc
      }));
    } catch (error) {
      console.error('Error fetching groups:', error);
      throw error;
    }
  }
  
  /**
   * Disconnect the client
   */
  async disconnect() {
    if (this.client) {
      try {
        await this.client.logout();
        await this.client.end();
        this.connected = false;
        
        VoxMemory.updateEntityProfile(
          this.options.clientId,
          'whatsapp_client',
          { 
            status: 'disconnected',
            disconnectedAt: Date.now()
          }
        );
        
        this.emit('disconnected', { shouldReconnect: false, reason: 'manual' });
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

module.exports = BaileysWhatsAppClient;
