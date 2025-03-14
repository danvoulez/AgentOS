// services/messaging/utils/messageFormatter.js
export function formatTextMessage(text) {
  return {
    type: 'text',
    content: text
  };
}

export function formatMediaMessage(url, caption = '') {
  return {
    type: 'media',
    url: url,
    caption: caption
  };
}

export function formatTemplateMessage(templateName, parameters = {}) {
  return {
    type: 'template',
    template: templateName,
    parameters: parameters
  };
}
