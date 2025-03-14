 
// services/access-control/index.js
import express from 'express';
import dotenv from 'dotenv';
import accessRoutes from './routes.js';

dotenv.config();
const app = express();
app.use(express.json());
app.use('/access', accessRoutes);

const PORT = process.env.ACCESS_PORT || 3006;
app.listen(PORT, () => console.log(`Access Control rodando na porta ${PORT}`));
