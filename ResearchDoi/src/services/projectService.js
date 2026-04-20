function getLocalProjects() {
    try {
        const data = localStorage.getItem('researchdoi_projects');
        return data ? JSON.parse(data) : {};
    } catch {
        return {};
    }
}

function saveLocalProjects(data) {
    localStorage.setItem('researchdoi_projects', JSON.stringify(data));
    // Trigger generic custom event so we can emulate onSnapshot across tabs/components
    window.dispatchEvent(new Event('projects_updated'));
}

export async function createProject(userId, { name, instructions = '' }) {
    const projects = getLocalProjects();
    const id = 'proj_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    projects[id] = {
        id,
        name,
        instructions,
        sources: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    };
    saveLocalProjects(projects);
    return id;
}

export function onUserProjects(userId, callback) {
    function notify() {
        const projectsObj = getLocalProjects();
        const arr = Object.values(projectsObj).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        callback(arr);
    }
    notify();
    window.addEventListener('projects_updated', notify);
    return () => window.removeEventListener('projects_updated', notify);
}

export async function getProject(userId, projectId) {
    const projects = getLocalProjects();
    return projects[projectId] || null;
}

export function onProject(userId, projectId, callback) {
    function notify() {
        const projects = getLocalProjects();
        callback(projects[projectId] || null);
    }
    notify();
    window.addEventListener('projects_updated', notify);
    return () => window.removeEventListener('projects_updated', notify);
}

export async function updateProject(userId, projectId, data) {
    const projects = getLocalProjects();
    if (!projects[projectId]) return;
    projects[projectId] = { ...projects[projectId], ...data, updatedAt: new Date().toISOString() };
    saveLocalProjects(projects);
}

export async function deleteProject(userId, projectId) {
    const projects = getLocalProjects();
    delete projects[projectId];
    saveLocalProjects(projects);
}

export async function removeSource(userId, projectId, sourceObj) {
    const projects = getLocalProjects();
    if (!projects[projectId]) return;
    const newSources = projects[projectId].sources.filter(s => 
        (s.doi && s.doi !== sourceObj.doi) || 
        (s.url && s.url !== sourceObj.url) || 
        (s.id && s.id !== sourceObj.id)
    );
    projects[projectId].sources = newSources;
    projects[projectId].updatedAt = new Date().toISOString();
    saveLocalProjects(projects);
}

import { apiFetch } from './api';

export async function addSourceViaApi(userId, projectId, data) {
    try {
        const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
            method: 'POST',
            userId: userId,
            body: JSON.stringify(data)
        });
        const result = await res.json();
        // Since we removed Firestore updates from backend to frontend, manually update LocalStorage
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources.push(data);
            projects[projectId].updatedAt = new Date().toISOString();
            saveLocalProjects(projects);
        }
        return result;
    } catch (err) {
        console.error('Failed API call, falling back to local addition', err);
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources.push(data);
            projects[projectId].updatedAt = new Date().toISOString();
            saveLocalProjects(projects);
        }
        return { success: true, localOnly: true };
    }
}

export async function addSourceFileViaApi(userId, projectId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);
    try {
        const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources/file`, {
            method: 'POST',
            userId: userId,
            body: formData
        });
        const result = await res.json();
        // Fallback local UI update
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources.push({ type: 'file', title: file.name });
            projects[projectId].updatedAt = new Date().toISOString();
            saveLocalProjects(projects);
        }
        return result;
    } catch (err) {
        console.error('Failed API call, falling back to local addition', err);
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources.push({ type: 'file', title: file.name });
            projects[projectId].updatedAt = new Date().toISOString();
            saveLocalProjects(projects);
        }
        return { success: true, localOnly: true };
    }
}
