import React from 'react';
import { ContentLayoutHint, LLMStructuredDataContent } from '../types/rendering';
import DataTable from './data_visualization/DataTable';
import ExplicitTable from './data_visualization/ExplicitTable';
import KeyValueBlock from './data_visualization/KeyValueBlock';
import DataList from './data_visualization/DataList';
import CardList from './adaptive_renderer/CardList';
import VisualFallback from './data_visualization/VisualFallback';

interface StructuredDataRendererProps {
  data: LLMStructuredDataContent | Record<string, any>;
  layoutHint?: ContentLayoutHint | null;
  columns?: number;
}

const detectTypeForRender = (data: LLMStructuredDataContent | Record<string, any>, hint?: ContentLayoutHint | null): ContentLayoutHint => {
  if (hint && hint !== 'auto') return hint;
  if (data && typeof data === 'object') {
    if ('table_data' in data && Array.isArray(data.table_data)) return 'table';
    if ('key_value_data' in data && typeof data.key_value_data === 'object' && data.key_value_data !== null) return 'key_value_list';
    if ('list_data' in data && Array.isArray(data.list_data)) return 'item_list';
    if ('raw_json_data' in data) return 'raw_json';
    if (Array.isArray(data)) {
      if (data.length > 0 && typeof data[0] === 'object') return 'table';
      return 'item_list';
    }
    return 'key_value_list';
  }
  return 'raw_json';
};

const StructuredDataRenderer: React.FC<StructuredDataRendererProps> = ({ data, layoutHint, columns }) => {
  if (data === null || data === undefined) {
    return <VisualFallback data={data} message="Nenhum dado estruturado para exibir." />;
  }
  const actualDataToRender = (data as LLMStructuredDataContent)?.table_data ||
                             (data as LLMStructuredDataContent)?.key_value_data ||
                             (data as LLMStructuredDataContent)?.list_data ||
                             (data as LLMStructuredDataContent)?.raw_json_data ||
                             data;
  const effectiveLayout = detectTypeForRender(data, layoutHint);

  switch (effectiveLayout) {
    case 'table':
      if (Array.isArray(actualDataToRender) && actualDataToRender.every(item => typeof item === 'object')) {
        return <DataTable data={actualDataToRender} />;
      }
      return <VisualFallback data={actualDataToRender} message="Dados de tabela esperados, mas formato incorreto."/>;
    case 'key_value_list':
      if (typeof actualDataToRender === 'object' && !Array.isArray(actualDataToRender) && actualDataToRender !== null) {
        return <KeyValueBlock data={actualDataToRender} />;
      }
      return <VisualFallback data={actualDataToRender} message="Dados chave-valor esperados, mas formato incorreto."/>;
    case 'item_list':
      if (Array.isArray(actualDataToRender)) {
        return <DataList data={actualDataToRender} />;
      }
      return <VisualFallback data={actualDataToRender} message="Dados de lista esperados, mas formato incorreto."/>;
    case 'card_grid':
      if (Array.isArray(actualDataToRender)) {
        return <CardList data={actualDataToRender} columns={columns} />;
      }
      return <VisualFallback data={actualDataToRender} message="Dados para grid de cards esperados, mas formato incorreto."/>;
    case 'text_block':
       if (typeof actualDataToRender === 'string') {
           return <p>{actualDataToRender}</p>;
       }
       return <VisualFallback data={actualDataToRender} message="Bloco de texto esperado, mas formato incorreto."/>;
    case 'raw_json':
    default:
      return <VisualFallback data={actualDataToRender} />;
  }
};

export default StructuredDataRenderer;