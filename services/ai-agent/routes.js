 
// services/ai-agent/routes.js
import express from 'express';
import { processAIRequest } from './controllers.js';

const router = express.Router();

router.post('/analyze', processAIRequest);

export default router;
