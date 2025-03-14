 
// services/ai-agent/index.js
import express from 'express';
import dotenv from 'dotenv';
import aiRoutes from './routes.js';

dotenv.config();
const app = express();
app.use(express.json());
app.use('/ai', aiRoutes);

const PORT = process.env.AI_PORT || 3005;
app.listen(PORT, () => console.log(`AI Service rodando na porta ${PORT}`));
