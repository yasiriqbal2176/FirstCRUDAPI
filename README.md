# Task API (FastAPI + Postgres, containerized)

CRUD task API running against a real PostgreSQL database in Docker — the third storage swap
in this lane: memory (A1) -> SQLite (A2) -> containerized Postgres (this one, A3).

## Stage 0 — Postgres in a container

Start Postgres by hand (before compose exists) to prove the engine works:

```bash
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks \
  -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres
```

Check it:

```bash
docker ps
docker exec -it taskdb psql -U postgres -d tasks
```

More setup and run instructions land in later stages of this README.
