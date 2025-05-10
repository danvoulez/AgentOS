import React from 'react';
import { DataForRendering, RenderHeuristics } from '../../types/rendering';
import { useRenderHeuristics } from '../../hooks/useRenderHeuristics';
import StructuredDataRenderer from '../StructuredDataRenderer';
import TooltipHeader from './TooltipHeader';
import { motion, AnimatePresence } from 'framer-motion';

interface SmartBlockProps extends DataForRendering {
  isLoading?: boolean;
}

const SmartBlock: React.FC<SmartBlockProps> = ({ data, meta, isLoading }) => {
  const heuristics: RenderHeuristics = useRenderHeuristics({ data, meta });

  const blockVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
    exit: { opacity: 0, y: -20, transition: { duration: 0.3, ease: "easeIn" } }
  };

  if (isLoading) {
    return <div className="smart-block" style={{padding: heuristics.padding}}>Carregando dados do bloco...</div>;
  }

  if (data === null || data === undefined || (Array.isArray(data) && data.length === 0) || (typeof data === 'object' && Object.keys(data).length === 0 && !(data instanceof Date))) {
    if (heuristics.blockStyle === 'minimal' && meta?.title) {
       return (
         <motion.div
          className={`smart-block smart-block-style-${heuristics.blockStyle}`}
          style={{ padding: heuristics.padding }}
          variants={heuristics.shouldAnimate ? blockVariants : undefined}
          initial={heuristics.shouldAnimate ? "hidden" : undefined}
          animate={heuristics.shouldAnimate ? "visible" : undefined}
          exit={heuristics.shouldAnimate ? "exit" : undefined}
         >
          <TooltipHeader title={meta.title} tooltipText={meta.tooltip} />
         </motion.div>
       );
    }
    return null;
  }

  return (
    <AnimatePresence>
      {heuristics.shouldAnimate ? (
         <motion.div
          key={meta?.title || JSON.stringify(data).substring(0,50)}
          className={`smart-block smart-block-style-${heuristics.blockStyle}`}
          style={{ padding: heuristics.padding }}
          variants={blockVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <TooltipHeader title={meta?.title} tooltipText={meta?.tooltip} />
          <StructuredDataRenderer data={data} layoutHint={heuristics.contentLayout} columns={heuristics.columns} />
        </motion.div>
      ) : (
        <div
          className={`smart-block smart-block-style-${heuristics.blockStyle}`}
          style={{ padding: heuristics.padding }}
        >
          <TooltipHeader title={meta?.title} tooltipText={meta?.tooltip} />
          <StructuredDataRenderer data={data} layoutHint={heuristics.contentLayout} columns={heuristics.columns} />
        </div>
      )}
    </AnimatePresence>
  );
};

export default SmartBlock;