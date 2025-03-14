// services/order-service/utils/yanpodoReader.js
import { exec } from 'child_process';

export async function readYanpodoTag() {
  return new Promise((resolve, reject) => {
    exec('python ./read_yanpodo.py', (error, stdout, stderr) => {
      if (error || stderr) {
        reject(new Error(`Erro no YanpodoReader: ${stderr || error.message}`));
        return;
      }
      try {
        const result = JSON.parse(stdout);
        if (result.success) {
          resolve(result.tag);
        } else {
          reject(new Error('Leitura Yanpodo sem sucesso.'));
        }
      } catch (parseError) {
        reject(new Error('Erro ao parsear resposta do YanpodoReader.'));
      }
    });
  });
}
