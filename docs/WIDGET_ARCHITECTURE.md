# Widget Architecture

This document explains how the embeddable chat widget is built, how it connects
to the agent backend, and what should happen next.

## Goal

The product goal is:

```text
Any host app
  Angular / Vue / React / plain HTML
    embeds <agent-chat>
      custom element wrapper
        Shadow DOM boundary
          React chat UI
            shadcn AI Elements-style primitives
              conversation API
                ConversationService
                  agent engine
```

The host application should not need to install React or know anything about
the agent runtime. It only loads `widget.js` and places `<agent-chat>` on the
page.

## Current Implementation

### Public Integration

The public contract is still a framework-agnostic Web Component:

```html
<script type="module" src="/widget.js"></script>
<agent-chat
  title="Support"
  color="#2563eb"
  greeting="Hi! How can I help?"
  mode="floating">
</agent-chat>
```

Attributes configure the widget. Host pages can listen for safe metadata through
the `agent-chat:answer` DOM event.

### Internal UI

Inside the custom element, the widget creates a Shadow DOM root and mounts a
React tree. The React layer uses local AI chat components under:

```text
src/agent_manager/api/static/widget/react/
```

The important components are:

- `Conversation` / `ConversationContent`
- `Message` / `MessageContent` / `MessageResponse`
- `PromptInput` / `PromptInputTextarea` / `PromptInputSubmit`
- `Tool` / `ToolHeader` / `ToolContent` / `ToolOutput`

These are adapted for widget usage from the shadcn AI Elements pattern. They use
real UI/runtime dependencies where useful:

- `streamdown` for markdown-like assistant responses.
- `use-stick-to-bottom` for chat auto-scroll behavior.
- `lucide-react` for icons.

They are not imported from a `shadcn` npm package because shadcn components are
source files copied into a project, not a runtime component package.

### Styling

The widget styles are injected into the Shadow DOM from:

```text
src/agent_manager/api/static/widget/styles/styles.ts
```

This keeps widget styling isolated from Angular, Vue, React, or any other host
application CSS. The host page does not need Tailwind.

## Backend Contract

The widget talks to the agent manager API:

```text
POST /conversations
GET  /conversations/{id}/messages
POST /conversations/{id}/messages
POST /conversations/{id}/messages/stream
```

The non-streaming endpoint remains as a fallback. The streaming endpoint returns
Server-Sent Events over a POST request, so the browser client uses `fetch()` and
`ReadableStream` instead of `EventSource`.

Streaming events include:

- `answer_delta` — append assistant text as it arrives.
- `route` — update the visited agent/sub-agent path.
- `tool_started`, `tool_succeeded`, `tool_failed` — update tool activity.
- `final` — authoritative final answer and metadata.
- `error` — stream failure.

## Agent Connection Behavior

The widget stores the current `conversation_id` in `localStorage` per endpoint.
If the backend no longer knows that conversation, the widget treats the stored
id as stale:

1. Clear the stale id from `localStorage`.
2. Create a new conversation.
3. Retry the message.

This prevents common local-development failures after restarting the backend.

## What Is Verified

Automated coverage verifies:

- The widget renders and remains accessible in floating and inline modes.
- Messages are sent through the conversation API.
- Streaming SSE responses update the assistant message.
- Stale conversation ids are recovered automatically.
- Browser demos still work through Playwright.
- The backend stream endpoint emits SSE frames.

Manual verification with the real demo config verifies:

```text
widget -> conversation API -> ConversationService -> engine -> sub-agent
```

For example, asking:

```text
what are your support hours?
```

routes through:

```text
concierge_router -> concierge_router/hours_agent
```

## Next Step

The next product step is to make the streamed agent activity richer in the UI:

1. Show routing as a first-class in-chat panel, not only a small metadata pill.
2. Show tool calls while they are running, with start/success/error states.
3. Add a visible "agent is thinking / routing" state before the first token.
4. Minify the widget bundle and consider size budgets.
5. Add configuration for theme, launcher text, panel size, and branding.

The next architecture step is to decide whether the copied AI Elements-style
components should remain local to the widget or be formalized as a small
internal UI package.
