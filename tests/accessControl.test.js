// tests/accessControl.test.js
import request from 'supertest';
import express from 'express';
import accessRoutes from '../services/access-control/routes.js';

const app = express();
app.use(express.json());
app.use('/access', accessRoutes);

test('POST /access/authenticate should authorize access', async () => {
  const res = await request(app).post('/access/authenticate').send({ user: 'test' });
  expect(res.statusCode).toEqual(200);
  expect(res.body.success).toBeTruthy();
});
