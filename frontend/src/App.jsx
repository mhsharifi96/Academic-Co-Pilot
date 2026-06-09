import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import * as auth from "./auth.js";
import SessionBar from "./components/SessionBar.jsx";
import SessionList from "./components/SessionList.jsx";
import FileSidebar from "./components/FileSidebar.jsx";
import PlanSidebar from "./components/PlanSidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import MessageInput from "./components/MessageInput.jsx";
import GuidelinesPage from "./components/GuidelinesPage.jsx";
import LoginPage from "./components/LoginPage.jsx";

export default function App() {
  const [user, setUser] = useState(() => auth.getUser());
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]); // {id, title, updated_at}
  const [messages, setMessages] = useState([]); // {role, content}
  const [files, setFiles] = useState([]); // {path, filename, type}
  const [plan, setPlan] = useState([]); // {text, status}
  const [interrupt, setInterrupt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState("");
  const [view, setView] = useState("chat"); // "chat" | "guidelines"

  // Drop back to the login screen if any request reports the token expired.
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setSessionId(null);
      setSessions([]);
      setMessages([]);
      setFiles([]);
      setInterrupt(null);
      setPlan([]);
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await api.listSessions();
      setSessions(list || []);
    } catch {
      /* handled by 401 logout or ignored */
    }
  }, []);

  // Load the user's session list once they're authenticated.
  useEffect(() => {
    if (user) refreshSessions();
  }, [user, refreshSessions]);

  // Fetch a session's transcript + files and load it into view.
  const loadSession = useCallback(async (sid) => {
    if (!sid) return;
    setError(null);
    setLoading(true);
    try {
      const [hist, listed, planResp] = await Promise.all([
        api.getHistory(sid),
        api.listFiles(sid),
        api.getPlan(sid),
      ]);
      setMessages((hist.messages || []).map((m) => ({ ...m })));
      setFiles(listed.files || []);
      setPlan(planResp.plan || []);
      setInterrupt(hist.interrupted ? hist.interrupt : null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Re-fetch just the agent's plan (after a reply, the agent may have updated it).
  const refreshPlan = useCallback(async (sid) => {
    if (!sid) return;
    try {
      const planResp = await api.getPlan(sid);
      setPlan(planResp.plan || []);
    } catch {
      /* non-fatal: leave the existing plan in place */
    }
  }, []);

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
      setError(null);
      setMessages((m) => [...m, { role: "user", content: trimmed }]);
      setDraft("");
      setLoading(true);
      try {
        const resp = await api.sendChat(trimmed, sessionId);
        const sid = applyResponse(resp);
        refreshSessions(); // backend upserts the session row (title/updated_at)
        refreshPlan(sid || sessionId); // the agent may have written/updated its plan
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading, applyResponse, refreshSessions, refreshPlan]
  );

  const handleResume = useCallback(
    async (decision, opts) => {
      if (!sessionId || loading) return;
      setError(null);
      setLoading(true);
      try {
        const resp = await api.resumeChat(sessionId, decision, opts);
        applyResponse(resp);
        refreshPlan(sessionId); // approving/rejecting may advance the agent's plan
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading, applyResponse, refreshPlan]
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
          refreshSessions();
        }
        return resp;
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, refreshSessions]
  );

  const startNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setFiles([]);
    setPlan([]);
    setInterrupt(null);
    setError(null);
    setDraft("");
    setView("chat");
  }, []);

  const handleSelectSession = useCallback(
    (sid) => {
      if (sid === sessionId) return;
      setSessionId(sid);
      setInterrupt(null);
      setView("chat");
      loadSession(sid);
    },
    [sessionId, loadSession]
  );

  const handleOpenKey = useCallback(
    async (sid) => {
      const id = sid.trim();
      if (!id) return;
      setSessionId(id);
      setInterrupt(null);
      setView("chat");
      await loadSession(id);
      refreshSessions();
    },
    [loadSession, refreshSessions]
  );

  const handleRenameSession = useCallback(
    async (sid, title) => {
      try {
        await api.renameSession(sid, title);
        refreshSessions();
      } catch (e) {
        setError(e.message);
      }
    },
    [refreshSessions]
  );

  const handleDeleteSession = useCallback(
    async (sid) => {
      try {
        await api.deleteSession(sid);
      } catch (e) {
        setError(e.message);
      }
      if (sid === sessionId) startNewSession();
      refreshSessions();
    },
    [sessionId, startNewSession, refreshSessions]
  );

  const handleLogout = useCallback(() => {
    auth.logout();
    setUser(null);
    startNewSession();
    setSessions([]);
  }, [startNewSession]);

  const insertPath = useCallback((path) => {
    setDraft((d) => (d && !d.endsWith(" ") ? `${d} ${path} ` : `${d}${path} `));
  }, []);

  // ----- Gate on authentication -----
  if (!user) {
    return <LoginPage onAuthed={setUser} />;
  }

  return (
    <div className="app">
      <SessionBar
        sessionId={sessionId}
        onNewSession={startNewSession}
        view={view}
        onNavigate={setView}
        user={user}
        onLogout={handleLogout}
      />

      {view === "guidelines" ? (
        <GuidelinesPage onBack={() => setView("chat")} />
      ) : (
        <>
          <aside className="sidebar">
            <SessionList
              sessions={sessions}
              activeId={sessionId}
              onSelect={handleSelectSession}
              onNew={startNewSession}
              onRename={handleRenameSession}
              onDelete={handleDeleteSession}
              onOpenKey={handleOpenKey}
            />
            <FileSidebar
              files={files}
              onUpload={handleUpload}
              onInsertPath={insertPath}
              busy={loading}
            />
            <PlanSidebar plan={plan} />
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
        </>
      )}
    </div>
  );
}
