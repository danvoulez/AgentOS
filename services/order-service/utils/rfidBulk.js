// services/order-service/utils/rfidBulk.js
import { readRFIDProduct } from './rfidInventory.js';

export async function performBulkRFIDScan(duration = 10000) {
  return new Promise((resolve) => {
    const scannedTags = new Set();
    const interval = setInterval(async () => {
      try {
        const tag = await readRFIDProduct();
        scannedTags.add(tag);
      } catch (error) {
        console.error("Erro durante o bulk scan:", error);
      }
    }, 2000);
    setTimeout(() => {
      clearInterval(interval);
      resolve(Array.from(scannedTags));
    }, duration);
  });
}
