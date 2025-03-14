// services/order-service/utils/chafonReader.js
export async function readChafonTag() {
  return new Promise((resolve) => {
    setTimeout(() => {
      const tag = "NFC" + Math.floor(Math.random() * 1000000);
      resolve({ success: true, tag });
    }, 1000);
  });
}
