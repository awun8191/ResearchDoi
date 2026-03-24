/**
 * PDF Resolver Service (API-backed)
 *
 * This module is now a thin client over the FastAPI /api/pdf/resolve endpoint.
 * - All 4-tier cascading resolution (Unpaywall, Semantic Scholar, OpenAlex,
 *   heuristics, CrossRef links) runs server-side.
 * - Personal email addresses are no longer exposed in the browser.
 * - No direct third-party API calls from the browser.
 *
 * @module services/pdfResolver
 */

import { apiFetch } from './api.js';

/**
 * Attempt to resolve a PDF URL for the given DOI.
 *
 * @param {string} doi - Cleaned DOI string (with or without URL prefix).
 * @returns {Promise<{
 *   pdfUrl:       string | null,
 *   isOpenAccess: boolean,
 *   oaStatus:     string | null,
 *   resolvedVia:  string,
 * }>}
 */
export async function resolvePdfUrl(doi) {
    const res = await apiFetch(`/api/pdf/resolve?doi=${encodeURIComponent(doi)}`);
    const data = await res.json();

    // Normalise snake_case API response to camelCase for frontend compatibility
    return {
        pdfUrl: data.pdf_url ?? null,
        isOpenAccess: data.is_open_access ?? false,
        oaStatus: data.oa_status ?? null,
        resolvedVia: data.resolved_via ?? 'none',
    };
}
