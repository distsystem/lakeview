import { Fragment } from "react";
import { Link } from "react-router";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

function splitSegments(path: string): string[] {
  // Keep `s3://bucket` as one segment so re-joining can't collapse `//`.
  if (path.startsWith("s3://")) {
    const [bucket, ...rest] = path.slice("s3://".length).split("/").filter(Boolean);
    return bucket ? [`s3://${bucket}`, ...rest] : [];
  }
  return path.split("/").filter(Boolean);
}

export function PathBreadcrumb({ path }: { path: string }) {
  const segments = splitSegments(path);

  return (
    <Breadcrumb>
      <BreadcrumbList className="text-sm">
        <BreadcrumbItem>
          {segments.length === 0 ? (
            <BreadcrumbPage className="font-mono">~</BreadcrumbPage>
          ) : (
            <BreadcrumbLink
              render={
                <Link to="/" className="font-mono no-underline">~</Link>
              }
            />
          )}
        </BreadcrumbItem>
        {segments.map((seg, i) => {
          const partial = segments.slice(0, i + 1).join("/");
          const isLast = i === segments.length - 1;
          return (
            <Fragment key={partial}>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage className="font-mono">{seg}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink
                    render={
                      <Link
                        to={`/?prefix=${encodeURIComponent(partial)}`}
                        className="font-mono no-underline"
                      >
                        {seg}
                      </Link>
                    }
                  />
                )}
              </BreadcrumbItem>
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
