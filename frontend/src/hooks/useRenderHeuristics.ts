import { useMemo } from 'react';
import { DataForRendering, RenderHeuristics, ContentLayoutHint, BlockStyleHint, VisualHint } from '../types/rendering';

const detectDataTypeInternal = (data: any, apiLayoutHint?: ContentLayoutHint | 'auto'): ContentLayoutHint => {
  if (apiLayoutHint && apiLayoutHint !== 'auto') {
    return apiLayoutHint;
  }
  if (Array.isArray(data)) {
    if (data.length === 0) return 'item_list';
    if (typeof data[0] === 'object' && data[0] !== null) {
      const keys = Object.keys(data[0]);
      if (keys.length > 4) return 'table';
      if (data.length > 3) return 'card_grid';
      return 'item_list';
    }
    return 'item_list';
  }
  if (typeof data === 'object' && data !== null) {
    return 'key_value_list';
  }
  if (typeof data === 'string') return 'text_block';
  return 'raw_json';
};

export const useRenderHeuristics = (renderData: DataForRendering): RenderHeuristics => {
  const heuristics = useMemo((): RenderHeuristics => {
    const { data, meta } = renderData;

    let contentLayout: ContentLayoutHint = detectDataTypeInternal(data, meta?.layoutHint);
    let blockStyle: BlockStyleHint = meta?.styleHint || 'default';
    let visualHint: VisualHint | null = meta?.isCompact ? 'compact' : null;
    let padding = meta?.isCompact ? 'var(--spacing-sm)' : 'var(--smartblock-padding-default)';
    let shouldAnimate = true;
    let columns: number | undefined = undefined;

    if (contentLayout === 'table' && (data as any[])?.length > 10) {
      visualHint = visualHint || 'compact';
    }
    if (contentLayout === 'card_grid') {
      const itemCount = (data as any[])?.length || 0;
      if (itemCount <= 2) columns = itemCount;
      else if (itemCount <= 6) columns = 3;
      else columns = 4;
    }
    if (contentLayout === 'key_value_list') {
      const keyCount = Object.keys(data || {}).length;
      if (keyCount > 8 && !visualHint) visualHint = 'compact';
    }
    if (blockStyle === 'minimal') {
      padding = 'var(--spacing-xs)';
    }

    return {
      contentLayout,
      blockStyle,
      visualHint,
      padding,
      shouldAnimate,
      columns,
    };
  }, [renderData]);

  return heuristics;
};