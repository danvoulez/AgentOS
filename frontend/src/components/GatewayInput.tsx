import React, { useState } from 'react';

interface GatewayInputProps {
  onSubmit: (text: string, currentConversationId?: string | null) => Promise<void>;
  isProcessing: boolean;
}

const GatewayInput: React.FC<GatewayInputProps> = ({ onSubmit, isProcessing }) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    onSubmit(inputText);
    setInputText('');
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', marginTop: '1rem' }}>
      <input
        type="text"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Digite seu comando ou pergunta..."
        disabled={isProcessing}
        style={{ flexGrow: 1, padding: '0.75rem', marginRight: '0.5rem' }}
      />
      <button type="submit" disabled={isProcessing || !inputText.trim()} style={{ padding: '0.75rem 1rem' }}>
        {isProcessing ? 'Processando...' : 'Enviar'}
      </button>
    </form>
  );
};

export default GatewayInput;