// tests/mediaService.test.js
import request from 'supertest';
import express from 'express';
import mediaRoutes from '../services/media-service/routes.js';

const app = express();
app.use(express.json());
app.use('/media', mediaRoutes);

test('POST /media/upload should respond with success message', async () => {
  const res = await request(app).post('/media/upload').send({ file: 'test.mp4' });
  expect(res.statusCode).toEqual(200);
  expect(res.body.success).toBeTruthy();
});
