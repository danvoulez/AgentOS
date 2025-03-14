
// services/order-service/index.js
import express from 'express';
import dotenv from 'dotenv';
import orderRoutes from './routes.js';

dotenv.config();
const app = express();
app.use(express.json());
app.use('/order', orderRoutes);

const PORT = process.env.ORDER_PORT || 3004;
app.listen(PORT, () => console.log(`Order Service rodando na porta ${PORT}`));
