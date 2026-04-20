import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useRows(
  root: string,
  path: string,
  offset: number = 0,
  limit: number = 50,
) {
  return useQuery({
    queryKey: ["rows", root, path, offset, limit],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{root}/{path}/rows", {
        params: {
          path: { root, path },
          query: { offset, limit },
        },
      });
      return data!;
    },
    enabled: !!root && !!path,
  });
}
