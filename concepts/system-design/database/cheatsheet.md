# Database Cheat Sheet (Postgres-first)

This is a practical command/reference sheet for day-to-day production work: **introspection, safety, performance, roles, migrations, troubleshooting**.

---

## Connect (psql)

```bash
# Connect (db + user). If you omit -d, Postgres often defaults db_name=user_name.
psql -h localhost -p 5432 -U <user> -d <db>

# Quick one-off command (non-interactive)
psql -U <user> -d <db> -c "SELECT now();"

# Connection string
psql "postgresql://<user>:<pass>@localhost:5432/<db>?sslmode=prefer"
```

---

## See what databases exist

### psql meta-commands

```sql
\l         -- list databases
\l+        -- list databases (with size and more)
```

### SQL (portable-ish)

```sql
SELECT datname FROM pg_database ORDER BY 1;
```

---

## Switch DB (inside psql)

```sql
\c <db_name>
```

---

## See what schemas exist

```sql
\dn

-- SQL
SELECT schema_name
FROM information_schema.schemata
ORDER BY 1;
```

---

## See what tables exist

### psql meta-commands (most used)

```sql
\dt                 -- tables in search_path (often public)
\dt *.*             -- tables in all schemas
\dt <schema>.*      -- tables in one schema
\dt+                -- includes size and more
```

### SQL

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
```

---

## Describe a table (columns, types, constraints)

```sql
\d <table>
\d+ <table>         -- includes storage, stats target, etc.

-- SQL
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<table>'
ORDER BY ordinal_position;
```

---

## Row counts + size (fast vs accurate)

```sql
-- Accurate but can be slow on huge tables:
SELECT count(*) FROM <table>;

-- Estimate (uses stats; fast):
SELECT reltuples::bigint AS estimated_rows
FROM pg_class
WHERE oid = '<schema>.<table>'::regclass;

-- Table size:
SELECT pg_size_pretty(pg_total_relation_size('<schema>.<table>')) AS total_size;

-- List biggest tables in a schema:
SELECT
  n.nspname AS schema,
  c.relname AS table,
  pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;
```

---

## Indexes

```sql
\di
\di <schema>.*          -- indexes in schema
\d <table>              -- shows indexes too

-- SQL: indexes for a table
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = '<table>'
ORDER BY 1;
```

### Create indexes (common patterns)

```sql
-- Basic
CREATE INDEX ON <table>(<col>);

-- Multi-column (order matters: leftmost prefix)
CREATE INDEX ON <table>(<col1>, <col2>);

-- Partial index (very common in prod)
CREATE INDEX ON <table>(<col>) WHERE deleted_at IS NULL;

-- Concurrent create (avoids blocking writes; slower; can't run in a transaction)
CREATE INDEX CONCURRENTLY idx_name ON <table>(<col>);

-- Drop concurrently (same blocking idea)
DROP INDEX CONCURRENTLY idx_name;
```

---

## Constraints + keys

```sql
\d <table>              -- shows PK/FK/unique/check

-- SQL: constraints
SELECT
  conname,
  contype,
  pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = '<schema>.<table>'::regclass
ORDER BY contype, conname;
```

---

## Views, materialized views, functions

```sql
\dv          -- views
\dm          -- materialized views
\df          -- functions
\df+         -- more details
```

---

## Quick query safety patterns (senior defaults)

```sql
-- Always check your filter with a safe SELECT first
SELECT *
FROM <table>
WHERE <predicate>
LIMIT 100;

-- Use a transaction when doing risky changes
BEGIN;
  -- UPDATE/DELETE here
  -- SELECT to validate
ROLLBACK; -- or COMMIT;

-- Avoid accidental full-table updates/deletes: make WHERE mandatory by habit
UPDATE <table> SET ... WHERE ...;
DELETE FROM <table> WHERE ...;
```

---

## EXPLAIN (performance fundamentals)

```sql
EXPLAIN SELECT ...;
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT ...;
```

What to look for:
- **Seq Scan** on big tables where you expected an index
- **Rows removed by filter** (bad selectivity)
- **Actual vs estimated rows** (stats issue → `ANALYZE`)
- **Sort** and **Hash** memory spills (work_mem, missing index, bad join order)
- **Buffers** (I/O heavy)

---

## Statistics / ANALYZE / VACUUM

```sql
ANALYZE <table>;

-- Regular VACUUM (non-blocking for reads/writes; reclaims dead tuples for reuse)
VACUUM (VERBOSE, ANALYZE) <table>;

-- Full vacuum (locks table; rewrites; use rarely/off-hours)
VACUUM FULL <table>;
```

---

## Transactions, isolation, and locks (debugging)

```sql
-- Current activity
SELECT pid, usename, datname, state, wait_event_type, wait_event, query_start, query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start NULLS LAST;

-- Who is blocking whom
SELECT
  blocked.pid     AS blocked_pid,
  blocked.query   AS blocked_query,
  blocker.pid     AS blocker_pid,
  blocker.query   AS blocker_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocker
  ON blocker.pid = ANY (pg_blocking_pids(blocked.pid))
ORDER BY blocked.pid;

-- See locks (advanced)
SELECT locktype, mode, granted, pid, relation::regclass
FROM pg_locks
WHERE pid IN (SELECT pid FROM pg_stat_activity WHERE datname = current_database())
ORDER BY granted, pid;
```

---

## Users/Roles and permissions

```sql
\du                 -- list roles
\dp                 -- table privileges

-- Create role/user (Postgres "user" is a role with login)
CREATE ROLE app_user LOGIN PASSWORD '<pw>';

-- Grant connect + schema usage + table privileges (common baseline)
GRANT CONNECT ON DATABASE <db> TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```

---

## Extensions (Postgres-specific but common in prod)

```sql
\dx

-- Examples:
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## Dump / restore (backups, migrations between envs)

```bash
# Dump one DB
pg_dump -h localhost -p 5432 -U <user> -d <db> > dump.sql

# Dump compressed custom format (better for big dumps)
pg_dump -h localhost -p 5432 -U <user> -Fc -d <db> -f dump.dump

# Restore SQL dump
psql -h localhost -p 5432 -U <user> -d <db> -f dump.sql

# Restore custom dump
createdb -h localhost -p 5432 -U <user> <db>
pg_restore -h localhost -p 5432 -U <user> -d <db> dump.dump
```

---

## Handy psql quality-of-life

```sql
\?            -- help for psql commands
\h            -- help for SQL commands
\h CREATE INDEX
\x on         -- expanded display (great for wide rows)
\timing on    -- show execution time
\pset pager off

\conninfo     -- show current connection
\encoding
\dtS          -- system tables too (careful)
```

---

## MySQL / SQLite quick equivalents (when you switch stacks)

### MySQL

```sql
SHOW DATABASES;
USE <db>;
SHOW TABLES;
DESCRIBE <table>;
SHOW CREATE TABLE <table>;
```

### SQLite

```sql
.databases
.tables
.schema <table>
```

---

## What you should master as a senior SWE (checklist)

- **Modeling**: normalization vs denormalization; constraints; nullability; surrogate vs natural keys.
- **Indexes**: btree basics; multi-column order; partial indexes; unique indexes; index-only scans; write amplification trade-offs.
- **Query planning**: `EXPLAIN (ANALYZE, BUFFERS)`; join types; selectivity; stats; avoiding N+1 at the app layer.
- **Transactions**: isolation levels, deadlocks, retries, idempotency; lock scope; long transactions are production hazards.
- **Schema change safety**: online migrations, `CREATE INDEX CONCURRENTLY`, backfills, dual writes, feature flags.
- **Operations**: backups/restore drills; RPO/RTO; replication; connection pooling; slow query triage.
- **Security**: least privilege; secrets; auditability; row-level access patterns; SQL injection hardening.

