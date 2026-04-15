import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useDatasetInfo(dbPath: string) {
  return useQuery({
    queryKey: ["dataset-info", dbPath],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{db_path}/info", {
        params: { path: { db_path: dbPath } },
      });
      return data!;
    },
  });
}
