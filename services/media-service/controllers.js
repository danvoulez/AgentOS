 
// services/media-service/controllers.js
export function uploadMedia(req, res) {
  res.json({ success: true, message: 'Mídia enviada com sucesso' });
}

export function getMedia(req, res) {
  res.json({ id: req.params.id, url: `https://storage.example.com/${req.params.id}` });
}
