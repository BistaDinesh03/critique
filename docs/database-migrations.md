# Database migrations

Critique does not use a migration framework. Schema changes are applied at
startup by `backend/app/database.py`. This page states the contract that keeps
that approach safe, so model changes are made the same way every time instead of
by improvisation.

If you are changing a model, read this first. If you think the contract is the
wrong approach, the trade-offs and the conditions that would justify switching to
a migration framework are discussed in
[issue #707](https://github.com/BistaDinesh03/critique/issues/707).

## How it works today

`init_db()` runs once as the application starts:

1. `Base.metadata.create_all(bind=engine)` creates any table that does not exist
   yet, from the SQLAlchemy models in `backend/app/models.py`.
2. Then one dialect-specific function runs:
   - **SQLite** (`_migrate_sqlite`) — currently adds `users.email` and its unique
     index if missing.
   - **PostgreSQL / anything non-SQLite** (`_migrate_postgresql`) — adds the
     `users` counter/email columns, the `projects` counter/timestamp columns, and
     makes `responses.user_id` nullable for guest feedback.

Both functions start from the live schema: `inspect(engine).get_columns("table")`
returns the columns that actually exist, and each statement runs only if the
column is absent. Nothing records that a statement ran; the schema itself is the
state.

## The contract

Every schema change to an **existing** table must follow these rules.

1. **Guard every statement on inspection.** Never run an `ALTER TABLE`
   unconditionally. Read the live columns with `inspect(engine)` and skip the
   statement when the column already exists. This is what makes startup safe to
   run on every boot and against every environment.
2. **Stay additive.** New columns are added with `ADD COLUMN` and a default
   (`DEFAULT 0 NOT NULL`) or as nullable. New tables need no migration entry —
   `create_all` creates them. Prefer a new table or a nullable column over
   changing an existing one.
3. **Cover both dialects.** If a change is not automatically handled by
   `create_all`, add it to both `_migrate_sqlite()` and `_migrate_postgresql()`.
   SQLite is the local and test database; PostgreSQL is production. Local tests
   passing does not prove the production path works.
4. **Fail loudly.** If the schema cannot be inspected, or an expected column is
   missing, log an `ERROR` and raise. The PostgreSQL path already does this for
   the `responses.user_id` case, and that is the pattern to follow. Do not wrap a
   migration in a bare `except Exception: pass` — that turns a broken deploy into
   silent data loss.
5. **No data backfills in the startup path.** Filling a column for existing rows
   is a separate, deliberate one-off. Startup migrations are for shape, not for
   data, and they must stay fast because they run on every boot.
6. **Add a test.** Assert the model and the migration agree — for example, that
   the column exists after `init_db()` on a fresh database, and that the
   inspection guard makes a second run a no-op.

### The reviewer's checklist

- Is every new statement guarded by an `inspect()` column check?
- Does the change exist in the dialect function for both SQLite and PostgreSQL?
- Is a new column nullable, or does it carry a safe default for existing rows?
- On failure, does it raise rather than continue?
- Is the migration idempotent — would running `init_db()` twice change anything?
- Is there a test?

## What is not supported

The startup approach cannot safely express any of these. Do not attempt them by
hand; see the escalation conditions below.

| Change | Why it is not supported |
|---|---|
| Dropping or renaming a column | Not idempotent and not reversible; existing code may still read the old name |
| Changing a column's type | Requires a table rewrite and dialect-specific syntax |
| Adding a `NOT NULL` column without a default | Fails on any table that already has rows |
| A staged backfill on a large table | Startup must stay fast; there is no batching or resume |
| Rolling back a bad schema change | There is no down path; the schema is forward-only |
| Detecting drift between environments | Differences are silently absorbed, not reported |

## When this contract is no longer enough

Adopt a migration framework (for example Alembic) if any of the following
becomes true:

- a destructive or type-changing migration is needed;
- a backfill must be staged while the app stays up;
- a deploy that changes the schema can be followed by a rollback deploy;
- a second writer appears (a worker, a cron job, or another service on the same
  database);
- more than one long-lived environment needs drift detection;
- compliance or audit requires a schema history.

Until then the startup approach is deliberate: it is smaller, has no dependencies,
and is easy to audit. [Issue #707](https://github.com/BistaDinesh03/critique/issues/707)
tracks the decision and the trade-offs, and
[#82](https://github.com/BistaDinesh03/critique/issues/82) tracks the SQLite path
currently swallowing failures instead of raising, which breaks rule 4 above.
