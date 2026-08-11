import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import * as auth from "./auth.js";
import SessionBar from "./components/SessionBar.jsx";
import SessionList from "./components/SessionList.jsx";
import FileSidebar from "./components/FileSidebar.jsx";
import PlanSidebar from "./components/PlanSidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import DownloadModal from "./components/DownloadModal.jsx";
import DownloadsPage from "./components/DownloadsPage.jsx";
import MessageInput from "./components/MessageInput.jsx";
import GuidelinesPage from "./components/GuidelinesPage.jsx";
import AdminPage from "./components/AdminPage.jsx";
import LoginPage from "./components/LoginPage.jsx";
import WizardDetail from "./components/WizardDetail.jsx";
import WizardLanding from "./components/WizardLanding.jsx";
import WizardRunner from "./components/WizardRunner.jsx";
import WizardRunsPage from "./components/WizardRunsPage.jsx";
import { navigate, replace, useHashRoute } from "./router.js";

// The existing chat application. `user` is owned by the router shell below so
// the public wizard pages can render before this component's auth gate.
function ChatApp({ user, setUser }) {
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]); // {id, title, updated_at}
  const [messages, setMessages] = useState([]); // {role, content}
  const [files, setFiles] = useState([]); // {path, filename, type}
  const [plan, setPlan] = useState([]); // {text, status}
  const [interrupt, setInterrupt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState("");
  const [view, setView] = useState("chat"); // "chat" | "guidelines" | "downloads" | "admin"
  const [agentType, setAgentType] = useState("academic"); // "academic" | "deep"
  const [downloadModalDoi, setDownloadModalDoi] = useState(null); // DOI awaiting confirm
  const [downloadReload, setDownloadReload] = useState(0); // bump to refresh job list

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

  // Refresh the fresh profile (balance + admin flag) on login, so a user who
  // logged in before these fields existed — or whose balance changed on the
  // server — sees current values.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.fetchMe();
        if (!cancelled && me) setUser(auth.setUser(me));
      } catch {
        /* non-fatal: keep the stored user */
      }
    })();
    return () => {
      cancelled = true;
    };
    // Only on auth transitions, not on every balance tweak.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

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
      setAgentType(hist.agent_type || "academic");
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
    // Reflect the balance the server billed this turn, if returned.
    if (typeof resp.balance === "number") {
      setUser((u) => (u ? auth.patchUser({ balance: resp.balance }) : u));
    }
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
        const resp = await api.sendChat(trimmed, sessionId, agentType);
        const sid = applyResponse(resp);
        refreshSessions(); // backend upserts the session row (title/updated_at)
        refreshPlan(sid || sessionId); // the agent may have written/updated its plan
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading, applyResponse, refreshSessions, refreshPlan, agentType]
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

  // ----- PDF downloads -----
  const refreshFiles = useCallback(
    async (sid) => {
      const id = sid || sessionId;
      if (!id) return;
      try {
        const listed = await api.listFiles(id);
        setFiles(listed.files || []);
      } catch {
        /* non-fatal */
      }
    },
    [sessionId]
  );

  const handleRequestPdf = useCallback((doi) => setDownloadModalDoi(doi), []);
  const handleDownloadCreated = useCallback(
    () => setDownloadReload((n) => n + 1),
    []
  );
  const handleDownloadIngested = useCallback(() => {
    refreshFiles();
  }, [refreshFiles]);
  const handleContinueWithout = useCallback((job) => {
    setMessages((m) => [
      ...m,
      {
        role: "assistant",
        content:
          `Okay — continuing without the full PDF for ${job.doi}. My answers ` +
          `will be based only on the information currently available in this ` +
          `conversation.`,
      },
    ]);
  }, []);

  const startNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setFiles([]);
    setPlan([]);
    setInterrupt(null);
    setError(null);
    setDraft("");
    setAgentType("academic");
    setDownloadModalDoi(null);
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
        // The wizard pages live on their own hash routes so their links are
        // shareable; that nav item hands over to the router instead of
        // switching this component's local view.
        onNavigate={(next) => (next === "wizards" ? navigate("/") : setView(next))}
        user={user}
        onLogout={handleLogout}
      />

      {view === "guidelines" ? (
        <GuidelinesPage onBack={() => setView("chat")} />
      ) : view === "admin" && user?.is_admin ? (
        <AdminPage onBack={() => setView("chat")} currentUserId={user.id} />
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
            {view === "downloads" ? (
              <DownloadsPage
                sessionId={sessionId}
                reloadToken={downloadReload}
                onCreated={handleDownloadCreated}
                onIngested={handleDownloadIngested}
                onUploadPdf={handleUpload}
                onContinueWithout={handleContinueWithout}
              />
            ) : (
              <>
                <ChatWindow
                  messages={messages}
                  interrupt={interrupt}
                  loading={loading}
                  onResume={handleResume}
                  agentType={agentType}
                  onAgentTypeChange={setAgentType}
                  agentLocked={messages.length > 0 || !!sessionId}
                  sessionId={sessionId}
                  onRequestPdf={handleRequestPdf}
                  downloadReload={downloadReload}
                  onDownloadIngested={handleDownloadIngested}
                  onUploadPdf={handleUpload}
                  onContinueWithout={handleContinueWithout}
                />
                {downloadModalDoi && (
                  <DownloadModal
                    doi={downloadModalDoi}
                    sessionId={sessionId}
                    onClose={() => setDownloadModalDoi(null)}
                    onCreated={handleDownloadCreated}
                  />
                )}
                <MessageInput
                  value={draft}
                  onChange={setDraft}
                  onSend={handleSend}
                  files={files}
                  disabled={loading || !!interrupt}
                  interrupted={!!interrupt}
                />
              </>
            )}
          </main>
        </>
      )}
    </div>
  );
}

// Where the user was headed before the login gate stopped them, so they land on
// the wizard they clicked rather than on the chat home page.
const PENDING_KEY = "paperagent.pendingRoute";

export default function App() {
  const [user, setUser] = useState(() => auth.getUser());
  const { route } = useHashRoute();

  // The 401 handler fires from anywhere in the app; clearing `user` here is
  // what swaps the whole tree back to the login screen.
  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  // Resume an interrupted destination once the user signs in.
  useEffect(() => {
    if (!user) return;
    let pending = null;
    try {
      pending = sessionStorage.getItem(PENDING_KEY);
      sessionStorage.removeItem(PENDING_KEY);
    } catch {
      /* storage disabled */
    }
    if (pending) replace(pending);
  }, [user]);

  function requireLogin(slug) {
    try {
      sessionStorage.setItem(PENDING_KEY, `/wizards/${encodeURIComponent(slug)}`);
    } catch {
      /* storage disabled */
    }
    navigate("/app");
  }

  // Public routes render ahead of ChatApp's auth gate.
  if (route.name === "landing") return <WizardLanding user={user} />;
  if (route.name === "wizard") {
    return (
      <WizardDetail slug={route.params.slug} user={user} onRequireLogin={requireLogin} />
    );
  }

  // Everything below needs an account. Falling through to ChatApp shows its
  // login screen, and the pending-route effect above brings them back here.
  if (user) {
    if (route.name === "run") return <WizardRunner runId={route.params.runId} />;
    if (route.name === "runs") return <WizardRunsPage />;
  }

  return <ChatApp user={user} setUser={setUser} />;
}
