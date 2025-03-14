// tests/integration/services/peopleService.test.js
const request = require('supertest');
const express = require('express');
const mongoose = require('mongoose');
const peopleRoutes = require('../../../services/people-service/routes');
const { connectDB } = require('../../../common/config/database');

// Create Express app for testing
const app = express();
app.use(express.json());
app.use('/api/people', peopleRoutes);

describe('People Service Integration Tests', () => {
  // Connect to test database before tests
  beforeAll(async () => {
    await connectDB();
  });
  
  // Clear test data after each test
  afterEach(async () => {
    if (mongoose.connection.readyState === 1) {
      const collections = await mongoose.connection.db.collections();
      for (let collection of collections) {
        await collection.deleteMany({});
      }
    }
  });
  
  // Disconnect after all tests
  afterAll(async () => {
    await mongoose.connection.close();
  });
  
  test('GET /api/people should return empty array initially', async () => {
    const res = await request(app).get('/api/people');
    
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual([]);
  });
  
  test('POST /api/people should create a new person', async () => {
    const personData = {
      name: 'John Doe',
      email: 'john@example.com',
      phone: '123-456-7890'
    };
    
    const res = await request(app)
      .post('/api/people')
      .send(personData);
    
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('_id');
    expect(res.body.name).toBe(personData.name);
    expect(res.body.email).toBe(personData.email);
  });
  
  test('GET /api/people/:id should return a specific person', async () => {
    // First create a person
    const personData = {
      name: 'Jane Smith',
      email: 'jane@example.com',
      phone: '987-654-3210'
    };
    
    const createRes = await request(app)
      .post('/api/people')
      .send(personData);
    
    const personId = createRes.body._id;
    
    // Then get the person by ID
    const getRes = await request(app).get(`/api/people/${personId}`);
    
    expect(getRes.statusCode).toBe(200);
    expect(getRes.body._id).toBe(personId);
    expect(getRes.body.name).toBe(personData.name);
  });
  
  test('PUT /api/people/:id should update a person', async () => {
    // First create a person
    const personData = {
      name: 'Bob Johnson',
      email: 'bob@example.com',
      phone: '555-123-4567'
    };
    
    const createRes = await request(app)
      .post('/api/people')
      .send(personData);
    
    const personId = createRes.body._id;
    
    // Then update the person
    const updateData = {
      name: 'Robert Johnson',
      email: 'robert@example.com'
    };
    
    const updateRes = await request(app)
      .put(`/api/people/${personId}`)
      .send(updateData);
    
    expect(updateRes.statusCode).toBe(200);
    expect(updateRes.body.name).toBe(updateData.name);
    expect(updateRes.body.email).toBe(updateData.email);
    expect(updateRes.body.phone).toBe(personData.phone); // Should not change
  });
  
  test('DELETE /api/people/:id should delete a person', async () => {
    // First create a person
    const personData = {
      name: 'Alice Brown',
      email: 'alice@example.com'
    };
    
    const createRes = await request(app)
      .post('/api/people')
      .send(personData);
    
    const personId = createRes.body._id;
    
    // Then delete the person
    const deleteRes = await request(app).delete(`/api/people/${personId}`);
    
    expect(deleteRes.statusCode).toBe(200);
    expect(deleteRes.body.success).toBe(true);
    
    // Verify the person is deleted
    const getRes = await request(app).get(`/api/people/${personId}`);
    expect(getRes.statusCode).toBe(404);
  });
});
