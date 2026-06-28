import { applyConfigAttributes } from "../config/parseConfig";
import type { AgentChatConfigInput } from "../types";
import { AgentChatElement } from "./AgentChatElement";

export function defineAgentChat(scriptOrigin: string): void {
  if (customElements.get("agent-chat")) return;
  customElements.define(
    "agent-chat",
    class extends AgentChatElement {
      constructor() {
        super(scriptOrigin);
      }
    },
  );
}

export function autoMountAgentChat(config: AgentChatConfigInput = window.agentChatConfig || {}): void {
  if (document.querySelector("agent-chat")) return;
  const element = document.createElement("agent-chat");
  applyConfigAttributes(element, config);
  document.body.appendChild(element);
}
