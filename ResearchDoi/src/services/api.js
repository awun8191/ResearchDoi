/**
 * Shared API client for all backend calls.
 *
 * Authentication: static API key sent as the `X-Api-Key` header.
 * Set VITE_API_KEY in your frontend `.env` to the same value as
 * API_KEY in the backend `.env`.
 *
 * In development (APP_ENV=development on the server) the backend
 * accepts any key (or no key at all), so you can leave VITE_API_KEY
 * empty locally.
 *
 * For multipart uploads, pass { body: FormData } and omit Content-Type
 * (the browser sets it automatically with the correct boundary).
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

/**
 * Authenticated fetch wrapper.
 * Attaches the static API key as an X-Api-Key header on every request.
 * Throws an Error with the API's `detail` message on non-2xx responses.
 *
 * @param {string} path      - API path, e.g. '/api/chat/message'
 * @param {RequestInit & { userId?: string }} [options] - Standard fetch options plus an optional explicit userId.
 * @returns {Promise<Response>}
 */
export async function apiFetch(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    let userId = options.userId;
    
    if (!userId) {
        // Keep API writes in the same user document path used by client Firestore.
        const firebaseAuthStorageKey = Object.keys(localStorage).find((k) =>
            k.startsWith('firebase:authUser:')
        );
        const firebaseUserRaw = firebaseAuthStorageKey
            ? localStorage.getItem(firebaseAuthStorageKey)
            : localStorage.getItem('firebase:authUser');
        
        if (firebaseUserRaw) {
            try {
                const parsed = JSON.parse(firebaseUserRaw);
                userId = parsed?.uid || '';
            } catch {
                userId = '';
            }
        }
    }

    const headers = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(API_KEY ? { 'X-Api-Key': API_KEY } : {}),
        ...(userId ? { 'X-User-Id': userId } : {}),
        ...options.headers,
    };

    // Remove our custom property before passing to native fetch
    const fetchOptions = { ...options, headers };
    delete fetchOptions.userId;

    const res = await fetch(`${API_BASE}${path}`, fetchOptions);

    if (!res.ok) {
        let detail = `API error ${res.status}`;
        try {
            const body = await res.clone().json();
            detail = body?.detail ?? detail;
        } catch { /* response body was not JSON */ }
        throw new Error(detail);
    }

    return res;
}
