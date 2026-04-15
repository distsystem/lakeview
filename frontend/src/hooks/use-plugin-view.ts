import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function usePluginView(
  dbPath: string,
  offset: number = 0,
  limit: number = 200,
  filter: string = "all",
) {
  return useQuery({
    queryKey: ["plugin-view", dbPath, offset, limit, filter],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{db_path}/view", {
        params: {
          path: { db_path: dbPath },
          query: { offset, limit, filter },
        },
      });
      return data!;
    },
    refetchInterval: 10_000,
  });
}
