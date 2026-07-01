/* eslint-disable react-hooks/exhaustive-deps, react-hooks/set-state-in-effect */
import { useState, useEffect, useRef } from 'react';
import { applyPatch } from 'fast-json-patch';

const API_BASE = import.meta.env?.VITE_API_BASE_URL ?? '';
const API_KEY = import.meta.env?.VITE_API_KEY ?? '';

export function useSSE(projectId, initialThesis = {}) {
    const [thesisState, setThesisState] = useState(initialThesis || {});
    const thesisRef = useRef(thesisState);
    
    // Keep ref in sync
    useEffect(() => {
        if (Object.keys(thesisState).length === 0 && Object.keys(initialThesis).length > 0) {
            setThesisState(initialThesis);
            thesisRef.current = initialThesis;
        }
    }, [initialThesis]);

    useEffect(() => {
        if (!projectId) return;

        let url = `${API_BASE}/api/stream/${projectId}`;
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            try {
                const patch = JSON.parse(event.data);
                // Apply patch to the current state
                const newState = applyPatch(
                    JSON.parse(JSON.stringify(thesisRef.current)),
                    [patch]
                ).newDocument;
                
                thesisRef.current = newState;
                setThesisState(newState);
            } catch (err) {
                console.error("Failed to parse or apply SSE patch:", err);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE connection error", err);
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, [projectId]);

    return thesisState;
}
