import React from 'react';
import { motion } from 'framer-motion';

interface ExplicitTableHeader {
  key: string;
  label: string;
  align?: 'left' | 'center' | 'right';
}
interface ExplicitTableRow extends Record<string, any> {}
interface ExplicitTableProps {
  data: {
    headers: ExplicitTableHeader[];
    rows: ExplicitTableRow[];
  };
}

const ExplicitTable: React.FC<ExplicitTableProps> = ({ data }) => {
  if (!data || !data.headers || !data.rows || data.rows.length === 0) {
    return <p>Nenhum dado para exibir na tabela explícita.</p>;
  }
  const { headers, rows } = data;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <table className="data-table explicit-table">
        <thead>
          <tr>
            {headers.map(header => (
              <th key={header.key} style={{ textAlign: header.align || 'left' }}>
                {header.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <motion.tr 
              key={rowIndex}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: rowIndex * 0.05 }}
            >
              {headers.map(header => (
                <td key={`${rowIndex}-${header.key}`} style={{ textAlign: header.align || 'left' }}>
                  {String(row[header.key] ?? '')}
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
};
export default ExplicitTable;