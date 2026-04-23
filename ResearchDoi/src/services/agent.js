/**
 * ADK Agent Service
 * 
 * Interacts with the deployed Google ADK agent via our API proxy
 * 
 * @module services/agent
 */

import { apiFetch } from './api.js';

/**
 * Create or get a session with the agent
 * 
 * @param {string} userId - Current user ID
 * @param {string} projectId - Project ID (used as session ID)
 * @param {string} chatId - Chat ID
 * @returns {Promise<boolean>} True if session created or exists
 */
export async function createSession(userId, projectId, chatId) {
    return true; // Session is created on first message
}

/**
 * Send a message to the agent via our API proxy
 * 
 * @param {string} userId - Current user ID
 * @param {string} projectId - Project ID
 * @param {string} chatId - Chat ID
 * @param {string} message - User message
 * @param {function} onChunk - Callback for each chunk of the response (optional, for streaming)
 * @returns {Promise<{reply: string, chatId: string}>} Agent response
 */
export async function sendMessage(userId, projectId, chatId, message, onChunk) {
    try {
        const res = await apiFetch('/api/chat/agent/message', {
            method: 'POST',
            userId: userId,
            body: JSON.stringify({
                project_id: projectId,
                chat_id: chatId,
                message: message,
            }),
        });
        
        const data = await res.json();
        
        if (onChunk && data.reply) {
            onChunk(data.reply);
        }
        

        return {
            reply: data.reply || '',
            chatId: data.chat_id || chatId,
            title: data.title,
            tool_calls: data.agent_response && data.agent_response.tool_calls ? data.agent_response.tool_calls : [],
        };

    } catch (err) {
        console.error('Agent sendMessage error:', err);
        throw err;
    }
}

/**
 * Get chat history from Firestore via our API
 * 
 * @param {string} userId - Current user ID
 * @param {string} projectId - Project ID
 * @param {string} chatId - Chat ID
 * @returns {Promise<Array>} Messages array
 */
export async function getChatHistory(userId, projectId, chatId) {
    const res = await apiFetch(`/api/chat/session/${projectId}?chat_id=${encodeURIComponent(chatId)}`, {
        userId: userId
    });
    const data = await res.json();
    return data.messages || [];
}

/**
 * Save a message to Firestore via our API
 * 
 * @param {string} userId - Current user ID
 * @param {string} projectId - Project ID
 * @param {string} chatId - Chat ID
 * @param {string} role - 'user' or 'model'
 * @param {string} text - Message text
 * @returns {Promise<void>}
 */
export async function saveMessage(userId, projectId, chatId, role, text) {
    await apiFetch('/api/chat/message', {
        method: 'POST',
        userId: userId,
        body: JSON.stringify({
            project_id: projectId,
            chat_id: chatId,
            message: text,
            role: role,
        }),
    });
}
