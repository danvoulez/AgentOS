import React from 'react';
import { KeyValueData } from '../../types/rendering';
import { motion } from 'framer-motion';

interface KeyValueBlockProps {
  data: KeyValueData;
}

const KeyValueBlock: React.FC<KeyValueBlockProps> = ({ data }) => {
  if (!data || Object.keys(data).length === 0) return <p>Nenhum dado chave-valor para exibir.</p>;
  return (
    <motion.div className="kv-block" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <dl>
        {Object.entries(data).map(([key, value], index) => (
          <React.Fragment key={key}>
            <motion.dt
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
            </motion.dt>
            <motion.dd
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              {typeof value === 'object' ? JSON.stringify(value) : String(value ?? '')}
            </motion.dd>
          </React.Fragment>
        ))}
      </dl>
    </motion.div>
  );
};
export default KeyValueBlock;