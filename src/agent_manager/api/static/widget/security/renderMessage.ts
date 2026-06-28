// Only bold, inline-code, and code fences are recognized. Line breaks are
// handled by CSS `white-space: pre-wrap` on `.msg`.
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function formatAssistantText(value: string): string {
  let out = escapeHtml(value);
  out = out.replace(/```([\s\S]*?)```/g, (_, code: string) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return out;
}
