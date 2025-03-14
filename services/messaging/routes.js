const express = require('express');
const controllers = require('./controllers');

const router = express.Router();

// WhatsApp routes
router.post('/whatsapp/send', controllers.sendWhatsAppMessage);
router.post('/whatsapp/webhook', controllers.whatsappWebhook);
router.get('/whatsapp/status', controllers.getWhatsAppStatus);

// General messaging routes
router.get('/channels', controllers.getAvailableChannels);
router.post('/broadcast', controllers.broadcastMessage);

module.exports = router;
