# Rebuild Services

Rebuild and restart Docker services after code changes.

## Usage
```
/rebuild backend
/rebuild frontend
/rebuild all
```

## Commands

### Rebuild backend (after Python changes)
```bash
docker compose build --no-cache backend && docker compose up -d backend
```

### Rebuild frontend (after TypeScript/React changes)
```bash
docker compose build --no-cache frontend && docker compose up -d frontend
```

### Rebuild everything
```bash
docker compose build --no-cache && docker compose up -d
```

### View logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Check health
```bash
docker compose ps
```

## Notes
- Backend rebuild needed when: agents, services, routes, schemas, config changed
- Frontend rebuild needed when: components, types, lib/api, styles changed
- `--no-cache` ensures pip/npm don't use stale layers
