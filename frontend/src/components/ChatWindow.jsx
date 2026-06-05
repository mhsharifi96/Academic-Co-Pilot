import { useEffect, useRef } from "react";
import Message from "./Message.jsx";
import InterruptCard from "./InterruptCard.jsx";

export default function ChatWindow({ messages, interrupt, loading, onResume }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, interrupt, loading]);

  const empty = messages.length === 0 && !interrupt;

  return (
    <div className="chat-window">
      {empty && (
        <div className="welcome">
          <h2>👋 Welcome to your Academic Co-Pilot</h2>
          <p>
            Upload your PDFs/CSVs on the left, then ask me to screen abstracts,
            draft sections, plan a paper, or analyze data.
          </p>
          <p>
            Tip: type <code>@</code> in the message box to reference an uploaded
            file by its exact path.
          </p>
        </div>
      )}

      {messages.map((m, i) => (
        <Message key={i} role={m.role} content={m.content} />
      ))}

      {interrupt && (
        <InterruptCard
          // Remount per distinct interrupt so edit/reject state never leaks
          // across the section-by-section approval flow.
          key={JSON.stringify(interrupt.pending_actions)}
          interrupt={interrupt}
          loading={loading}
          onResume={onResume}
        />
      )}

      {loading && <div className="typing">Co-Pilot is thinking…</div>}

      <div ref={endRef} />
    </div>
  );
}
