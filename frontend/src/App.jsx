import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [selectedImages, setSelectedImages] = useState([]);
  const [userMode, setUserMode] = useState("personal"); // 'personal', 'art', 'poster', 'story', 'transform', 'business'
  const [conversationId, setConversationId] = useState(null);
  const [expandedReasoning, setExpandedReasoning] = useState({});
  const [editableSlogans, setEditableSlogans] = useState({});
  
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Simulated Progress Logic with better stages
  useEffect(() => {
    let timers = [];
    if (loading) {
      const stages = [
        "Understanding your vision...",
        "Analyzing creative direction...",
        "Generating variations...",
        "Adding finishing touches...",
        "Preparing your results..."
      ];
      
      stages.forEach((stage, index) => {
        const timer = setTimeout(() => {
          setLoadingStage(stage);
        }, index * 2000);
        timers.push(timer);
      });
      
      return () => {
        timers.forEach(timer => clearTimeout(timer));
        setLoadingStage("");
      };
    }
  }, [loading]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, loadingStage]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Set mode function - ONLY sets the mode, doesn't send a message
  const setMode = (mode) => {
    setUserMode(mode);
    // Focus input for user to type their own prompt
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const toggleReasoning = (messageIndex) => {
    setExpandedReasoning(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }));
  };

  const updateSlogan = (messageIndex, imageIndex, newSlogan) => {
    setEditableSlogans(prev => ({
      ...prev,
      [`${messageIndex}-${imageIndex}`]: newSlogan
    }));
  };

  const sendMessage = async (overrideText) => {
    const textToSend = overrideText || input;
    if (!textToSend.trim()) return;

    // Add user message
    const userMessage = { 
      sender: "user", 
      text: textToSend,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user_id: "demo-user", 
          message: textToSend,
          conversation_id: conversationId,
          mode: userMode  
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Store conversation ID for context
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
      }

      // Process response based on type
      let botMessage = { 
        sender: "bot", 
        type: data.type,
        timestamp: data.timestamp || Date.now()
      };

      if (data.type === "question") {
        botMessage.text = data.content.text;
        botMessage.suggestions = data.content.suggestions || [];
      }
      else if (data.type === "image" || data.type === "poster") {
        botMessage.images = data.content.images;
        botMessage.reasoning = data.content.reasoning;
        botMessage.metadata = data.content.metadata;
        botMessage.promptUsed = data.content.prompt_used;
        botMessage.mode = data.content.mode;
        botMessage.style = data.content.style;
        
        // For posters, include slogan
        if (data.type === "poster") {
          botMessage.slogan = data.content.slogan;
        }
      }
      else if (data.type === "story") {
        botMessage.title = data.content.title;
        botMessage.scenes = data.content.scenes;
        botMessage.images = data.content.images;
        botMessage.reasoning = data.content.reasoning;
        botMessage.metadata = data.content.metadata;
        botMessage.mode = data.content.mode;
        botMessage.style = data.content.style;
      }
      else if (data.type === "text") {
        botMessage.text = data.content.text;
      }
      else if (data.type === "conversation_with_image") {
      // Only add text message if there's actual text content
      if (data.content.text && data.content.text.trim() !== "") {
        const textMessage = {
          sender: "bot",
          text: data.content.text,
          timestamp: Date.now()
        };
        setMessages(prev => [...prev, textMessage]);
      }
      
      // Then add the image result as a separate message
      const imageResult = data.content.image_result;
      let imageMessage = {
        sender: "bot",
        type: imageResult.type,
        images: imageResult.content.images,
        reasoning: imageResult.content.reasoning,
        metadata: imageResult.content.metadata,
        mode: imageResult.content.mode,
        style: imageResult.content.style,
        timestamp: Date.now()
      };
      
      setMessages(prev => [...prev, imageMessage]);
    }
      else if (data.type === "error") {
        botMessage.text = data.message || "Something went wrong. Please try again.";
        botMessage.isError = true;
      }

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error("Error:", err);
      setMessages(prev => [...prev, { 
        sender: "bot", 
        text: "Connection error. Is the backend running?",
        isError: true,
        timestamp: Date.now()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageSelect = (image, messageIndex) => {
    setSelectedImages(prev => [...prev, { image, messageIndex }]);
  };

  const handleRefine = (refinement) => {
    sendMessage(refinement);
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const clearChat = async () => {
    setMessages([]);
    setSelectedImages([]);
    setConversationId(null);
    setExpandedReasoning({});
    try {
      await fetch(`${API_URL}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "demo-user" })
      });
    } catch (err) {
      console.error("Failed to reset backend context:", err);
    }
  };

  // Get placeholder text based on mode
  const getPlaceholderText = () => {
    switch(userMode) {
      case "art":
        return "Describe what you want to create in Art mode... (e.g., 'A surreal landscape with floating islands')";
      case "poster":
        return 'Describe your poster in Poster mode... (e.g., "Poster with slogan \'Delivering Success\' for tech company")';
      case "story":
        return "Describe your story in Story mode... (e.g., 'A dragon who couldn't breathe fire')";
      case "transform":
        return "Describe what to transform in Transform mode... (e.g., 'Turn this into a watercolor painting')";
      case "business":
        return "Describe your business visual in Business mode... (e.g., 'Premium product shot for headphones')";
      default:
        return "Describe your vision... (e.g., 'Paint my emotions')";
    }
  };

  return (
    <div className="app-shell">
      <div className="bg-orb orb-1"></div>
      <div className="bg-orb orb-2"></div>
      <div className="bg-orb orb-3"></div>

      <aside className="side-panel">
        <div className="brand">
          <div className="brand-mark">🎨 Vizzy Chat</div>
          <div className="brand-subtitle">Your creative AI studio</div>
        </div>

        <div className="mode-section">
          <h3>Select Mode</h3>
          <div className="mode-buttons">
            <button 
              className={`mode-btn ${userMode === 'personal' ? 'active' : ''}`}
              onClick={() => setMode('personal')}
            >
              🏠 Personal
            </button>
            <button 
              className={`mode-btn ${userMode === 'art' ? 'active' : ''}`}
              onClick={() => setMode('art')}
            >
              🎨 Art
            </button>
            <button 
              className={`mode-btn ${userMode === 'poster' ? 'active' : ''}`}
              onClick={() => setMode('poster')}
            >
              📰 Poster
            </button>
            <button 
              className={`mode-btn ${userMode === 'story' ? 'active' : ''}`}
              onClick={() => setMode('story')}
            >
              📖 Story
            </button>
            <button 
              className={`mode-btn ${userMode === 'transform' ? 'active' : ''}`}
              onClick={() => setMode('transform')}
            >
              🔄 Transform
            </button>
            <button 
              className={`mode-btn ${userMode === 'business' ? 'active' : ''}`}
              onClick={() => setMode('business')}
            >
              💼 Business
            </button>
          </div>
        </div>

        <div className="side-section">
          <h2>What I Can Create</h2>
          <div className="info-cards">
            <div className="info-card">
              <span className="tag">🎨 Art Mode</span>
              <p>Artistic interpretations, creative expressions, abstract visions</p>
            </div>
            <div className="info-card">
              <span className="tag">📰 Poster Mode</span>
              <p>Professional posters with text overlay, marketing materials</p>
            </div>
            <div className="info-card">
              <span className="tag">📖 Story Mode</span>
              <p>3-scene narratives with illustrations</p>
            </div>
            <div className="info-card">
              <span className="tag">🔄 Transform Mode</span>
              <p>Style transfer, reimagining concepts</p>
            </div>
            <div className="info-card">
              <span className="tag">💼 Business Mode</span>
              <p>Professional visuals, product shots, branding</p>
            </div>
          </div>
        </div>

        {userMode === 'business' && (
          <div className="side-section business-features">
            <h2>Business Tools</h2>
            <div className="feature-tags">
              <span className="tag">📊 Campaigns</span>
              <span className="tag">🏷️ Branding</span>
              <span className="tag">📱 Social</span>
              <span className="tag">🖼️ Signage</span>
            </div>
          </div>
        )}

        <div className="side-footer">
          <div className="status-pill">
            <span className="status-dot"></span>
            Connected to AI Studio • {userMode} mode
          </div>
          <button className="ghost-button" onClick={clearChat}>
            New Conversation
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="main-header">
          <div>
            <h1>
              {userMode === 'personal' && 'What would you like to create?'}
              {userMode === 'art' && 'Create something artistic'}
              {userMode === 'poster' && 'Design a professional poster'}
              {userMode === 'story' && 'Tell me a story'}
              {userMode === 'transform' && 'Transform your vision'}
              {userMode === 'business' && 'Create business visuals'}
            </h1>
            <div className="mode-status">
              <span>Active mode:</span>
              <span className="mode-status-badge">{userMode}</span>
            </div>
            <p>
              {userMode === 'personal' && 'Describe a scene, emotion, or idea'}
              {userMode === 'art' && 'Express yourself through art - describe what you want'}
              {userMode === 'poster' && 'Your text will be overlaid perfectly - describe your poster'}
              {userMode === 'story' && 'I\'ll create a 3-scene visual story - describe your tale'}
              {userMode === 'transform' && 'Change style, mood, or medium - describe the transformation'}
              {userMode === 'business' && 'Professional marketing materials - describe your needs'}
            </p>
          </div>
          <div className="header-actions">
            <button
              className="ghost-button"
              onClick={() => {
                const prompts = {
                  personal: "Create something surprising and beautiful",
                  art: "Abstract representation of joy with vibrant colors",
                  poster: 'Minimalist poster with slogan "Dream Big"',
                  story: "A magical forest adventure with mysterious creatures",
                  transform: "Transform this scene into an oil painting",
                  business: "Premium product visualization for luxury brand"
                };
                sendMessage(prompts[userMode]);
              }}
            >
              ✨ Surprise me
            </button>
          </div>
        </header>

        <div className="chat-wrapper">
          <div className="messages-area" ref={scrollRef}>
            {messages.length === 0 && (
              <div className="welcome-hero">
                <h2>Let's create something amazing together</h2>
                <p>Select a mode above and describe what you want:</p>
                <div className="hero-chips">
                  {userMode === 'personal' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage("Paint how my last year felt")}>Paint my emotions</button>
                      <button className="idea-chip" onClick={() => sendMessage("Create a dreamlike memory")}>Dreamlike memory</button>
                    </>
                  )}
                  {userMode === 'art' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage("Abstract representation of happiness")}>Abstract happiness</button>
                      <button className="idea-chip" onClick={() => sendMessage("Surreal landscape with floating islands")}>Surreal landscape</button>
                    </>
                  )}
                  {userMode === 'poster' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage('Poster with slogan "Innovation Now" for tech company')}>Tech poster</button>
                      <button className="idea-chip" onClick={() => sendMessage('Sale poster with text "50% OFF"')}>Sale poster</button>
                    </>
                  )}
                  {userMode === 'story' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage("A dragon who couldn't breathe fire")}>Dragon story</button>
                      <button className="idea-chip" onClick={() => sendMessage("Two friends discover a hidden world")}>Hidden world</button>
                    </>
                  )}
                  {userMode === 'transform' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage("Turn this into an oil painting")}>Oil painting</button>
                      <button className="idea-chip" onClick={() => sendMessage("Make it look like a sketch")}>Sketch style</button>
                    </>
                  )}
                  {userMode === 'business' && (
                    <>
                      <button className="idea-chip" onClick={() => sendMessage("Create premium product visuals")}>Product visuals</button>
                      <button className="idea-chip" onClick={() => sendMessage("Design brand artwork")}>Brand artwork</button>
                    </>
                  )}
                </div>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={index} className={`message-row ${msg.sender} ${msg.isError ? 'error' : ''}`}>
                <div className="bubble">
                  {/* Mode indicator for bot messages */}
                  {msg.sender === 'bot' && msg.mode && (
                    <div className="mode-indicator">
                      <span className="mode-tag">{msg.mode} mode</span>
                      {msg.style && <span className="style-tag">Style: {msg.style}</span>}
                    </div>
                  )}

                  {msg.text && <p>{msg.text}</p>}
                  
                  {/* AI Reasoning with Accordion */}
                  {msg.reasoning && (
                    <div className="reasoning-accordion">
                      <button 
                        className="reasoning-toggle"
                        onClick={() => toggleReasoning(index)}
                      >
                        <span className="reasoning-toggle-left">
                          <span className="reasoning-icon">🧠</span>
                          Why was this generated?
                        </span>
                        <span className="reasoning-toggle-arrow">
                          {expandedReasoning[index] ? '▼' : '▶'}
                        </span>
                      </button>
                      {expandedReasoning[index] && (
                        <div className="reasoning-content">
                          {msg.reasoning}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Suggestions for questions - optionally remove or keep minimal */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="suggestions">
                      {msg.suggestions.map((sugg, i) => (
                        <button 
                          key={i} 
                          className="suggestion-chip"
                          onClick={() => handleSuggestionClick(sugg)}
                        >
                          {sugg}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Image Grid - with special handling for posters */}
                  {msg.images && !msg.scenes && (
                    <div className="image-grid">
                      {msg.images.map((img, i) => (
                        <div 
                          key={i} 
                          className={`image-card ${msg.type === 'poster' ? 'poster-card' : ''} ${selectedImages.some(s => s.image === img) ? 'selected' : ''}`}
                          onClick={() => handleImageSelect(img, index)}
                        >
                          <div className="image-container">
                            <img src={`data:image/png;base64,${img}`} alt={`Variation ${i+1}`} />
                            
                            {/* Text overlay for posters */}
                            {msg.type === 'poster' && msg.slogan && (
                              <div className="poster-text-overlay">
                                {editableSlogans[`${index}-${i}`] || msg.slogan}
                              </div>
                            )}
                          </div>
                          
                          {/* Slogan editor for posters */}
                          {msg.type === 'poster' && msg.slogan && (
                            <div className="poster-controls">
                              <input 
                                type="text" 
                                className="slogan-input"
                                defaultValue={msg.slogan}
                                onChange={(e) => updateSlogan(index, i, e.target.value)}
                                placeholder="Edit slogan"
                                onClick={(e) => e.stopPropagation()}
                              />
                              <button 
                                className="apply-text-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  // Force re-render with new slogan
                                  setEditableSlogans({...editableSlogans});
                                }}
                              >
                                Update Text
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Story Display */}
                  {msg.scenes && (
                    <div className="story-block">
                      {msg.title && <h3 className="story-title">{msg.title}</h3>}
                      {msg.scenes.map((scene, i) => (
                        <div key={i} className="scene-card">
                          <div className="scene-header">Scene {i + 1}</div>
                          <p className="scene-text">{scene}</p>
                          {msg.images && msg.images[i] && (
                            <img 
                              src={`data:image/png;base64,${msg.images[i]}`} 
                              alt={`Scene ${i+1}`}
                              className="scene-image"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Refinement options after generation */}
                  {msg.images && msg.images.length > 0 && (
                    <div className="refinement-options">
                      <p className="refinement-label">Refine this:</p>
                      <div className="refinement-chips">
                        <button onClick={() => handleRefine("Make it brighter")}>✨ Brighter</button>
                        <button onClick={() => handleRefine("More abstract")}>🎨 More abstract</button>
                        <button onClick={() => handleRefine("Add warm tones")}>🔥 Warmer</button>
                        <button onClick={() => handleRefine("Different style")}>🔄 Different style</button>
                      </div>
                    </div>
                  )}

                  {/* Metadata (generation time, etc) */}
                  {msg.metadata && (
                    <div className="message-metadata">
                      <span>✨ Generated in {msg.metadata.generation_time}s</span>
                      {msg.metadata.style && <span>🎨 Style: {msg.metadata.style}</span>}
                      {msg.metadata.mood && <span>🌙 Mood: {msg.metadata.mood}</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-row bot">
                <div className="shimmer-container">
                  <div className="shimmer-text">{loadingStage}</div>
                  <div className="shimmer-card"></div>
                  <div className="shimmer-card"></div>
                </div>
              </div>
            )}
          </div>

          <div className="input-container">
            <div className="quick-actions">
              <button 
                className={`action-pill ${userMode === 'art' ? 'active' : ''}`}
                onClick={() => setMode('art')}
              >
                🎨 Art mode
              </button>
              <button 
                className={`action-pill ${userMode === 'poster' ? 'active' : ''}`}
                onClick={() => setMode('poster')}
              >
                📰 Poster mode
              </button>
              <button 
                className={`action-pill ${userMode === 'story' ? 'active' : ''}`}
                onClick={() => setMode('story')}
              >
                📖 Story mode
              </button>
              <button 
                className={`action-pill ${userMode === 'transform' ? 'active' : ''}`}
                onClick={() => setMode('transform')}
              >
                🔄 Transform
              </button>
            </div>
            <div className="input-wrapper">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={getPlaceholderText()}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                disabled={loading}
              />
              <button 
                className="gen-button" 
                onClick={() => sendMessage()}
                disabled={loading}
              >
                {loading ? 'Creating...' : 'Generate →'}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;