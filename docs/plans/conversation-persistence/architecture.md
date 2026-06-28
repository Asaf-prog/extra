# Conversation Persistence Architecture

## Domain Model

The domain layer should expose pure Python value objects:

- `User`
  - `user_id`
  - `external_user_id`
  - `username`
  - `display_name`
  - `metadata`
  - `created_at`
  - `updated_at`
- `ConversationSession`
  - `session_id`
  - `user_id`
  - `system_name`
  - `config_path`
  - `title`
  - `metadata`
  - `created_at`
  - `updated_at`
  - `last_message_at`
  - `expires_at`
- `ConversationMessage`
  - `message_id`
  - `session_id`
  - `run_id`
  - `user_id`
  - `role`
  - `node_id`
  - `agent_id`
  - `parent_message_id`
  - `content`
  - `content_type`
  - `tool_name`
  - `provider`
  - `model_provider`
  - `model_name`
  - `input_tokens`
  - `output_tokens`
  - `latency_ms`
  - `status`
  - `error_type`
  - `metadata`
  - `created_at`
- `ConversationSnapshot`
  - `session_id`
  - `user_id`
  - `conversation_json`
  - `message_count`
  - `last_message_id`
  - `last_message_at`
  - `model_context_tokens`
  - `updated_at`
  - `expires_at`
- `ConversationContext`
  - bounded list of messages suitable for prompt construction
  - snapshot metadata such as source and message count

Roles should broaden beyond the current `user` and `assistant` values to include
`system`, `tool`, `orchestrator`, and `agent`.

## Storage Abstraction

The application layer should depend on a repository protocol, not SQLAlchemy:

- `upsert_user`
- `get_user`
- `create_session`
- `get_session`
- `append_message`
- `list_messages`
- `get_snapshot`
- `rebuild_snapshot`
- `get_context`
- `delete_expired_snapshots`

For backward compatibility, the current `Repository` methods can remain as a
thin compatibility port or be implemented by the richer repository.

## Database Backend Strategy

SQLite is the first implemented backend using the existing async SQLAlchemy and
SQLModel setup. PostgreSQL should use the same table definitions and repository
logic where possible, selected by SQLAlchemy URL:

- SQLite: `sqlite+aiosqlite:///path/to/chat.db`
- PostgreSQL: `postgresql+asyncpg://user:pass@host/db`

Backend-specific behavior should stay in infrastructure helpers and migrations,
not in domain/application code.

## Transaction Boundaries

Appending a message must be one logical transaction:

1. Insert one cold message row.
2. Update the owning session timestamps.
3. Upsert/update the hot snapshot row.
4. Commit.

If any step fails, none of the writes should be committed.

## Read Paths

- `list_messages(session_id, limit)` reads cold messages oldest-first.
- `get_snapshot(session_id)` reads the hot row if present and not expired.
- `get_context(session_id, max_messages, max_chars, max_tokens)` prefers a valid
  snapshot, then applies bounds.
- If the hot snapshot is missing or stale, rebuild it from cold messages and
  return the rebuilt bounded context.

## Write Paths

- A user message is appended before invoking the engine.
- The assistant final response is appended after the engine succeeds.
- A failed run may append a failed assistant/system message later, but the first
  implementation can keep failure persistence minimal.
- Important intermediate events can be added later through existing hook/trace
  seams without changing the cold table shape.

## Full Conversation Context Reconstruction

The hot snapshot stores JSON shaped for prompt/context reconstruction, e.g.

```json
{
  "messages": [
    {"role": "user", "content": "hello", "created_at": "..."},
    {"role": "assistant", "content": "hi", "created_at": "..."}
  ]
}
```

Rebuild scans cold messages for the session in insertion order and writes a new
snapshot. Retrieval then applies `max_messages` and `max_chars`. Token bounds
are exposed as a parameter and reserved for future token counting.
