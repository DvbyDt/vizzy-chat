import React, { useState, useEffect, useRef } from "react";

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  const sendMessage = async (overrideText) => {
    const textToSend = overrideText || input;
    if (!textToSend.trim()) return;

    setMessages(prev => [...prev, { sender: "user", text: textToSend }]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "demo-user", message: textToSend })
      });

      const data = await response.json();
      setMessages(prev => [...prev, { sender: "bot", ...data }]);
    } catch (err) {
      setMessages(prev => [...prev, { sender: "bot", text: "Connection error." }]);
    }
    setLoading(false);
  };

  return (
    <div className="chat-wrapper">
      <div className="messages-area" ref={scrollRef}>
        {messages.map((msg, index) => (
  <div key={index} className={`message ${msg.sender}`}>
    {msg.text && <p>{msg.text}</p>}

    {/* NEW: Display the reasoning block if it exists */}
    {msg.reasoning && (
      <div className="ai-explanation">
        <span className="sparkle">✨</span>
        <p><strong>Perspective:</strong> {msg.reasoning}</p>
      </div>
    )}

    {msg.images && !msg.scenes && (
      <div className="image-grid">
        {/* ... existing image mapping ... */}
      </div>
    )}
  </div>
))}
        {loading && <div className="typing">AI is generating...</div>}
      </div>

      <div className="input-container">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your vision..."
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={() => sendMessage()}>Generate</button>
      </div>
    </div>
  );
}

export default Chat;