import {
    collection,
    addDoc,
    deleteDoc,
    doc,
    updateDoc,
    onSnapshot,
    query,
    orderBy,
    serverTimestamp,
    arrayUnion,
    arrayRemove,
    getDoc,
} from 'firebase/firestore';
import { db } from '../firebase';

/**
 * Returns the Firestore collection reference for a user's projects.
 * Path: users/{userId}/projects
 */
function projectsRef(userId) {
    return collection(db, 'users', userId, 'projects');
}

/**
 * Returns a single project document reference.
 * Path: users/{userId}/projects/{projectId}
 */
function projectDocRef(userId, projectId) {
    return doc(db, 'users', userId, 'projects', projectId);
}

/**
 * Creates a new project for the given user.
 * @param {string} userId
 * @param {{ name: string, instructions?: string }} data
 * @returns {Promise<string>} The new project's ID
 */
export async function createProject(userId, { name, instructions = '' }) {
    const docRef = await addDoc(projectsRef(userId), {
        name,
        instructions,
        sources: [],
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
    });
    return docRef.id;
}

/**
 * Subscribes to real-time updates for a user's projects list.
 * @param {string} userId
 * @param {function} callback - receives an array of project objects
 * @returns {function} Unsubscribe function
 */
export function onUserProjects(userId, callback) {
    const q = query(projectsRef(userId), orderBy('createdAt', 'desc'));
    return onSnapshot(q, (snapshot) => {
        const projects = snapshot.docs.map((doc) => ({
            id: doc.id,
            ...doc.data(),
        }));
        callback(projects);
    });
}

/**
 * Fetches a single project document.
 * @param {string} userId
 * @param {string} projectId
 * @returns {Promise<Object|null>}
 */
export async function getProject(userId, projectId) {
    const snap = await getDoc(projectDocRef(userId, projectId));
    if (!snap.exists()) return null;
    return { id: snap.id, ...snap.data() };
}

/**
 * Subscribes to real-time updates for a single project.
 * @param {string} userId
 * @param {string} projectId
 * @param {function} callback
 * @returns {function} Unsubscribe function
 */
export function onProject(userId, projectId, callback) {
    return onSnapshot(projectDocRef(userId, projectId), (snap) => {
        if (!snap.exists()) {
            callback(null);
            return;
        }
        callback({ id: snap.id, ...snap.data() });
    });
}

/**
 * Updates a project's fields.
 * @param {string} userId
 * @param {string} projectId
 * @param {Object} data - fields to update (name, instructions)
 */
export async function updateProject(userId, projectId, data) {
    await updateDoc(projectDocRef(userId, projectId), {
        ...data,
        updatedAt: serverTimestamp(),
    });
}

/**
 * Deletes a project.
 * @param {string} userId
 * @param {string} projectId
 */
export async function deleteProject(userId, projectId) {
    await deleteDoc(projectDocRef(userId, projectId));
}

/**
 * Removes a DOI source from a project's sources array.
 * @param {string} userId
 * @param {string} projectId
 * @param {Object} sourceObj - the exact source object to remove
 */
export async function removeSource(userId, projectId, sourceObj) {
    await updateDoc(projectDocRef(userId, projectId), {
        sources: arrayRemove(sourceObj),
        updatedAt: serverTimestamp(),
    });
}

import { apiFetch } from './api';

/**
 * Add a DOI or URL source via the API (handles metadata, storage, and Vertex RAG ingestion)
 * @param {string} userId
 * @param {string} projectId 
 * @param {Object} data - { type: "doi" | "url", doi?: string, url?: string, title?: string, ... }
 */
export async function addSourceViaApi(userId, projectId, data) {
    const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
        method: 'POST',
        userId: userId,
        body: JSON.stringify(data)
    });
    return res.json();
}

/**
 * Add a file source via the API (handles storage and Vertex RAG ingestion)
 * @param {string} userId
 * @param {string} projectId 
 * @param {File} file 
 */
export async function addSourceFileViaApi(userId, projectId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);
    
    const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources/file`, {
        method: 'POST',
        userId: userId,
        body: formData
    });
    return res.json();
}
