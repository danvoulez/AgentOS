const whatsapp = require('./whatsapp');

// WhatsApp controllers
exports.sendWhatsAppMessage = async (req, res) => {
  try {
    const { to, message, mediaUrl } = req.body;
    const result = await whatsapp.sendMessage(to, message, mediaUrl);
    res.status(200).json(result);
  } catch (error) {
    console.error('Error sending WhatsApp message:', error);
    res.status(500).json({ error: error.message });
  }
};

exports.whatsappWebhook = async (req, res) => {
  try {
    const webhookData = req.body;
    await whatsapp.handleWebhook(webhookData);
    res.status(200).send('OK');
  } catch (error) {
    console.error('Error processing WhatsApp webhook:', error);
    res.status(500).json({ error: error.message });
  }
};

exports.getWhatsAppStatus = async (req, res) => {
  try {
    const status = await whatsapp.getStatus();
    res.status(200).json(status);
  } catch (error) {
    console.error('Error getting WhatsApp status:', error);
    res.status(500).json({ error: error.message });
  }
};

// General messaging controllers
exports.getAvailableChannels = async (req, res) => {
  try {
    const channels = [
      { id: 'whatsapp', name: 'WhatsApp', status: 'active' }
      // Add other channels as they become available
    ];
    res.status(200).json(channels);
  } catch (error) {
    console.error('Error getting available channels:', error);
    res.status(500).json({ error: error.message });
  }
};

exports.broadcastMessage = async (req, res) => {
  try {
    const { channels, message, recipients, mediaUrl } = req.body;
    
    if (!channels || !Array.isArray(channels) || channels.length === 0) {
      return res.status(400).json({ error: 'At least one channel must be specified' });
    }
    
    if (!recipients || !Array.isArray(recipients) || recipients.length === 0) {
      return res.status(400).json({ error: 'At least one recipient must be specified' });
    }
    
    if (!message && !mediaUrl) {
      return res.status(400).json({ error: 'Either message or mediaUrl must be provided' });
    }
    
    const results = [];
    
    // Process each channel
    for (const channel of channels) {
      if (channel === 'whatsapp') {
        for (const recipient of recipients) {
          try {
            const result = await whatsapp.sendMessage(recipient, message, mediaUrl);
            results.push({ channel, recipient, status: 'sent', result });
          } catch (error) {
            results.push({ channel, recipient, status: 'failed', error: error.message });
          }
        }
      }
      // Add other channels as they become available
    }
    
    res.status(200).json({ results });
  } catch (error) {
    console.error('Error broadcasting message:', error);
    res.status(500).json({ error: error.message });
  }
};
