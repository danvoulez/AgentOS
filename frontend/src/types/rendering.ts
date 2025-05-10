export type TableData = Record<string, any>[];
export type KeyValueData = Record<string, any>;
export type ListData = Record<string, any>[];

export type ContentLayoutHint =
  | 'table'
  | 'key_value_list'
  | 'item_list'
  | 'card_grid'
  | 'flow'
  | 'raw_json'
  | 'text_block';

export type BlockStyleHint = 'default' | 'highlight' | 'minimal' | 'warning' | 'info';
export type VisualHint = 'compact' | 'spacious' | 'interactive';

export interface RenderHeuristics {
  contentLayout: ContentLayoutHint;
  blockStyle: BlockStyleHint;
  visualHint: VisualHint | null;
  padding: string;
  shouldAnimate: boolean;
  columns?: number;
}

export interface DisplayMetaFromAPI {
  title?: string;
  tooltip?: string;
  layoutHint?: ContentLayoutHint | 'auto';
  styleHint?: BlockStyleHint;
  isCompact?: boolean;
}

export interface DataForRendering {
  data: any;
  meta?: DisplayMetaFromAPI | null;
}