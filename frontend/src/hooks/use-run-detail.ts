import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useRunDetail(dbPath: string, key: string | null) {
  return useQuery({
    queryKey: ["run", dbPath, key],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{db_path}/runs/{key}", {
        params: { path: { db_path: dbPath, key: key! } },
      });
      return data!;
    },
    enabled: key !== null,
  });
}
