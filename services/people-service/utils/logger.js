// services/people-service/utils/logger.js
import fs from 'fs';

export function logEvent(event) {
  const log = `[${new Date().toISOString()}] ${event}\n`;
  fs.appendFileSync('AgentOS/logs/system.log', log);
}
