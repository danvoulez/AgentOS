import React from 'react';
import { motion } from 'framer-motion';

interface VisualFallbackProps {
  data: any;
  message?: string;
}

const VisualFallback: React.FC<VisualFallbackProps> = ({ data, message }) => (
  <motion.div 
    style={{ padding: 'var(--spacing-md)', border: '1px dashed var(--theme-border-color)', background: 'var(--theme-background-color)'}}
    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
  >
    <p>{message || "Não foi possível determinar um formato visual otimizado. Exibindo dados brutos:"}</p>
    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 'var(--font-size-sm)' }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  </motion.div>
);
export default VisualFallback;