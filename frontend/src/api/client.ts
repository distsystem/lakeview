import createClient from "openapi-fetch";
import type { paths, components } from "./types";

export const api = createClient<paths>({ baseUrl: "/" });

// Re-export common schema types
export type DatasetEntry = components["schemas"]["DatasetEntry"];
export type RowSummary = components["schemas"]["RowSummary"];
export type Stats = components["schemas"]["Stats"];
export type RowListResponse = components["schemas"]["RowListResponse"];
export type RunDetailResponse = components["schemas"]["RunDetailResponse"];
