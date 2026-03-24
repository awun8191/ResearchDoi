/**
 * RAG Service (API-backed)
 *
 * This module is now a thin client over the FastAPI /api/rag/* endpoints.
 * - Embeddings are generated server-side (Gemini API key never exposed).
 * - The in-process vector store lives on the server, scoped to (uid, project_id, chat_id).
 * - On page refresh the store is empty — callers must re-seed via ingestDocument().
 *
 * @module services/rag
 */

import { apiFetch } from './api.js';

/**
 * Ingest a document into the server-side RAG vector store.
 *
 * @param {string} userId
 * @param {string} projectId         - Firestore project ID to scope the store.
 * @param {string} chatId            - Chat session ID to scope the store.
 * @param {string} text              - Full document text to chunk and embed.
 * @param {Object} [metadata]        - Optional metadata (doi, title, source, etc.).
 * @returns {Promise<number>}          Number of chunks stored.
 */
export async function ingestDocument(userId, projectId, chatId, text, metadata = {}) {
    const res = await apiFetch('/api/rag/ingest', {
        method: 'POST',
        userId: userId,
        body: JSON.stringify({ project_id: projectId, chat_id: chatId, text, metadata }),
    });
    const data = await res.json();
    return data.chunks_stored;
}

/**
 * Ingest a website URL into the server-side RAG vector store.
 *
 * @param {string} userId
 * @param {string} projectId - Firestore project ID.
 * @param {string} chatId    - Chat session ID.
 * @param {string} url       - Website URL to scrape and ingest.
 * @returns {Promise<number>} Number of chunks stored.
 */
export async function ingestUrl(userId, projectId, chatId, url) {
    const res = await apiFetch(`/api/rag/ingest/url?project_id=${encodeURIComponent(projectId)}&chat_id=${encodeURIComponent(chatId)}&url=${encodeURIComponent(url)}`, {
        method: 'POST',
        userId: userId,
    });
    const data = await res.json();
    return data.chunks_stored;
}

/**
 * Upload and ingest a PDF file.
 *
 * @param {string} userId
 * @param {string} projectId - Firestore project ID.
 * @param {string} chatId    - Chat session ID.
 * @param {File} file        - PDF file to upload.
 * @returns {Promise<number>} Number of chunks stored.
 */
export async function ingestFile(userId, projectId, chatId, file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await apiFetch(`/api/rag/ingest/file?project_id=${encodeURIComponent(projectId)}&chat_id=${encodeURIComponent(chatId)}`, {
        method: 'POST',
        userId: userId,
        body: formData,
    });
    
    const data = await res.json();
    return data.chunks_stored;
}

/**
 * Ingest all sources from project metadata.
 *
 * @param {string} userId
 * @param {string} projectId - Firestore project ID.
 * @param {string} chatId    - Chat session ID.
 * @returns {Promise<number>} Number of chunks stored.
 */
export async function ingestProjectSources(userId, projectId, chatId) {
    const res = await apiFetch(`/api/rag/ingest/sources?project_id=${encodeURIComponent(projectId)}&chat_id=${encodeURIComponent(chatId)}`, {
        method: 'POST',
        userId: userId,
    });
    const data = await res.json();
    return data.chunks_stored;
}

/**
 * Search the server-side RAG vector store.
 *
 * @param {string} userId
 * @param {string} projectId - Firestore project ID.
 * @param {string} chatId    - Chat session ID.
 * @param {string} query     - Semantic search query.
 * @param {number} [topK=3]  - Number of top results to return.
 * @returns {Promise<Array<{ id: string, text: string, score: number, metadata: Object }>>}
 */
export async function searchKnowledgeBase(userId, projectId, chatId, query, topK = 3) {
    const res = await apiFetch('/api/rag/search', {
        method: 'POST',
        userId: userId,
        body: JSON.stringify({ project_id: projectId, chat_id: chatId, query, top_k: topK }),
    });
    return res.json();
}

/**
 * Clear the server-side RAG vector store for a project/chat.
 * Useful before re-seeding after sources are updated.
 *
 * @param {string} userId
 * @param {string} projectId
 * @param {string} chatId
 * @returns {Promise<void>}
 */
export async function clearRagStore(userId, projectId, chatId) {
    await apiFetch(`/api/rag/store?project_id=${encodeURIComponent(projectId)}&chat_id=${encodeURIComponent(chatId)}`, {
        method: 'DELETE',
        userId: userId,
    });
}
