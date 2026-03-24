/**
 * Gemini Chat Service (API-backed)
 *
 * This module is now a thin client over the FastAPI backend.
 * - The Gemini API key is NEVER exposed in the frontend bundle.
 * - Chat history is persisted in Firestore by the server.
 * - The RAG function-calling loop runs entirely server-side.
 *
 * @module services/gemini
 */

import { apiFetch } from './api.js';

/**
 * Create a chat session object for a specific project.
 *
 * The returned session object mirrors the original interface so callers
 * in ProjectWorkspace.jsx do not need to change.
 *
 * @param {string} userId              - Current user ID.
 * @param {string} projectId           - Firestore project document ID.
 * @param {string} [systemPrompt]      - Project-level instructions (project.instructions).
 * @param {string} [chatId]            - Chat thread ID under project documents.
 * @returns {{ sendMessage: Function, clearHistory: Function }}
 */
export function createChatSession(userId, projectId, systemPrompt = '', chatId = 'default') {
    /**
     * Send a user message and get the model's reply.
     *
     * @param {string} userText
     * @param {string} [chatTitle]
     * @returns {Promise<{reply: string, chatId: string, title: string | null}>}
     */
    async function sendMessage(userText, chatTitle) {
        const res = await apiFetch('/api/chat/message', {
            method: 'POST',
            userId: userId,
            body: JSON.stringify({
                project_id: projectId,
                chat_id: chatId,
                message: userText,
                chat_title: chatTitle || undefined,
                system_prompt: systemPrompt || undefined,
            }),
        });
        const data = await res.json();
        return {
            reply: data.reply,
            chatId: data.chat_id || chatId,
            title: data.title || null,
        };
    }

    /**
     * Clear all chat history for this project from Firestore.
     * @returns {Promise<void>}
     */
    async function clearHistory() {
        await apiFetch('/api/chat/session', {
            method: 'DELETE',
            userId: userId,
            body: JSON.stringify({
                project_id: projectId,
                chat_id: chatId,
            }),
        });
    }

    /**
     * Fetch all chat history for this project from Firestore.
     * @returns {Promise<{chatId: string, title: string | null, messages: Array}>}
     */
    async function getHistory() {
        const res = await apiFetch(`/api/chat/session/${projectId}?chat_id=${encodeURIComponent(chatId)}`, {
            userId: userId
        });
        const data = await res.json();
        return {
            chatId: data.chat_id || chatId,
            title: data.title || null,
            messages: data.messages || [],
        };
    }

    return { sendMessage, clearHistory, getHistory };
}

export async function listChatSessions(userId, projectId) {
    const res = await apiFetch(`/api/chat/sessions/${projectId}`, {
        userId: userId
    });
    const data = await res.json();
    return data.sessions || [];
}

export async function deleteChatSession(userId, projectId, chatId) {
    await apiFetch(`/api/chat/sessions/${projectId}/${encodeURIComponent(chatId)}`, {
        method: 'DELETE',
        userId: userId
    });
}
