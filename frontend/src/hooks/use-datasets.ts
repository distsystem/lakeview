import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useDatasets(root: string, path: string = "") {
  return useQuery({
    queryKey: ["datasets", root, path],
    queryFn: async () => {
      const { data } = await api.GET("/api/datasets", {
        params: { query: { root, path } },
      });
      return data!;
    },
    enabled: !!root,
  });
}
