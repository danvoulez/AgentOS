// tests/peopleService.test.js
import request from 'supertest';
import express from 'express';
import peopleRoutes from '../services/people-service/routes.js';

const app = express();
app.use(express.json());
app.use('/people', peopleRoutes);

test('GET /people should return a list of people', async () => {
  const res = await request(app).get('/people');
  expect(res.statusCode).toEqual(200);
  expect(Array.isArray(res.body)).toBeTruthy();
});
