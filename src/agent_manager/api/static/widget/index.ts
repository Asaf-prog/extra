import { autoMountAgentChat, defineAgentChat } from "./element/defineAgentChat";

export { AgentChatClient } from "./api/AgentChatClient";
export { DEFAULT_CONFIG, applyConfigAttributes, parseConfig } from "./config/parseConfig";
export { AgentChatElement } from "./element/AgentChatElement";
export { autoMountAgentChat, defineAgentChat } from "./element/defineAgentChat";
export { escapeHtml, formatAssistantText } from "./security/renderMessage";
export {
  conversationStorageKey,
  getStoredConversationId,
  setStoredConversationId,
} from "./storage/conversationStorage";

if (typeof document !== "undefined") {
  const scriptOrigin = new URL(import.meta.url).origin;
  defineAgentChat(scriptOrigin);
  const mount = () => autoMountAgentChat();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    setTimeout(mount, 0);
  }
}
