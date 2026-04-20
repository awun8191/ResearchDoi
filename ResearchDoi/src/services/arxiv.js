/**
 * ArXiv Article Metadata Service
 *
 * Fetches article metadata from the backend API which proxies ArXiv API.
 * This avoids CORS issues and extracts direct PDF links.
 *
 * @module arxiv
 */

import { apiFetch } from './api.js';
import { resolvePdfUrl } from "./pdfResolver.js";

/**
 * Fetches article metadata from the backend identifier endpoint (which proxies ArXiv).
 * @param {string} identifier - Search query, ArXiv ID, or DOI
 * @returns {Promise<Object>} Metadata from backend
 */
async function fetchArxivData(identifier) {
    const res = await apiFetch(`/api/doi/${encodeURIComponent(identifier)}`);
    return res.json();
}

/**
 * Performs a keyword search on ArXiv via the backend.
 * @param {string} query - Keyword search query
 * @param {number} limit - Max results
 * @returns {Promise<Article[]>}
 */
export async function searchArticles(query, limit = 10) {
    const res = await apiFetch(`/api/doi/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    const data = await res.json();
    return (data.results || []).map(item => parseArticle(item));
}

/**
 * Parses backend ArXiv response into a clean Article object.
 * @param {Object} data - Backend ArXiv response object
 * @param {import('./pdfResolver.js').PdfResolution} pdfData - Optional resolution data
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

    const journal = data.venue || "ArXiv Preprint";

    // Rely primarily on ArXiv's direct PDF, otherwise use fallback resolver
    const finalPdfUrl = data.pdf_url || (pdfData ? pdfData.pdfUrl : null);
    
    // If we have an ArXiv PDF directly, we assume it's open access
    const isOpenAccess = !!data.pdf_url || (pdfData ? pdfData.isOpenAccess : false);

    return {
        title: data.title || "Untitled Article",
        authors,
        journal,
        date,
        doi: data.doi, // Can be identifier, original query or actual doi
        url: data.url,
        abstract: data.abstract || null,
        type: "article",
        pdfUrl: finalPdfUrl,
        isOpenAccess: isOpenAccess,
        oaStatus: data.pdf_url ? "gold" : (pdfData ? pdfData.oaStatus : null),
        resolvedVia: data.pdf_url ? "arxiv" : (pdfData ? pdfData.resolvedVia : "none"),
    };
}

/**
 * Fetches article metadata from ArXiv. If ArXiv does not provide a direct 
 * PDF link, safely falls back to backend heuristic resolver.
 *
 * @param {string} identifier - The ArXiv ID, DOI, or keyword to look up
 * @returns {Promise<Article>}
 */
export async function fetchArticle(identifier) {
    if (!identifier || !identifier.trim()) {
        throw new Error("Please enter a valid identifier or keyword");
    }

    try {
        const metadata = await fetchArxivData(identifier);
        
        let pdfData = null;
        // If ArXiv API doesn't provide a PDF directly, fallback to our regular resolver
        if (!metadata.pdf_url) {
             try {
                // If the returned identifier looks like a doi, we try resolving it
                 if (metadata.doi && metadata.doi.startsWith("10.")) {
                    pdfData = await resolvePdfUrl(metadata.doi);
                 }
             } catch (e) {
                 console.warn("PDF resolution fallback failed", e);
             }
        }

        return parseArticle(metadata, pdfData);
    } catch (error) {
        console.error("Article Fetch Error:", error);
        throw error;
    }
}
