 
// services/access-control/routes.js
import express from 'express';
import { authenticateAccess } from './controllers.js';

const router = express.Router();

router.post('/authenticate', authenticateAccess);

export default router;
