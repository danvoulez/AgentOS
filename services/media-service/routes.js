 
// services/media-service/routes.js
import express from 'express';
import { uploadMedia, getMedia } from './controllers.js';

const router = express.Router();

router.post('/upload', uploadMedia);
router.get('/:id', getMedia);

export default router;
