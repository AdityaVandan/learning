# Database Basics Cheat Sheet (SQL + Postgres examples)

This is a fundamentals-first cheatsheet: **how databases work**, **how to model data**, and the **core SQL** you’ll use daily.  
(Postgres examples, but concepts apply broadly.)

---

## What a database is (mental model)

- **Database**: a named container for schemas/objects (tables, views, functions).
- **Schema**: a namespace (e.g., `public`) holding tables, etc.
- **Table**: rows + columns (a relation).
- **Row**: one record/tuple.
- **Column**: one attribute (type + constraints).
- **Index**: data structure to speed up reads (usually costs extra writes/storage).
- **Constraint**: rule that must always be true (data correctness at the DB layer).

---

## ACID + why transactions matter

- **Atomicity**: all-or-nothing changes.
- **Consistency**: constraints/invariants preserved.
- **Isolation**: concurrent transactions don’t corrupt each other.
- **Durability**: committed data survives crashes.

In Postgres you use a transaction:

```sql
BEGIN;
  -- multiple statements
COMMIT;   -- or ROLLBACK;
```

---

## OLTP vs OLAP (two DB “modes”)

- **OLTP**: many small reads/writes (apps). Model to avoid anomalies; indexes matter.
- **OLAP**: large scans/aggregations (analytics). Columnar stores, partitioning, denormalized facts.

---

## Keys and relationships

- **Primary key (PK)**: uniquely identifies a row.
- **Foreign key (FK)**: points to another table’s PK (enforces referential integrity).
- **Natural key**: real-world unique value (e.g., email). Can change.
- **Surrogate key**: generated id (e.g., `BIGSERIAL`). Stable.

Common relationship shapes:
- **1–1**: split table for optional/secure data.
- **1–many**: parent `users` → child `orders`.
- **many–many**: join table `user_groups(user_id, group_id)`.

---

## Normalization (practical)

Goal: reduce duplication and anomalies.

- **1NF**: no repeating groups; columns hold atomic values.
- **2NF/3NF (practical)**: non-key columns depend on the key, not other non-key columns.
- Denormalize when:
  - you measured read bottlenecks,
  - you can keep duplicates consistent (triggers, app logic, jobs),
  - or you’re building OLAP-style models.

---

## Data types (Postgres basics)

- IDs: `BIGINT`, `BIGSERIAL`, `UUID`
- Text: `TEXT`, `VARCHAR(n)` (rarely need `n`)
- Time: `TIMESTAMPTZ` (prefer with timezone)
- Boolean: `BOOLEAN`
- Numeric: `INT`, `BIGINT`, `NUMERIC(p,s)` (money/precision)
- JSON: `JSONB` (but don’t treat it as “schema-free forever”)

---

## Core SQL you must know (CRUD)

### SELECT

```sql
SELECT col1, col2
FROM table
WHERE predicate
ORDER BY col1 DESC
LIMIT 50 OFFSET 0;
```

### INSERT

```sql
INSERT INTO table (col1, col2)
VALUES ('a', 123)
RETURNING *;
```

### UPDATE

```sql
UPDATE table
SET col2 = 456
WHERE id = 1
RETURNING *;
```

### DELETE

```sql
DELETE FROM table
WHERE id = 1
RETURNING *;
```

---

## Joins (what they mean)

- **INNER JOIN**: only matching rows.
- **LEFT JOIN**: keep left rows; right side may be NULL.
- **RIGHT JOIN**: (rare) mirror of left.
- **FULL OUTER JOIN**: keep both; missing sides NULL.

Example:

```sql
SELECT u.id, u.name, o.id AS order_id
FROM users u
LEFT JOIN orders o ON o.user_id = u.id;
```

---

## Constraints (data correctness)

### NOT NULL

```sql
ALTER TABLE users ALTER COLUMN name SET NOT NULL;
```

### UNIQUE

```sql
ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email);
```

### CHECK (including “col A equals col B”)

```sql
ALTER TABLE t
ADD CONSTRAINT t_a_equals_b_chk
CHECK (a IS NOT DISTINCT FROM b);
```

Notes:
- `a = b` does **not** treat `NULL = NULL` as true.
- `IS NOT DISTINCT FROM` treats `NULL` values as equal.

### Foreign key

```sql
ALTER TABLE orders
ADD CONSTRAINT orders_user_id_fk
FOREIGN KEY (user_id) REFERENCES users(id);
```

---

## Indexes (when and why)

- Add an index when queries frequently filter/join on a column and table is large.
- Indexes speed reads, but:
  - slow writes,
  - consume disk,
  - require maintenance.

Common patterns:
- **B-tree**: default; great for equality and ranges.
- **Multi-column**: order matters (`(a, b)` helps queries filtering on `a`, maybe `b`).
- **Partial**: only index rows you actually query:

```sql
CREATE INDEX ON events(created_at) WHERE deleted_at IS NULL;
```

---

## Postgres quick-start (from this conversation)

### Create a database

In `psql`, **end statements with `;`**. Prompt `postgres-#` means “unfinished statement”.

```sql
CREATE DATABASE learningdb;
```

### Connect to it

```sql
\c learningdb
```

### Create a table

```sql
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Insert data

```sql
INSERT INTO users (name, email)
VALUES ('Alice', 'alice@example.com')
RETURNING *;
```

### Alter a table (examples)

```sql
ALTER TABLE users ADD COLUMN age INT;

ALTER TABLE users RENAME COLUMN name TO full_name;

ALTER TABLE users
ADD CONSTRAINT users_age_nonnegative_chk CHECK (age >= 0);
```

---

## `psql` mini-cheatsheet

```sql
\l      -- list databases
\c db   -- connect
\dt     -- list tables
\d t    -- describe table
\x on   -- expanded output
```

---

## Practical “production habits”

- Always sanity-check with:

```sql
SELECT ... WHERE ... LIMIT 50;
```

before `UPDATE/DELETE`.

- Prefer constraints over “trusting the app”.
- Keep transactions short; long transactions cause lock/space issues.
- Measure before denormalizing; indexes are often enough.

