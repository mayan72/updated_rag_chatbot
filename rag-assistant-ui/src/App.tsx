import { useEffect, useMemo, useState } from "react";
import {
  Bot, FileSpreadsheet, History, Menu, Moon, Plus, Search,
  Send, Settings, Sparkles, Sun, TerminalSquare, X
} from "lucide-react";
import { sendChat } from "./api";
import type { Conversation, Message, Theme } from "./types";

const STORAGE_KEY = "rag-assistant-conversations";
const THEME_KEY = "rag-assistant-theme";

function makeConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    updatedAt: new Date().toISOString(),
    messages: []
  };
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function answerText(answer: unknown): string {
  if (typeof answer === "string") return answer;
  if (answer === null || answer === undefined) return "No answer returned.";
  return JSON.stringify(answer, null, 2);
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(
    (localStorage.getItem(THEME_KEY) as Theme) || "dark"
  );
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations());
  const [activeId, setActiveId] = useState(() => loadConversations()[0]?.id ?? "");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [search, setSearch] = useState("");

  const active = conversations.find(c => c.id === activeId);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  const visibleConversations = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? conversations.filter(c => c.title.toLowerCase().includes(q)) : conversations;
  }, [conversations, search]);

  function createChat() {
    const c = makeConversation();
    setConversations(items => [c, ...items]);
    setActiveId(c.id);
    setInput("");
    setLogsOpen(false);
    setMobileSidebar(false);
  }

  async function submit() {
    const question = input.trim();
    if (!question || sending) return;

    let conversation = active;
    if (!conversation) {
      conversation = makeConversation();
      setConversations(items => [conversation!, ...items]);
      setActiveId(conversation.id);
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      createdAt: new Date().toISOString()
    };

    setConversations(items => items.map(item =>
      item.id === conversation!.id
        ? {
            ...item,
            title: item.messages.length === 0 ? question.slice(0, 48) : item.title,
            updatedAt: new Date().toISOString(),
            messages: [...item.messages, userMessage]
          }
        : item
    ));

    setInput("");
    setSending(true);

    try {
      const result = await sendChat(question);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: answerText(result.answer),
        createdAt: new Date().toISOString(),
        response: {
          type: result.type,
          plan: result.plan,
          sources: result.sources
        }
      };

      setConversations(items => items.map(item =>
        item.id === conversation!.id
          ? {...item, updatedAt: new Date().toISOString(), messages: [...item.messages, assistantMessage]}
          : item
      ));
    } catch (error) {
      const message: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: error instanceof Error
          ? `I couldn't complete that request: ${error.message}`
          : "I couldn't complete that request.",
        createdAt: new Date().toISOString()
      };

      setConversations(items => items.map(item =>
        item.id === conversation!.id
          ? {...item, updatedAt: new Date().toISOString(), messages: [...item.messages, message]}
          : item
      ));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "open" : "collapsed"} ${mobileSidebar ? "mobile-open" : ""}`}>
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-mark"><Sparkles size={17}/></div>
            {sidebarOpen && <div><div className="brand-name">RAG Assistant</div><div className="brand-subtitle">Intelligent data workspace</div></div>}
          </div>
          {sidebarOpen && <button className="icon-button mobile-only" onClick={() => setMobileSidebar(false)}><X size={18}/></button>}
        </div>

        <div className="sidebar-content">
          <button className="new-chat" onClick={createChat}><Plus size={18}/>{sidebarOpen && "New chat"}</button>

          {sidebarOpen && <>
            <div className="section">
              <div className="section-label">Workspace</div>
              <div className="nav-item active"><Bot size={17}/>Chat</div>
              <div className="nav-item"><FileSpreadsheet size={17}/>Files <span>Soon</span></div>
              <div className="nav-item"><TerminalSquare size={17}/>Logs <span>In chat</span></div>
            </div>

            <div className="history-header"><div className="section-label">History</div><History size={15}/></div>

            <div className="search-box"><Search size={15}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search chats"/></div>

            <div className="conversation-list">
              {visibleConversations.length === 0
                ? <div className="empty-history">No conversations yet.</div>
                : visibleConversations.map(c =>
                    <button key={c.id} className={`conversation ${c.id === activeId ? "selected" : ""}`} onClick={() => {setActiveId(c.id);setMobileSidebar(false)}}>{c.title}</button>
                  )}
            </div>
          </>}
        </div>

        <div className="sidebar-footer">
          <button className="footer-item"><Settings size={17}/>{sidebarOpen && "Settings"}</button>
          <button className="footer-item" onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}>
            {theme === "dark" ? <Sun size={17}/> : <Moon size={17}/>}
            {sidebarOpen && (theme === "dark" ? "Light mode" : "Dark mode")}
          </button>
        </div>
      </aside>

      {mobileSidebar && <div className="overlay" onClick={() => setMobileSidebar(false)}/>}

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button" onClick={() => window.innerWidth < 900 ? setMobileSidebar(true) : setSidebarOpen(v => !v)}><Menu size={19}/></button>
            <span className="mobile-title">RAG Assistant</span>
          </div>
          <div className="topbar-right">
            <div className="status"><i/>API ready</div>
            <button className={`logs-button ${logsOpen ? "active" : ""}`} onClick={() => setLogsOpen(v => !v)}><TerminalSquare size={16}/>Logs</button>
          </div>
        </header>

        <section className="chat-layout">
          <div className="chat-content">
            {!active || active.messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-icon"><Sparkles size={25}/></div>
                <h1>How can I help with your data?</h1>
                <p>Ask questions about your uploaded structured and unstructured data in natural language.</p>
                <div className="suggestions">
                  <button onClick={() => setInput("What is the total sales in South India?")}><b>Analyze numbers</b><span>What is the total sales in South India?</span></button>
                  <button onClick={() => setInput("Why did Electronics sales increase during Q2?")}><b>Find insights</b><span>Why did Electronics sales increase during Q2?</span></button>
                  <button onClick={() => setInput("What were the Electronics sales in South India and why was demand strong there?")}><b>Hybrid question</b><span>Combine numbers with textual evidence.</span></button>
                </div>
              </div>
            ) : (
              <div className="messages">
                {active.messages.map(m => <MessageBubble key={m.id} message={m}/>)}
                {sending && <div className="message-row assistant-row"><div className="avatar assistant-avatar"><Sparkles size={15}/></div><div className="message-content"><div className="author">RAG Assistant</div><div className="typing"><i/><i/><i/></div></div></div>}
              </div>
            )}

            <div className="composer-wrap">
              <div className="composer">
                <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => {if(e.key === "Enter" && !e.shiftKey){e.preventDefault();submit()}}} placeholder="Ask anything about your data..." rows={1}/>
                <button className="send" disabled={!input.trim() || sending} onClick={submit}><Send size={17}/></button>
              </div>
              <div className="composer-note">RAG Assistant can make mistakes. Verify important results.</div>
            </div>
          </div>

          {logsOpen && active && (
            <aside className="logs-panel">
              <div className="logs-header">
                <div><b>Response details</b><small>Structured execution and retrieval metadata</small></div>
                <button className="icon-button" onClick={() => setLogsOpen(false)}><X size={17}/></button>
              </div>
              <div className="logs-body">
                {[...active.messages].reverse().find(m => m.role === "assistant")?.response
                  ? <ResponseDetails response={[...active.messages].reverse().find(m => m.role === "assistant")?.response}/>
                  : <div className="logs-empty">Send a question to inspect response details.</div>}
              </div>
            </aside>
          )}
        </section>
      </main>
    </div>
  );
}

function MessageBubble({message}:{message:Message}) {
  const user = message.role === "user";
  return (
    <div className={`message-row ${user ? "user-row" : "assistant-row"}`}>
      {!user && <div className="avatar assistant-avatar"><Sparkles size={15}/></div>}
      <div className="message-content">
        <div className="author">{user ? "You" : "RAG Assistant"}</div>
        <div className={`bubble ${user ? "user-bubble" : "assistant-bubble"}`}>
          <div className="message-text">{message.content}</div>
          {!user && message.response?.type && <div className="response-type">{message.response.type}</div>}
        </div>
      </div>
    </div>
  );
}

function ResponseDetails({response}:{response?:Message["response"]}) {
  if (!response) return null;
  return <>
    <div className="detail-card"><div className="detail-label">Query type</div><div className="detail-value">{response.type}</div></div>
    {response.plan && <div className="detail-card"><div className="detail-label">Structured plan</div><pre>{JSON.stringify(response.plan,null,2)}</pre></div>}
    {response.sources && response.sources.length > 0 && <div className="detail-card"><div className="detail-label">Retrieved sources ({response.sources.length})</div><pre>{JSON.stringify(response.sources,null,2)}</pre></div>}
  </>;
}