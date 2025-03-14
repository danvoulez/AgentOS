
// core/agentos.js
import dotenv from 'dotenv';
import { registerService, listServices, routeEvent } from './serviceRegistry.js';
dotenv.config();

console.log("──────────────────────────────────────────");
console.log("       AgentOS Core - Orquestrador (Vox)");
console.log("──────────────────────────────────────────");

// Registra os serviços integrados
registerService({
  name: "people",
  endpoint: "http://localhost:3001",
  interestedEvents: ["people_created", "people_authenticated", "rfid_scanned"]
});
registerService({
  name: "order",
  endpoint: "http://localhost:3004",
  interestedEvents: ["order_placed", "rfid_inventory_update"]
});
registerService({
  name: "media",
  endpoint: "http://localhost:3003",
  interestedEvents: ["media_uploaded", "video_processed"]
});
registerService({
  name: "ai",
  endpoint: "http://localhost:3005",
  interestedEvents: ["order_placed", "rfid_alert"]
});
registerService({
  name: "access-control",
  endpoint: "http://localhost:3006",
  interestedEvents: ["rfid_authenticated", "access_attempt"]
});

console.log("Serviços registrados:", listServices());

// Exemplo de roteamento de evento
const sampleEvent = {
  type: "rfid_scanned",
  data: { tag: "NFC1234567890", source: "people" }
};
console.log("Roteando evento:", sampleEvent);
routeEvent(sampleEvent);
