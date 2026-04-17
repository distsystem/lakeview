import { BrowserRouter, Routes, Route } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import { DatasetList } from "@/components/dataset-list";
import { DatasetView } from "@/components/dataset-view";
import { CommandPalette } from "@/components/command-palette";

const queryClient = new QueryClient();

function Topbar() {
  return (
    <div className="flex items-center justify-between px-4 h-12">
      <a href="/" className="font-mono font-bold tracking-wider text-sm no-underline">
        LAKEVIEW
      </a>
      <kbd className="hidden sm:inline-flex items-center gap-1 rounded border bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
        <span className="text-xs">⌘</span>K
      </kbd>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Topbar />
          <Separator />
          <CommandPalette />
          <Routes>
            <Route path="/" element={<DatasetList />} />
            <Route path="/*" element={<DatasetView />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
