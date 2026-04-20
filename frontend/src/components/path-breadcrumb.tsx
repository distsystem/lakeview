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

export function PathBreadcrumb({ root, path }: { root: string; path: string }) {
  // Clean path splits — no scheme, no `//`, no encoding gymnastics.
  const segments = path.split("/").filter(Boolean);

  return (
    <Breadcrumb>
      <BreadcrumbList className="text-sm">
        <BreadcrumbItem>
          {segments.length === 0 ? (
            <BreadcrumbPage className="font-mono">{root}</BreadcrumbPage>
          ) : (
            <BreadcrumbLink
              render={
                <Link to={`/${root}`} className="font-mono no-underline">
                  {root}
                </Link>
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
                        to={`/${root}/${partial}`}
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
