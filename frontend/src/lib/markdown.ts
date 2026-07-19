/**
 * Client-side markdown parser for strategy.md `##` headers.
 *
 * Parses raw markdown body from the API response (content field)
 * into structured sections with title, bullets, and priority.
 */

export interface ParsedSection {
  /** Full header text e.g. "ШАГ 1: Терапевт (Получение направлений)" */
  header: string;
  /** Section key: "ЕЖЕДНЕВНО" | "ШАГ 1" | "ШАГ 2" etc. */
  sectionKey: string;
  /** Title after colon in header, e.g. "Терапевт (Получение направлений)" */
  title: string | null;
  /** Step number extracted from "ШАГ X" (1-based), null for non-step headers */
  stepNumber: number | null;
  /** Bullet items under this section (trimmed, without leading `* -`) */
  bullets: string[];
}

/**
 * Parse raw markdown content into sections based on `## ` headers.
 *
 * Sections before the first `## ` are ignored (preamble).
 * Each `## HEADER` starts a new section, bullet lines are collected.
 */
export function parseStrategyMarkdown(content: string): ParsedSection[] {
  const lines = content.split("\n");
  const sections: ParsedSection[] = [];
  let current: ParsedSection | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    // Detect ## header
    if (line.startsWith("## ")) {
      // Save previous section
      if (current) {
        sections.push(current);
      }

      const header = line.slice(3).trim();
      current = parseHeader(header);
      continue;
    }

    // Collect bullets under current section
    if (current) {
      const bullet = extractBullet(line);
      if (bullet) {
        current.bullets.push(bullet);
      }
    }
  }

  // Save last section
  if (current) {
    sections.push(current);
  }

  return sections;
}

function parseHeader(header: string): ParsedSection {
  // Check if it's a step header: "ШАГ 1: ..." or "ШАГ 2: ..."
  const stepMatch = header.match(/^ШАГ\s+(\d+)(?::\s*(.*))?$/i);
  if (stepMatch) {
    const stepNumber = parseInt(stepMatch[1]!, 10);
    const title = stepMatch[2]?.trim() || null;
    return {
      header,
      sectionKey: `ШАГ ${stepNumber}`,
      title,
      stepNumber,
      bullets: [],
    };
  }

  // Generic section (e.g. "ЕЖЕДНЕВНО", "ДО СТРАХОВКИ", etc.)
  return {
    header,
    sectionKey: header.trim().toUpperCase(),
    title: header.trim(),
    stepNumber: null,
    bullets: [],
  };
}

function extractBullet(line: string): string | null {
  const trimmed = line.trim();
  if (!trimmed) return null;

  // Match bullet formats: "* text", "- text", "* text", "  * text"
  const match = trimmed.match(/^\s*[*•\-–—]\s+(.+)/);
  if (match) {
    // Clean up inline formatting markers
    return match[1]!.trim();
  }

  return null;
}

/**
 * Check if a section is the daily routine block.
 */
export function isDailySection(section: ParsedSection): boolean {
  return section.sectionKey === "ЕЖЕДНЕВНО";
}

/**
 * Check if a section is a numbered step (ШАГ X).
 */
export function isStepSection(section: ParsedSection): boolean {
  return section.stepNumber !== null;
}
