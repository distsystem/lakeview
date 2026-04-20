import { BrowserRouter, Navigate, Routes, Route } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import { DatasetPage } from "@/components/dataset-page";
import { CommandPalette } from "@/components/command-palette";
import { RootSwitcher } from "@/components/root-switcher";
import { useRoots } from "@/hooks/use-roots";

const queryClient = new QueryClient();

function Topbar() {
  return (
    <div className="flex items-center gap-3 px-4 h-12">
      <a href="/" className="font-mono font-bold tracking-wider text-sm no-underline">
        LAKEVIEW
      </a>
      <RootSwitcher />
      <div className="ml-auto">
        <kbd className="hidden sm:inline-flex items-center gap-1 rounded border bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
          <span className="text-xs">⌘</span>K
        </kbd>
      </div>
    </div>
  );
}

function RootRedirect() {
  const { data } = useRoots();
  if (!data) return null;
  if (!data.default) return <div className="p-6 text-sm text-muted-foreground">No roots configured.</div>;
  return <Navigate to={`/${data.default}`} replace />;
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
            <Route path="/" element={<RootRedirect />} />
            <Route path="/:root" element={<DatasetPage />} />
            <Route path="/:root/*" element={<DatasetPage />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
