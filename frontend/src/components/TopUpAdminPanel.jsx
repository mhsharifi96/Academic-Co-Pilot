"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "../api.js";

// The "Top-ups" tab of the admin console. Works the manual crypto flow:
//   pending          → enter the wallet address, "Send payment email"
//   awaiting_payment → (re-send) or confirm once the transfer is visible
//   paid             → check the tx hash, "Confirm & credit"
// Confirming credits the user's balance server-side. When SMTP isn't
// configured the email isn't sent automatically; a mailto: link with the same
// message is offered instead.
const STATUS_LABEL = {
  pending: "Requested",
  awaiting_payment: "Awaiting payment",
  paid: "Paid — confirm",
  completed: "Credited",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export default function TopUpAdminPanel() {
  const [filter, setFilter] = useState("open"); // "open" | "" (all)
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null); // { text, mailto? }
  const [busyId, setBusyId] = useState(null);
  const [wallets, setWallets] = useState({}); // requestId -> address draft
  const [notes, setNotes] = useState({}); // requestId -> note draft

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows((await api.adminListTopUps(filter || undefined)) || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function run(id, fn) {
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  const sendEmail = (r) =>
    run(r.id, async () => {
      const walletAddress = (wallets[r.id] ?? r.wallet_address ?? "").trim();
      if (!walletAddress) throw new Error("Enter the wallet address first.");
      const res = await api.adminSendTopUpEmail(r.id, {
        walletAddress,
        note: notes[r.id] ?? r.admin_note ?? "",
      });
      setNotice(
        res.email_sent
          ? { text: `Payment email sent to ${r.email}.` }
          : {
              text: `${res.email_error} The request is marked as awaiting payment — send the email yourself:`,
              mailto: res.mailto,
            }
      );
    });

  const confirm = (r) => {
    if (!window.confirm(`Credit $${r.amount} to ${r.user_email || r.email}?`)) return;
    run(r.id, async () => {
      const res = await api.adminConfirmTopUp(r.id);
      setNotice({ text: `Credited $${r.amount}. New balance: $${res.user_balance.toFixed(3)}.` });
    });
  };

  const reject = (r) => {
    const reason = window.prompt("Reason (optional, kept on the request):", "");
    if (reason === null) return;
    run(r.id, () => api.adminRejectTopUp(r.id, reason));
  };

  return (
    <>
      <p className="admin-sub">
        Balance top-up requests, paid in crypto. Email the user the wallet address
        for their network, wait for the payment, then confirm to credit their
        balance.
      </p>

      <div className="topup-filter">
        <button
          className={`admin-badge-btn${filter === "open" ? " on" : ""}`}
          onClick={() => setFilter("open")}
        >
          Open
        </button>
        <button
          className={`admin-badge-btn${filter === "" ? " on" : ""}`}
          onClick={() => setFilter("")}
        >
          All
        </button>
      </div>

      {error && <div className="banner-error">⚠️ {error}</div>}
      {notice && (
        <div className="topup-admin-notice">
          {notice.text}{" "}
          {notice.mailto && (
            <a href={notice.mailto} target="_blank" rel="noreferrer">
              Open in mail client
            </a>
          )}
        </div>
      )}

      {loading ? (
        <p className="empty-note">Loading requests…</p>
      ) : rows.length === 0 ? (
        <p className="empty-note">No {filter === "open" ? "open " : ""}top-up requests.</p>
      ) : (
        <table className="admin-table topup-table">
          <thead>
            <tr>
              <th>User / contact</th>
              <th>Amount</th>
              <th>Network</th>
              <th>Status</th>
              <th>Payment</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const busy = busyId === r.id;
              const canEmail = r.status === "pending" || r.status === "awaiting_payment";
              const canConfirm = r.status === "awaiting_payment" || r.status === "paid";
              const canReject = canEmail || r.status === "paid";
              return (
                <tr key={r.id}>
                  <td className="admin-email">
                    {r.user_email}
                    {r.email !== r.user_email && <div className="topup-sub">✉ {r.email}</div>}
                    <div className="topup-sub">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                    </div>
                  </td>
                  <td>${r.amount}</td>
                  <td>{r.network_label}</td>
                  <td>
                    <span className={`topup-status s-${r.status}`}>
                      {STATUS_LABEL[r.status] || r.status}
                    </span>
                  </td>
                  <td className="topup-payment">
                    {canEmail ? (
                      <>
                        <input
                          className="topup-admin-input"
                          placeholder="Wallet address"
                          value={wallets[r.id] ?? r.wallet_address ?? ""}
                          onChange={(e) => setWallets((w) => ({ ...w, [r.id]: e.target.value }))}
                          disabled={busy}
                        />
                        <input
                          className="topup-admin-input"
                          placeholder="Note for the email (optional)"
                          value={notes[r.id] ?? r.admin_note ?? ""}
                          onChange={(e) => setNotes((n) => ({ ...n, [r.id]: e.target.value }))}
                          disabled={busy}
                        />
                      </>
                    ) : (
                      r.wallet_address && <code className="topup-sub">{r.wallet_address}</code>
                    )}
                    {r.tx_hash && (
                      <div className="topup-sub">
                        tx: <code>{r.tx_hash}</code>
                      </div>
                    )}
                    {!canEmail && r.admin_note && <div className="topup-sub">{r.admin_note}</div>}
                  </td>
                  <td className="admin-actions">
                    {canEmail && (
                      <button className={r.status === "pending" ? "primary" : ""} disabled={busy} onClick={() => sendEmail(r)}>
                        {r.status === "pending" ? "Send payment email" : "Re-send email"}
                      </button>
                    )}
                    {canConfirm && (
                      <button className={r.status === "paid" ? "primary" : ""} disabled={busy} onClick={() => confirm(r)}>
                        Confirm & credit
                      </button>
                    )}
                    {canReject && (
                      <button className="ghost" disabled={busy} onClick={() => reject(r)}>
                        Reject
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}
