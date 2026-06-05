import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import * as registry from "./sessions.js";
import SessionBar from "./components/SessionBar.jsx";
import SessionList from "./components/SessionList.jsx";
import FileSidebar from "./components/FileSidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import MessageInput from "./components/MessageInput.jsx";

const SESSION_KEY = "paperagent.session_id";

export default function App() {
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) || null
  );
  const [sessions, setSessions] = useState(() => registry.listSessions());
  const [messages, setMessages] = useState([]); // {role, content}
  const [files, setFiles] = useState([]); // {path, filename, type}
  const [interrupt, setInterrupt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState("");

  // Persist the active session id whenever it changes.
  useEffect(() => {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
    else localStorage.removeItem(SESSION_KEY);
  }, [sessionId]);

  // Fetch a session's transcript + files from the backend and load it into view.
  const loadSession = useCallback(async (sid) => {
    if (!sid) return;
    setError(null);
    setLoading(true);
    try {
      const [hist, listed] = await Promise.all([
        api.getHistory(sid),
        api.listFiles(sid),
      ]);
      setMessages((hist.messages || []).map((m) => ({ ...m })));
      setFiles(listed.files || []);
      setInterrupt(hist.interrupted ? hist.interrupt : null);
      setSessions(registry.touchSession(sid));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // On first mount, restore the last-active session's transcript.
  useEffect(() => {
    if (sessionId) loadSession(sessionId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Adopt the server-assigned session id and route a chat/resume response into
  // either an assistant message or a pending interrupt.
  const applyResponse = useCallback((resp) => {
    if (resp.session_id) setSessionId(resp.session_id);
    if (resp.status === "interrupted") {
      setInterrupt(resp.interrupt || null);
    } else {
      setInterrupt(null);
      if (resp.response) {
        setMessages((m) => [...m, { role: "assistant", content: resp.response }]);
      }
    }
    return resp.session_id;
  }, []);

  const handleSend = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;
      const isFirst = messages.length === 0;
      setError(null);
      setMessages((m) => [...m, { role: "user", content: trimmed }]);
      setDraft("");
      setLoading(true);
      try {
        const resp = await api.sendChat(trimmed, sessionId);
        const sid = applyResponse(resp);
        // Register / refresh this session in the browser list.
        if (sid) {
          setSessions(
            registry.upsertSession(sid, {
              title: isFirst ? registry.titleFromMessage(trimmed) : undefined,
            })
          );
        }
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading, messages.length, applyResponse]
  );

  const handleResume = useCallback(
    async (decision, opts) => {
      if (!sessionId || loading) return;
      setError(null);
      setLoading(true);
      try {
        const resp = await api.resumeChat(sessionId, decision, opts);
        applyResponse(resp);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading, applyResponse]
  );

  const handleUpload = useCallback(
    async (fileList) => {
      if (!fileList || fileList.length === 0) return;
      setError(null);
      setLoading(true);
      try {
        const resp = await api.uploadFiles(Array.from(fileList), sessionId);
        const sid = resp.session_id || sessionId;
        if (sid) {
          setSessionId(sid);
          const listed = await api.listFiles(sid);
          setFiles(listed.files || []);
          // A pre-chat upload should still create a list entry.
          setSessions(registry.upsertSession(sid, {}));
        }
        return resp; // FileSidebar shows per-file status from this
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const startNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setFiles([]);
    setInterrupt(null);
    setError(null);
    setDraft("");
  }, []);

  const handleSelectSession = useCallback(
    (sid) => {
      if (sid === sessionId) return;
      setSessionId(sid);
      setInterrupt(null);
      loadSession(sid);
    },
    [sessionId, loadSession]
  );

  const handleRenameSession = useCallback((sid, title) => {
    setSessions(registry.renameSession(sid, title));
  }, []);

  const handleDeleteSession = useCallback(
    async (sid) => {
      setSessions(registry.removeSession(sid));
      try {
        await api.deleteSession(sid);
      } catch (e) {
        setError(e.message);
      }
      if (sid === sessionId) startNewSession();
    },
    [sessionId, startNewSession]
  );

  const insertPath = useCallback((path) => {
    setDraft((d) => (d && !d.endsWith(" ") ? `${d} ${path} ` : `${d}${path} `));
  }, []);

  return (
    <div className="app">
      <SessionBar sessionId={sessionId} onNewSession={startNewSession} />

      <aside className="sidebar">
        <SessionList
          sessions={sessions}
          activeId={sessionId}
          onSelect={handleSelectSession}
          onNew={startNewSession}
          onRename={handleRenameSession}
          onDelete={handleDeleteSession}
        />
        <FileSidebar
          files={files}
          onUpload={handleUpload}
          onInsertPath={insertPath}
          busy={loading}
        />
      </aside>

      <main className="main">
        {error && <div className="banner-error">⚠️ {error}</div>}
        <ChatWindow
          messages={messages}
          interrupt={interrupt}
          loading={loading}
          onResume={handleResume}
        />
        <MessageInput
          value={draft}
          onChange={setDraft}
          onSend={handleSend}
          files={files}
          disabled={loading || !!interrupt}
          interrupted={!!interrupt}
        />
      </main>
    </div>
  );
}
