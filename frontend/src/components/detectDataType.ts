export function detectDataType(data: any, layoutHint?: string | null): { type: string } {
  if (layoutHint === 'table' || data?.table_data) return { type: 'table' };
  if (layoutHint === 'kv_list' || data?.key_value_data) return { type: 'kv' };
  if (layoutHint === 'card_list') return { type: 'card_list' };
  if (data?.list_data) return { type: 'list' };
  return { type: 'generic' };
}