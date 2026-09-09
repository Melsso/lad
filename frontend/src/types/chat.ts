export interface Chat {
  id: number;
  title: string;
  mode: "chat" | "agent";
  created_at: string;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  content: string;
  role: string;
  tool_call_id?: string | null;
  tool_name?: string | null;
  tool_arguments?: string | null;
  created_at: string;
}

export interface SendMessageRequest {
  chat_id: number;
  msg: string;
}

export interface StreamMessageHandlers {
  onChunk: (text: string) => void;
  onToolCall?: (message: ChatMessage) => void;
  onToolResult?: (message: ChatMessage) => void;
  onDone: (message: ChatMessage) => void;
  onError: (detail: string) => void;
  signal?: AbortSignal;
}
