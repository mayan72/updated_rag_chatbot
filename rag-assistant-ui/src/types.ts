export type Theme = "light" | "dark";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  response?: {
    type: string;
    plan?: unknown;
    sources?: unknown[];
  };
};

export type Conversation = {
  id: string;
  title: string;
  updatedAt: string;
  messages: Message[];
};