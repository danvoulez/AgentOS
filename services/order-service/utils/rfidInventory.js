// services/order-service/utils/rfidInventory.js
import { readYanpodoTag } from './yanpodoReader.js';

export async function readRFIDProduct() {
  try {
    const tag = await readYanpodoTag();
    return tag;
  } catch (error) {
    console.error("Erro na leitura de RFID para produto:", error);
    throw error;
  }
}
