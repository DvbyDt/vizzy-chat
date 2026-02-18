import React, { useState, useRef, useEffect } from "react";

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "demo-user",
        message: input
      })
    });

    const data = await response.json();
    let botMessage = { sender: "bot" };

    if (data.type === "image" || data.type === "poster") {
      botMessage.images = data.images;
    }

    if (data.type === "story") {
      botMessage.scenes = data.scenes;
      botMessage.images = data.images;
    }

    if (data.type === "question" || data.type === "text") {
      botMessage.text = data.text;
    }

    setMessages(prev => [...prev, botMessage]);
    setLoading(false);
  };

  return (
    <div className="chat-wrapper">

      <div className="messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.sender}`}>

            {msg.text && (
              <div className="bubble">
                {msg.text}
              </div>
            )}

            {msg.images && !msg.scenes && (
              <div className="image-grid">
                {msg.images.map((img, i) => (
                  <img
                    key={i}
                    className="generated-image"
                    src={`data:image/png;base64,${img}`}
                    alt=""
                  />
                ))}
              </div>
            )}

            {msg.scenes && (
              <div className="story-block">
                {msg.scenes.map((scene, i) => (
                  <div key={i} className="scene-card">
                    <h4>Scene {i + 1}</h4>
                    <p>{scene}</p>
                    <img
                      src={`data:image/png;base64,${msg.images[i]}`}
                      alt=""
                    />
                  </div>
                ))}
              </div>
            )}

          </div>
        ))}

        {loading && (
          <div className="message-row bot">
            <div className="bubble typing">
              AI is creating...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Vizzy to create something..."
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>Generate</button>
      </div>

    </div>
  );
}

export default Chat;
