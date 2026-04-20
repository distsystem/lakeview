import type { ComponentType } from "react";
import { AgentRunSidebar } from "./agent-run/sidebar";
import { AgentRunDetail } from "./agent-run/detail";

interface PluginComponents {
  Sidebar: ComponentType<{
    root: string;
    path: string;
    selectedKey?: string | null;
  }>;
  Detail: ComponentType<{ root: string; path: string; runKey: string }>;
}

const plugins: Record<string, PluginComponents> = {
  agent_run: {
    Sidebar: AgentRunSidebar,
    Detail: AgentRunDetail,
  },
};

export function getPlugin(name: string): PluginComponents | undefined {
  return plugins[name];
}
