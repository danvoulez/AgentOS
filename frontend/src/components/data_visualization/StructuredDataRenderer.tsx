import React from "react";
import { motion } from "framer-motion";
import { detectDataType, StructuredDataType } from "./detectDataType";
import DataTable from "./DataTable";
import ExplicitTable from "./ExplicitTable";
import DataList from "./DataList";
import KeyValueBlock from "./KeyValueBlock";
import VisualFallback from "./VisualFallback";

interface StructuredDataRendererProps {
  data: any;
}

const componentMap: Record<StructuredDataType, React.ElementType> = {
  DataTable: DataTable,
  ExplicitTable: ExplicitTable,
  DataList: DataList,
  KeyValueBlock: KeyValueBlock,
  VisualFallback: VisualFallback,
};

const StructuredDataRenderer: React.FC<StructuredDataRendererProps> = ({ data }) => {
  const dataType = detectDataType(data);
  const ComponentToRender = componentMap[dataType];

  const motionVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "circOut" } },
  };
  
  // Prepare props for VisualFallback if that's the type
  const fallbackProps = dataType === "VisualFallback"
    ? { 
        dataType: typeof data, 
        message: (data === null || data === undefined) ? "No data provided." : "Unsupported data format." 
      }
    : {};

  return (
    <motion.div
      className="mosaic-motion-item"
      variants={motionVariants}
      initial="hidden"
      animate="visible"
      layout // Smooth layout changes if data/type changes
    >
      {ComponentToRender ? (
        <ComponentToRender data={data} {...fallbackProps} />
      ) : (
        <VisualFallback dataType="unknown" message="Cannot determine data type." />
      )}
    </motion.div>
  );
};

export default StructuredDataRenderer;