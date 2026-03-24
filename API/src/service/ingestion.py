import logging
import re
from typing import Any

import fitz  # PyMuPDF
import pymupdf4llm

from src.service.rag import rag_service

logger = logging.getLogger(__name__)


def _extract_markdown(pdf_bytes: bytes) -> str:
    """
    Extracts structured Markdown from PDF bytes using pymupdf4llm.
    """
    try:
        # PyMuPDF can open from memory
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # Extract markdown string
        md_text = pymupdf4llm.to_markdown(doc)
        return str(md_text)
    except Exception as e:
        logger.error(f"[ingestion] Failed to extract text from PDF: {e}")
        raise


def _segment_into_sections(md_text: str) -> list[dict[str, str]]:
    """
    Splits the markdown text into logical sections based on common academic headers.
    Target sections: abstract, introduction, related work, methodology, results, discussion, conclusion.
    """
    # Define a regex to find Markdown headers (e.g., # Introduction, ## 1. Related Work)
    # We look for lines starting with 1 to 3 '#' characters.
    header_pattern = re.compile(r"^(#{1,3})\s+(.*)", re.MULTILINE)
    
    # We want to normalize the headers to broad categories.
    # Order matters: more specific/longer terms should come first.
    target_categories = [
        "methodology", "method", "results", "result",
        "background", "related work", "introduction",
        "abstract", "discussion", "conclusion", "references"
    ]
    
    sections = []
    current_section_name = "general"
    current_content = []
    
    lines = md_text.splitlines()
    for line in lines:
        match = header_pattern.match(line)
        if match:
            raw_header = match.group(2).strip().lower()
            # Try to map to a target category
            mapped_category = None
            for cat in target_categories:
                if cat in raw_header:
                    mapped_category = cat
                    break
            
            new_section_name = mapped_category if mapped_category else raw_header
            
            # Save the current section if it has content
            if current_content:
                sections.append({
                    "section": current_section_name,
                    "text": "\n".join(current_content).strip()
                })
            
            current_section_name = new_section_name
            current_content = [line]  # Keep the header in the text
        else:
            current_content.append(line)
            
    # Add the last section
    if current_content:
        sections.append({
            "section": current_section_name,
            "text": "\n".join(current_content).strip()
        })
        
    return sections


async def ingest_pdf(uid: str, project_id: str, doi: str, pdf_bytes: bytes, base_metadata: dict[str, Any] | None = None) -> int:
    """
    Full ingestion pipeline for a downloaded PDF.
    Step 4: Text Extraction
    Step 5: Section Segmentation
    Step 6 & 7: Embedding and Vector Storage (via RagService)
    """
    logger.info(f"[ingestion] Starting ingestion for project={project_id}, doi={doi}")
    
    # Step 4: Text Extraction
    md_text = _extract_markdown(pdf_bytes)
    
    # Step 5: Section Segmentation
    sections = _segment_into_sections(md_text)
    logger.info(f"[ingestion] Segmented into {len(sections)} sections")
    
    base_metadata = base_metadata or {}
    base_metadata["doi"] = doi
    
    total_chunks_stored = 0
    
    # Step 6 & 7: Embed and Store
    for sec in sections:
        # We augment the metadata with the section name
        sec_metadata = base_metadata.copy()
        sec_metadata["section"] = sec["section"]
        
        # Ingest this specific section. The RAG service will chunk it further if needed.
        response = await rag_service.ingest(
            uid=uid,
            project_id=project_id,
            text=sec["text"],
            metadata=sec_metadata
        )
        total_chunks_stored += response.chunks_stored

    logger.info(f"[ingestion] Successfully ingested {total_chunks_stored} chunks for doi={doi}")
    return total_chunks_stored
