export type AgentChatPosition = "bottom-right" | "bottom-left";
export type AgentChatMode = "floating" | "inline";
export type ChatRole = "user" | "assistant" | "system" | "tool" | "orchestrator" | "agent";

export interface AgentChatConfig {
  endpoint: string;
  title: string;
  color: string;
  greeting: string;
  position: AgentChatPosition;
  avatar: string;
  mode: AgentChatMode;
}

export interface AgentChatConfigInput {
  endpoint?: string;
  title?: string;
  color?: string;
  greeting?: string;
  position?: string;
  avatar?: string;
  mode?: string;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  created_at?: string;
}

export interface SendMessageResponse {
  answer: string;
}

declare global {
  interface Window {
    agentChatConfig?: AgentChatConfigInput;
  }
}
