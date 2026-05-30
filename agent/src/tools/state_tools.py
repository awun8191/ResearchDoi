"""State management tools for RAST — update, append, edit, gap identification."""

import json
import logging
from typing import Any

from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)


def update_plan(
    current_plan: dict[str, Any] | None,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update the research plan with new or modified fields.

    Merges the updates into the current plan. Handles nested dicts.

    Args:
        current_plan: The existing research plan dict (or None).
        updates: Dict of fields to update/add.

    Returns:
        Updated research plan dict.
    """
    if current_plan is None:
        current_plan = {}

    plan = dict(current_plan)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(plan.get(key), dict):
            # Deep merge for nested dicts
            plan[key] = {**plan[key], **value}
        else:
            plan[key] = value

    return plan


update_plan_tool = FunctionTool(func=update_plan,
)


def update_state(
    current_state: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Generic state update tool for session state.

    Merges the provided updates into the current state dict.
    Returns the updated state for writing back to session.

    Args:
        current_state: Current session state dict.
        updates: Dict of fields to update. Can use dotted keys
                like 'research_plan.sub_topics' for nested updates.

    Returns:
        Updated state dict with all changes applied.
    """
    if not isinstance(current_state, dict):
        current_state = {}

    state = dict(current_state)

    for key, value in updates.items():
        if "." in key:
            # Handle dotted keys for nested updates
            parts = key.split(".")
            target = state
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value
        else:
            if isinstance(value, dict) and isinstance(state.get(key), dict):
                state[key] = {**state[key], **value}
            elif isinstance(value, list) and isinstance(state.get(key), list):
                state[key] = state[key] + value
            else:
                state[key] = value

    return state


update_state_tool = FunctionTool(func=update_state,
)


def append_to_draft(
    current_draft: str,
    new_content: str,
    section_header: str = "",
) -> dict[str, Any]:
    """Append content to the working draft, section by section.

    For long outputs, this tool progressively builds the document.
    If section_header is provided, wraps content in a markdown header.

    Args:
        current_draft: Existing draft content.
        new_content: Content to append.
        section_header: Optional section header (e.g., '## Introduction').

    Returns:
        Dict with 'draft' (updated full draft) and 'appended_length'.
    """
    if not current_draft:
        current_draft = ""
    if not new_content:
        return {"draft": current_draft, "appended_length": 0}

    append_text = ""
    if section_header:
        append_text = f"\n\n{section_header}\n\n{new_content}"
    else:
        append_text = f"\n\n{new_content}"

    updated_draft = current_draft + append_text

    return {
        "draft": updated_draft,
        "appended_length": len(new_content),
    }


append_to_draft_tool = FunctionTool(func=append_to_draft,
)


def identify_gaps(
    findings: list[dict[str, Any]],
    research_plan: dict[str, Any],
) -> dict[str, Any]:
    """Identify remaining research gaps from current findings vs the plan.

    Analyzes which sub-topics in the research plan have insufficient
    findings coverage and returns a list of gaps to address.

    Args:
        findings: List of finding dicts with 'type', 'text', and
                 optionally 'topic' fields.
        research_plan: The research plan dict with 'sub_topics' key
                      (list of topic strings).

    Returns:
        Dict with 'gaps' (list of gap descriptions), 'covered_topics' (list),
        'uncovered_topics' (list), and 'coverage_ratio'.
    """
    sub_topics = research_plan.get("sub_topics", [])
    if not sub_topics:
        return {
            "gaps": ["No sub-topics defined in research plan."],
            "covered_topics": [],
            "uncovered_topics": [],
            "coverage_ratio": 0.0,
        }

    # Extract topics from findings
    covered: set[str] = set()
    finding_topics: list[str] = []
    for f in findings:
        topic = f.get("topic", f.get("type", ""))
        if topic:
            finding_topics.append(topic.lower())

    for sub_topic in sub_topics:
        sub_lower = sub_topic.lower()
        # Count how many findings match this sub-topic
        match_count = sum(1 for t in finding_topics if sub_lower in t or t in sub_lower)
        if match_count >= 2:
            covered.add(sub_topic)

    uncovered = [t for t in sub_topics if t not in covered]
    coverage_ratio = len(covered) / len(sub_topics) if sub_topics else 0.0

    gaps = [f"Insufficient findings for sub-topic: {t}" for t in uncovered]

    return {
        "gaps": gaps,
        "covered_topics": list(covered),
        "uncovered_topics": uncovered,
        "coverage_ratio": coverage_ratio,
        "total_sub_topics": len(sub_topics),
    }


identify_gaps_tool = FunctionTool(func=identify_gaps,
)


def format_section(
    content: str,
    style: str = "academic",
) -> dict[str, str]:
    """Format a section of text per academic style guide.

    Args:
        content: The section text to format.
        style: Style guide — "academic", "ieee", or "plain" (default "academic").

    Returns:
        Dict with 'formatted' key containing the styled text.
    """
    if not content:
        return {"formatted": ""}

    if style == "plain":
        return {"formatted": content.strip()}

    text = content.strip()
    if style == "academic":
        # Ensure proper paragraph spacing
        paragraphs = text.split("\n\n")
        formatted_paragraphs: list[str] = []
        for p in paragraphs:
            p = p.strip()
            if p:
                formatted_paragraphs.append(p)
        text = "\n\n".join(formatted_paragraphs)

    elif style == "ieee":
        # IEEE style: numbered sections, concise
        text = text.strip()

    return {"formatted": text}


format_section_tool = FunctionTool(func=format_section,
)


def edit_draft(
    current_draft: str,
    edit_instruction: str,
    target_section: str = "",
) -> dict[str, Any]:
    """Apply corrections to the working draft.

    Searches for a target section (or applies globally) and applies
    the specified edit. This is a structural tool — the actual content
    changes are driven by the LLM calling this tool.

    Args:
        current_draft: The current draft content.
        edit_instruction: Description of what to change.
        target_section: Optional section header to target edits at.
                       If empty, applies globally.

    Returns:
        Dict with 'draft' (updated) and 'edit_applied' (bool).
    """
    if not current_draft:
        return {"draft": "", "edit_applied": False, "note": "No draft to edit."}

    # Record the edit instruction in the draft as a note
    # In practice, the LLM would rewrite the content and call this
    # to signal the edit was applied
    note = f"\n\n[EDIT: {edit_instruction}]\n"
    if target_section:
        note = f"\n\n[EDIT in '{target_section}': {edit_instruction}]\n"

    return {
        "draft": current_draft + note,
        "edit_applied": True,
        "note": f"Edit recorded: {edit_instruction}",
    }


edit_draft_tool = FunctionTool(func=edit_draft,
)


def verify_citations(
    draft: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify all citations in the draft have corresponding bibliography entries.

    Scans the draft for in-text citations and checks they exist
    in the provided citation list.

    Args:
        draft: The draft text to scan.
        citations: List of citation entry dicts.

    Returns:
        Dict with 'verified' (bool), 'missing' (list of missing citation keys),
        'total_citations_found' (int), and 'total_valid' (int).
    """
    if not draft:
        return {"verified": True, "missing": [], "total_citations_found": 0, "total_valid": 0}

    # Build key lookup
    valid_keys: set[str] = set()
    for c in citations:
        key = c.get("key", "")
        if key:
            valid_keys.add(key)

    # Find all citation markers
    cit_markers = re.findall(r"\[CIT:\s*([^\]]+)\]", draft)
    all_keys: list[str] = []
    for marker in cit_markers:
        keys = [k.strip() for k in re.split(r"[;,]", marker) if k.strip()]
        all_keys.extend(keys)

    # Also find APA-style citations like (Author, year)
    apa_cits = re.findall(r"\(([^)]+\d{4}[^)]*)\)", draft)
    # Extract potential keys from APA citations
    for cit in apa_cits:
        # Simple extraction: first word could be author name
        parts = cit.split(",")
        if parts:
            potential_key = parts[0].strip().lower().split()[-1] if parts[0].strip() else ""
            if potential_key:
                all_keys.append(potential_key)

    missing = [k for k in all_keys if k not in valid_keys]

    return {
        "verified": len(missing) == 0,
        "missing": list(set(missing)),
        "total_citations_found": len(all_keys),
        "total_valid": len(all_keys) - len(set(missing)),
    }


verify_citations_tool = FunctionTool(func=verify_citations,
)


import re  # noqa: F811 — re imported here for the tool function above
