import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { onProject, updateProject, addSourceViaApi, addSourceFileViaApi, removeSource } from '../services/projectService';
import { fetchArticle } from '../services/crossref';
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

export default function ProjectWorkspace() {
  const { projectId } = useParams();
  const { currentUser } = useAuth();
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
          // Use _ prefix to signal intentionally unused high-level variable if that's the case
          // or just don't assign it if it's truly not needed. 
          // However, we'll keep it as 'codeBlockLang' to fix the lint by actually using it or naming it '_codeBlockLang'.
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
        <Loader2 size={32} className="spin" />
        <style>{styles}</style>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="ws-not-found">
        <h2>Project not found</h2>
        <p>This project may have been deleted.</p>
        <button className="ws-back-btn" onClick={() => navigate('/projects')}>
          <ArrowLeft size={16} /> Back to Projects
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
      <aside className={`ws-sidebar ${mobileSidebarOpen ? 'mobile-open' : ''}`}>
        <div className="ws-sidebar-header">
          <div className="ws-project-title-row">
            <div className="folder-icon-wrapper">
              <PanelLeft size={16} />
            </div>
            <h2 className="ws-project-name">{project.name}</h2>
            <button className="ws-project-menu">
              <MoreHorizontal size={16} />
            </button>
          </div>
          <button className="ws-sidebar-toggle" onClick={() => setMobileSidebarOpen(false)}>
            <span style={{ fontSize: '10px' }}>[|]</span>
          </button>
        </div>

        <div className="ws-sidebar-content">
          {/* Instructions Section */}
          <div className="ws-card-btn" onClick={startEditingInstructions}>
            <div className="ws-card-icon">
              <Settings2 size={16} />
            </div>
            <div className="ws-card-text">
              <span className="ws-card-title">Instructions</span>
              <p className="ws-card-subtitle">
                {editingInstructions
                  ? "Editing instructions..."
                  : (project.instructions || "You are my final year thesis research assistant. Your aim is to help me analyze and build my project...")}
              </p>
            </div>
          </div>

          {editingInstructions && (
            <div className="instructions-edit">
              <textarea
                className="instructions-textarea"
                value={instructionsDraft}
                onChange={(e) => setInstructionsDraft(e.target.value)}
                placeholder="Add project instructions or research focus..."
                rows={4}
                autoFocus
              />
              <div className="instructions-actions">
                <button className="btn-icon-sm" onClick={() => setEditingInstructions(false)}>
                  <X size={14} />
                </button>
                <button className="btn-icon-sm accent" onClick={handleSaveInstructions}>
                  <Check size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Sources Section */}
          <div className="ws-card-btn" onClick={() => { setShowDoiInput(!showDoiInput); setSourceError(''); }}>
            <div className="ws-card-icon">
              <Database size={16} />
            </div>
            <div className="ws-card-text">
              <span className="ws-card-title">Sources</span>
              <p className="ws-card-subtitle">Custom knowledge base for this project</p>
            </div>
          </div>

          {showDoiInput && (
            <div className="sources-expanded">
              <div className="source-type-toggle">
                <button 
                  className={`source-type-btn ${sourceType === 'doi' ? 'active' : ''}`}
                  onClick={() => setSourceType('doi')}
                >
                  DOI
                </button>
                <button 
                  className={`source-type-btn ${sourceType === 'url' ? 'active' : ''}`}
                  onClick={() => setSourceType('url')}
                >
                  URL
                </button>
                <button 
                  className={`source-type-btn ${sourceType === 'file' ? 'active' : ''}`}
                  onClick={() => setSourceType('file')}
                >
                  File
                </button>
              </div>
              <form className="doi-add-form" onSubmit={handleAddSource}>
                <div className="doi-input-row" style={sourceType === 'file' ? { padding: '0.5rem' } : {}}>
                  {sourceType === 'file' ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
                      <label className="file-upload-label" style={{ flexShrink: 0, cursor: 'pointer', background: 'rgba(255,255,255,0.05)', padding: '0.4rem 0.8rem', borderRadius: '6px', fontSize: '0.8rem', border: '1px solid var(--border)' }}>
                        Choose File
                        <input
                          type="file"
                          style={{ display: 'none' }}
                          onChange={(e) => { setSourceFile(e.target.files[0]); setSourceError(''); }}
                        />
                      </label>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {sourceFile ? sourceFile.name : 'No file selected'}
                      </span>
                    </div>
                  ) : (
                    <>
                      <Search size={14} className="doi-input-icon" />
                      <input
                        type="text"
                        className="doi-input"
                        placeholder={sourceType === 'doi' ? "Enter DOI..." : "Enter Website URL..."}
                        value={sourceValue}
                        onChange={(e) => { setSourceValue(e.target.value); setSourceError(''); }}
                        autoFocus
                      />
                    </>
                  )}
                  <button type="submit" className="doi-submit" disabled={fetching || (sourceType === 'file' ? !sourceFile : !sourceValue.trim())}>
                    {fetching ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
                  </button>
                </div>
                {sourceError && <p className="doi-error">{sourceError}</p>}
                {fetching && sourceType === 'file' && <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem', paddingLeft: '0.5rem' }}>Uploading and processing file...</p>}
              </form>
              <div className="sources-list">
                {project.sources?.map((source, i) => (
                  <div key={source.doi || source.url || i} className="source-item">
                    <div className="source-info">
                      <div className="source-text">
                        <p className="source-title" title={source.title}>{source.title}</p>
                        <p className="source-meta">
                          {source.type === 'url' ? 'Website Source' : source.type === 'file' ? 'Uploaded File' : (source.authors || 'Unknown Author')}
                        </p>
                      </div>
                    </div>
                    <div className="source-actions">
                      <button className="btn-icon-xs danger" onClick={() => handleRemoveSource(source)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="ws-personal-files row-link">
            <div className="row-left">
              <Paperclip size={14} className="doc-icon" />
              <span>Personal files</span>
            </div>
            <div className="row-right">
              <span>{project.sources?.length || 0} &gt;</span>
            </div>
          </div>

          <div className="ws-conversations-section">
            <div className="ws-conversations-header">
              <span>Conversations</span>
              <button className="conv-new-btn" onClick={startNewConversation} title="New conversation">
                <Plus size={12} />
              </button>
            </div>
            {chatSessions.length === 0 ? (
              <div className="ws-conversation-item">
                <span className="conv-title" style={{ color: 'var(--text-dim)' }}>No conversations yet</span>
              </div>
            ) : (
              chatSessions.map((session) => (
                <div key={session.chat_id} className={`ws-conversation-row ${activeChatId === session.chat_id ? 'active' : ''}`}>
                  <button
                    className="ws-conversation-item"
                    onClick={() => switchConversation(session.chat_id, session.title)}
                  >
                    <span className="conv-title" title={session.title || 'Untitled Chat'}>
                      {session.title || 'Untitled Chat'}
                    </span>
                    <span className="conv-date">
                      {session.updated_at
                        ? new Date(session.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        : 'Recent'}
                    </span>
                  </button>
                  <button
                    className="conv-delete-btn"
                    title="Delete conversation"
                    onClick={() => handleDeleteConversation(session.chat_id)}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="ws-main">
        {/* Messages Area */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty-state">
              <h2>Start a conversation in this project</h2>
              <p>Use this project to keep your conversations and files in a single place.</p>
              <div className="chat-suggestions">
                <button
                  className="chat-suggestion-chip"
                  onClick={() => {
                    setInputValue('Ask a question');
                    inputRef.current?.focus();
                  }}
                >
                  Ask a question
                </button>
                <button
                  className="chat-suggestion-chip"
                  onClick={() => {
                    setInputValue('Get help with a task');
                    inputRef.current?.focus();
                  }}
                >
                  Get help with a task
                </button>
              </div>
            </div>
          ) : (
            <div className="chat-messages-inner">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id}
                  className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : 'chat-message-ai'} ${msg.error ? 'chat-message-error' : ''}`}
                  style={{ animationDelay: `${idx * 0.1}s` }}
                >
                  <div className="chat-msg-avatar">
                    {msg.role === 'user' ? (
                      <User size={18} />
                    ) : (
                      <Bot size={18} />
                    )}
                  </div>
                  <div className="chat-msg-content">
                    <span className="chat-msg-sender">
                      {msg.role === 'user' ? 'Scientist' : 'Rast AI'}
                    </span>
                    <div className="chat-msg-text-container">
                      {msg.loading ? (
                        <div className="chat-loading-indicator">
                          <span className="dot"></span>
                          <span className="dot"></span>
                          <span className="dot"></span>
                        </div>
                      ) : (
                        <div className="chat-msg-text">
                          {msg.role === 'user' ? (
                            <p className="chat-p">{msg.text}</p>
                          ) : (
                            renderMessageText(msg.text)
                          )}
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

        {/* Chat Input */}
        <div className="chat-bottom-wrapper">
          <form className="chat-input-form" onSubmit={handleSend}>
            <div className="chat-input-container">
              <button type="button" className="input-icon-btn"><Paperclip size={18} /></button>
              <textarea
                ref={inputRef}
                className="chat-input"
                placeholder="Ask anything"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={sending}
              />
              <div className="input-actions-right">
                <button type="button" className="input-icon-btn"><Mic size={18} /></button>
                <button
                  type="submit"
                  className="chat-send-btn"
                  disabled={sending || !inputValue.trim()}
                >
                  {sending ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <ArrowUp size={16} />
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </main>

      <style>{styles}</style>
    </div>
  );
}

const styles = `
  .ws-loading,
  .ws-not-found {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    gap: 1.5rem;
    color: var(--text-dim);
    background: var(--bg-primary);
  }

  .ws-not-found h2 {
    color: var(--text-main);
    font-size: 2rem;
    font-weight: 700;
  }

  .ws-back-btn {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    color: var(--text-muted);
    font-size: 0.95rem;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .ws-back-btn:hover {
    background: rgba(255,255,255,0.08);
    color: white;
    border-color: var(--border-bright);
    transform: translateY(-1px);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  /* Container */
  .ws-container {
    display: flex;
    height: 100vh;
    overflow: hidden;
    background: var(--bg-primary);
  }

  /* Sidebar */
  .ws-sidebar {
    width: 340px;
    min-width: 340px;
    margin: 20px 0 20px 40px;
    height: calc(100vh - 40px);
    border-radius: var(--radius-xl);
    border: 1px solid var(--secondary-glow);
    background: color-mix(in srgb, var(--bg-sidebar) 40%, var(--bg-surface) 60%);
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow-xl);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 1.5rem;
    position: relative;
    z-index: 10;
    transition: var(--transition-base);
  }

  .ws-sidebar:hover {
    border-color: var(--secondary);
    box-shadow: 0 0 40px var(--secondary-glow);
  }

  .ws-sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  
  .ws-project-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .folder-icon-wrapper {
    color: var(--text-dim);
    display: flex;
    align-items: center;
  }

  .ws-project-name {
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--text-main);
  }

  .ws-project-menu {
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    display: flex;
    align-items: center;
    padding: 0.2rem;
    border-radius: var(--radius-sm);
  }

  .ws-project-menu:hover {
    background: rgba(255, 255, 255, 0.05);
    color: white;
  }

  .ws-sidebar-toggle {
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    display: flex;
    align-items: center;
  }

  .ws-sidebar-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .ws-card-btn {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .ws-card-btn:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .ws-card-icon {
    color: var(--text-dim);
    margin-top: 0.1rem;
  }

  .ws-card-text {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .ws-card-title {
    font-size: 0.9rem;
    color: var(--text-main);
    font-weight: 500;
  }

  .ws-card-subtitle {
    font-size: 0.75rem;
    color: var(--text-dim);
    line-height: 1.4;
  }
  
  .sources-expanded {
    padding-left: 2.25rem;
    margin-bottom: 0.5rem;
  }

  .row-link {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    font-size: 0.9rem;
    color: var(--text-main);
    cursor: pointer;
    border-radius: var(--radius-md);
  }

  .row-link:hover {
    background: rgba(255, 255, 255, 0.03);
  }
  
  .row-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .row-right {
    color: var(--text-dim);
    font-size: 0.8rem;
  }

  /* Conversations Section */
  .ws-conversations-section {
    margin-top: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .ws-conversations-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-dim);
    font-weight: 600;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.25rem;
  }

  .conv-new-btn {
    width: 20px;
    height: 20px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: transparent;
    color: var(--text-dim);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .conv-new-btn:hover {
    color: var(--text-main);
    border-color: var(--border-bright);
    background: rgba(255, 255, 255, 0.05);
  }

  .ws-conversation-item {
    width: 100%;
    border: none;
    background: transparent;
    text-align: left;
    display: flex;
    flex-direction: column;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-md);
    cursor: pointer;
  }

  .ws-conversation-item:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .ws-conversation-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    border-radius: var(--radius-md);
  }

  .ws-conversation-row.active .ws-conversation-item {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--secondary-glow);
  }

  .conv-delete-btn {
    width: 26px;
    height: 26px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
  }

  .conv-delete-btn:hover {
    color: #f87171;
    border-color: #f87171;
    background: rgba(248, 113, 113, 0.08);
  }

  .conv-title {
    font-size: 0.85rem;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .conv-date {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
  }

  /* Instructions editing */
  .instructions-edit {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .instructions-textarea {
    width: 100%;
    padding: 0.85rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text-main);
    font-size: 0.9rem;
    font-family: var(--font-body);
    resize: vertical;
    outline: none;
    transition: var(--transition-fast);
  }

  .instructions-textarea:focus {
    border-color: var(--border-bright);
    box-shadow: 0 0 0 3px rgba(255,255,255,0.03);
  }

  .instructions-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .btn-icon-sm {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    color: var(--text-dim);
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .source-type-toggle {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    padding: 0.25rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
  }

  .source-type-btn {
    flex: 1;
    padding: 0.4rem;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .source-type-btn.active {
    background: var(--secondary);
    color: white;
    box-shadow: 0 0 10px var(--secondary-glow);
  }

  .btn-icon-sm:hover {
    color: white;
    background: rgba(255,255,255,0.1);
    border-color: var(--border-bright);
  }

  .btn-icon-sm.accent {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.2);
    color: var(--secondary);
  }

  .btn-icon-sm.accent:hover {
    background: rgba(59, 130, 246, 0.2);
    border-color: var(--secondary);
  }

  /* DOI Add Form */
  .doi-add-form {
    margin-bottom: 1rem;
    animation: slideDown 0.3s ease-out;
  }

  .doi-input-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 0 0.75rem;
    transition: var(--transition-fast);
  }

  .doi-input-row:focus-within {
    border-color: var(--border-bright);
    box-shadow: 0 0 0 3px rgba(255,255,255,0.03);
  }

  .doi-input-icon {
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .doi-input {
    flex: 1;
    padding: 0.85rem 0;
    background: transparent;
    border: none;
    color: var(--text-main);
    font-size: 0.9rem;
    outline: none;
  }

  .doi-submit {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    background: white;
    color: black;
    cursor: pointer;
    flex-shrink: 0;
    transition: var(--transition-fast);
    border: none;
  }

  .doi-submit:hover:not(:disabled) {
    transform: scale(1.05);
  }

  .doi-submit:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .doi-error {
    font-size: 0.8rem;
    color: #fb7185;
    margin-top: 0.5rem;
    padding-left: 0.5rem;
  }

  /* Sources List */
  .sources-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .sources-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1;
    overflow-y: auto;
    padding-right: 0.5rem;
  }

  /* Custom scrollbar for sidebar */
  .ws-sidebar .sources-list::-webkit-scrollbar {
    width: 4px;
  }
  .ws-sidebar .sources-list::-webkit-scrollbar-track {
    background: transparent;
  }
  .ws-sidebar .sources-list::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
  }

  .ws-empty-text {
    font-size: 0.85rem;
    color: var(--text-dim);
    padding: 1rem 0.5rem;
    text-align: center;
    border: 1px dashed var(--border);
    border-radius: var(--radius-md);
  }

  .source-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: var(--radius-lg);
    background: rgba(255,255,255,0.02);
    border: 1px solid var(--border);
    transition: var(--transition-fast);
    position: relative;
    overflow: hidden;
  }

  .source-item:hover {
    background: rgba(255,255,255,0.04);
    border-color: var(--border-bright);
    transform: translateX(4px);
  }

  .source-icon-wrapper {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    flex-shrink: 0;
    transition: var(--transition-fast);
  }

  .source-icon-wrapper.has-pdf {
    background: rgba(248, 113, 113, 0.05);
    border-color: rgba(248, 113, 113, 0.1);
    color: #fca5a5;
  }

  .source-item:hover .source-icon-wrapper {
    border-color: var(--border-bright);
    color: white;
  }

  .source-item:hover .source-icon-wrapper.has-pdf {
    border-color: rgba(248, 113, 113, 0.3);
    color: #fca5a5;
  }

  .source-info {
    display: flex;
    gap: 0.85rem;
    flex: 1;
    min-width: 0;
    align-items: center;
  }

  .source-text {
    flex: 1;
    min-width: 0;
  }

  .source-icon {
    color: var(--text-dim);
    flex-shrink: 0;
    opacity: 0.6;
  }

  .source-icon.has-pdf {
    color: #fca5a5;
    opacity: 1;
  }

  .source-title {
    font-size: 0.85rem;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-main);
  }

  .source-meta {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-top: 0.15rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .source-actions {
    display: flex;
    gap: 0.4rem;
    flex-shrink: 0;
    opacity: 0;
    transition: var(--transition-fast);
    transform: translateX(10px);
  }

  .source-item:hover .source-actions {
    opacity: 1;
    transform: translateX(0);
  }

  .btn-icon-xs {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    color: var(--text-dim);
    cursor: pointer;
    text-decoration: none;
    transition: var(--transition-fast);
  }

  .btn-icon-xs:hover {
    color: white;
    background: rgba(255,255,255,0.1);
    border-color: var(--border-bright);
  }

  .btn-icon-xs.pdf-link {
    color: #fca5a5;
    background: rgba(248, 113, 113, 0.05);
    border-color: rgba(248, 113, 113, 0.1);
  }

  .btn-icon-xs.pdf-link:hover {
    background: rgba(248, 113, 113, 0.1);
    border-color: rgba(248, 113, 113, 0.3);
  }

  .btn-icon-xs.danger:hover {
    color: #fb7185;
    background: rgba(244, 63, 94, 0.1);
    border-color: rgba(244, 63, 94, 0.2);
  }

  /* ========= CHAT ========= */
  .ws-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    background: var(--bg-primary);
    position: relative;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    scroll-behavior: smooth;
  }

  .chat-empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    max-width: 500px;
    margin: auto;
    animation: fadeIn 0.5s ease-out;
  }

  .chat-empty-state h2 {
    font-size: 1.75rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    letter-spacing: -0.02em;
    color: var(--text-main);
  }

  .chat-empty-state p {
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 2rem;
  }

  .chat-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    justify-content: center;
  }

  .chat-suggestion-chip {
    padding: 0.6rem 1.25rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    color: var(--text-dim);
    font-size: 0.85rem;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .chat-suggestion-chip:hover {
    background: rgba(255,255,255,0.08);
    color: white;
    border-color: var(--border-bright);
  }

  .chat-messages-inner {
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .chat-message {
    display: flex;
    gap: 1.25rem;
    opacity: 0;
    animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  .chat-msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 4px;
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-dim);
  }

  .chat-message-user .chat-msg-avatar {
    background: transparent;
    border: 1px solid var(--border);
  }

  .chat-message-ai .chat-msg-avatar {
    background: var(--text-main);
    color: var(--bg-body);
  }

  .chat-msg-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding-top: 0.25rem;
  }

  .chat-msg-sender {
    font-weight: 700;
    font-size: 0.85rem;
    color: var(--text-main);
  }

  .chat-msg-text-container {
    color: var(--text-main);
    font-size: 0.95rem;
    line-height: 1.6;
  }

  .chat-loading-indicator {
    display: flex;
    gap: 6px;
    padding: 0.5rem 0;
  }

  .dot {
    width: 6px;
    height: 6px;
    background: var(--text-dim);
    border-radius: 50%;
    animation: pulse 1.5s infinite cubic-bezier(0.4, 0, 0.6, 1);
  }

  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes pulse {
    0%, 100% { opacity: 0.4; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1.2); }
  }

  /* Chat Markdown Rendering */
  .chat-msg-text {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .chat-p {
    margin-bottom: 0.75rem;
  }

  .chat-p:last-child {
    margin-bottom: 0;
  }

  .chat-bottom-wrapper {
    padding: 0 2rem 2rem 2rem;
    display: flex;
    justify-content: center;
    background: linear-gradient(to top, var(--bg-primary) 50%, transparent 100%);
    position: sticky;
    bottom: 0;
  }

  .chat-input-form {
    max-width: 800px;
    width: 100%;
    background: var(--bg-surface);
    border: 2px solid var(--secondary-glow);
    border-radius: 24px;
    padding: 0.75rem 1.25rem;
    box-shadow: 0 8px 32px var(--secondary-glow);
    transition: var(--transition-base);
  }

  .chat-input-form:focus-within {
    border-color: var(--secondary);
    box-shadow: 0 12px 40px var(--secondary-glow);
    transform: translateY(-2px);
  }

  .chat-input-container {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .input-icon-btn {
    background: transparent;
    border: none;
    color: var(--secondary);
    cursor: pointer;
    padding: 0.6rem;
    display: flex;
    align-items: center;
    border-radius: 12px;
    transition: var(--transition-fast);
  }

  .input-icon-btn:hover {
    color: var(--text-main);
    background: var(--secondary-glow);
  }

  .chat-input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-main);
    font-size: 1.15rem;
    font-weight: 500;
    font-family: var(--font-body);
    resize: none;
    outline: none;
    max-height: 200px;
    min-height: 28px;
    padding: 0.5rem 0;
    line-height: 1.6;
  }

  .chat-input::placeholder {
    color: var(--text-dim);
    font-weight: 400;
  }

  .input-actions-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .chat-send-btn {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    cursor: pointer;
    border: none;
    transition: var(--transition-base);
    box-shadow: 0 4px 15px var(--secondary-glow);
  }

  .chat-send-btn svg {
    width: 20px;
    height: 20px;
  }

  .chat-send-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px var(--secondary-glow);
    opacity: 1;
  }

  .chat-send-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    background: var(--text-dim);
  }

  /* Mobile Tweaks */
  @media (max-width: 1024px) {
    .ws-sidebar {
      width: 280px;
      min-width: 280px;
    }
  }

  @media (max-width: 768px) {
    .ws-container {
      position: relative;
    }

    .ws-sidebar {
      position: fixed;
      left: 0;
      top: calc(var(--appbar-height) + 20px);
      width: 280px;
      margin: 0;
      height: calc(100vh - var(--appbar-height) - 20px);
      border-radius: 0;
      border-top-right-radius: var(--radius-xl);
      border-bottom-right-radius: var(--radius-xl);
      z-index: 1999;
      transform: translateX(-100%);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 20px 0 50px rgba(0,0,0,0.5);
      background: var(--bg-surface);
      border: none;
      border-right: 1px solid var(--border);
    }

    .ws-sidebar.mobile-open {
      transform: translateX(0);
    }

    .ws-main {
      width: 100%;
      height: calc(100vh - var(--navbar-height));
    }

    .chat-messages {
      padding: 1rem;
    }

    .chat-bottom-wrapper {
      padding: 1rem;
      padding-bottom: max(1rem, env(safe-area-inset-bottom));
    }

    .chat-empty-state h2 {
      font-size: 1.4rem;
    }

    .chat-input-form {
      padding: 0.85rem 1rem;
      border-radius: 20px;
    }

    .chat-input-container {
      gap: 0.75rem;
    }

    .chat-input {
      font-size: 1rem;
      padding: 0.6rem 0;
    }

    .input-icon-btn {
      padding: 0.5rem;
    }

    .input-icon-btn svg {
      width: 20px;
      height: 20px;
    }

    .chat-send-btn {
      width: 42px;
      height: 42px;
      min-width: 42px;
      border-radius: 14px;
    }

    .chat-send-btn svg {
      width: 18px;
      height: 18px;
    }

    .chat-message {
      gap: 0.85rem;
    }

    .chat-msg-avatar {
      width: 28px;
      height: 28px;
    }

    .chat-msg-content {
      gap: 0.25rem;
    }

    .chat-msg-sender {
      font-size: 0.8rem;
    }

    .chat-msg-text-container {
      font-size: 0.9rem;
    }

    .chat-suggestions {
      flex-direction: column;
      align-items: stretch;
    }

    .chat-suggestion-chip {
      width: 100%;
      text-align: center;
    }

    .ws-sidebar-overlay {
      position: fixed;
      top: calc(var(--appbar-height) + 20px);
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.4);
      backdrop-filter: blur(4px);
      z-index: 1998;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s;
    }

    .ws-sidebar-overlay.active {
      opacity: 1;
      pointer-events: auto;
    }

    .ws-mobile-toggle-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      background: var(--primary-glow);
      color: var(--text-main);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      cursor: pointer;
    }

    .ws-mobile-toggle-floating {
      position: fixed;
      top: max(22px, env(safe-area-inset-top));
      right: max(1rem, env(safe-area-inset-right));
      z-index: 2101;
    }
  }

  @media (min-width: 769px) {
    .ws-mobile-toggle-btn {
      display: none;
    }
  }
`;
