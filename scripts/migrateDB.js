// scripts/migrateDB.js
import mongoose from 'mongoose';
import dotenv from 'dotenv';

dotenv.config();

mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/agentos', {
  useNewUrlParser: true,
  useUnifiedTopology: true
})
  .then(() => {
    console.log('Conectado ao MongoDB');
    // Executar migrações ou seeds aqui
    process.exit(0);
  })
  .catch(err => {
    console.error('Erro na conexão com o MongoDB', err);
    process.exit(1);
  });
