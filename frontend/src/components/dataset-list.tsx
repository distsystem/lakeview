import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useDatasets } from "@/hooks/use-datasets";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export function DatasetList({ prefix: routePrefix }: { prefix?: string }) {
  const [input, setInput] = useState(routePrefix || "sample-data");
  const [prefix, setPrefix] = useState(routePrefix || "sample-data");
  const navigate = useNavigate();
  const { data, isLoading } = useDatasets(prefix);

  if (routePrefix && routePrefix !== prefix) {
    setPrefix(routePrefix);
    setInput(routePrefix);
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-mono font-bold mb-6">lakeview</h1>
      {!routePrefix && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPrefix(input);
          }}
          className="flex gap-2 mb-6"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="local path or s3 prefix"
            className="flex-1 font-mono text-sm"
          />
          <Button type="submit">Browse</Button>
        </form>
      )}
      {routePrefix && (
        <p className="text-muted-foreground text-sm mb-4 font-mono">{prefix}</p>
      )}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      )}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.datasets.map((ds) => {
            const isLance = ds.kind === "lance";
            return (
              <Link
                key={ds.path}
                to={`/${ds.path}`}
                onClick={
                  !isLance
                    ? (e) => {
                        e.preventDefault();
                        navigate(`/?prefix=${encodeURIComponent(ds.path)}`);
                        setPrefix(ds.path);
                        setInput(ds.path);
                      }
                    : undefined
                }
                className="no-underline"
              >
                <Card className="hover:border-foreground/30 transition-colors cursor-pointer">
                  <CardHeader>
                    <CardTitle className="font-mono text-sm">{ds.name}</CardTitle>
                    <CardDescription>
                      {isLance ? (
                        <Badge variant="secondary">
                          {ds.row_count != null ? `${ds.row_count} rows` : "lance"}
                        </Badge>
                      ) : (
                        <Badge variant="outline">dir</Badge>
                      )}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
      {data && data.datasets.length === 0 && (
        <p className="text-muted-foreground">No datasets found under: {data.prefix}</p>
      )}
    </div>
  );
}
