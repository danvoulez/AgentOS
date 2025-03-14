 
// services/media-service/index.js
import express from 'express';
import dotenv from 'dotenv';
import mediaRoutes from './routes.js';

dotenv.config();
const app = express();
app.use(express.json());
app.use('/media', mediaRoutes);

const PORT = process.env.MEDIA_PORT || 3003;
app.listen(PORT, () => console.log(`Media Service rodando na porta ${PORT}`));
