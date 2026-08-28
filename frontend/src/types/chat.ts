export interface Chat {
  id: number;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  content: string;
  role: string;
  created_at: string;
}

export interface SendMessageRequest {
  chat_id: number;
  msg: string;
}
