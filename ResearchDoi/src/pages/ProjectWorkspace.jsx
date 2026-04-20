import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { onProject, updateProject, addSourceViaApi, addSourceFileViaApi, removeSource } from '../services/projectService';
import { fetchArticle } from '../services/arxiv';
import { useChat } from '../hooks/useChat';
import {
  ArrowLeft,
  Plus,
  Trash2,
  ExternalLink,
  FileText,
  FileDown,
  Loader2,
  Search,
  X,
  Edit3,
  Check,
  Send,
  Bot,
  RotateCcw,
  User,
  PanelLeft,
  Settings2,
  Database,
  Paperclip,
  Lightbulb,
  Mic,
  ArrowUp,
  MoreHorizontal
} from 'lucide-react';

const currentUser = { uid: "localUser" };

export default function ProjectWorkspace() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Source add form
  const [showDoiInput, setShowDoiInput] = useState(false);
  const [sourceType, setSourceType] = useState('doi'); // 'doi' or 'url' or 'file'
  const [sourceValue, setSourceValue] = useState('');
  const [sourceFile, setSourceFile] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [sourceError, setSourceError] = useState('');

  // Instructions editing
  const [editingInstructions, setEditingInstructions] = useState(false);
  const [instructionsDraft, setInstructionsDraft] = useState('');

  // Chat state
  const [inputValue, setInputValue] = useState('');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    activeChatId,
    chatSessions,
    messages,
    chatTitle,
    sending,
    setChatTitle,
    refreshChatSessions,
    sendMessage,
    startNewConversation,
    deleteConversation,
    switchConversation,
    reseedRAG,
    ingestSource,
  } = useChat(currentUser?.uid, projectId, project?.instructions || '');

  // Reseed RAG when project or chat changes
  useEffect(() => {
    if (project?.sources && project.sources.length > 0) {
      const timer = setTimeout(() => reseedRAG(project.sources), 1000);
      return () => clearTimeout(timer);
    }
  }, [project?.id, activeChatId, reseedRAG]);

  useEffect(() => {
    if (!currentUser || !projectId) return;
    const unsubscribe = onProject(currentUser.uid, projectId, (data) => {
      if (!data) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      setProject(data);
      setLoading(false);
    });
    return unsubscribe;
  }, [currentUser, projectId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(e) {
    e?.preventDefault();
    const text = inputValue.trim();
    if (!text || sending) return;

    setInputValue('');
    
    try {
      await sendMessage(text);
    } catch (err) {
      // Error handling is done in the hook
    } finally {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }



  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function handleAddSource(e) {
    e.preventDefault();
    if (sourceType !== 'file' && !sourceValue.trim()) return;
    if (sourceType === 'file' && !sourceFile) return;

    setFetching(true);
    setSourceError('');
    try {
      if (sourceType === 'file') {
        // Upload File
        await addSourceFileViaApi(currentUser.uid, projectId, sourceFile);
      } else {
        let sourceData;
        if (sourceType === 'doi') {
          const article = await fetchArticle(sourceValue.trim());
          sourceData = {
            type: 'doi',
            doi: article.doi,
            title: article.title,
            authors: article.authors.map((a) => `${a.given} ${a.family}`.trim()),
            journal: article.journal,
            date: article.date,
            url: article.url || `https://doi.org/${article.doi}`,
            pdf_url: article.pdfUrl || null,
          };
          if (project.sources?.some((s) => s.doi === article.doi)) {
            setSourceError('This DOI is already in the project.');
            setFetching(false);
            return;
          }
        } else {
          // Simple URL source
          sourceData = {
            type: 'url',
            url: sourceValue.trim(),
            title: sourceValue.trim().replace(/^https?:\/\//, '').split('/')[0],
          };
          if (project.sources?.some((s) => s.url === sourceData.url)) {
            setSourceError('This URL is already in the project.');
            setFetching(false);
            return;
          }
        }

        // Add to backend API
        await addSourceViaApi(currentUser.uid, projectId, sourceData);
      }

      setSourceValue('');
      setSourceFile(null);
      setShowDoiInput(false);
    } catch (err) {
      setSourceError(err.message || 'Failed to add source.');
    } finally {
      setFetching(false);
    }
  }

  async function handleRemoveSource(source) {
    try {
      await removeSource(currentUser.uid, projectId, source);
    } catch (err) {
      console.error('Failed to remove source:', err);
    }
  }

  async function handleSaveInstructions() {
    try {
      await updateProject(currentUser.uid, projectId, {
        instructions: instructionsDraft,
      });
      setEditingInstructions(false);
    } catch (err) {
      console.error('Failed to update instructions:', err);
    }
  }

  function startEditingInstructions() {
    setInstructionsDraft(project?.instructions || '');
    setEditingInstructions(true);
  }

  async function handleDeleteConversation(chatId) {
    if (!window.confirm('Delete this conversation and all its messages?')) return;
    try {
      await deleteConversation(chatId);
    } catch (err) {
      alert(err.message || 'Failed to delete conversation');
    }
  }

  /** Simple markdown-like rendering for chat messages */
  function renderMessageText(text) {
    if (!text) return null;

    // Process the text line by line for basic markdown rendering
    const lines = text.split('\n');
    const elements = [];
    let inCodeBlock = false;
    let codeBlockContent = [];
    let _codeBlockLang = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code block toggle
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${i}`} className="chat-code-block" data-lang={_codeBlockLang}>
              <code>{codeBlockContent.join('\n')}</code>
            </pre>
          );
          codeBlockContent = [];
          _codeBlockLang = '';
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
          _codeBlockLang = line.slice(3).trim();
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Headings
      if (line.startsWith('### ')) {
        elements.push(<h4 key={i} className="chat-h3">{processInlineMarkdown(line.slice(4))}</h4>);
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(<h3 key={i} className="chat-h2">{processInlineMarkdown(line.slice(3))}</h3>);
        continue;
      }
      if (line.startsWith('# ')) {
        elements.push(<h2 key={i} className="chat-h1">{processInlineMarkdown(line.slice(2))}</h2>);
        continue;
      }

      // Bullet points
      if (/^[-*•]\s/.test(line)) {
        elements.push(
          <div key={i} className="chat-bullet">
            <span className="bullet-dot">•</span>
            <span>{processInlineMarkdown(line.replace(/^[-*•]\s/, ''))}</span>
          </div>
        );
        continue;
      }

      // Numbered list
      if (/^\d+\.\s/.test(line)) {
        const num = line.match(/^(\d+)\./)[1];
        elements.push(
          <div key={i} className="chat-numbered">
            <span className="num-marker">{num}.</span>
            <span>{processInlineMarkdown(line.replace(/^\d+\.\s/, ''))}</span>
          </div>
        );
        continue;
      }

      // Empty lines = spacing
      if (line.trim() === '') {
        elements.push(<div key={i} className="chat-spacer" />);
        continue;
      }

      // Regular paragraph
      elements.push(<p key={i} className="chat-p">{processInlineMarkdown(line)}</p>);
    }

    // Handle unclosed code block
    if (inCodeBlock && codeBlockContent.length > 0) {
      elements.push(
        <pre key="code-end" className="chat-code-block">
          <code>{codeBlockContent.join('\n')}</code>
        </pre>
      );
    }

    return elements;
  }

  /** Process inline markdown: bold, italic, inline code */
  function processInlineMarkdown(text) {
    if (!text) return text;

    const parts = [];
    let remaining = text;
    let keyIdx = 0;

    while (remaining.length > 0) {
      // Inline code
      const codeMatch = remaining.match(/`([^`]+)`/);
      // Bold
      const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
      // Italic
      const italicMatch = remaining.match(/\*([^*]+)\*/);

      // Find the earliest match
      let earliest = null;
      let earliestIdx = Infinity;

      if (codeMatch && remaining.indexOf(codeMatch[0]) < earliestIdx) {
        earliest = { type: 'code', match: codeMatch };
        earliestIdx = remaining.indexOf(codeMatch[0]);
      }
      if (boldMatch && remaining.indexOf(boldMatch[0]) < earliestIdx) {
        earliest = { type: 'bold', match: boldMatch };
        earliestIdx = remaining.indexOf(boldMatch[0]);
      }
      if (italicMatch && remaining.indexOf(italicMatch[0]) < earliestIdx && !boldMatch?.index !== italicMatch?.index) {
        earliest = { type: 'italic', match: italicMatch };
        earliestIdx = remaining.indexOf(italicMatch[0]);
      }

      if (!earliest) {
        parts.push(remaining);
        break;
      }

      // Add text before the match
      if (earliestIdx > 0) {
        parts.push(remaining.slice(0, earliestIdx));
      }

      const m = earliest.match;
      if (earliest.type === 'code') {
        parts.push(<code key={keyIdx++} className="chat-inline-code">{m[1]}</code>);
      } else if (earliest.type === 'bold') {
        parts.push(<strong key={keyIdx++}>{m[1]}</strong>);
      } else {
        parts.push(<em key={keyIdx++}>{m[1]}</em>);
      }

      remaining = remaining.slice(earliestIdx + m[0].length);
    }

    return parts;
  }

  if (loading) {
    return (
      <div className="ws-loading">
        <CircularProgress size={32} sx={{ color: 'var(--secondary)' }} />
        <p>SYNCHRONIZING WORKSPACE...</p>
        <style>{styles}</style>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="ws-not-found">
        <h2>WORKSPACE NOT FOUND</h2>
        <p>This analytical sector has been terminated or moved.</p>
        <button className="ws-back-btn" onClick={() => navigate('/projects')}>
          <ArrowLeft size={16} /> BACK TO REGISTRY
        </button>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="ws-container">
      <button
        className="ws-mobile-toggle-btn ws-mobile-toggle-floating"
        onClick={() => setMobileSidebarOpen(true)}
        aria-label="Open project sidebar"
      >
        <PanelLeft size={20} />
      </button>
      {/* Mobile Sidebar Overlay */}
      <div
        className={`ws-sidebar-overlay ${mobileSidebarOpen ? 'active' : ''}`}
        onClick={() => setMobileSidebarOpen(false)}
      />

      {/* Workspace Sidebar */}
      <aside className={`ws-sidebar glass ${mobileSidebarOpen ? 'mobile-open' : ''}`}>
        <div className="ws-sidebar-header">
          <div className="ws-project-title-row">
            <div className="folder-icon-wrapper">
              <Database size={16} />
            </div>
            <h2 className="ws-project-name">{project.name}</h2>
          </div>
        </div>

        <div className="ws-sidebar-content">
          {/* Instructions Section */}
          <div className="ws-card-btn glass" onClick={startEditingInstructions}>
            <div className="ws-card-icon">
              <Plus size={16} />
            </div>
            <div className="ws-card-text">
              <span className="ws-card-title">INSTRUCTIONS</span>
              <p className="ws-card-subtitle">
                {editingInstructions
                  ? "UPDATING..."
                  : (project.instructions || "Click to add project parameters.")}
              </p>
            </div>
          </div>

          {editingInstructions && (
            <div className="instructions-edit glass">
              <textarea
                className="instructions-textarea"
                value={instructionsDraft}
                onChange={(e) => setInstructionsDraft(e.target.value)}
                placeholder="DEFINE SECTOR PARAMETERS..."
                rows={4}
                autoFocus
              />
              <div className="instructions-actions">
                <button className="btn-lab-sm" onClick={() => setEditingInstructions(false)}>ABORT</button>
                <button className="btn-lab-sm primary" onClick={handleSaveInstructions}>APPLY</button>
              </div>
            </div>
          )}

          {/* Sources Section */}
          <div className={`ws-card-btn glass ${showDoiInput ? 'active' : ''}`} onClick={() => { setShowDoiInput(!showDoiInput); setSourceError(''); }}>
            <div className="ws-card-icon">
              <Database size={16} />
            </div>
            <div className="ws-card-text">
              <span className="ws-card-title">SOURCES</span>
              <p className="ws-card-subtitle">{project.sources?.length || 0} REFERENCES</p>
            </div>
          </div>

          {showDoiInput && (
            <div className="sources-expanded glass">
              <div className="source-type-toggle">
                <button className={`type-opt ${sourceType === 'doi' ? 'active' : ''}`} onClick={() => setSourceType('doi')}>DOI</button>
                <button className={`type-opt ${sourceType === 'url' ? 'active' : ''}`} onClick={() => setSourceType('url')}>URL</button>
                <button className={`type-opt ${sourceType === 'file' ? 'active' : ''}`} onClick={() => setSourceType('file')}>FILE</button>
              </div>
              <form className="doi-add-form" onSubmit={handleAddSource}>
                <div className="doi-input-row">
                  {sourceType === 'file' ? (
                    <div className="file-input-box">
                      <label className="file-label">
                        <span>SELECT ARCHIVE</span>
                        <input type="file" style={{ display: 'none' }} onChange={(e) => { setSourceFile(e.target.files[0]); setSourceError(''); }} />
                      </label>
                      <span className="file-name-hint">{sourceFile ? sourceFile.name : 'NO FILE'}</span>
                    </div>
                  ) : (
                    <input
                      type="text"
                      className="lab-source-input"
                      placeholder={sourceType === 'doi' ? "DOI IDENTIFIER..." : "URL..."}
                      value={sourceValue}
                      onChange={(e) => { setSourceValue(e.target.value); setSourceError(''); }}
                      autoFocus
                    />
                  )}
                  <button type="submit" className="lab-source-submit" disabled={fetching || (sourceType === 'file' ? !sourceFile : !sourceValue.trim())}>
                    {fetching ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
                  </button>
                </div>
                {sourceError && <p className="doi-error">{sourceError}</p>}
              </form>
              <div className="sources-list">
                {project.sources?.map((source, i) => (
                  <div key={source.doi || source.url || i} className="source-item glass">
                    <div className="source-text">
                      <p className="source-title">{source.title}</p>
                      <p className="source-meta">{source.type.toUpperCase()}</p>
                    </div>
                    <div className="source-actions">
                      {source.pdf_url && (
                        <button className="source-action-btn" onClick={() => window.open(source.pdf_url, '_blank')}>
                          <FileText size={12} />
                        </button>
                      )}
                      {source.url && (
                        <button className="source-action-btn" onClick={() => window.open(source.url, '_blank')}>
                          <ExternalLink size={12} />
                        </button>
                      )}
                      <button className="source-del" onClick={() => handleRemoveSource(source)}>
                        <X size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="ws-conversations-section">
            <div className="ws-conversations-header">
              <span>ACTIVE STREAMS</span>
              <button className="conv-new-btn" onClick={startNewConversation}>
                <Plus size={14} />
              </button>
            </div>
            <div className="chat-streams">
              {chatSessions.length === 0 ? (
                <div className="no-streams">NO DATA STREAMS</div>
              ) : (
                chatSessions.map((session) => (
                  <div key={session.chat_id} className={`stream-row glass ${activeChatId === session.chat_id ? 'active' : ''}`}>
                    <button className="stream-btn" onClick={() => switchConversation(session.chat_id, session.title)}>
                      <span className="stream-title">{session.title || 'UNTITLED STREAM'}</span>
                    </button>
                    <button className="stream-del" onClick={() => handleDeleteConversation(session.chat_id)}>
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="ws-main">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty-lab stagger-in">
              <div className="lab-pulse-large"></div>
              <h2>INITIALIZE ANALYTICAL STREAM</h2>
              <p>WORKSPACE: {project.name}</p>
              <div className="chat-suggestions">
                <button className="lab-suggest-chip glass" onClick={() => { setInputValue('Analyze indexed sources'); handleSend(); }}>ANALYZE INDEXED SOURCES</button>
                <button className="lab-suggest-chip glass" onClick={() => { setInputValue('Identify core themes'); handleSend(); }}>IDENTIFY CORE THEMES</button>
              </div>
            </div>
          ) : (
            <div className="chat-messages-inner">
              {messages.map((msg, idx) => (
                <div key={msg.id} className={`lab-msg ${msg.role === 'user' ? 'user' : 'ai'}`}>
                  <div className="msg-avatar glass">
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div className="msg-content">
                    <header className="msg-header">
                      <span className="msg-sender">{msg.role === 'user' ? 'SCIENTIST' : 'RAST AI'}</span>
                      <div className="msg-line"></div>
                    </header>
                    <div className="msg-text-box">
                      {msg.loading ? (
                        <div className="lab-loader-dots"><span></span><span></span><span></span></div>
                      ) : (
                        <div className="msg-rendered">
                          {msg.role === 'user' ? <p>{msg.text}</p> : renderMessageText(msg.text)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="chat-input-zone">
          <form className="lab-input-form glass" onSubmit={handleSend}>
            <button type="button" className="lab-input-tool"><Paperclip size={20} /></button>
            <textarea
              ref={inputRef}
              className="lab-textarea-main"
              placeholder="INITIALIZE QUERY..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <div className="input-ops-right">
              <button type="button" className="lab-input-tool"><Mic size={20} /></button>
              <button type="submit" className="lab-send-trigger" disabled={sending || !inputValue.trim()}>
                {sending ? <Loader2 size={18} className="spin" /> : <ArrowUp size={20} />}
              </button>
            </div>
          </form>
        </div>
      </main>

      <style>{styles}</style>
    </div>
  );
}

const styles = `
  .ws-container {
    display: flex;
    height: 100vh;
    width: 100%;
    gap: 1rem;
    overflow: hidden;
  }

  .ws-sidebar {
    width: 320px;
    min-width: 320px;
    display: flex;
    flex-direction: column;
    background: #000;
    border-right: 1px solid var(--border);
    padding: 2rem 1.5rem;
    gap: 1.5rem;
    z-index: 10;
  }

  .ws-sidebar-header {
    padding-bottom: 1rem;
  }

  .ws-project-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-main);
  }

  .ws-sidebar-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    overflow-y: auto;
  }

  .ws-card-btn {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1.25rem;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .ws-card-btn:hover {
    border-color: var(--secondary);
    background: var(--secondary-glow);
  }

  .ws-card-icon {
    width: 32px;
    height: 32px;
    background: var(--bg-body);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary);
  }

  .ws-card-title {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.2em;
    color: var(--text-dim);
  }

  .ws-card-subtitle {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
    line-height: 1.4;
  }

  .sources-expanded {
    padding: 1.5rem;
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    background: rgba(0, 0, 0, 0.2);
  }

  .source-type-toggle {
    display: flex;
    background: var(--bg-body);
    padding: 3px;
    border-radius: 8px;
    border: 1px solid var(--glass-border);
  }

  .type-opt {
    flex: 1;
    padding: 0.5rem;
    background: transparent;
    border: none;
    color: var(--text-dim);
    font-family: var(--font-mono);
    font-size: 0.6rem;
    font-weight: 800;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .type-opt.active {
    background: var(--secondary);
    color: #fff;
  }

  .doi-input-row {
    display: flex;
    gap: 0.75rem;
  }

  .lab-source-input {
    flex: 1;
    background: var(--bg-body);
    border: 1px solid var(--glass-border);
    border-radius: 6px;
    padding: 0.75rem;
    color: var(--text-main);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    outline: none;
  }

  .lab-source-submit {
    width: 38px;
    height: 38px;
    background: var(--secondary);
    color: #fff;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .source-item {
    padding: 1rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .source-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .source-meta {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-dim);
    margin-top: 0.25rem;
  }

  .ws-conversations-section {
    margin-top: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .ws-conversations-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 800;
    color: var(--text-dim);
    letter-spacing: 0.2em;
    padding: 0 0.5rem;
  }

  .stream-row {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    transition: all 0.3s ease;
  }

  .stream-row.active {
    background: var(--secondary-glow);
    border-color: var(--secondary);
  }

  .stream-btn {
    flex: 1;
    text-align: left;
    background: transparent;
    border: none;
    padding: 0.5rem;
    cursor: pointer;
    overflow: hidden;
  }

  .stream-title {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ws-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #000;
    overflow: hidden;
    position: relative;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 3rem;
  }

  .chat-empty-lab {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 2rem;
  }

  .lab-pulse-large {
    width: 20px;
    height: 20px;
    background: var(--secondary);
    border-radius: 50%;
    box-shadow: 0 0 30px var(--secondary);
    animation: pulse-glow 2s infinite;
  }

  .chat-empty-lab h2 {
    font-family: var(--font-mono);
    font-size: 1.25rem;
    letter-spacing: 0.4em;
    color: var(--text-main);
  }

  .lab-msg {
    display: flex;
    gap: 2rem;
    margin-bottom: 3rem;
    max-width: 900px;
  }

  .lab-msg.user {
    margin-left: auto;
    flex-direction: row-reverse;
  }

  .msg-avatar {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: var(--secondary);
  }

  .msg-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .msg-header {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .msg-sender {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 800;
    color: var(--text-dim);
    letter-spacing: 0.2em;
  }

  .msg-line {
    flex: 1;
    height: 1px;
    background: var(--border);
    opacity: 0.5;
  }

  .msg-text-box {
    font-size: 1.05rem;
    line-height: 1.7;
    color: var(--text-main);
  }

  .chat-input-zone {
    padding: 2rem 3rem 3rem;
  }

  .lab-input-form {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 1rem 1.5rem;
    border-radius: 20px;
    background: rgba(0, 0, 0, 0.4);
  }

  .lab-textarea-main {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-main);
    font-family: var(--font-body);
    font-size: 1.1rem;
    outline: none;
    resize: none;
    padding: 0.5rem 0;
  }

  .lab-send-trigger {
    width: 48px;
    height: 48px;
    background: var(--secondary);
    color: #fff;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .lab-send-trigger:hover:not(:disabled) {
    box-shadow: 0 0 25px var(--secondary);
    transform: translateY(-2px);
  }

  @media (max-width: 1024px) {
    .ws-container { flex-direction: column; padding: 1rem; }
    .ws-sidebar { width: 100%; min-width: 0; }
  }

  .source-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .source-action-btn {
    background: transparent;
    border: none;
    color: var(--text-dim);
    padding: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .source-action-btn:hover {
    color: var(--secondary);
    transform: scale(1.1);
  }
`;
