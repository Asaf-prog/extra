# Embeddable Chat Widget

The browser widget is a framework-agnostic custom element served as an ES module:

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
