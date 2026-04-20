# Design Spec: The Scholar's Console

**Date:** 2026-04-16  
**Status:** Draft  
**Aesthetic:** Technical Void + Modern Academic  

## 1. Vision & Strategy
The goal is to refine ResearchDoi into "The Scholar's Console"—a high-performance, technical workspace for researchers. It blends the existing "Technical Void" (dark, noise-textured, glowing) with "Modern Academic" (high-legibility typography, structured bento layouts).

## 2. Visual System
### 2.1 Color Palette (Extensions)
- **Base:** Keep existing `--bg-body` (#09090b) and `--bg-sidebar` (#050a1a).
- **Accents:** Use `--secondary` (#3b82f6) for primary actions and glowing borders.
- **Surface:** Glassmorphic cards using `--glass-bg` and `--glass-border`.

### 2.2 Typography
- **Interface/Headers:** `Geist` (Modern, technical).
- **Metadata/Identifiers:** `JetBrains Mono` (Technical precision for DOIs/stats).
- **Reading/Abstracts:** `Atkinson Hyperlegible` (Scholarly accessibility).

## 3. Key Components
### 3.1 Home Page (The Hero)
- **Search Hero:** Centered, wide input with a `--secondary-glow` border.
- **Focus State:** Intense glow effect using `pulse-glow` animation.
- **Quick Actions:** Minimal triggers for "Paste DOI" and "Upload PDF" below the bar.

### 3.2 Search Results (The Grid)
- **Layout:** Bento-style grid (`.bento-grid`).
- **Cards:** `.bento-item` with glassmorphism.
- **Metadata:** 
  - DOI in Mono font.
  - Citation count badge with subtle glow.
  - Abstract snippet in Atkinson font.
- **Actions:** "Resolve PDF" and "Add to Project" buttons directly on cards.

### 3.3 Workspace (The Deep Dive)
- **Navigation:** Vertical technical sidebar with glowing active indicators.
- **Side Panel:** `slidePanelIn` animation for paper details and abstract deep-dives.
- **Project View:** Multi-column layout for managing saved research.

## 4. Interaction & Motion
- **Boot Sequence:** `stagger-in` animation for home page elements.
- **Transitions:** 250ms cubic-bezier for all glass/glow states.
- **Mobile:** Collapsed single-column grid; `MobileBottomNav` for primary actions.

## 5. Technical Constraints (Logic Alignment)
- No "Trending Topics" (unsupported by current logic).
- Direct integration with `crossref.js`, `pdfResolver.js`, and `projectService.js`.
- Respects existing `AuthContext` and `ThemeContext`.
