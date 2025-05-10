import React from 'react';
import { TableData } from '../../types/rendering';
import { motion } from 'framer-motion';

interface DataTableProps {
  data: TableData;
  headers?: { key: string; label: string }[];
}

const DataTable: React.FC<DataTableProps> = ({ data, headers }) => {
  if (!data || data.length === 0) return <p>Nenhum dado para exibir na tabela.</p>;
  const actualHeaders = headers || Object.keys(data[0]).map(key => ({ key, label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) }));

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <table className="data-table">
        <thead>
          <tr>
            {actualHeaders.map(header => <th key={header.key}>{header.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <motion.tr 
              key={rowIndex}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: rowIndex * 0.05 }}
            >
              {actualHeaders.map(header => (
                <td key={`${rowIndex}-${header.key}`}>{String(row[header.key] ?? '')}</td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
};
export default DataTable;