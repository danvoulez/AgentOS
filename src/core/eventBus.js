
// core/eventBus.js
const subscribers = {};

/**
 * Subscreve uma função callback a um tópico.
 * @param {string} topic 
 * @param {Function} callback 
 */
export function subscribe(topic, callback) {
  if (!subscribers[topic]) {
    subscribers[topic] = [];
  }
  subscribers[topic].push(callback);
  console.log(`Subscreveu callback no tópico: ${topic}`);
}

/**
 * Publica um evento para os subscribers de um tópico.
 * @param {string} topic 
 * @param {any} payload 
 */
export function publish(topic, payload) {
  console.log(`Publicando no tópico "${topic}":`, payload);
  if (subscribers[topic]) {
    subscribers[topic].forEach(cb => {
      try {
        cb(payload);
      } catch (error) {
        console.error(`Erro no callback do tópico "${topic}":`, error);
      }
    });
  }
}
