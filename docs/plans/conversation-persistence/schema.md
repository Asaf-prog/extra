# Conversation Persistence Schema

## Proposed Relational Schema

### `conversation_users`

- `user_id` string primary key
- `external_user_id` string nullable, indexed
- `username` string nullable, indexed
- `display_name` string nullable
- `metadata_json` JSON/text object, not secret-bearing
- `created_at` timestamp UTC
- `updated_at` timestamp UTC

### `conversation_sessions`

- `session_id` string primary key
- `user_id` string nullable, foreign key to `conversation_users.user_id`
- `system_name` string nullable
- `config_path` string nullable
- `title` string nullable
- `metadata_json` JSON/text object
- `created_at` timestamp UTC
- `updated_at` timestamp UTC
- `last_message_at` timestamp nullable
- `expires_at` timestamp nullable

### `conversation_messages`

- `message_id` string primary key
- `session_id` string, indexed, foreign key to sessions
- `run_id` string nullable, indexed
- `user_id` string nullable, indexed
- `role` string
- `node_id` string nullable
- `agent_id` string nullable
- `parent_message_id` string nullable
- `content` text
- `content_type` string
- `tool_name` string nullable
- `provider` string nullable
- `model_provider` string nullable
- `model_name` string nullable
- `input_tokens` integer nullable
- `output_tokens` integer nullable
- `latency_ms` integer nullable
- `status` string
- `error_type` string nullable
- `metadata_json` JSON/text object
- `created_at` timestamp UTC

### `conversation_snapshots`

- `session_id` string primary key, foreign key to sessions
- `user_id` string nullable, indexed
- `conversation_json` JSON/text object
- `message_count` integer
- `last_message_id` string nullable
- `last_message_at` timestamp nullable
- `model_context_tokens` integer nullable
- `updated_at` timestamp UTC
- `expires_at` timestamp nullable, indexed

## SQLite Notes

SQLite stores JSON values as text through SQLAlchemy's JSON type. The first
implementation should keep JSON values as dictionaries at the domain boundary
and let SQLAlchemy serialize/deserialize them.

The default behavior is persistent SQLite at `sqlite+aiosqlite:///chat.db` when
no database environment variables are set. In-memory SQLite is used only when a
caller explicitly provides an in-memory URL such as
`sqlite+aiosqlite:///:memory:` for tests.

SQLite tests can use `sqlite+aiosqlite:///:memory:` with `StaticPool`, matching
the existing `create_db_engine` helper.

## PostgreSQL Notes

PostgreSQL should use the same repository port and preferably the same table
definitions. The expected URL is:

```text
postgresql+asyncpg://user:password@host:5432/database
```

PostgreSQL JSON can later be upgraded to JSONB if needed. Do not claim live
PostgreSQL support until a real or containerized Postgres test is added.

## Indexes

- `conversation_users.external_user_id`
- `conversation_users.username`
- `conversation_sessions.user_id`
- `conversation_sessions.last_message_at`
- `conversation_messages(session_id, created_at)`
- `conversation_messages(session_id, message_id)`
- `conversation_messages.run_id`
- `conversation_messages.user_id`
- `conversation_snapshots.user_id`
- `conversation_snapshots.expires_at`

## Retention / Cleanup Behavior

Cold messages are retained indefinitely for now. Snapshot rows are hot cache
rows and can be deleted when `expires_at <= now`.

The application should call `delete_expired_snapshots(now)` daily. If a snapshot
is missing after cleanup, the repository rebuilds it from cold messages.

## JSON Storage Strategy

Use `dict[str, Any]` in domain models and SQLAlchemy JSON columns in the
infrastructure. Avoid storing secrets in metadata. Keep snapshot JSON small
enough for prompt construction by applying retrieval bounds; summarization can
be added later.
