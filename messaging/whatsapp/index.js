/**
 * WhatsApp Integration for AgentOS
 * 
 * This module exports all WhatsApp-related functionality,
 * including the unified WhatsApp manager and both client
 * implementations (Baileys for groups and Web.js for direct messaging).
 */

const WhatsAppManager = require('./WhatsAppManager');
const WhatsAppIntegration = require('./integration');
const BaileysWhatsAppClient = require('./baileys/client');
const WebJsWhatsAppClient = require('./webjs/client');
const WhatsAppUtils = require('./common/utils');

module.exports = {
  // Main integration and management classes
  WhatsAppManager,
  WhatsAppIntegration,
  
  // Client implementations
  BaileysWhatsAppClient,  // For group interactions
  WebJsWhatsAppClient,    // For direct messaging
  
  // Utilities
  WhatsAppUtils
};
