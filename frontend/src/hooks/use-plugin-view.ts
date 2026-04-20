import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function usePluginView(
  root: string,
  path: string,
  offset: number = 0,
  limit: number = 200,
  filter: string = "all",
) {
  return useQuery({
    queryKey: ["plugin-view", root, path, offset, limit, filter],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{root}/{path}/view", {
        params: {
          path: { root, path },
          query: { offset, limit, filter },
        },
      });
      return data!;
    },
    enabled: !!root && !!path,
    refetchInterval: 10_000,
  });
}
