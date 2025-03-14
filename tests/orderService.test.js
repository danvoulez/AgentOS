// tests/orderService.test.js
import request from 'supertest';
import express from 'express';
import orderRoutes from '../services/order-service/routes.js';

const app = express();
app.use(express.json());
app.use('/order', orderRoutes);

test('GET /order should return a list of orders', async () => {
  const res = await request(app).get('/order');
  expect(res.statusCode).toEqual(200);
  expect(Array.isArray(res.body)).toBeTruthy();
});
