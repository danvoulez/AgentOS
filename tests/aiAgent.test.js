// tests/aiAgent.test.js
import request from 'supertest';
import express from 'express';
import aiRoutes from '../services/ai-agent/routes.js';

const app = express();
app.use(express.json());
app.use('/ai', aiRoutes);

test('POST /ai/analyze should process AI request', async () => {
  const res = await request(app).post('/ai/analyze').send({ input: 'Test data' });
  expect(res.statusCode).toEqual(200);
  expect(res.body.success).toBeTruthy();
});
