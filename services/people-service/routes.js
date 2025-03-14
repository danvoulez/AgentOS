
// services/people-service/routes.js
import express from 'express';
import { getPeople, createPerson, rfidAuthenticate } from './controllers.js';

const router = express.Router();

router.get('/', getPeople);
router.post('/', createPerson);
router.post('/rfid', rfidAuthenticate); // Endpoint para autenticação via RFID

export default router;
