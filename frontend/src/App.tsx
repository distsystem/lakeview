import { BrowserRouter, Routes, Route } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DatasetList } from "@/components/dataset-list";
import { DatasetView } from "@/components/dataset-view";

const queryClient = new QueryClient();

function Topbar() {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b h-12">
      <a href="/" className="font-mono font-bold tracking-wider text-sm no-underline">
        LAKEVIEW
      </a>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Topbar />
        <Routes>
          <Route path="/" element={<DatasetList />} />
          <Route path="/*" element={<DatasetView />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
