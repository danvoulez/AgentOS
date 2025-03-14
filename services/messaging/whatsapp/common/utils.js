/**
 * Common utilities for WhatsApp clients
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

/**
 * Determine if an ID is a group ID
 * @param {String} id - WhatsApp ID
 * @returns {Boolean} Whether ID is a group
 */
function isGroupId(id) {
  return id.endsWith('@g.us');
}

/**
 * Save media to disk
 * @param {Object} media - Media object
 * @param {String} outputDir - Output directory
 * @returns {Promise<String>} Path to saved file
 */
async function saveMediaToDisk(media, outputDir = 'media') {
  try {
    // Ensure directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const filename = media.filename || 
      `${media.type}_${Date.now()}.${getExtensionFromMimetype(media.mimetype)}`;
    const filepath = path.join(outputDir, filename);
    
    // Handle different data formats
    if (Buffer.isBuffer(media.data)) {
      fs.writeFileSync(filepath, media.data);
    } else if (typeof media.data === 'string') {
      // Check if it's base64
      if (media.data.startsWith('data:') || media.data.match(/^[A-Za-z0-9+/=]+$/)) {
        // It's a base64 string
        const dataBuffer = Buffer.from(
          media.data.replace(/^data:[^;]+;base64,/, ''), 
          'base64'
        );
        fs.writeFileSync(filepath, dataBuffer);
      } else if (fs.existsSync(media.data)) {
        // It's a file path, copy the file
        fs.copyFileSync(media.data, filepath);
      } else {
        // It might be a URL
        if (media.data.startsWith('http')) {
          const response = await axios.get(media.data, {
            responseType: 'arraybuffer'
          });
          fs.writeFileSync(filepath, Buffer.from(response.data));
        } else {
          throw new Error('Unsupported media data format');
        }
      }
    } else {
      throw new Error('Unsupported media data format');
    }
    
    return filepath;
  } catch (error) {
    console.error('Error saving media to disk:', error);
    throw error;
  }
}

/**
 * Get file extension from mimetype
 * @param {String} mimetype - MIME type
 * @returns {String} File extension
 */
function getExtensionFromMimetype(mimetype) {
  const map = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'video/mp4': 'mp4',
    'video/webm': 'webm',
    'audio/mp4': 'm4a',
    'audio/mpeg': 'mp3',
    'audio/ogg': 'ogg',
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'text/plain': 'txt'
  };
  
  return map[mimetype] || 'bin';
}

/**
 * Normalize a phone number to WhatsApp format
 * @param {String} phone - Phone number
 * @returns {String} Normalized phone number
 */
function normalizePhoneNumber(phone) {
  // Remove all non-numeric characters
  const cleaned = phone.replace(/\D/g, '');
  
  // Add country code if needed
  if (cleaned.length <= 10) {
    // Assumes default country code is +1 (USA/Canada)
    return `1${cleaned.padStart(10, '0')}`;
  }
  
  return cleaned;
}

/**
 * Format a phone number for WhatsApp API
 * @param {String} phone - Phone number
 * @returns {String} Formatted phone number
 */
function formatPhoneNumber(phone) {
  const normalized = normalizePhoneNumber(phone);
  return `${normalized}@c.us`;
}

module.exports = {
  isGroupId,
  saveMediaToDisk,
  getExtensionFromMimetype,
  normalizePhoneNumber,
  formatPhoneNumber
};
