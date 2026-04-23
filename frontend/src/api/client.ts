import createClient from "openapi-fetch";
import type { paths, components } from "./types";

export const api = createClient<paths>({ baseUrl: "/" });

export type ColumnInfo = components["schemas"]["ColumnInfo"];
export type AgentRunStats = components["schemas"]["AgentRunStats"];
export type AgentRunSidebar = components["schemas"]["AgentRunSidebar"];
