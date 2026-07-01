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

import { apiFetch } from './api';

export async function createProject(userId, { name, instructions = '' }) {
    try {
        const res = await apiFetch('/api/projects', {
            method: 'POST',
            userId: userId,
            body: JSON.stringify({ name, instructions })
        });
        const result = await res.json();
        
        // Save to local storage for UI state
        const projects = getLocalProjects();
        const id = result.id;
        projects[id] = {
            id,
            name,
            instructions,
            sources: [],
            createdAt: result.created_at || new Date().toISOString(),
            updatedAt: result.updated_at || new Date().toISOString(),
            ...result
        };
        saveLocalProjects(projects);
        return id;
    } catch (err) {
        console.error('Failed API call to create project', err);
        throw err;
    }
}

export function onUserProjects(userId, callback) {
    function notify() {
        const projectsObj = getLocalProjects();
        const arr = Object.values(projectsObj).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        callback(arr);
    }
    notify();
    window.addEventListener('projects_updated', notify);

    // Fetch from backend to sync
    apiFetch('/api/projects', { userId }).then(res => res.json()).then(backendProjects => {
        if (Array.isArray(backendProjects)) {
            const projects = getLocalProjects();
            backendProjects.forEach(p => {
                projects[p.id] = { ...p, createdAt: p.created_at || p.createdAt, updatedAt: p.updated_at || p.updatedAt };
            });
            saveLocalProjects(projects);
        }
    }).catch(err => console.error('Failed to sync projects from backend', err));

    return () => window.removeEventListener('projects_updated', notify);
}

export async function getProject(userId, projectId) {
    try {
        const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}`, { userId });
        const backendProj = await res.json();
        if (backendProj && backendProj.id) {
            const projects = getLocalProjects();
            projects[projectId] = {
                ...backendProj,
                createdAt: backendProj.created_at || backendProj.createdAt,
                updatedAt: backendProj.updated_at || backendProj.updatedAt
            };
            saveLocalProjects(projects);
            return projects[projectId];
        }
    } catch (err) {
        console.error(`Failed to fetch project ${projectId} via API`, err);
    }
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

    // Sync from backend
    apiFetch(`/api/projects/${encodeURIComponent(projectId)}`, { userId })
        .then(res => res.json())
        .then(backendProj => {
            if (backendProj && backendProj.id) {
                const projects = getLocalProjects();
                projects[projectId] = {
                    ...backendProj,
                    createdAt: backendProj.created_at || backendProj.createdAt,
                    updatedAt: backendProj.updated_at || backendProj.updatedAt
                };
                saveLocalProjects(projects);
            }
        })
        .catch(err => console.error(`Failed to sync project ${projectId} from backend`, err));

    return () => window.removeEventListener('projects_updated', notify);
}

export async function updateProject(userId, projectId, data) {
    try {
        await apiFetch(`/api/projects/${encodeURIComponent(projectId)}`, {
            method: 'PATCH',
            userId: userId,
            body: JSON.stringify(data)
        });
        
        const projects = getLocalProjects();
        if (!projects[projectId]) return;
        projects[projectId] = { ...projects[projectId], ...data, updatedAt: new Date().toISOString() };
        saveLocalProjects(projects);
    } catch (err) {
        console.error('Failed to update project via API', err);
        // Fallback local update
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId] = { ...projects[projectId], ...data, updatedAt: new Date().toISOString() };
            saveLocalProjects(projects);
        }
    }
}

export async function deleteProject(userId, projectId) {
    try {
        await apiFetch(`/api/projects/${encodeURIComponent(projectId)}`, {
            method: 'DELETE',
            userId: userId
        });
    } catch (err) {
        console.error('Failed to delete project via API', err);
    }
    const projects = getLocalProjects();
    delete projects[projectId];
    saveLocalProjects(projects);
}

export async function removeSource(userId, projectId, sourceObj) {
    try {
        if (sourceObj.doi) {
            const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceObj.doi)}`, {
                method: 'DELETE',
                userId: userId
            });
            const result = await res.json();
            if (result && result.id) {
                const projects = getLocalProjects();
                projects[projectId] = {
                    ...result,
                    createdAt: result.created_at || result.createdAt,
                    updatedAt: result.updated_at || result.updatedAt
                };
                saveLocalProjects(projects);
                return result;
            }
        }
    } catch (err) {
        console.error('Failed to remove source via API', err);
    }
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

export async function addSourceViaApi(userId, projectId, data) {
    try {
        const res = await apiFetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
            method: 'POST',
            userId: userId,
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result && result.id) {
            const projects = getLocalProjects();
            projects[projectId] = {
                ...result,
                createdAt: result.created_at || result.createdAt,
                updatedAt: result.updated_at || result.updatedAt
            };
            saveLocalProjects(projects);
            return result;
        }
    } catch (err) {
        console.error('Failed API call, falling back to local addition', err);
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources = projects[projectId].sources || [];
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
        if (result && result.id) {
            const projects = getLocalProjects();
            projects[projectId] = {
                ...result,
                createdAt: result.created_at || result.createdAt,
                updatedAt: result.updated_at || result.updatedAt
            };
            saveLocalProjects(projects);
            return result;
        }
    } catch (err) {
        console.error('Failed API call, falling back to local addition', err);
        const projects = getLocalProjects();
        if (projects[projectId]) {
            projects[projectId].sources = projects[projectId].sources || [];
            projects[projectId].sources.push({ type: 'file', title: file.name });
            projects[projectId].updatedAt = new Date().toISOString();
            saveLocalProjects(projects);
        }
        return { success: true, localOnly: true };
    }
}
