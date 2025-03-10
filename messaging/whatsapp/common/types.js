/**
 * Common WhatsApp type definitions for AgentOS
 */

/**
 * @typedef {Object} WhatsAppMessage
 * @property {string} id - Unique message ID
 * @property {string} content - Message content
 * @property {string} sender - Sender ID (phone number)
 * @property {string} [senderName] - Sender name if available
 * @property {string} [group] - Group ID if message is from a group
 * @property {string} [groupName] - Group name if available
 * @property {boolean} isGroup - Whether the message is from a group
 * @property {Date} timestamp - Message timestamp
 * @property {Array<string>} [mentions] - Array of mentioned user IDs
 * @property {Object} [media] - Media object if message contains media
 * @property {string} clientType - 'baileys' or 'webjs'
 * @property {Object} raw - Raw message object from the client
 */

/**
 * @typedef {Object} WhatsAppClient
 * @property {Function} initialize - Initialize the client
 * @property {Function} sendMessage - Send a message
 * @property {Function} sendMediaMessage - Send a media message
 * @property {Function} getQR - Get QR code for authentication
 * @property {Function} isAuthenticated - Check if client is authenticated
 * @property {Function} disconnect - Disconnect the client
 * @property {Function} on - Register an event listener
 */

/**
 * @typedef {Object} WhatsAppMediaMessage
 * @property {string} type - Media type (image, video, document, audio)
 * @property {Buffer|string} data - Media data or path
 * @property {string} [caption] - Optional caption
 * @property {string} [filename] - Optional filename for documents
 * @property {string} [mimetype] - Optional mimetype
 */

module.exports = {};
