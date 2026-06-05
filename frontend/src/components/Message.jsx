import ReactMarkdown from "react-markdown";

export default function Message({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`msg ${role}`}>
      <div className="role">{isUser ? "You" : "Co-Pilot"}</div>
      {isUser ? (
        <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {content}
        </div>
      ) : (
        <div className="md">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
