import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import Message from "./Message.jsx";
import Icon from "./Icon.jsx";
import InterruptCard from "./InterruptCard.jsx";
import AgentSelector from "./AgentSelector.jsx";
import DownloadStatus from "./DownloadStatus.jsx";

// How close to the bottom still counts as "following the conversation".
const AT_BOTTOM_SLACK = 120;

export default function ChatWindow({
  messages,
  interrupt,
  loading,
  onResume,
  agentType,
  onAgentTypeChange,
  agentLocked,
  sessionId,
  onRequestPdf,
  downloadReload,
  onDownloadIngested,
  onUploadPdf,
  onContinueWithout,
}) {
  const scrollRef = useRef(null);
  const endRef = useRef(null);
  // Whether the user is still pinned to the newest message. Kept in a ref as
  // well as state because the scroll effect must read it without re-subscribing.
  const followingRef = useRef(true);
  const [following, setFollowing] = useState(true);

  const isNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < AT_BOTTOM_SLACK;
  }, []);

  const onScroll = useCallback(() => {
    const near = isNearBottom();
    followingRef.current = near;
    setFollowing(near);
  }, [isNearBottom]);

  // Auto-scroll ONLY while the user is already at the bottom. Scrolling on
  // every update regardless is the classic chat bug: you scroll up to re-read
  // something, a reply lands, and you get yanked away mid-sentence.
  useLayoutEffect(() => {
    if (!followingRef.current) return;
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, interrupt, loading]);

  // A brand-new conversation should start pinned again.
  useEffect(() => {
    followingRef.current = true;
    setFollowing(true);
  }, [sessionId]);

  function jumpToLatest() {
    followingRef.current = true;
    setFollowing(true);
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }

  const empty = messages.length === 0 && !interrupt;

  return (
    <div className="chat-scroll" ref={scrollRef} onScroll={onScroll}>
      {/* The conversation is a log: `aria-live="polite"` makes a screen reader
          announce each reply as it arrives instead of leaving the user to
          discover it by exploring the page. */}
      <div
        className="chat-window"
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        aria-label="Conversation"
      >
        {/* Pick an agent before the first message; a locked badge afterwards. */}
        <AgentSelector
          value={agentType}
          onChange={onAgentTypeChange}
          locked={agentLocked}
        />

        {empty && (
          <div className="welcome">
            <span className="welcome-icon" aria-hidden="true">
              <Icon name="sparkles" size={26} />
            </span>
            <h2>Welcome to your Academic Co-Pilot</h2>
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
          <Message
            key={i}
            role={m.role}
            content={m.content}
            onRequestPdf={onRequestPdf}
          />
        ))}

        <DownloadStatus
          sessionId={sessionId}
          reloadToken={downloadReload}
          onIngested={onDownloadIngested}
          onUploadPdf={onUploadPdf}
          onContinueWithout={onContinueWithout}
        />

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

        {/* An animated placeholder in the shape of the reply reads as "the
            answer is coming", where a line of static text reads as content. */}
        {loading && (
          <div className="msg assistant typing-bubble">
            <div className="role">Co-Pilot</div>
            <div className="typing-dots" role="status" aria-label="Co-Pilot is thinking">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Only offered once the user has actually scrolled away. */}
      {!following && (
        <button className="jump-latest" onClick={jumpToLatest}>
          <Icon name="chevronDown" size={16} />
          <span>Jump to latest</span>
        </button>
      )}
    </div>
  );
}
