// tests/e2e/flows/rfidWorkflow.test.js
const request = require('supertest');
const { app } = require('../../../src/core/app');
const mongoose = require('mongoose');
const { connectDB } = require('../../../common/config/database');
const jwt = require('jsonwebtoken');

describe('RFID Management End-to-End Flow', () => {
  let authToken;
  let createdPersonId;
  let createdRfidId;
  
  // Connect to test database and create test user before tests
  beforeAll(async () => {
    await connectDB();
    
    // Create test admin user and generate token
    authToken = jwt.sign(
      { id: 'admin-user-id', role: 'admin' },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: '1h' }
    );
  });
  
  // Clear test data after all tests
  afterAll(async () => {
    if (mongoose.connection.readyState === 1) {
      const collections = await mongoose.connection.db.collections();
      for (let collection of collections) {
        await collection.deleteMany({});
      }
    }
    await mongoose.connection.close();
  });
  
  test('Complete RFID management workflow', async () => {
    // Step 1: Create a new person
    const personData = {
      name: 'Test User',
      email: 'test@example.com',
      phone: '123-456-7890',
      department: 'Engineering'
    };
    
    const createPersonRes = await request(app)
      .post('/api/people')
      .set('Authorization', `Bearer ${authToken}`)
      .send(personData);
    
    expect(createPersonRes.statusCode).toBe(201);
    createdPersonId = createPersonRes.body._id;
    
    // Step 2: Register a new RFID card
    const rfidData = {
      cardId: 'RFID12345',
      cardType: 'employee',
      isActive: true
    };
    
    const createRfidRes = await request(app)
      .post('/api/access/rfid')
      .set('Authorization', `Bearer ${authToken}`)
      .send(rfidData);
    
    expect(createRfidRes.statusCode).toBe(201);
    createdRfidId = createRfidRes.body._id;
    
    // Step 3: Assign RFID card to person
    const assignRes = await request(app)
      .post(`/api/access/rfid/${createdRfidId}/assign`)
      .set('Authorization', `Bearer ${authToken}`)
      .send({ personId: createdPersonId });
    
    expect(assignRes.statusCode).toBe(200);
    expect(assignRes.body.assignedTo).toBe(createdPersonId);
    
    // Step 4: Verify person has RFID card assigned
    const getPersonRes = await request(app)
      .get(`/api/people/${createdPersonId}`)
      .set('Authorization', `Bearer ${authToken}`);
    
    expect(getPersonRes.statusCode).toBe(200);
    expect(getPersonRes.body.rfidCards).toContain(createdRfidId);
    
    // Step 5: Simulate RFID scan for access
    const accessRes = await request(app)
      .post('/api/access/authenticate')
      .send({ cardId: 'RFID12345' });
    
    expect(accessRes.statusCode).toBe(200);
    expect(accessRes.body.access).toBe(true);
    expect(accessRes.body.person.name).toBe(personData.name);
    
    // Step 6: Deactivate RFID card
    const deactivateRes = await request(app)
      .put(`/api/access/rfid/${createdRfidId}`)
      .set('Authorization', `Bearer ${authToken}`)
      .send({ isActive: false });
    
    expect(deactivateRes.statusCode).toBe(200);
    expect(deactivateRes.body.isActive).toBe(false);
    
    // Step 7: Verify access is denied with deactivated card
    const deniedAccessRes = await request(app)
      .post('/api/access/authenticate')
      .send({ cardId: 'RFID12345' });
    
    expect(deniedAccessRes.statusCode).toBe(403);
    expect(deniedAccessRes.body.access).toBe(false);
    expect(deniedAccessRes.body.message).toContain('inactive');
    
    // Step 8: Unassign RFID card from person
    const unassignRes = await request(app)
      .post(`/api/access/rfid/${createdRfidId}/unassign`)
      .set('Authorization', `Bearer ${authToken}`);
    
    expect(unassignRes.statusCode).toBe(200);
    expect(unassignRes.body.assignedTo).toBeNull();
    
    // Step 9: Delete RFID card
    const deleteRfidRes = await request(app)
      .delete(`/api/access/rfid/${createdRfidId}`)
      .set('Authorization', `Bearer ${authToken}`);
    
    expect(deleteRfidRes.statusCode).toBe(200);
    
    // Step 10: Delete person
    const deletePersonRes = await request(app)
      .delete(`/api/people/${createdPersonId}`)
      .set('Authorization', `Bearer ${authToken}`);
    
    expect(deletePersonRes.statusCode).toBe(200);
  });
});
