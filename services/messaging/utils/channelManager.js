// services/messaging/utils/channelManager.js
export function getAvailableChannels() {
  return [
    {
      id: 'whatsapp',
      name: 'WhatsApp',
      status: 'active',
      capabilities: ['text', 'media', 'templates']
    },
    {
      id: 'sms',
      name: 'SMS',
      status: 'inactive',
      capabilities: ['text']
    },
    {
      id: 'email',
      name: 'Email',
      status: 'active',
      capabilities: ['text', 'media', 'html']
    }
  ];
}

export function validateMessageForChannel(message, channelId) {
  const channels = getAvailableChannels();
  const channel = channels.find(c => c.id === channelId);
  
  if (!channel) {
    throw new Error(`Channel ${channelId} not found`);
  }
  
  if (channel.status !== 'active') {
    throw new Error(`Channel ${channelId} is not active`);
  }
  
  if (message.type === 'media' && !channel.capabilities.includes('media')) {
    throw new Error(`Channel ${channelId} does not support media messages`);
  }
  
  return true;
}
