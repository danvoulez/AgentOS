
// services/order-service/controllers.js
let orders = [];
let inventory = [];
let salesData = []; // Simulação de vendas

export function createOrder(req, res) {
  const order = { id: Date.now(), ...req.body };
  orders.push(order);
  res.status(201).json({ message: "Pedido criado", order });
}

export function getOrders(req, res) {
  res.json(orders);
}

// Cadastro individual de RFID para produtos (inserido no inventário)
export function addRFIDToInventory(req, res) {
  const { tag, productName } = req.body;
  if (!tag || !productName) {
    return res.status(400).json({ message: "Dados incompletos" });
  }
  if (inventory.find(item => item.tag === tag)) {
    return res.status(400).json({ message: "RFID já cadastrado" });
  }
  const record = { tag, productName, registeredAt: new Date() };
  inventory.push(record);
  res.json({ message: "RFID cadastrado no inventário", record });
}

// Cadastro em bulk de RFID para produtos
export function bulkRFIDRegister(req, res) {
  const { tags, productName } = req.body;
  if (!Array.isArray(tags) || !productName) {
    return res.status(400).json({ message: "Dados inválidos para bulk" });
  }
  const registered = [];
  tags.forEach(tag => {
    if (!inventory.find(item => item.tag === tag)) {
      const record = { tag, productName: `${productName} - ${tag}`, registeredAt: new Date() };
      inventory.push(record);
      registered.push(record);
    }
  });
  res.json({ message: "Bulk RFID cadastrado", registered });
}

// Dashboard: confronto entre inventário RFID e vendas
export function getDashboardData(req, res) {
  if (salesData.length === 0) {
    salesData = inventory.map(item => ({
      tag: item.tag,
      sold: Math.floor(Math.random() * 10)
    }));
  }
  const dashboard = inventory.map(item => {
    const sale = salesData.find(s => s.tag === item.tag) || { sold: 0 };
    return {
      tag: item.tag,
      productName: item.productName,
      registeredAt: item.registeredAt,
      sold: sale.sold,
      inStock: Math.max(0, 100 - sale.sold)
    };
  });
  res.json({ dashboard });
}
