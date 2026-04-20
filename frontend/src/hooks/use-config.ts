import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const { data } = await api.GET("/api/config");
      return data!;
    },
    staleTime: Infinity,
  });
}
