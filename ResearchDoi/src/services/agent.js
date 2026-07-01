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
export async function createSession(/* userId, projectId, chatId */) {
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
export async function sendMessage(userId, projectId, chatId, message, onChunk, onActivity) {
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
        
        if (onActivity && data.agent_response) {
            onActivity(normalizeAgentActivity(data.agent_response));
        }

        if (onChunk && data.reply) {
            await streamText(data.reply, onChunk);
        }
        
        return {
            reply: data.reply || '',
            chatId: data.chat_id || chatId,
            title: data.title,
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


function getPartText(part) {
    if (!part || typeof part !== 'object') return '';
    if (typeof part.text === 'string') return part.text;
    if (part.functionCall?.name) return `Calling ${part.functionCall.name}`;
    if (part.functionResponse?.name) return `Completed ${part.functionResponse.name}`;
    return '';
}

function normalizeAgentActivity(agentResponse) {
    const events = Array.isArray(agentResponse) ? agentResponse : [agentResponse];
    return events.map((event, index) => {
        const parts = event?.content?.parts || event?.parts || [];
        const functionCall = parts.find((part) => part?.functionCall)?.functionCall;
        const functionResponse = parts.find((part) => part?.functionResponse)?.functionResponse;
        const text = parts.map(getPartText).filter(Boolean).join(' • ');
        const type = functionCall ? 'tool_call' : functionResponse ? 'tool_result' : event?.author ? 'agent' : 'event';
        return {
            id: event?.id || `${Date.now()}-${index}`,
            type,
            actor: event?.author || event?.name || 'agent',
            label: functionCall?.name || functionResponse?.name || event?.author || 'Agent event',
            status: functionResponse ? 'completed' : functionCall ? 'running' : 'observed',
            summary: text || (event?.actions?.stateDelta ? 'State updated' : 'Agent step recorded'),
        };
    }).filter((event) => event.summary || event.label);
}

function streamText(text, onChunk) {
    const chunkSize = 24;
    const frameMs = 16;
    return new Promise((resolve) => {
        let index = 0;
        const emit = () => {
            index = Math.min(index + chunkSize, text.length);
            onChunk(text.slice(0, index), { replace: true });
            if (index >= text.length) {
                resolve();
                return;
            }
            window.setTimeout(emit, frameMs);
        };
        emit();
    });
}
