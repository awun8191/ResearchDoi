import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CircularProgress } from '@mui/material';
import { onProject, updateProject, addSourceViaApi, addSourceFileViaApi, removeSource } from '../services/projectService';
import { fetchArticle } from '../services/arxiv';
import { useChat } from '../hooks/useChat';
import { useSSE } from '../hooks/useSSE';
import DualPane from '../components/DualPane';
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
    historyLoading,
    agentActivity,
    chatTitle, // eslint-disable-line no-unused-vars
    sending,
    setChatTitle, // eslint-disable-line no-unused-vars
    refreshChatSessions, // eslint-disable-line no-unused-vars
    sendMessage,
    startNewConversation,
    deleteConversation,
    switchConversation,
    reseedRAG,
    ingestSource, // eslint-disable-line no-unused-vars
  } = useChat(currentUser?.uid, projectId, project?.instructions || '');

  // Reseed RAG when project or chat changes
  useEffect(() => {
    if (project?.sources && project.sources.length > 0) {
      const timer = setTimeout(() => reseedRAG(project.sources), 1000);
      return () => clearTimeout(timer);
    }
  }, [project?.id, project?.sources, activeChatId, reseedRAG]);

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
  }, [projectId]);

  // Auto-scroll to bottom without smooth-scroll jank while the model response is updating.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: sending ? 'auto' : 'smooth', block: 'end' });
  }, [messages.length, sending]);

  // Handle SSE state for the thesis pane
  const thesisState = useSSE(projectId, project?.thesis || {});

  async function handleSend(e, overrideText) {
    e?.preventDefault();
    const text = (overrideText ?? inputValue).trim();
    if (!text || sending) return;

    setInputValue('');
    
    try {
      await sendMessage(text);
    } catch {
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
      // Keep input area open so user gets immediate visual confirmation
      setShowDoiInput(true);
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
      // Citation
      const citeMatch = remaining.match(/\[Cite:\s*([^\]]+)\]/);

      // Find the earliest match
      let earliest = null;
      let earliestIdx = Infinity;

      if (citeMatch && remaining.indexOf(citeMatch[0]) < earliestIdx) {
        earliest = { type: 'cite', match: citeMatch };
        earliestIdx = remaining.indexOf(citeMatch[0]);
      }
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
      if (earliest.type === 'cite') {
        const displayCite = m[1].length > 30 ? m[1].substring(0, 30) + '...' : m[1];
        parts.push(
          <span key={keyIdx++} className="citation-badge" title={m[1]}>
            [{displayCite}]
          </span>
        );
      } else if (earliest.type === 'code') {
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
        <p>Opening the reading room...</p>
        <style>{styles}</style>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="ws-not-found">
        <h2>Workspace not found</h2>
        <p>This research room may have been moved, renamed, or archived.</p>
        <button className="ws-back-btn" onClick={() => navigate('/projects')}>
          <ArrowLeft size={16} /> Back to library
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
          <button className="ws-back-link" onClick={() => navigate('/projects')}>
            <ArrowLeft size={14} /> <span>Library</span>
          </button>
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
              <span className="ws-card-title">Guidance</span>
              <p className="ws-card-subtitle">
                {editingInstructions
                  ? "Updating notes..."
                  : (project.instructions || "Add tone, scope, or thesis constraints.")}
              </p>
            </div>
          </div>

          {editingInstructions && (
            <div className="instructions-edit glass">
              <textarea
                className="instructions-textarea"
                value={instructionsDraft}
                onChange={(e) => setInstructionsDraft(e.target.value)}
                placeholder="Add research goals, preferred structure, citation expectations..."
                rows={4}
                autoFocus
              />
              <div className="instructions-actions">
                <button className="btn-lab-sm" onClick={() => setEditingInstructions(false)}>Cancel</button>
                <button className="btn-lab-sm primary" onClick={handleSaveInstructions}>Save</button>
              </div>
            </div>
          )}

          {/* Sources Section */}
          <div className={`ws-card-btn glass ${showDoiInput ? 'active' : ''}`} onClick={() => { setShowDoiInput(!showDoiInput); setSourceError(''); }}>
            <div className="ws-card-icon">
              <Database size={16} />
            </div>
            <div className="ws-card-text">
              <span className="ws-card-title">Sources</span>
              <p className="ws-card-subtitle">{project.sources?.length || 0} references indexed</p>
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
                        <span>Select file</span>
                        <input type="file" style={{ display: 'none' }} onChange={(e) => { setSourceFile(e.target.files[0]); setSourceError(''); }} />
                      </label>
                      <span className="file-name-hint">{sourceFile ? sourceFile.name : 'No file selected'}</span>
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
                {!project.sources || project.sources.length === 0 ? (
                  <div className="sources-empty-state">
                    <Database size={24} className="empty-icon" />
                    <p>No indexed sources</p>
                    <span>Add DOIs, URLs or PDF files above to ground the AI's generation.</span>
                  </div>
                ) : (
                  project.sources.map((source, i) => (
                    <div key={source.doi || source.url || i} className="source-item glass">
                      <div className="source-text">
                        <p className="source-title" title={source.title}>{source.title}</p>
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
                  ))
                )}
              </div>
            </div>
          )}

          <div className="ws-conversations-section">
            <div className="ws-conversations-header">
              <span>Conversations</span>
              <button className="conv-new-btn" onClick={startNewConversation}>
                <Plus size={14} />
              </button>
            </div>
            <div className="chat-streams">
              {chatSessions.length === 0 ? (
                <div className="no-streams">No conversations yet</div>
              ) : (
                chatSessions.map((session) => (
                  <div key={session.chat_id} className={`stream-row glass ${activeChatId === session.chat_id ? 'active' : ''}`}>
                    <button className="stream-btn" onClick={() => switchConversation(session.chat_id, session.title)}>
                      <span className="stream-title">{session.title || 'Untitled conversation'}</span>
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
          {historyLoading ? (
            <div className="chat-empty-lab stagger-in">
              <div className="lab-pulse-large"></div>
              <h2>Gathering the conversation memory</h2>
              <p>Session: {activeChatId}</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-empty-lab stagger-in">
              <div className="lab-pulse-large"></div>
              <h2>Begin a scholarly conversation</h2>
              <p>Workspace: {project.name}</p>
              <div className="chat-suggestions">
                <button className="lab-suggest-chip glass" onClick={() => handleSend(null, 'Analyze indexed sources')}>Analyze indexed sources</button>
                <button className="lab-suggest-chip glass" onClick={() => handleSend(null, 'Identify core themes')}>Identify core themes</button>
              </div>
            </div>
          ) : (
            <div className="chat-messages-inner">
              {messages.map((msg) => (
                <div key={msg.id} className={`lab-msg ${msg.role === 'user' ? 'user' : 'ai'}`}>
                  <div className="msg-avatar glass">
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div className="msg-content">
                    <header className="msg-header">
                      <span className="msg-sender">{msg.role === 'user' ? 'You' : 'Research agent'}</span>
                      <div className="msg-line"></div>
                    </header>
                    <div className="msg-text-box">
                      <div className="msg-rendered">
                        {msg.role === 'user' ? <p>{msg.text}</p> : renderMessageText(msg.text)}
                        {msg.loading && !msg.text ? <div className="lab-loader-dots"><span></span><span></span><span></span></div> : null}
                        {msg.loading && msg.text ? <span className="stream-cursor" aria-hidden="true" /> : null}
                      </div>
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
              placeholder="Ask about your sources, thesis, or next section..."
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
          {sending ? (
            <div className="agent-computing-note">
              <span className="thinking-orb" />
              <span>The agent is reading context, choosing tools, and preparing a response.</span>
            </div>
          ) : null}
        </div>
      </main>

      <aside className="agent-observability glass">
        <header className="obs-header">
          <span>Agent trace</span>
          <span className={sending ? 'obs-live active' : 'obs-live'}>{sending ? 'LIVE' : 'IDLE'}</span>
        </header>
        <div className="obs-session">Session <strong>{activeChatId}</strong></div>
        <div className="obs-list">
          {agentActivity.length === 0 ? (
            <div className="obs-empty">Tool calls, sub-agent transfers, and agent events will appear here after each run.</div>
          ) : (
            agentActivity.map((item) => (
              <div key={item.id} className={`obs-item ${item.type}`}>
                <div className="obs-dot"></div>
                <div>
                  <div className="obs-title">{item.label}</div>
                  <div className="obs-meta">{item.actor} · {item.status}</div>
                  <div className="obs-summary">{item.summary}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Dual Pane (Editor) */}
      <DualPane thesisState={thesisState} />

      <style>{styles}</style>
    </div>
  );
}

const styles = `
  .ws-container {
    display: flex;
    height: 100vh;
    width: 100%;
    background: #000;
    overflow: hidden;
  }

  .ws-sidebar {
    width: 320px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--glass-border);
    background: rgba(8, 8, 10, 0.85);
    backdrop-filter: var(--glass-blur);
    z-index: 10;
    box-shadow: var(--shadow-md);
  }

  .ws-sidebar-header {
    padding: 1.5rem 1.5rem 1rem 1.5rem;
    border-bottom: 1px solid var(--glass-border);
  }

  .ws-back-link {
    background: transparent;
    color: var(--text-dim);
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    transition: color 0.2s ease;
    margin-bottom: 0.75rem;
    padding: 0;
  }
  .ws-back-link:hover {
    color: var(--secondary);
  }

  .ws-project-title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .folder-icon-wrapper {
    color: var(--secondary);
    display: flex;
    align-items: center;
  }

  .ws-project-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #fff;
    margin: 0;
  }

  .ws-sidebar-content {
    flex: 1;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    overflow-y: auto;
  }

  .ws-sidebar-content::-webkit-scrollbar {
    width: 4px;
  }
  .ws-sidebar-content::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
  }

  .ws-card-btn {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.25rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-base);
  }

  .ws-card-btn:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: var(--border-bright);
    box-shadow: var(--shadow-inner), 0 0 15px var(--secondary-glow);
  }

  .ws-card-btn.active {
    background: rgba(99, 102, 241, 0.06);
    border-color: var(--secondary);
    box-shadow: var(--shadow-inner), 0 0 20px var(--secondary-glow);
  }

  .ws-card-icon {
    width: 28px;
    height: 28px;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid var(--glass-border);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary);
    flex-shrink: 0;
  }

  .ws-card-text {
    flex: 1;
    min-width: 0;
  }

  .ws-card-title {
    display: block;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.25em;
    color: var(--text-dim);
  }

  .ws-card-subtitle {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.15rem;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sources-expanded, .instructions-edit {
    padding: 1.25rem;
    border-radius: var(--radius-md);
    background: rgba(5, 5, 5, 0.5);
    border: 1px solid var(--glass-border);
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: -0.75rem;
    animation: slideDown 0.25s var(--ease-out) forwards;
  }

  .instructions-textarea {
    width: 100%;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    padding: 0.75rem;
    color: var(--text-main);
    font-family: var(--font-body);
    font-size: 0.85rem;
    outline: none;
    resize: vertical;
  }
  .instructions-textarea:focus {
    border-color: var(--secondary);
  }

  .instructions-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn-lab-sm {
    padding: 0.4rem 0.75rem;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 700;
    border-radius: 6px;
    background: transparent;
    border: 1px solid var(--glass-border);
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-lab-sm.primary {
    background: var(--secondary);
    border-color: var(--secondary);
    color: #fff;
  }
  .btn-lab-sm:hover {
    filter: brightness(1.1);
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .source-type-toggle {
    display: flex;
    background: rgba(0, 0, 0, 0.4);
    padding: 2px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.04);
  }

  .type-opt {
    flex: 1;
    padding: 0.35rem 0.5rem;
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
    box-shadow: 0 2px 8px var(--secondary-glow);
  }

  .doi-input-row {
    display: flex;
    gap: 0.5rem;
  }

  .lab-source-input {
    flex: 1;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    color: var(--text-main);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    outline: none;
    transition: border-color 0.2s ease;
  }

  .lab-source-input:focus {
    border-color: var(--secondary);
  }

  .lab-source-submit {
    width: 34px;
    height: 34px;
    background: var(--secondary);
    color: #fff;
    border: none;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .lab-source-submit:hover:not(:disabled) {
    background: var(--accent);
    box-shadow: 0 0 10px var(--secondary-glow);
  }

  .lab-source-submit:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .doi-error {
    font-size: 0.65rem;
    color: #ef4444;
    margin-top: 2px;
  }

  .sources-list {
    max-height: 220px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding-right: 2px;
  }
  .sources-list::-webkit-scrollbar {
    width: 4px;
  }
  .sources-list::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
  }

  .source-item {
    padding: 0.6rem 0.75rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    transition: all 0.2s ease;
  }

  .source-item:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
  }

  .source-text {
    flex: 1;
    min-width: 0;
  }

  .source-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .source-meta {
    font-family: var(--font-mono);
    font-size: 0.55rem;
    color: var(--text-dim);
    margin-top: 0.15rem;
    text-transform: uppercase;
  }

  .source-actions {
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }

  .source-action-btn {
    background: transparent;
    border: none;
    color: var(--text-dim);
    padding: 3px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s ease;
  }
  .source-action-btn:hover {
    color: var(--secondary);
  }

  .source-del {
    background: transparent;
    border: none;
    color: var(--text-dim);
    padding: 3px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s ease;
  }
  .source-del:hover {
    color: #ef4444;
  }

  .sources-empty-state {
    padding: 1.5rem 1rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
  }
  .sources-empty-state .empty-icon {
    opacity: 0.3;
    margin-bottom: 0.5rem;
    color: var(--text-dim);
  }
  .sources-empty-state p {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }
  .sources-empty-state span {
    font-size: 0.65rem;
    line-height: 1.3;
    opacity: 0.7;
  }

  .file-input-box {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .file-label {
    background: rgba(0, 0, 0, 0.2);
    border: 1px dashed var(--glass-border);
    border-radius: 8px;
    padding: 0.5rem;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .file-label:hover {
    border-color: var(--secondary);
    background: rgba(99, 102, 241, 0.05);
  }
  .file-name-hint {
    font-size: 0.6rem;
    color: var(--text-dim);
    text-align: center;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ws-conversations-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: auto;
    border-top: 1px solid var(--glass-border);
    padding-top: 1.25rem;
  }

  .ws-conversations-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 800;
    color: var(--text-dim);
    letter-spacing: 0.15em;
  }

  .chat-streams {
    max-height: 150px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .chat-streams::-webkit-scrollbar {
    width: 4px;
  }
  .chat-streams::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
  }

  .stream-row {
    display: flex;
    align-items: center;
    padding: 0.15rem 0.5rem;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    transition: all 0.2s ease;
  }
  .stream-row:hover {
    background: rgba(255, 255, 255, 0.02);
  }
  .stream-row.active {
    background: rgba(99, 102, 241, 0.05);
    border-color: rgba(99, 102, 241, 0.15);
  }

  .stream-btn {
    flex: 1;
    text-align: left;
    background: transparent;
    border: none;
    padding: 0.35rem;
    cursor: pointer;
    min-width: 0;
  }

  .stream-title {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stream-row.active .stream-title {
    color: #fff;
    font-weight: 600;
  }

  .stream-del {
    background: transparent;
    border: none;
    color: var(--text-dim);
    opacity: 0;
    padding: 2px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .stream-row:hover .stream-del {
    opacity: 1;
  }
  .stream-del:hover {
    color: #ef4444;
  }

  .ws-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #070709;
    overflow: hidden;
    border-right: 1px solid var(--glass-border);
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 2.5rem 2rem;
  }
  .chat-messages::-webkit-scrollbar {
    width: 6px;
  }
  .chat-messages::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 3px;
  }

  .chat-messages-inner {
    max-width: 760px;
    width: 100%;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .chat-empty-lab {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 1.5rem;
  }

  .lab-pulse-large {
    width: 12px;
    height: 12px;
    background: var(--secondary);
    border-radius: 50%;
    box-shadow: 0 0 20px var(--secondary);
    animation: pulse-glow 2s infinite;
  }

  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 8px var(--secondary-glow); opacity: 0.8; }
    50% { box-shadow: 0 0 20px var(--secondary), 0 0 30px var(--secondary-glow); opacity: 1; }
  }

  .chat-empty-lab h2 {
    font-family: var(--font-mono);
    font-size: 1rem;
    letter-spacing: 0.3em;
    color: #fff;
  }
  .chat-empty-lab p {
    font-size: 0.75rem;
    font-family: var(--font-mono);
    color: var(--text-dim);
    letter-spacing: 0.1em;
  }

  .chat-suggestions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .lab-suggest-chip {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--glass-border);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .lab-suggest-chip:hover {
    background: rgba(99, 102, 241, 0.06);
    border-color: var(--secondary-glow);
    color: #fff;
  }

  .lab-msg {
    display: flex;
    gap: 1.25rem;
    width: 100%;
  }

  .lab-msg.user {
    flex-direction: row-reverse;
  }

  .msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--glass-border);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .lab-msg.ai .msg-avatar {
    color: var(--secondary);
    border-color: var(--secondary-glow);
    box-shadow: 0 0 10px var(--secondary-glow);
    background: rgba(99, 102, 241, 0.05);
  }

  .msg-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .msg-sender {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    color: var(--text-dim);
  }

  .msg-line {
    flex: 1;
    height: 1px;
    background: var(--glass-border);
    opacity: 0.5;
  }

  .msg-text-box {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text-main);
    background: rgba(12, 12, 16, 0.5);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    box-shadow: var(--shadow-sm);
  }

  .lab-msg.user .msg-text-box {
    background: rgba(99, 102, 241, 0.02);
    border-color: rgba(99, 102, 241, 0.1);
  }

  .chat-input-zone {
    padding: 1.25rem 2rem 2rem;
    background: linear-gradient(to top, #070709 80%, transparent);
  }

  .lab-input-form {
    max-width: 760px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.4rem 0.75rem;
    border-radius: 14px;
    background: rgba(12, 12, 15, 0.9);
    border: 1px solid var(--glass-border);
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
    transition: all 0.25s ease;
  }

  .lab-input-form:focus-within {
    border-color: var(--secondary);
    box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 20px var(--secondary-glow);
  }

  .lab-input-tool {
    background: transparent;
    border: none;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: color 0.2s ease;
    padding: 0.25rem;
  }
  .lab-input-tool:hover {
    color: var(--text-main);
  }

  .lab-textarea-main {
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-family: var(--font-body);
    font-size: 0.95rem;
    outline: none;
    resize: none;
    padding: 0.4rem 0;
    max-height: 100px;
  }

  .input-ops-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .lab-send-trigger {
    width: 32px;
    height: 32px;
    background: var(--secondary);
    color: #fff;
    border: none;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .lab-send-trigger:hover:not(:disabled) {
    background: var(--accent);
    transform: translateY(-1px);
    box-shadow: 0 0 10px var(--secondary);
  }
  .lab-send-trigger:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }


  .agent-observability {
    width: 280px;
    flex-shrink: 0;
    border-left: 1px solid var(--glass-border);
    background: rgba(8, 10, 14, 0.78);
    display: flex;
    flex-direction: column;
    padding: 1rem;
    gap: 0.85rem;
    overflow: hidden;
  }

  .obs-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: var(--text-main);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.14em;
  }

  .obs-live {
    color: var(--text-dim);
    border: 1px solid var(--glass-border);
    border-radius: 999px;
    padding: 0.18rem 0.45rem;
    font-size: 0.58rem;
  }

  .obs-live.active {
    color: var(--secondary);
    border-color: rgba(0, 245, 212, 0.45);
  }

  .obs-session,
  .obs-empty,
  .obs-meta,
  .obs-summary {
    color: var(--text-dim);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    line-height: 1.45;
  }

  .obs-session strong {
    color: var(--secondary);
    word-break: break-all;
  }

  .obs-list {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding-right: 0.25rem;
  }

  .obs-item {
    display: grid;
    grid-template-columns: 10px 1fr;
    gap: 0.6rem;
    padding: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.035);
  }

  .obs-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--secondary);
    margin-top: 0.25rem;
    box-shadow: 0 0 14px rgba(0, 245, 212, 0.5);
  }

  .obs-title {
    color: #fff;
    font-size: 0.78rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
  }

  .obs-summary {
    margin-top: 0.35rem;
    word-break: break-word;
  }

  .stream-cursor {
    display: inline-block;
    width: 0.5rem;
    height: 1rem;
    margin-left: 0.2rem;
    border-radius: 2px;
    background: var(--secondary);
    vertical-align: text-bottom;
    opacity: 0.85;
  }

  /* Responsive fixes */
  .ws-mobile-toggle-btn {
    display: none;
  }

  @media (max-width: 768px) {
    .ws-container {
      position: relative;
    }
    .agent-observability { display: none; }
    .ws-sidebar {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 280px;
      transform: translateX(-100%);
      transition: transform 0.3s ease;
    }
    .ws-sidebar.mobile-open {
      transform: translateX(0);
    }
    .ws-sidebar-overlay {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(4px);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
      z-index: 9;
    }
    .ws-sidebar-overlay.active {
      opacity: 1;
      pointer-events: auto;
    }
    .ws-mobile-toggle-btn {
      display: flex;
      position: absolute;
      left: 1rem;
      top: 1rem;
      z-index: 8;
      background: rgba(20, 20, 25, 0.8);
      border: 1px solid var(--glass-border);
      color: #fff;
      padding: 0.5rem;
      border-radius: 8px;
      cursor: pointer;
    }
  }

  /* Inline markdown styles */
  .chat-h1 { font-size: 1.25rem; font-weight: 700; color: #fff; margin: 1rem 0 0.5rem; }
  .chat-h2 { font-size: 1.1rem; font-weight: 600; color: #fff; margin: 0.85rem 0 0.4rem; }
  .chat-h3 { font-size: 1rem; font-weight: 600; color: #fff; margin: 0.75rem 0 0.35rem; }
  .chat-bullet { display: flex; gap: 0.5rem; margin-bottom: 0.35rem; font-size: 0.95rem; }
  .bullet-dot { color: var(--secondary); font-weight: bold; }
  .chat-numbered { display: flex; gap: 0.5rem; margin-bottom: 0.35rem; font-size: 0.95rem; }
  .num-marker { color: var(--secondary); font-family: var(--font-mono); font-weight: bold; }
  .chat-spacer { height: 0.75rem; }
  .chat-p { margin-bottom: 0.5rem; font-size: 0.95rem; }
  .chat-inline-code { font-family: var(--font-mono); font-size: 0.85em; background: rgba(255,255,255,0.06); padding: 0.15em 0.3em; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); color: var(--accent); }
  .chat-code-block { font-family: var(--font-mono); font-size: 0.85rem; background: #000; border: 1px solid var(--glass-border); border-radius: 8px; padding: 1rem; margin: 0.75rem 0; overflow-x: auto; color: var(--text-main); }
  .chat-code-block code { font-family: inherit; }
  .citation-badge { display: inline-block; background: rgba(99, 102, 241, 0.15); color: var(--accent); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 4px; padding: 0 4px; margin: 0 2px; font-size: 0.75em; font-family: var(--font-mono); cursor: help; }

  /* Bubbly academia workspace refresh */
  .ws-container {
    --ws-ink: #f8f3ff;
    --ws-cream: #f5ecff;
    --ws-muted: #cbbdde;
    --ws-faint: #9b8bad;
    --ws-plum: #8b5cf6;
    --ws-lavender: #c4b5fd;
    --ws-mint: #8ee8d8;
    --ws-rose: #f0abfc;
    background:
      radial-gradient(circle at 20% 8%, rgba(196, 181, 253, 0.16), transparent 32rem),
      radial-gradient(circle at 76% 18%, rgba(142, 232, 216, 0.12), transparent 28rem),
      linear-gradient(135deg, #110b17 0%, #08070b 48%, #14101d 100%);
    color: var(--ws-ink);
    font-family: var(--font-body);
  }

  .ws-container h1,
  .ws-container h2,
  .ws-container h3,
  .ws-container h4,
  .ws-container button,
  .ws-container textarea,
  .ws-container input {
    letter-spacing: -0.01em;
  }

  .ws-sidebar,
  .agent-observability {
    background: rgba(28, 21, 38, 0.64);
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
  }

  .ws-sidebar { width: 336px; }

  .ws-sidebar-header {
    padding: 1.4rem;
    border-bottom-color: rgba(255,255,255,0.08);
  }

  .ws-back-link,
  .ws-card-title,
  .ws-conversations-header,
  .msg-sender,
  .obs-header,
  .obs-live,
  .obs-session,
  .obs-empty,
  .obs-meta,
  .obs-summary,
  .btn-lab-sm,
  .type-opt,
  .lab-suggest-chip,
  .file-label,
  .source-meta {
    font-family: var(--font-heading);
    text-transform: none;
    letter-spacing: 0.01em;
  }

  .ws-back-link,
  .ws-card-title,
  .ws-conversations-header,
  .msg-sender,
  .obs-header {
    color: var(--ws-cream);
  }

  .ws-project-name {
    font-size: 1.2rem;
    font-weight: 700;
    text-wrap: balance;
    color: var(--ws-ink);
  }

  .folder-icon-wrapper,
  .ws-card-icon,
  .msg-avatar,
  .obs-dot {
    border-radius: 999px;
  }

  .ws-card-btn,
  .sources-expanded,
  .instructions-edit,
  .source-item,
  .stream-row,
  .msg-text-box,
  .lab-input-form,
  .obs-item,
  .chat-code-block {
    border-radius: 22px;
    background: linear-gradient(145deg, rgba(255,255,255,0.1), rgba(255,255,255,0.035));
    border-color: rgba(255,255,255,0.11);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
  }

  .ws-card-btn {
    padding: 1rem;
    align-items: flex-start;
  }

  .ws-card-btn:hover,
  .stream-row:hover,
  .source-item:hover,
  .obs-item:hover {
    background: linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.055));
    border-color: rgba(196, 181, 253, 0.28);
  }

  .ws-card-btn.active,
  .stream-row.active {
    background: linear-gradient(145deg, rgba(139, 92, 246, 0.22), rgba(142, 232, 216, 0.07));
    border-color: rgba(196, 181, 253, 0.34);
  }

  .ws-card-icon,
  .folder-icon-wrapper,
  .msg-avatar {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    color: var(--ws-lavender);
  }

  .ws-card-subtitle,
  .stream-title,
  .source-title,
  .chat-p,
  .chat-bullet,
  .chat-numbered,
  .obs-summary,
  .instructions-textarea,
  .lab-source-input,
  .lab-textarea-main {
    color: var(--ws-cream);
  }

  .source-meta,
  .obs-meta,
  .chat-empty-lab p,
  .file-name-hint,
  .sources-empty-state span {
    color: var(--ws-muted);
  }

  .ws-main {
    background: rgba(15, 12, 21, 0.42);
    border-color: rgba(255,255,255,0.08);
    position: relative;
  }

  .ws-main::before {
    content: '';
    position: absolute;
    inset: 1rem;
    pointer-events: none;
    border-radius: 34px;
    border: 1px solid rgba(255,255,255,0.06);
    background: linear-gradient(180deg, rgba(255,255,255,0.035), transparent 34%);
  }

  .chat-messages,
  .chat-input-zone { position: relative; z-index: 1; }

  .chat-messages-inner { max-width: 820px; gap: 1.5rem; }

  .chat-empty-lab {
    max-width: 560px;
    margin: 0 auto;
    color: var(--ws-ink);
  }

  .chat-empty-lab h2 {
    font-family: var(--font-heading);
    font-size: 1.65rem;
    letter-spacing: -0.02em;
    color: var(--ws-ink);
    text-wrap: balance;
  }

  .lab-pulse-large {
    width: 4.2rem;
    height: 4.2rem;
    background:
      radial-gradient(circle at 35% 30%, #ffffff 0 10%, var(--ws-mint) 11% 28%, var(--ws-lavender) 29% 62%, rgba(139, 92, 246, 0.4) 63% 100%);
    box-shadow: 0 0 36px rgba(196, 181, 253, 0.28);
    animation: scholarly-breathe 1.8s ease-in-out infinite;
  }

  @keyframes scholarly-breathe {
    0%, 100% { transform: scale(0.96); opacity: 0.82; }
    50% { transform: scale(1.04); opacity: 1; }
  }

  .lab-suggest-chip,
  .btn-lab-sm,
  .type-opt,
  .lab-send-trigger,
  .lab-source-submit,
  .conv-new-btn,
  .source-action-btn,
  .source-del,
  .stream-del,
  .lab-input-tool {
    border-radius: 999px;
  }

  .lab-suggest-chip {
    padding: 0.7rem 1rem;
    font-size: 0.82rem;
    color: var(--ws-ink);
    background: rgba(255,255,255,0.08);
  }

  .lab-msg { align-items: flex-start; gap: 0.9rem; }

  .msg-avatar {
    width: 38px;
    height: 38px;
  }

  .lab-msg.ai .msg-avatar {
    color: var(--ws-mint);
    border-color: rgba(142, 232, 216, 0.28);
    background: rgba(142, 232, 216, 0.08);
  }

  .msg-header { display: flex; align-items: center; gap: 0.8rem; }

  .msg-sender { font-size: 0.78rem; font-weight: 700; color: var(--ws-muted); }

  .msg-line { background: linear-gradient(90deg, rgba(196,181,253,0.24), transparent); }

  .msg-text-box {
    padding: 1rem 1.15rem;
    font-size: 0.98rem;
    line-height: 1.68;
  }

  .lab-msg.user .msg-text-box {
    background: linear-gradient(145deg, rgba(139, 92, 246, 0.22), rgba(255,255,255,0.045));
    border-color: rgba(196,181,253,0.28);
  }

  .lab-loader-dots {
    display: inline-flex;
    gap: 0.35rem;
    align-items: center;
    min-height: 1.5rem;
  }

  .lab-loader-dots span {
    width: 0.58rem;
    height: 0.58rem;
    border-radius: 999px;
    background: var(--ws-lavender);
    animation: bubble-thinking 0.95s ease-in-out infinite;
  }

  .lab-loader-dots span:nth-child(2) { animation-delay: 0.12s; background: var(--ws-mint); }
  .lab-loader-dots span:nth-child(3) { animation-delay: 0.24s; background: var(--ws-rose); }

  @keyframes bubble-thinking {
    0%, 100% { transform: translateY(0) scale(0.86); opacity: 0.52; }
    50% { transform: translateY(-0.35rem) scale(1); opacity: 1; }
  }

  .chat-input-zone {
    padding: 1rem 2rem 1.6rem;
    background: linear-gradient(to top, rgba(15,12,21,0.94) 72%, transparent);
  }

  .lab-input-form {
    max-width: 820px;
    padding: 0.62rem 0.72rem;
    background: rgba(255,255,255,0.09);
  }

  .lab-input-form:focus-within {
    border-color: rgba(142, 232, 216, 0.44);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 0 0 3px rgba(142, 232, 216, 0.1);
  }

  .lab-textarea-main::placeholder,
  .lab-source-input::placeholder,
  .instructions-textarea::placeholder { color: #d8cdea; opacity: 1; }

  .lab-send-trigger,
  .lab-source-submit,
  .btn-lab-sm.primary,
  .type-opt.active {
    background: linear-gradient(135deg, var(--ws-plum), #a78bfa);
    color: white;
  }

  .agent-computing-note {
    max-width: 820px;
    margin: 0.65rem auto 0;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--ws-muted);
    font-size: 0.82rem;
  }

  .thinking-orb {
    width: 0.72rem;
    height: 0.72rem;
    border-radius: 999px;
    background: var(--ws-mint);
    box-shadow: 0 0 18px rgba(142, 232, 216, 0.5);
    animation: scholarly-breathe 1.2s ease-in-out infinite;
  }

  .agent-observability { width: 304px; }

  .obs-header { font-size: 0.86rem; }

  .obs-live {
    font-size: 0.68rem;
    color: var(--ws-muted);
    background: rgba(255,255,255,0.055);
  }

  .obs-live.active {
    color: var(--ws-mint);
    border-color: rgba(142, 232, 216, 0.32);
  }

  .obs-session strong { color: var(--ws-mint); }

  .obs-item { grid-template-columns: 12px 1fr; }

  .obs-dot {
    width: 10px;
    height: 10px;
    background: var(--ws-mint);
    box-shadow: 0 0 16px rgba(142, 232, 216, 0.45);
  }

  .obs-title { color: var(--ws-ink); font-size: 0.86rem; }

  .stream-cursor {
    width: 0.42rem;
    height: 1.05rem;
    border-radius: 999px;
    background: var(--ws-mint);
    animation: cursor-breathe 0.9s ease-in-out infinite;
  }

  @keyframes cursor-breathe {
    0%, 100% { opacity: 0.35; }
    50% { opacity: 1; }
  }

  .chat-h1, .chat-h2, .chat-h3 {
    font-family: var(--font-heading);
    color: var(--ws-ink);
    text-wrap: balance;
  }

  .chat-inline-code,
  .citation-badge {
    border-radius: 999px;
    background: rgba(196, 181, 253, 0.14);
    border-color: rgba(196, 181, 253, 0.26);
    color: var(--ws-lavender);
  }

  .chat-code-block { background: rgba(8, 7, 12, 0.72); }

  .ws-loading,
  .ws-not-found {
    --ws-ink: #f8f3ff;
    --ws-muted: #cbbdde;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background:
      radial-gradient(circle at 50% 30%, rgba(196,181,253,0.16), transparent 24rem),
      #0d0912;
    color: var(--text-main);
  }

  .ws-loading p,
  .ws-not-found p { color: var(--ws-muted); }

  .ws-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.7rem 1rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.09);
    color: var(--ws-ink);
    border: 1px solid rgba(255,255,255,0.12);
  }

  @media (max-width: 1240px) {
    .agent-observability { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    .ws-container *,
    .ws-container *::before,
    .ws-container *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }

`;
