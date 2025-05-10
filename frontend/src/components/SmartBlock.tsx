import React from 'react';
import { useRenderHeuristics } from '../hooks/useRenderHeuristics';

interface SmartBlockProps {
  data: any;
  meta?: any;
}

const SmartBlock: React.FC<SmartBlockProps> = ({ data, meta }) => {
  const heuristics = useRenderHeuristics(data, meta);

  return (
    <div
      className={`smart-block smart-block-style-${heuristics.blockStyle}`}
      style={{
        padding: heuristics.padding,
        background: 'var(--mosaic-bg, #f8f9fa)',
        border: '1.5px solid var(--mosaic-border, #d7eaff)',
        borderRadius: 8,
        margin: '1rem 0'
      }}
    >
      {meta?.title && <h4 style={{ marginBottom: 8 }}>{meta.title}</h4>}
      <heuristics.DisplayComponent data={data} displayMeta={meta} />
    </div>
  );
};

export default SmartBlock;