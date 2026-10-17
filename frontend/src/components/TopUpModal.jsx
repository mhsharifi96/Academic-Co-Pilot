import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api.js";
import * as auth from "../auth.js";
import { useT } from "../i18n.js";

// "Increase balance" modal, opened from the balance chip. Payment is in crypto
// and handled by hand: the user requests an amount on a network, an admin
// emails the wallet address, the user pays and marks it paid here, and the
// admin confirms — which credits the balance.
const OPEN = ["pending", "awaiting_payment", "paid"];
const STEPS = ["pending", "awaiting_payment", "paid", "completed"];

export default function TopUpModal({ onClose, onBalance }) {
  const { t } = useT();
  const user = auth.getUser();
  const [options, setOptions] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const [email, setEmail] = useState(user?.email || "");
  const [amount, setAmount] = useState(null);
  const [network, setNetwork] = useState("");
  const [txHash, setTxHash] = useState("");
  // Held in a ref so a parent passing an inline callback doesn't re-trigger
  // the load effect on every render.
  const onBalanceRef = useRef(onBalance);
  onBalanceRef.current = onBalance;

  const load = useCallback(async () => {
    setError(null);
    try {
      const [opts, list, me] = await Promise.all([
        api.getTopUpOptions(),
        api.listMyTopUps(),
        api.fetchMe().catch(() => null),
      ]);
      setOptions(opts);
      setRequests(list || []);
      setAmount((a) => a ?? opts.amounts[0]);
      setNetwork((n) => n || opts.networks[0]?.key || "");
      // An admin may have credited the balance since the page loaded.
      if (me && typeof me.balance === "number") {
        auth.setUser(me);
        onBalanceRef.current?.(me.balance);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const open = requests.find((r) => OPEN.includes(r.status));
  const past = requests.filter((r) => r !== open);

  async function act(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e) {
    e.preventDefault();
    if (!email.trim()) return setError(t("topup.errEmail"));
    act(() => api.createTopUp({ email: email.trim(), amount, network }));
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card topup-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="topup-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="topup-head">
          <h4 id="topup-title">{t("topup.title")}</h4>
          {typeof user?.balance === "number" && (
            <span className={`user-balance${user.balance <= 0 ? " empty" : ""}`}>
              <bdi>${user.balance.toFixed(3)}</bdi>
            </span>
          )}
        </div>

        {loading ? (
          <p className="modal-desc">{t("common.loading")}</p>
        ) : open ? (
          <OpenRequest
            req={open}
            busy={busy}
            txHash={txHash}
            setTxHash={setTxHash}
            onPaid={() => act(() => api.markTopUpPaid(open.id, txHash.trim()))}
            onCancel={() => act(() => api.cancelTopUp(open.id))}
          />
        ) : (
          options && (
            <form onSubmit={submit} className="topup-form">
              <p className="modal-desc">{t("topup.intro")}</p>

              <label className="topup-field">
                <span>{t("topup.email")}</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={busy}
                  required
                  dir="ltr"
                />
              </label>

              <div className="topup-field">
                <span id="topup-amount-label">{t("topup.amount")}</span>
                <div className="topup-amounts" role="radiogroup" aria-labelledby="topup-amount-label">
                  {options.amounts.map((a) => (
                    <button
                      key={a}
                      type="button"
                      role="radio"
                      aria-checked={amount === a}
                      className={`topup-amount${amount === a ? " active" : ""}`}
                      onClick={() => setAmount(a)}
                      disabled={busy}
                    >
                      <bdi>${a}</bdi>
                    </button>
                  ))}
                </div>
              </div>

              <label className="topup-field">
                <span>{t("topup.network")}</span>
                <select
                  value={network}
                  onChange={(e) => setNetwork(e.target.value)}
                  disabled={busy}
                  dir="ltr"
                >
                  {options.networks.map((n) => (
                    <option key={n.key} value={n.key}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="topup-notice">{t("topup.cryptoNotice")}</div>

              {error && <div className="modal-err">{error}</div>}

              <div className="modal-actions">
                <button className="primary" type="submit" disabled={busy || !amount || !network}>
                  {busy ? t("topup.sending") : t("topup.submit")}
                </button>
                <button className="ghost" type="button" disabled={busy} onClick={onClose}>
                  {t("common.cancel")}
                </button>
              </div>
            </form>
          )
        )}

        {open && error && <div className="modal-err">{error}</div>}
        {!loading && !options && error && <div className="modal-err">{error}</div>}

        {past.length > 0 && (
          <details className="topup-history">
            <summary>{t("topup.history")}</summary>
            <ul>
              {past.map((r) => (
                <li key={r.id}>
                  <bdi>${r.amount}</bdi> · {r.network_label}
                  <span className={`topup-status s-${r.status}`}>{t(`topup.status.${r.status}`)}</span>
                </li>
              ))}
            </ul>
          </details>
        )}

        {open && (
          <div className="modal-actions">
            <button className="ghost" onClick={onClose}>
              {t("common.close")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function OpenRequest({ req, busy, txHash, setTxHash, onPaid, onCancel }) {
  const { t } = useT();
  const at = STEPS.indexOf(req.status);

  return (
    <div className="topup-open">
      <p className="modal-desc">
        <bdi>${req.amount}</bdi> · {req.network_label} · <bdi>{req.email}</bdi>
      </p>

      <ol className="topup-steps">
        {STEPS.map((s, i) => (
          <li key={s} className={i < at ? "done" : i === at ? "current" : ""}>
            {t(`topup.step.${s}`)}
          </li>
        ))}
      </ol>

      <p className="topup-explain">{t(`topup.explain.${req.status}`)}</p>

      {req.status === "awaiting_payment" && (
        <>
          {req.wallet_address && (
            <div className="modal-doi topup-wallet">
              <span className="modal-doi-label">{t("topup.wallet")}</span>
              <input readOnly value={req.wallet_address} dir="ltr" onFocus={(e) => e.target.select()} />
            </div>
          )}
          {req.admin_note && <p className="topup-note">{req.admin_note}</p>}
          <label className="topup-field">
            <span>{t("topup.txHash")}</span>
            <input
              value={txHash}
              onChange={(e) => setTxHash(e.target.value)}
              placeholder={t("topup.txHashHint")}
              disabled={busy}
              dir="ltr"
            />
          </label>
        </>
      )}

      {req.status === "paid" && req.tx_hash && (
        <p className="topup-note">
          {t("topup.txHash")}: <code dir="ltr">{req.tx_hash}</code>
        </p>
      )}

      <div className="modal-actions">
        {req.status === "awaiting_payment" && (
          <button className="primary" disabled={busy} onClick={onPaid}>
            {t("topup.markPaid")}
          </button>
        )}
        {req.status !== "paid" && (
          <button className="ghost" disabled={busy} onClick={onCancel}>
            {t("topup.cancelRequest")}
          </button>
        )}
      </div>
    </div>
  );
}
