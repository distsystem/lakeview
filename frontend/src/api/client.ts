import createClient from "openapi-fetch";
import type { paths, components } from "./types";

export const api = createClient<paths>({ baseUrl: "/" });

// Re-export common schema types
export type DatasetEntry = components["schemas"]["DatasetEntry"];
export type DatasetInfoResponse = components["schemas"]["DatasetInfoResponse"];
export type ColumnInfo = components["schemas"]["ColumnInfo"];
export type GenericRowListResponse = components["schemas"]["GenericRowListResponse"];
export type PluginViewResponse = components["schemas"]["PluginViewResponse"];
export type PluginDetailResponse = components["schemas"]["PluginDetailResponse"];
