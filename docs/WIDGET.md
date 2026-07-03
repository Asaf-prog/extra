# Embeddable Chat Widget

The browser widget is a framework-agnostic custom element served as an ES
module. Host apps still embed a plain `<agent-chat>` element, while the widget
mounts a React chat surface internally inside its Shadow DOM. That keeps Angular
/ Vue / server-rendered pages isolated from the widget implementation while
letting the chat UI use shadcn AI Elements-style primitives:

- `Conversation` powered by `use-stick-to-bottom`.
- `Message` / `MessageContent` / `MessageResponse` powered by `streamdown`.
- `PromptInput` / `PromptInputTextarea` / `PromptInputSubmit`.
- `Tool` / `ToolHeader` / `ToolContent` / `ToolOutput` for agent/tool activity.

```html
<script type="module" src="/widget.js"></script>
<agent-chat title="Support" color="#2563eb"></agent-chat>
```

## Floating Mode

```html
<script type="module" src="https://your-backend.example/widget.js"></script>
<agent-chat
  title="Support"
  color="#2563eb"
  greeting="Hi! How can I help?"
  mode="floating"
  position="bottom-right">
</agent-chat>
```

## Inline Mode

```html
<script type="module" src="https://your-backend.example/widget.js"></script>
<agent-chat
  title="Inline Assistant"
  color="#7c3aed"
  mode="inline">
</agent-chat>
```

## Script-Only Auto-Mount

When no `<agent-chat>` exists on the page, `window.agentChatConfig` can create
one automatically:

```html
<script>
  window.agentChatConfig = {
    title: "Auto-mounted Assistant",
    color: "#16a34a",
    greeting: "Hi from auto-mount"
  };
</script>
<script type="module" src="https://your-backend.example/widget.js"></script>
```

## Host Frameworks

The host framework does not need to install React, Streamdown, or the AI UI
dependencies. They are bundled inside `widget.js`; the public integration
contract is still the custom element, attributes, and DOM events.

React can render the custom element directly:

```tsx
export function HelpChat() {
  return <agent-chat title="Support" color="#2563eb" />;
}
```

Angular apps should allow custom elements in the owning module:

```ts
import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from "@angular/core";

@NgModule({
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class AppModule {}
```

Then use the element in a template:

```html
<agent-chat title="Support" color="#2563eb"></agent-chat>
```

## Local Demo Pages

Run the API/static server, then open:

- `/widget-demo.html` for floating mode.
- `/widget-demo-inline.html` for inline mode.
- `/widget-demo-automount.html` for script-only auto-mount.
- `/widget-demo-attribute-override.html` for authored element attributes with a global config present.

The Playwright smoke tests mock the conversation endpoints for deterministic
browser coverage. For a manual test against the real API, run `agent-manager`
with a valid agent config and open the same demo pages.

## Routing Evidence

Against a real system (e.g. the flagship
[`examples/enterprise-knowledge-assistant/agents.yaml`](../examples/enterprise-knowledge-assistant/agents.yaml)),
the `/conversations/{id}/messages` response includes a safe `visited` routing
path (e.g. `["research_router", "research_router/documentation_agent"]`) showing
which orchestrator routed to which sub-agent. The widget emits this as an
`agent-chat:answer` DOM event; the same path appears in the server logs
(`run ended … visited=…`). Only routing/tool metadata is exposed — never
reasoning or hidden content.

Host pages can consume the same signal:

```js
document.addEventListener("agent-chat:answer", (e) => {
  console.log(e.detail.visited, e.detail.used_tools);
});
```

## Streaming

The widget prefers the streaming endpoint:

```text
POST /conversations/{id}/messages/stream
```

Assistant text is rendered as `answer_delta` events arrive. The final event
settles the answer and emits `agent-chat:answer` with the safe route/tool
metadata. If streaming is unavailable or fails before a usable answer, the
widget falls back to the regular non-streaming send endpoint.

See [WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md) for the implementation
details and next-step plan.
