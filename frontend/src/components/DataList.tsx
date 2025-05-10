import React from 'react';
import { ListData } from '../../types/rendering';
import { motion } from 'framer-motion';

interface DataListProps {
  data: ListData;
}

const DataList: React.FC<DataListProps> = ({ data }) => {
  if (!data || data.length === 0) return <p>Nenhuma lista de dados para exibir.</p>;
  return (
    <motion.div className="data-list" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <ul>
        {data.map((item, index) => (
          <motion.li 
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            {item.name || item.title || item.label || (typeof item === 'object' ? JSON.stringify(item) : String(item))}
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
};
export default DataList;