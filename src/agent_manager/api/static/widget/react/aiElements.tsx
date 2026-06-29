import type { FormEvent, KeyboardEvent, PropsWithChildren, ReactNode, RefObject } from "react";

export function Conversation({
  children,
  scrollRef,
}: PropsWithChildren<{ scrollRef: RefObject<HTMLDivElement | null> }>) {
  return (
    <div className="messages" aria-live="polite" aria-relevant="additions text" ref={scrollRef}>
      {children}
    </div>
  );
}

export function Message({
  children,
  role,
  typing = false,
}: PropsWithChildren<{ role: "user" | "ai"; typing?: boolean }>) {
  return (
    <div
      className={`msg ${role === "user" ? "user" : "ai"}${typing ? " typing" : ""}`}
      role={typing ? "status" : undefined}
      aria-label={typing ? "Assistant is typing" : undefined}
    >
      {children}
    </div>
  );
}

export function MessageContent({
  children,
  html,
}: PropsWithChildren<{ html?: string }>) {
  if (html !== undefined) {
    return <div className="message-content" dangerouslySetInnerHTML={{ __html: html }} />;
  }
  return <div className="message-content">{children}</div>;
}

export function ToolStrip({ route, tools }: { route?: string[]; tools?: ReactNode }) {
  if (!route?.length && !tools) return null;
  return (
    <div className="agent-meta" aria-label="Agent activity">
      {route?.length ? <span className="route">{route.join(" -> ")}</span> : null}
      {tools}
    </div>
  );
}

export function PromptInput({
  disabled,
  inputRef,
  onSubmit,
}: {
  disabled: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  onSubmit: (value: string) => void;
}) {
  function submit(form: HTMLFormElement) {
    const input = form.elements.namedItem("message") as HTMLTextAreaElement | null;
    const value = input?.value.trim() ?? "";
    if (!value) return;
    input!.value = "";
    input!.style.height = "auto";
    onSubmit(value);
  }

  function onFormSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit(event.currentTarget);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit(event.currentTarget.form!);
    }
  }

  return (
    <form className="composer" onSubmit={onFormSubmit}>
      <textarea
        aria-label="Message"
        className="input"
        ref={inputRef}
        name="message"
        onInput={(event) => {
          const input = event.currentTarget;
          input.style.height = "auto";
          input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
        }}
        onKeyDown={onKeyDown}
        placeholder="Message..."
        rows={1}
      />
      <button aria-label="Send message" className="send" disabled={disabled} type="submit">
        <SendIcon />
      </button>
    </form>
  );
}

function SendIcon() {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}
