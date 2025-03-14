
// core/serviceRegistry.js
const services = [];

/**
 * Registra um serviço no AgentOS.
 * @param {Object} service - { name, endpoint, interestedEvents? }
 */
export function registerService(service) {
  services.push(service);
  console.log(`Serviço registrado: ${service.name}`);
}

/**
 * Retorna a lista de serviços registrados.
 */
export function listServices() {
  return services;
}

/**
 * Roteia um evento para os serviços interessados.
 * @param {Object} event - { type, data }
 */
export function routeEvent(event) {
  console.log("──────────────────────────────────────────");
  console.log("  Roteando evento para serviços interessados");
  console.log("──────────────────────────────────────────");
  
  services.forEach(service => {
    if (!service.interestedEvents || (Array.isArray(service.interestedEvents) && service.interestedEvents.includes(event.type))) {
      try {
        console.log(`Despachando evento '${event.type}' para ${service.name} em ${service.endpoint}`);
      } catch (error) {
        console.error(`Erro ao despachar para ${service.name}:`, error);
      }
    } else {
      console.log(`Serviço ${service.name} não está interessado no evento '${event.type}'`);
    }
  });
}
