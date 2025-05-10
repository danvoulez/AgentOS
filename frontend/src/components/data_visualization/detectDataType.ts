export type StructuredDataType =
  | "DataTable"
  | "ExplicitTable"
  | "DataList"
  | "KeyValueBlock"
  | "VisualFallback";

export function detectDataType(data: any): StructuredDataType {
  if (data === null || data === undefined) {
    return "VisualFallback";
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      // Could be an empty table or list. Default to list for simple display.
      return "DataList";
    }
    // If all elements are objects (and not null), treat as DataTable
    if (data.every((item) => typeof item === "object" && item !== null && !Array.isArray(item))) {
      return "DataTable";
    }
    // Otherwise, it's a list of primitives or mixed types
    return "DataList";
  }

  if (typeof data === "object") {
    // Check for explicit table structure: { headers: [], rows: [[]] }
    if (
      Object.prototype.hasOwnProperty.call(data, "headers") &&
      Array.isArray(data.headers) &&
      data.headers.every((h: any) => typeof h === 'string') &&
      Object.prototype.hasOwnProperty.call(data, "rows") &&
      Array.isArray(data.rows) &&
      (data.rows.length === 0 || data.rows.every((r: any) => Array.isArray(r)))
    ) {
      return "ExplicitTable";
    }
    // Otherwise, it's a key-value object
    return "KeyValueBlock";
  }

  // For primitive types (string, number, boolean) that aren't structured
  // It's better to show them in a KeyValueBlock if they are part of a larger structure,
  // but if passed directly to StructuredDataRenderer, fallback might be appropriate.
  // However, the original StructuredDataRenderer stringified them, which KeyValueBlock can handle.
  // Let's send them to KeyValueBlock as a single value. Or Fallback if we want to be stricter.
  // For now, let's treat them as "unknown" for the router to decide or fallback directly.
  return "VisualFallback"; // Fallback for primitives passed directly.
}