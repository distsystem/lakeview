# lakeview

General-purpose datalake frontend — browse S3/local storage, view structured datasets (Lance native), with schema-aware plugin views.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Plugin Layer      schema match → rich view (sidebar + detail)  │
│  (agent_run, ...)  fallback → generic table view                │
├─────────────────────────────────────────────────────────────────┤
│  Format Layer      DatasetReader protocol                       │
│  (lance, ...)      schema / count / scan / get_row              │
├─────────────────────────────────────────────────────────────────┤
│  Storage Layer     browse S3 + local directories                │
│  (local, s3)       detect datalake formats by structure         │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
src/lakeview/
  app.py              FastAPI — generic + plugin-aware endpoints
  models.py           Pydantic response models (generic only)
  storage/
    base.py           EntryInfo dataclass
    local.py          local FS browse + format detection
    s3.py             S3 prefix browse (PyArrow fs)
  formats/
    base.py           DatasetReader protocol
    lance.py          LanceReader (open, cache, scan, get_row)
  plugins/
    base.py           SchemaPlugin protocol
    registry.py       detect_plugin(schema) — ordered list, first match
    agent_run.py      matches {messages, session_id, correct}
frontend/src/
  api/
    types.ts          generated from OpenAPI
    client.ts         openapi-fetch wrapper
  hooks/
    use-datasets.ts       GET /api/datasets
    use-dataset-info.ts   GET /api/d/{path}/info — schema + plugin detection
    use-rows.ts           GET /api/d/{path}/rows — generic paginated
    use-plugin-view.ts    GET /api/d/{path}/view — plugin-enriched listing
    use-plugin-detail.ts  GET /api/d/{path}/view/{key} — plugin-enriched detail
  components/
    ui/               shadcn/ui primitives
    dataset-list.tsx   directory browser
    dataset-view.tsx   dispatcher: /info → plugin or generic table
    generic/
      table-view.tsx   TanStack Table, dynamic columns from schema
      row-detail.tsx   JSON tree per column
    plugins/
      index.ts         { agent_run: { Sidebar, Detail } }
      agent-run/
        sidebar.tsx    run list + filter tabs + stats
        detail.tsx     message stream with parts
        stats-bar.tsx  ok/wrong/error/pending counts
```

## API Endpoints

```
Generic (any dataset):
  GET /api/datasets?prefix=             browse storage
  GET /api/d/{path}/info                schema + detected plugin + filters
  GET /api/d/{path}/schema              column list
  GET /api/d/{path}/rows?offset&limit   raw paginated rows
  GET /api/d/{path}/row/{offset}        single row (all columns)

Plugin-aware:
  GET /api/d/{path}/view?offset&limit&filter   enriched listing + stats
  GET /api/d/{path}/view/{key}                 enriched detail
```

## Adding a New Plugin

Backend: add `src/lakeview/plugins/my_plugin.py` implementing `SchemaPlugin`, register in `registry.py`.

Frontend: add `components/plugins/my-plugin/` with Sidebar + Detail components, register in `plugins/index.ts`.

## Verify

```bash
pixi run dev
curl localhost:8766/api/datasets?prefix=sample-data
curl localhost:8766/api/d/sample-data/kaggle.lance/info
curl localhost:8766/api/d/sample-data/kaggle.lance/rows?limit=5
curl localhost:8766/api/d/sample-data/kaggle.lance/view?limit=5
curl localhost:8766/api/d/sample-data/kaggle.lance/view/0
```
