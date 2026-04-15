import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useRows(dbPath: string, offset: number = 0, limit: number = 50) {
  return useQuery({
    queryKey: ["rows", dbPath, offset, limit],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{db_path}/rows", {
        params: {
          path: { db_path: dbPath },
          query: { offset, limit },
        },
      });
      return data!;
    },
  });
}
