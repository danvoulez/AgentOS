
// services/order-service/routes.js
import express from 'express';
import {
  createOrder,
  getOrders,
  addRFIDToInventory,
  bulkRFIDRegister,
  getDashboardData
} from './controllers.js';

const router = express.Router();

router.get('/', getOrders);
router.post('/', createOrder);
router.post('/rfid/inventory', addRFIDToInventory);
router.post('/rfid/bulk', bulkRFIDRegister);
router.get('/dashboard', getDashboardData);

export default router;
