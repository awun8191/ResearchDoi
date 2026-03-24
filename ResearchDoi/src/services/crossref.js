/**
 * CrossRef Article Metadata Service
 *
 * Fetches article metadata from the backend API which proxies CrossRef.
 * This avoids CORS issues from calling CrossRef directly from the browser.
 *
 * @module crossref
 */

import { apiFetch } from './api.js';
import { resolvePdfUrl } from "./pdfResolver.js";

/**
 * Cleans a DOI string: strips URL prefixes, trims whitespace.
 * @param {string} doi
 * @returns {string}
 */
function cleanDoi(doi) {
    return doi
        .replace(/^(https?:\/\/)?(dx\.)?doi\.org\//i, "")
        .replace(/^doi:/i, "")
        .replace(/^info:doi\//i, "")
        .trim();
}

/**
 * Fetches article metadata from the backend DOI endpoint (which proxies CrossRef).
 * @param {string} doi - Cleaned DOI
 * @returns {Promise<Object>} DOI metadata from backend
 */
async function fetchCrossRefData(doi) {
    const res = await apiFetch(`/api/doi/${encodeURIComponent(doi)}`);
    return res.json();
}

/**
 * Parses backend DOI response into a clean Article object.
 * @param {Object} data - Backend DOI response object
 * @param {import('./pdfResolver.js').PdfResolution} pdfData
 * @returns {Article}
 */
function parseArticle(data, pdfData) {
    const date = data.publication_year ? String(data.publication_year) : "Unknown Date";

    const authors = data.authors?.map((name) => {
        const parts = name.split(" ");
        return {
            given: parts.slice(0, -1).join(" "),
            family: parts.length > 0 ? parts[parts.length - 1] : "",
        };
    }) || [];

    const journal = data.venue || "Unknown Journal";

    return {
        title: data.title || "Untitled Article",
        authors,
        journal,
        date,
        doi: data.doi,
        url: data.url,
        abstract: null,
        type: "article",
        pdfUrl: pdfData.pdfUrl,
        isOpenAccess: pdfData.isOpenAccess,
        oaStatus: pdfData.oaStatus,
        resolvedVia: pdfData.resolvedVia,
    };
}

/**
 * Fetches article metadata from CrossRef and resolves a PDF URL
 * through the backend's cascading 4-tier resolver.
 *
 * Flow:
 *   1. Fetch CrossRef metadata
 *   2. Delegate PDF resolution to POST /api/pdf/resolve (server-side: Unpaywall → S2 → OpenAlex → heuristics)
 *
 * @param {string} doi - The DOI to look up
 * @returns {Promise<Article>}
 */
export async function fetchArticle(doi) {
    const cleaned = cleanDoi(doi);
    if (!cleaned) {
        throw new Error("Please enter a valid DOI");
    }

    try {
        // CrossRef metadata + backend PDF resolution in parallel
        const [crossrefData, pdfData] = await Promise.all([
            fetchCrossRefData(cleaned),
            resolvePdfUrl(cleaned),
        ]);

        return parseArticle(crossrefData, pdfData);
    } catch (error) {
        console.error("Article Fetch Error:", error);
        throw error;
    }
}
