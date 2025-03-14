
// services/people-service/index.js
import express from 'express';
import dotenv from 'dotenv';
import peopleRoutes from './routes.js';

dotenv.config();
const app = express();
app.use(express.json());
app.use('/people', peopleRoutes);

const PORT = process.env.PEOPLE_PORT || 3001;
app.listen(PORT, () => console.log(`People Service rodando na porta ${PORT}`));
