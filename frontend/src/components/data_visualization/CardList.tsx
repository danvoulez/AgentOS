import React from 'react';

const CardList: React.FC<{ data: any[] }> = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) return <div>Nenhum card disponível.</div>;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
      {data.map((item, idx) => (
        <div key={idx} style={{ border: '1.5px solid #09c', borderRadius: 8, padding: 14, minWidth: 210, background: '#eef9fa' }}>
          {Object.entries(item).map(([k, v]) => (
            <div key={k}><strong>{k}:</strong> {String(v)}</div>
          ))}
        </div>
      ))}
    </div>
  );
};
export default CardList;