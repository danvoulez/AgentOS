
// services/people-service/controllers.js
export function getPeople(req, res) {
  res.json([{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }]);
}

export function createPerson(req, res) {
  const { name, email } = req.body;
  res.status(201).json({ id: Date.now(), name, email });
}

// Autenticação via RFID para pessoas
export function rfidAuthenticate(req, res) {
  const { rfid } = req.body;
  if (!rfid) {
    return res.status(400).json({ message: "RFID não fornecido" });
  }
  res.json({ success: true, message: "Pessoa autenticada via RFID", rfid });
}
