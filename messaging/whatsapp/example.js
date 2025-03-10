/**
 * WhatsApp Integration Example for AgentOS
 * 
 * This example demonstrates how to:
 * 1. Initialize the WhatsApp integration
 * 2. Create WhatsApp clients for both group and direct messaging
 * 3. Listen for WhatsApp messages
 * 4. Send responses back
 */

const mongoose = require('mongoose');
const VoxAgent = require('../../core/VoxAgent');
const { WhatsAppIntegration } = require('./index');
const qrcode = require('qrcode-terminal');

async function main() {
  try {
    console.log('Starting WhatsApp Integration Example');
    
    // Connect to MongoDB (required for Memory)
    const mongoURL = process.env.MONGO_URL || 'mongodb://localhost:27017/agentos';
    const mongoConnection = await mongoose.connect(mongoURL, {
      useNewUrlParser: true,
      useUnifiedTopology: true
    });
    
    console.log('Connected to MongoDB');
    
    // Initialize VoxAgent
    const voxAgent = new VoxAgent();
    await voxAgent.initialize(mongoConnection);
    
    console.log('VoxAgent initialized');
    
    // Initialize WhatsApp integration
    const whatsapp = new WhatsAppIntegration(voxAgent, {
      sessionsDir: './.whatsapp-sessions',
      mediaDir: './media'
    });
    
    await whatsapp.initialize();
    console.log('WhatsApp integration initialized');
    
    // Create a client for group interactions (Baileys)
    const groupClient = await whatsapp.createGroupClient('group-phone', {
      // Add any client-specific options here
    });
    
    console.log('Group client (Baileys) created');
    
    // Create a client for direct messaging (Web.js)
    const directClient = await whatsapp.createDirectClient('direct-phone', {
      showQrInTerminal: true // For testing, print QR in terminal
    });
    
    console.log('Direct client (Web.js) created');
    
    // Set up event handlers for WhatsApp integration
    whatsapp.manager.on('client_qr', ({ clientId, type, qr }) => {
      console.log(`New QR code available for client: ${clientId} (${type})`);
      
      // Print QR code to terminal for scanning
      if (type === 'bailey' && !process.env.NO_QR) {
        console.log('Scan this QR code with your WhatsApp to authenticate:');
        qrcode.generate(qr, { small: true });
      }
    });
    
    whatsapp.manager.on('client_ready', ({ clientId, type }) => {
      console.log(`WhatsApp client ${clientId} (${type}) is now connected!`);
    });
    
    whatsapp.manager.on('message_for_vox', (event) => {
      console.log(`New message received from ${event.sourceId} for VoxAgent`);
      
      // VoxAgent will process this automatically through the integration
      // You can add custom handling here if needed
    });
    
    // To send a message manually:
    // Function to send test messages
    const sendTestMessage = async (phoneNumber) => {
      try {
        // Format: country code + phone number without any symbols
        const result = await whatsapp.sendMessage(phoneNumber, 'Hello from VoxAgent!');
        console.log('Test message sent:', result);
      } catch (error) {
        console.error('Error sending test message:', error);
      }
    };
    
    // Register process handlers
    process.on('SIGINT', async () => {
      console.log('Shutting down...');
      await whatsapp.shutdown();
      await voxAgent.shutdown();
      process.exit(0);
    });
    
    console.log('\nWhatsApp integration is running!');
    console.log('Scan the QR codes to authenticate your WhatsApp clients');
    console.log('Press Ctrl+C to quit');
    
    // To send a test message, uncomment this line and replace with a real phone number:
    // setTimeout(() => sendTestMessage('1234567890'), 10000);
  } catch (error) {
    console.error('Error in WhatsApp integration example:', error);
    process.exit(1);
  }
}

// Run the example
if (require.main === module) {
  main();
}

module.exports = { main };
