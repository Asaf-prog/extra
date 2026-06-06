# Task 0010 — Docker Deployment

## Goal

Package the API server as a container and provide a basic local deployment
(API + a fake/example sidecar) for development, with no secrets baked in.

## Context

Deployment is a late concern. This task provides a minimal, reproducible
container and compose setup; it does not introduce production topology.

**Read first:** `AGENTS.md`, `docs/ARCHITECTURE.md` (deployment + API layers),
`docs/SIDECAR_CONTEXT_AUTH.md` (the sidecar runs as a separate service).

## Scope

- Add a `Dockerfile` for the API server.
- Add a `docker-compose.yml` wiring the API and a placeholder/example sidecar.
- Document configuration via environment variables.

## Files allowed to change

- `Dockerfile` (new)
- `docker-compose.yml` (new)
- `docs/` (a short deploy note; e.g. extend `DEVELOPMENT_WORKFLOW.md` or add a
  deploy doc)
- `.dockerignore` (new)

## Requirements

- The image builds and runs the API with the runtime created once at startup.
- Configuration (provider keys, sidecar URL) comes from **environment
  variables**, never baked into the image or YAML.
- `docker-compose up` starts the API and a sidecar placeholder for local dev.
- `.dockerignore` excludes caches, `.git`, `.env`, and build artifacts.
- No secrets committed; `.env.example` documents required variables (no values).

## Out of scope

- Production orchestration (Kubernetes, scaling, TLS termination).
- A real client sidecar implementation.
- Observability backends (task 0011).

## Acceptance criteria

- [ ] `docker build` produces a runnable image.
- [ ] `docker-compose up` starts API + sidecar placeholder.
- [ ] All config via env vars; no secrets in image, YAML, or compose file.
- [ ] `.dockerignore` excludes the right paths.
- [ ] `.env.example` lists required variables without values.
- [ ] `make check` still passes (no app regressions).

## Commands to run before finishing

```bash
make check
docker build -t agentplatform-api .
```

## Expected final report

Use the AGENTS.md §9 format. Confirm no secrets are baked in and the engine is
built once at container startup. Recommend task 0011 next.
