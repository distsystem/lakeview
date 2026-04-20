import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useDatasetInfo(root: string, path: string) {
  return useQuery({
    queryKey: ["dataset-info", root, path],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{root}/{path}/info", {
        params: { path: { root, path } },
      });
      return data!;
    },
    enabled: !!root && !!path,
  });
}
