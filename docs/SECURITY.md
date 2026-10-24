# Security notes

## The incident

The repository tracked `ResearchDoi/.env` on the public branch `master`. The file
held `VITE_API_KEY` and `VITE_API_BASE_URL`. Two blobs of that file existed in the
history of `master` (14 commits). Any person could read the key.

## What this change does

| Change | Path |
|---|---|
| The file is gone from all history | `ResearchDoi/.env` |
| A safe template replaces it | `ResearchDoi/.env.example` |
| The weak default key is removed | `AGENT/src/service/pdf_resolver.py`, `AGENT/src/service/doi_lookup.py`, `AGENT/src/research/tools.py` |
| The helper that reads the key | `AGENT/src/__init__.py` |

The history rewrite used `git filter-repo --path ResearchDoi/.env --invert-paths`.
The branch `master` was force pushed. Two blobs are no longer in the history of
`master`.

## Rotate the key now (owner step)

The agent cannot do this step. Only the owner can use the provider console.

1. Open the provider console that issued `VITE_API_KEY`.
2. Revoke the old `VITE_API_KEY`.
3. Create a new key.
4. Put the new value in your local `ResearchDoi/.env`. Do not commit that file.
5. Set the new value in the frontend build environment.
6. Update `API_KEY` in the backend environment to the same value.
7. Deploy the frontend and the backend again.

Check every other key that the old file held. Rotate each one.

## The cached blob risk

GitHub can keep an old blob available by its SHA after a history rewrite. A
deletion does not revoke a leaked key. Treat the old `VITE_API_KEY` as public.

Rotation is the only complete fix. Do not rely on the history rewrite alone.

Residual copies on the remote:

- The stale branches `fix-agent-tool-calls-7013000909272883673` and
  `perf-concurrent-section-ingestion-1560778766749434202` still hold the old blob.
- The pull request refs `refs/pull/1/head` to `refs/pull/3/head` still hold the old blob.
  GitHub does not let a push change those refs.

Delete the stale branches, or close the repository, if you must remove the blob
from the remote. Rotation stays the primary control.

## Unset key behavior

`AGENT/src/__init__.py` holds one helper, `require_api_key`. The three modules
call it at import time. When `API_KEY` is unset or empty, the helper raises
`MissingApiKeyError`. The process stops at start. There is no default key.
