# lakeview

Typed data lake frontend — Lance native, Python+Rust backend, TypeScript frontend.

## Architecture

```
Lance Dataset ──→ Python API (FastAPI) ──→ React SPA (TypeScript)
                  │                         │
                  ├ Pydantic models          ├ openapi-typescript types
                  ├ OpenAPI 3.1              ├ TanStack Query (data fetching)
                  └ Arrow IPC (opt)          ├ shadcn/ui (components + DataTable)
                                             └ Tailwind CSS (styling)
```

## File Structure

```
lakeview/
  sample-data/          → symlink to agent/output (Lance datasets)
  pixi.toml
  pyproject.toml
  src/lakeview/
    __init__.py
    app.py              FastAPI app factory + SPA mount
    models.py           Pydantic response models
    lance_io.py         Lance read/cache/query
  frontend/
    package.json
    vite.config.ts
    components.json     shadcn/ui config
    src/
      api/types.ts      generated from OpenAPI
      api/client.ts     openapi-fetch wrapper
      components/
        ui/             shadcn/ui primitives (auto-generated)
        dataset-list.tsx
        run-sidebar.tsx
        run-detail.tsx
        message-view.tsx
        part-view.tsx
        stats-bar.tsx
      hooks/
        use-rows.ts
        use-run-detail.ts
```

## Phase 1: API Backend

### Endpoints

```
GET /api/datasets?prefix={path}
    → { prefix, datasets: [{ name, path, row_count, columns }] }

GET /api/d/{db_path}/rows?offset=0&limit=50&status=all
    → { total, offset, limit, rows: [RowSummary], stats }

GET /api/d/{db_path}/runs/{key}
    → { row: RowSummary, messages: [MessageRecord] }

GET /api/d/{db_path}/schema
    → { columns: [{ name, type, nullable }] }
```

### Data Models

Reuse `PartRecord`, `MessageRecord` from agent project. New response wrappers:

```python
class RowSummary(BaseModel):
    row_offset: int
    session_id: str | None = None
    output: dict | None = None
    error: str | None = None
    metadata: dict | None = None
    correct: bool | None = None

class Stats(BaseModel):
    total: int
    ok: int
    wrong: int
    error: int
    pending: int
    accuracy: float | None = None

class RowListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[RowSummary]
    stats: Stats

class RunDetailResponse(BaseModel):
    row: RowSummary
    messages: list[dict]  # MessageRecord as dict (JSON-decoded)
```

### Lance I/O

Extract from `agent/viewer/app.py`:
- Dataset open + cache (version-based invalidation)
- Column projection (exclude `messages` for listings)
- Row lookup by offset or session_id filter
- S3/local URI resolution
- Status filtering + stats computation

### Verify

```bash
pixi run dev
curl localhost:8766/api/datasets?prefix=sample-data
curl localhost:8766/api/d/sample-data/kaggle.lance/rows?limit=5
curl localhost:8766/api/d/sample-data/kaggle.lance/runs/0
curl localhost:8766/openapi.json
```

## Phase 2: TypeScript Frontend

### Stack

- **shadcn/ui** — UI components (Card, Badge, Tabs, ScrollArea, Collapsible, DataTable...)
- **TanStack Table** — shadcn DataTable 的底层，提供排序/过滤/分页逻辑
- **TanStack Query** — 数据获取 + 缓存 + 轮询
- **openapi-typescript + openapi-fetch** — 从 OpenAPI spec 生成类型安全的 API 客户端
- **react-markdown + remark-math + rehype-katex** — Markdown/LaTeX 渲染
- **Vite** — 构建工具

### Type Generation

```bash
cd frontend
bun run generate-types   # openapi-typescript → src/api/types.ts
```

### Component Mapping (from agent/viewer/app.py)

| Origin | shadcn component | What it renders |
|---|---|---|
| `home_body()` | Card grid | dataset card grid |
| `_sidebar()` | ScrollArea + Card | scrollable run list + filter tabs + stats |
| `run_card()` | Card + Badge | UUID7 time, slug, answer pair, status icon |
| `_detail_main()` | 自定义 | header + message stream |
| `message_el()` | Collapsible | collapsible message with parts |
| `part_el()` | Card + Badge | dispatch by part_kind |
| `_stats_header()` | Badge group | ok/wrong/error/pending counts |
| `_filter_tabs()` | Tabs | status filter (all/ok/wrong/error/pending) |
| `_compare_column()` | ResizablePanel | side-by-side run comparison |
| dark mode toggle | shadcn dark mode | Tailwind `dark:` class, `next-themes` |

### Routing

```
/                          → DatasetList
/{db_path}/                → RunSidebar + empty main
/{db_path}/r/{key}         → RunSidebar + RunDetail
/{db_path}/compare?keys=   → RunSidebar + CompareView
```

### Markdown + LaTeX

`react-markdown` + `remark-math` + `rehype-katex` replaces server-side mistletoe + math stashing.

## Phase 3: Production

- SPA static files served from FastAPI (`StaticFiles`)
- Arrow IPC via content negotiation for bulk data
- Virtual scrolling (TanStack Virtual) for 1000+ rows
- Multimodal: `GET /api/d/{db_path}/blob/{row}/{col}` → `<img>`/`<audio>`/`<video>`

## Phase 4: Rust (later)

PyO3 extension replacing `lance_io.py` for zero-copy Arrow serialization.
