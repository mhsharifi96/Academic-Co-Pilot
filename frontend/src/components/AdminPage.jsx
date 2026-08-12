import { useCallback, useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import SiteSettingsPanel from "./SiteSettingsPanel.jsx";
import WizardAdminPanel from "./WizardAdminPanel.jsx";

// Admin console, split into tabs: user balances, guided workflows, and
// site-wide switches. Only rendered when the logged-in user has
// is_admin === true (gated in App.jsx / SessionBar).
export default function AdminPage({ onBack, currentUserId }) {
  const { t } = useT();
  const [tab, setTab] = useState("users"); // "users" | "wizards" | "site"
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [drafts, setDrafts] = useState({}); // userId -> editable balance string
  const [savingId, setSavingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listUsers();
      setUsers(list || []);
      setDrafts(
        Object.fromEntries((list || []).map((u) => [u.id, String(u.balance)]))
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Only fetch the user list when its tab is actually showing.
  useEffect(() => {
    if (tab === "users") load();
  }, [tab, load]);

  const applyUpdated = useCallback((updated) => {
    setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)));
    setDrafts((d) => ({ ...d, [updated.id]: String(updated.balance) }));
  }, []);

  const saveBalance = useCallback(
    async (userId) => {
      const raw = drafts[userId];
      const balance = Number(raw);
      if (Number.isNaN(balance) || balance < 0) {
        setError("Balance must be a number ≥ 0.");
        return;
      }
      setSavingId(userId);
      setError(null);
      try {
        const updated = await api.updateUser(userId, { balance });
        applyUpdated(updated);
      } catch (e) {
        setError(e.message);
      } finally {
        setSavingId(null);
      }
    },
    [drafts, applyUpdated]
  );

  const credit = useCallback(
    async (userId, amount) => {
      setSavingId(userId);
      setError(null);
      try {
        const updated = await api.adjustBalance(userId, amount);
        applyUpdated(updated);
      } catch (e) {
        setError(e.message);
      } finally {
        setSavingId(null);
      }
    },
    [applyUpdated]
  );

  const toggleAdmin = useCallback(
    async (user) => {
      setSavingId(user.id);
      setError(null);
      try {
        const updated = await api.updateUser(user.id, { isAdmin: !user.is_admin });
        applyUpdated(updated);
      } catch (e) {
        setError(e.message);
      } finally {
        setSavingId(null);
      }
    },
    [applyUpdated]
  );

  return (
    <div className="admin-page">
      <div className="admin-inner">
        <button className="ghost back-btn" onClick={onBack}>
          ← Back to chat
        </button>
        <h1>Administration</h1>

        <div className="admin-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === "users"}
            className={`admin-tab${tab === "users" ? " active" : ""}`}
            onClick={() => setTab("users")}
          >
            Users
          </button>
          <button
            role="tab"
            aria-selected={tab === "wizards"}
            className={`admin-tab${tab === "wizards" ? " active" : ""}`}
            onClick={() => setTab("wizards")}
          >
            {t("admin.title")}
          </button>
          <button
            role="tab"
            aria-selected={tab === "site"}
            className={`admin-tab${tab === "site" ? " active" : ""}`}
            onClick={() => setTab("site")}
          >
            Site
          </button>
        </div>

        {tab === "wizards" ? (
          <WizardAdminPanel />
        ) : tab === "site" ? (
          <SiteSettingsPanel />
        ) : (
          <>
        <p className="admin-sub">
          Manage each user's remaining balance (USD). Balances are consumed as
          users chat with the agents.
        </p>

        {error && <div className="banner-error">⚠️ {error}</div>}

        {loading ? (
          <p className="empty-note">Loading users…</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Balance ($)</th>
                <th>Admin</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="admin-email">
                    {u.email}
                    {u.id === currentUserId && <span className="you-tag">you</span>}
                  </td>
                  <td>
                    <input
                      className="balance-input"
                      type="number"
                      step="0.01"
                      min="0"
                      value={drafts[u.id] ?? ""}
                      onChange={(e) =>
                        setDrafts((d) => ({ ...d, [u.id]: e.target.value }))
                      }
                    />
                  </td>
                  <td>
                    <button
                      className={`admin-badge-btn${u.is_admin ? " on" : ""}`}
                      disabled={savingId === u.id || u.id === currentUserId}
                      title={
                        u.id === currentUserId
                          ? "You can't change your own admin status here"
                          : "Toggle admin"
                      }
                      onClick={() => toggleAdmin(u)}
                    >
                      {u.is_admin ? "Admin" : "User"}
                    </button>
                  </td>
                  <td className="admin-actions">
                    <button
                      className="primary"
                      disabled={savingId === u.id}
                      onClick={() => saveBalance(u.id)}
                    >
                      Save
                    </button>
                    <button
                      disabled={savingId === u.id}
                      onClick={() => credit(u.id, 0.5)}
                      title="Add $0.50"
                    >
                      +$0.50
                    </button>
                    <button
                      disabled={savingId === u.id}
                      onClick={() => credit(u.id, 1)}
                      title="Add $1.00"
                    >
                      +$1
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
          </>
        )}
      </div>
    </div>
  );
}
