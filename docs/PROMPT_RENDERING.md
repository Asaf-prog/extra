# Prompt Rendering

This document defines how prompts become text. It is a design specification;
prompt rendering is implemented in task `0005`.

→ See [ADR 0004](adr/0004-prompts-are-templates-rendered-per-request.md).

---

## Core rules

1. **Prompt files are templates.** They contain placeholders, not finished text.
2. **Dynamic values are resolved per request** from the `ExecutionContext`.
3. **Raw/parsed templates may be cached.** Parsing is deterministic and
   reusable, so cache the compiled template.
4. **Rendered prompts are never globally cached.** A rendered prompt contains
   request-specific (often tenant/identity-specific) data and must not be shared.
5. **Missing required variables fail clearly.** Rendering a template without a
   declared required variable raises a precise error — it never silently emits
   an empty string or `None`.
6. **Prompt injection is not security.** Enforcement happens at the tool/data
   layer, never via prompt wording. → See
   [SIDECAR_CONTEXT_AUTH.md](SIDECAR_CONTEXT_AUTH.md).

---

## Template vs. rendered prompt

| Concept          | Contains                         | Cacheable?            | Lifetime    |
| ---------------- | -------------------------------- | --------------------- | ----------- |
| Prompt template  | placeholders + static text       | ✅ yes (parsed form)  | application |
| Rendered prompt  | concrete values for one request  | ❌ never globally     | request     |

```
prompt file (template)  ──parse──►  cached template  ──render(context)──►  rendered prompt
        (on disk)                     (in memory)                            (per request)
```

---

## Where context values come from

The YAML **declares the source**; the runtime **resolves it**. Possible sources:

- the **request** (body fields, query params)
- **identity** (resolved user/tenant/customer)
- the **sidecar** (`context` map from `/resolve-context`)
- **system time** (now, timezone)
- **memory** (conversation/session state)
- a **tool** result
- a **database** lookup
- an external **API**
- a **plugin**

An agent or prompt declares which variables it requires (`requires_context`);
the context resolver gathers them from the declared sources before rendering.

```yaml
# declarative source mapping (illustrative)
agents:
  invoice_agent:
    prompt: prompts/invoice_agent.md
    requires_context:
      - tenant_id        # from sidecar/identity
      - customer_code    # from sidecar/identity
      - now              # from system time
```

The runtime resolves each declared variable, then renders the template. If a
required variable cannot be resolved, rendering fails with a clear error naming
the missing variable.

---

## Rendering behavior

- Use an explicit, sandboxed template mechanism — **templates are not code**.
  No arbitrary execution inside a prompt template.
- Unknown/undeclared variables in a template are an error (strict mode), not a
  silent blank.
- Output is plain text handed to the LLM provider. It carries **no** trust:
  any instruction a user can influence is treated as untrusted input.

---

## Caching policy (explicit)

- ✅ Cache the **parsed template** keyed by file path + version.
- ❌ Do **not** cache the **rendered** result across requests.
- ❌ Do **not** cache rendered results keyed by partial context (risk of leaking
  one request's data into another).

---

## Validation checklist (for prompt changes)

- [ ] Templates are loaded/parsed once and cached; rendering happens per request.
- [ ] No rendered prompt is stored in a global/shared cache.
- [ ] Missing required variables raise a clear, named error.
- [ ] No executable logic is embedded in templates.
- [ ] No secrets are embedded in prompt files.
- [ ] Enforcement that matters for security lives in the tool/data layer, not the
      prompt text.
- [ ] `make check` passes.
