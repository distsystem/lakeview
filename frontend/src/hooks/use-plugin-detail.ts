import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function usePluginDetail(
  root: string,
  path: string,
  key: string | null,
) {
  return useQuery({
    queryKey: ["plugin-detail", root, path, key],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{root}/{path}/view/{key}", {
        params: { path: { root, path, key: key! } },
      });
      return data!;
    },
    enabled: !!root && !!path && key !== null,
  });
}
