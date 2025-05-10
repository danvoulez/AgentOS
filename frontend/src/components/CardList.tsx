import React from 'react';
import { ListData } from '../../types/rendering';
import { motion } from 'framer-motion';
import TooltipHeader from './TooltipHeader';

interface CardListProps {
  data: ListData;
  columns?: number;
}

const CardList: React.FC<CardListProps> = ({ data, columns }) => {
  if (!data || data.length === 0) return <p>Nenhum card para exibir.</p>;
  const gridStyle: React.CSSProperties = {};
  if (columns) gridStyle.gridTemplateColumns = `repeat(${columns}, 1fr)`;

  return (
    <motion.div className="card-list" style={gridStyle} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {data.map((cardData, index) => (
        <motion.div
          key={cardData.id || index}
          className="card-list-item"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: index * 0.07 }}
        >
          <TooltipHeader title={cardData.title || cardData.name} tooltipText={cardData.tooltip} />
          {Object.entries(cardData).map(([key, value]) => {
            if (key === 'id' || key === 'title' || key === 'name' || key === 'tooltip') return null;
            return <p key={key}><strong style={{textTransform: 'capitalize'}}>{key.replace(/_/g, ' ')}:</strong> {String(value)}</p>;
          })}
        </motion.div>
      ))}
    </motion.div>
  );
};
export default CardList;