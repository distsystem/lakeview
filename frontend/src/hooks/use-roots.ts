import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useRoots() {
  return useQuery({
    queryKey: ["roots"],
    queryFn: async () => {
      const { data } = await api.GET("/api/roots");
      return data!;
    },
    staleTime: Infinity,
  });
}
