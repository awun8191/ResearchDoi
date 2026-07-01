import { useState, useEffect, useCallback } from 'react';
import { listChatSessions, deleteChatSession } from '../services/gemini';
import { getChatHistory, sendMessage as agentSendMessage } from '../services/agent';
import { ingestUrl, ingestFile, ingestProjectSources, clearRagStore } from '../services/rag';

function getStoredActiveChatId(projectId) {
  if (!projectId || typeof window === 'undefined') return 'default';
  return localStorage.getItem(`researchdoi_active_chat_${projectId}`) || 'default';
}

function storeActiveChatId(projectId, chatId) {
  if (!projectId || !chatId || typeof window === 'undefined') return;
  localStorage.setItem(`researchdoi_active_chat_${projectId}`, chatId);
}

export function useChat(userId, projectId) {
  const [activeChatId, setActiveChatId] = useState(() => getStoredActiveChatId(projectId));
  const [chatSessions, setChatSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [chatTitle, setChatTitle] = useState('');
  const [sending, setSending] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [loading, setLoading] = useState(false);

  const refreshChatSessions = useCallback(async (preferredChatId) => {
    if (!userId || !projectId) return;
    try {
      const sessions = await listChatSessions(userId, projectId);
      setChatSessions(sessions);
      const wanted = preferredChatId || getStoredActiveChatId(projectId) || activeChatId;
      if (sessions.length > 0 && !sessions.some((s) => s.chat_id === wanted)) {
        setActiveChatId(sessions[0].chat_id);
        storeActiveChatId(projectId, sessions[0].chat_id);
      } else if (sessions.some((s) => s.chat_id === wanted)) {
        setActiveChatId(wanted);
        storeActiveChatId(projectId, wanted);
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  }, [userId, projectId, activeChatId]);

  const reseedRAG = useCallback(async (sources) => {
    if (!userId || !projectId || !activeChatId || !sources || sources.length === 0) return;
    try {
      await clearRagStore(userId, projectId, activeChatId);
      
      const ingestions = sources.map(async (source) => {
        if (source.type === 'url') {
          return ingestUrl(userId, projectId, activeChatId, source.url);
        } else if (source.pdfUrl) {
          return ingestUrl(userId, projectId, activeChatId, source.pdfUrl);
        }
      });
      await Promise.all(ingestions);
      console.log('RAG Knowledge Base re-seeded successfully for chat:', activeChatId);
    } catch (err) {
      console.error('RAG re-seed failed:', err);
    }
  }, [userId, projectId, activeChatId]);

  const ingestFromProjectSources = useCallback(async () => {
    if (!userId || !projectId || !activeChatId) return;
    try {
      return await ingestProjectSources(userId, projectId, activeChatId);
    } catch (err) {
      console.error('Ingest from project sources failed:', err);
      throw err;
    }
  }, [userId, projectId, activeChatId]);

  const ingestSource = useCallback(async (sourceData) => {
    if (!userId || !projectId || !activeChatId) return;
    try {
      if (sourceData.type === 'url') {
        return await ingestUrl(userId, projectId, activeChatId, sourceData.url);
      } else if (sourceData.pdfUrl) {
        return await ingestUrl(userId, projectId, activeChatId, sourceData.pdfUrl);
      }
    } catch (err) {
      console.error('Ingest source failed:', err);
      throw err;
    }
  }, [userId, projectId, activeChatId]);

  const ingestUploadedFile = useCallback(async (file) => {
    if (!userId || !projectId || !activeChatId) return;
    try {
      return await ingestFile(userId, projectId, activeChatId, file);
    } catch (err) {
      console.error('Ingest file failed:', err);
      throw err;
    }
  }, [userId, projectId, activeChatId]);

  useEffect(() => {
    refreshChatSessions();
  }, [userId, projectId, refreshChatSessions]);

  useEffect(() => {
    setActiveChatId(getStoredActiveChatId(projectId));
  }, [projectId]);

  useEffect(() => {
    storeActiveChatId(projectId, activeChatId);
  }, [projectId, activeChatId]);

  useEffect(() => {
    if (!userId || !projectId || !activeChatId) return;
    let isMounted = true;
    setMessages([]);
    async function fetchHistory() {
      try {
        const history = await getChatHistory(userId, projectId, activeChatId);
        if (isMounted) {
          const title = history.length > 0 ? history[0]?.text?.slice(0, 50) || 'Chat' : '';
          setChatTitle(title);
          setMessages((history || []).map(msg => ({
            id: msg.id || Date.now() + Math.random(),
            role: msg.role === 'model' ? 'model' : 'user',
            text: msg.text,
            timestamp: msg.timestamp
          })));
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    }
    fetchHistory();
    return () => { isMounted = false; };
  }, [userId, projectId, activeChatId]);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || sending) return;

    setSending(true);
    const userMsg = { id: Date.now(), role: 'user', text };
    setMessages((prev) => [...prev, userMsg]);

    const aiPlaceholderId = Date.now() + 1;
    setMessages((prev) => [
      ...prev,
      { id: aiPlaceholderId, role: 'model', text: '', loading: true },
    ]);

    try {
      let fullResponse = '';
      
      await agentSendMessage(
        userId,
        projectId || 'default',
        activeChatId,
        text,
        (chunk) => {
          fullResponse += chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiPlaceholderId
                ? { ...m, text: fullResponse, loading: true }
                : m
            )
          );
        }
      );

      const nextTitle = chatTitle || text.slice(0, 80).trim();
      setChatTitle(nextTitle);
      
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiPlaceholderId
            ? { ...m, text: fullResponse, loading: false }
            : m
        )
      );
      
      await refreshChatSessions(activeChatId);
      storeActiveChatId(projectId, activeChatId);
      return { reply: fullResponse, title: nextTitle };
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiPlaceholderId
            ? {
              ...m,
              text: `**Error:** ${err.message || 'Something went wrong. Please try again.'}`,
              loading: false,
              error: true,
            }
            : m
        )
      );
      throw err;
    } finally {
      setSending(false);
    }
  }, [userId, projectId, activeChatId, chatTitle, refreshChatSessions, sending]);

  const startNewConversation = useCallback(() => {
    const nextId = `chat-${Date.now()}`;
    setChatSessions((prev) => [
      {
        chat_id: nextId,
        title: 'Untitled Chat',
        created_at: null,
        updated_at: null,
      },
      ...prev,
    ]);
    setActiveChatId(nextId);
    storeActiveChatId(projectId, nextId);
    setChatTitle('');
    setMessages([]);
  }, [projectId]);

  const deleteConversation = useCallback(async (chatId) => {
    if (!userId || !projectId) return;
    try {
      await deleteChatSession(userId, projectId, chatId);
      const remaining = chatSessions.filter((s) => s.chat_id !== chatId);
      setChatSessions(remaining);

      if (activeChatId === chatId) {
        if (remaining.length > 0) {
          setActiveChatId(remaining[0].chat_id);
          storeActiveChatId(projectId, remaining[0].chat_id);
          setChatTitle(remaining[0].title || '');
        } else {
          setActiveChatId('default');
          storeActiveChatId(projectId, 'default');
          setChatTitle('');
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      throw err;
    }
  }, [userId, projectId, chatSessions, activeChatId]);

  const switchConversation = useCallback((chatId, title) => {
    setActiveChatId(chatId);
    storeActiveChatId(projectId, chatId);
    setChatTitle(title || '');
  }, [projectId]);

  return {
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
    ingestFromProjectSources,
    ingestUploadedFile,
  };
}
