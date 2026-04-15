import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useDatasets(prefix: string) {
  return useQuery({
    queryKey: ["datasets", prefix],
    queryFn: async () => {
      const { data } = await api.GET("/api/datasets", {
        params: { query: { prefix } },
      });
      return data!;
    },
  });
}
