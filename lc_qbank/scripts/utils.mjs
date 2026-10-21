/**
 * @fileoverview Shared utilities for the LeetCode question bank pipeline.
 * This is the CORE module used by all pipeline scripts.
 * @module utils
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------
dotenv.config();

// ---------------------------------------------------------------------------
// Path Constants
// ---------------------------------------------------------------------------

/** Absolute path to the project root directory. */
export const PROJECT_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..'
);

/** LeetCode GraphQL API endpoint. */
export const LEETCODE_GRAPHQL =
  process.env.LEETCODE_API_URL || 'https://leetcode.com/graphql';

/** Directory where normalised question JSON files are stored. */
export const QUESTIONS_DIR = path.join(
  PROJECT_ROOT,
  process.env.QUESTIONS_DIR || 'questions'
);

/** Directory for manifest / state files. */
export const MANIFESTS_DIR = path.join(
  PROJECT_ROOT,
  process.env.MANIFESTS_DIR || 'manifests'
);

/** Directory for pipeline reports. */
export const REPORTS_DIR = path.join(
  PROJECT_ROOT,
  process.env.REPORTS_DIR || 'reports'
);

/** Directory for JSON schemas. */
export const SCHEMAS_DIR = path.join(
  PROJECT_ROOT,
  process.env.SCHEMAS_DIR || 'schemas'
);

/** Path to the collection state file that tracks pipeline progress. */
export const STATE_FILE = path.join(MANIFESTS_DIR, 'collection-state.json');

/** Batch size for API collection requests. */
export const BATCH_SIZE = Number(process.env.COLLECTION_BATCH_SIZE) || 50;

/** Delay (ms) between API batches to avoid rate-limiting. */
export const DELAY_MS = Number(process.env.COLLECTION_DELAY_MS) || 1500;

/** Maximum retry count for failed API requests. */
export const MAX_RETRIES = Number(process.env.COLLECTION_MAX_RETRIES) || 3;

// ---------------------------------------------------------------------------
// Tag → Category / Subcategory Mapping
// ---------------------------------------------------------------------------

/**
 * Maps LeetCode topic-tag slugs to `{ category, subcategory }`.
 * When a question has multiple matching tags the `SUBCATEGORY_PRIORITY` array
 * determines which subcategory wins (most-specific first).
 *
 * @type {Record<string, { category: string, subcategory: string }>}
 */
export const TAG_TO_CATEGORY = {
  // ── Arrays & Strings ────────────────────────────────────────────────
  'array':                  { category: 'dsa', subcategory: 'arrays' },
  'matrix':                 { category: 'dsa', subcategory: 'arrays' },
  'string':                 { category: 'dsa', subcategory: 'strings' },
  'string-matching':        { category: 'dsa', subcategory: 'strings' },

  // ── Hashing ─────────────────────────────────────────────────────────
  'hash-table':             { category: 'dsa', subcategory: 'hashing' },

  // ── Two Pointers ────────────────────────────────────────────────────
  'two-pointers':           { category: 'dsa', subcategory: 'two-pointers' },

  // ── Sliding Window ──────────────────────────────────────────────────
  'sliding-window':         { category: 'dsa', subcategory: 'sliding-window' },

  // ── Binary Search ───────────────────────────────────────────────────
  'binary-search':          { category: 'dsa', subcategory: 'binary-search' },

  // ── Linked Lists ────────────────────────────────────────────────────
  'linked-list':            { category: 'dsa', subcategory: 'linked-lists' },

  // ── Stacks & Queues ─────────────────────────────────────────────────
  'stack':                  { category: 'dsa', subcategory: 'stacks-queues' },
  'queue':                  { category: 'dsa', subcategory: 'stacks-queues' },
  'monotonic-stack':        { category: 'dsa', subcategory: 'stacks-queues' },
  'monotonic-queue':        { category: 'dsa', subcategory: 'stacks-queues' },

  // ── Trees ───────────────────────────────────────────────────────────
  'tree':                   { category: 'dsa', subcategory: 'trees' },
  'binary-tree':            { category: 'dsa', subcategory: 'trees' },
  'binary-search-tree':     { category: 'dsa', subcategory: 'trees' },

  // ── Heaps ───────────────────────────────────────────────────────────
  'heap-priority-queue':    { category: 'dsa', subcategory: 'heaps' },

  // ── Graphs ──────────────────────────────────────────────────────────
  'graph':                  { category: 'dsa', subcategory: 'graphs' },
  'breadth-first-search':   { category: 'dsa', subcategory: 'graphs' },
  'depth-first-search':     { category: 'dsa', subcategory: 'graphs' },
  'shortest-path':          { category: 'dsa', subcategory: 'graphs' },
  'topological-sort':       { category: 'dsa', subcategory: 'graphs' },
  'minimum-spanning-tree':  { category: 'dsa', subcategory: 'graphs' },
  'union-find':             { category: 'dsa', subcategory: 'graphs' },

  // ── Recursion & Backtracking ────────────────────────────────────────
  'recursion':              { category: 'dsa', subcategory: 'recursion-backtracking' },
  'backtracking':           { category: 'dsa', subcategory: 'recursion-backtracking' },

  // ── Greedy ──────────────────────────────────────────────────────────
  'greedy':                 { category: 'dsa', subcategory: 'greedy' },

  // ── Dynamic Programming ─────────────────────────────────────────────
  'dynamic-programming':    { category: 'dsa', subcategory: 'dynamic-programming' },
  'memoization':            { category: 'dsa', subcategory: 'dynamic-programming' },

  // ── Tries ───────────────────────────────────────────────────────────
  'trie':                   { category: 'dsa', subcategory: 'tries' },

  // ── Bit Manipulation ────────────────────────────────────────────────
  'bit-manipulation':       { category: 'dsa', subcategory: 'bit-manipulation' },

  // ── Mathematics ─────────────────────────────────────────────────────
  'math':                   { category: 'dsa', subcategory: 'mathematics' },
  'number-theory':          { category: 'dsa', subcategory: 'mathematics' },
  'combinatorics':          { category: 'dsa', subcategory: 'mathematics' },
  'geometry':               { category: 'dsa', subcategory: 'mathematics' },
  'counting':               { category: 'dsa', subcategory: 'mathematics' },

  // ── Sorting ─────────────────────────────────────────────────────────
  'sorting':                { category: 'dsa', subcategory: 'sorting' },
  'merge-sort':             { category: 'dsa', subcategory: 'sorting' },
  'counting-sort':          { category: 'dsa', subcategory: 'sorting' },
  'radix-sort':             { category: 'dsa', subcategory: 'sorting' },
  'bucket-sort':            { category: 'dsa', subcategory: 'sorting' },

  // ── Divide & Conquer ────────────────────────────────────────────────
  'divide-and-conquer':     { category: 'dsa', subcategory: 'divide-and-conquer' },

  // ── Advanced Data Structures ────────────────────────────────────────
  'segment-tree':           { category: 'dsa', subcategory: 'advanced-data-structures' },
  'binary-indexed-tree':    { category: 'dsa', subcategory: 'advanced-data-structures' },
  'ordered-set':            { category: 'dsa', subcategory: 'advanced-data-structures' },

  // ── Design ──────────────────────────────────────────────────────────
  'design':                 { category: 'dsa', subcategory: 'design' },

  // ── Simulation / Enumeration ────────────────────────────────────────
  'simulation':             { category: 'dsa', subcategory: 'simulation' },
  'enumeration':            { category: 'dsa', subcategory: 'simulation' },

  // ── Prefix Sum ──────────────────────────────────────────────────────
  'prefix-sum':             { category: 'dsa', subcategory: 'prefix-sum' },

  // ── Database ────────────────────────────────────────────────────────
  'database':               { category: 'database', subcategory: 'select-filtering' },
};

/**
 * Priority order for subcategory selection.  When a question matches
 * multiple tags the **first** matching subcategory in this list wins.
 * More-specific algorithmic topics appear before broad structural ones.
 *
 * @type {string[]}
 */
export const SUBCATEGORY_PRIORITY = [
  'dynamic-programming',
  'greedy',
  'graphs',
  'trees',
  'tries',
  'heaps',
  'recursion-backtracking',
  'divide-and-conquer',
  'sliding-window',
  'two-pointers',
  'binary-search',
  'stacks-queues',
  'linked-lists',
  'bit-manipulation',
  'advanced-data-structures',
  'prefix-sum',
  'sorting',
  'hashing',
  'design',
  'simulation',
  'mathematics',
  'strings',
  'arrays',
];

// ---------------------------------------------------------------------------
// Database Subcategory Inference
// ---------------------------------------------------------------------------

/**
 * Infers a database subcategory from the SQL content and question title.
 *
 * @param {string} content - The problem statement / SQL body (Markdown or HTML).
 * @param {string} title   - The question title.
 * @returns {string} The inferred database subcategory slug.
 */
export function inferDatabaseSubcategory(content = '', title = '') {
  const text = `${title} ${content}`.toUpperCase();

  // Order matters – check more-specific patterns first.
  if (/\b(RANK|ROW_NUMBER|DENSE_RANK)\b/.test(text) ||
      /\bOVER\s*\(/.test(text) ||
      /\bPARTITION\s+BY\b/.test(text)) {
    return 'window-functions';
  }

  if (/\bWITH\s+\w+\s+AS\b/.test(text) || /\bCTE\b/.test(text)) {
    return 'cte';
  }

  if (/\b(UNION|INTERSECT|EXCEPT)\b/.test(text)) {
    return 'set-operations';
  }

  if (/\bJOIN\b/.test(text) || /\bCOMBINE\s+TWO\s+TABLES\b/.test(text) || /\bTWO\s+TABLES\b/.test(text)) {
    return 'joins';
  }

  if (/\b(GROUP\s+BY|HAVING|COUNT\s*\(|SUM\s*\(|AVG\s*\(|MIN\s*\(|MAX\s*\()/.test(text) ||
      /\b(HIGHEST|LOWEST)\s+SALARY\b/.test(text)) {
    return 'aggregation';
  }

  if (/\(\s*SELECT\b/.test(text) || /\bSUBQUER/.test(text) || /\b(SECOND|NTH)\s+HIGHEST\b/.test(text)) {
    return 'subqueries';
  }

  if (/\b(DATEDIFF|TIMESTAMPDIFF|DATE_ADD|DATE_SUB|DATE_FORMAT)\b/.test(text) ||
      /\bDATE\s*\(/.test(text)) {
    return 'date-time';
  }

  if (/\b(CONCAT|SUBSTRING|REGEXP|LIKE)\b/.test(text)) {
    return 'string-functions';
  }

  if (/\b(IFNULL|COALESCE|IS\s+NULL|IS\s+NOT\s+NULL|ISNULL)\b/.test(text)) {
    return 'null-handling';
  }

  return 'select-filtering';
}

// ---------------------------------------------------------------------------
// General Helpers
// ---------------------------------------------------------------------------

/**
 * Converts arbitrary text into a URL-safe slug.
 *
 * @param {string} text - The text to slugify.
 * @returns {string} A lowercase, hyphen-separated slug.
 *
 * @example
 * slugify('Two Sum')          // 'two-sum'
 * slugify('3Sum Closest!!!')  // '3sum-closest'
 */
export function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Robustly decodes all HTML entities into their plain text / JSON equivalents.
 *
 * @param {string} text - The input string containing HTML entities.
 * @returns {string} The decoded string.
 */
export function unescapeHtml(text) {
  if (!text || typeof text !== 'string') return text;
  return text
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&#40;/g, '(')
    .replace(/&#41;/g, ')')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;/g, ' ')
    .replace(/&minus;/g, '-')
    .replace(/&times;/g, '×')
    .replace(/&divide;/g, '÷')
    .replace(/&plusmn;/g, '±')
    .replace(/&le;/g, '<=')
    .replace(/&ge;/g, '>=')
    .replace(/&ne;/g, '!=')
    .replace(/&asymp;/g, '≈')
    .replace(/&rarr;/g, '→')
    .replace(/&larr;/g, '←')
    .replace(/&uarr;/g, '↑')
    .replace(/&darr;/g, '↓')
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&rsquo;/g, '’')
    .replace(/&lsquo;/g, '‘')
    .replace(/&rdquo;/g, '”')
    .replace(/&ldquo;/g, '“')
    .replace(/&oplus;/g, '⊕')
    .replace(/&empty;/g, '∅')
    .replace(/&lfloor;/g, '⌊')
    .replace(/&rfloor;/g, '⌋')
    .replace(/&lceil;/g, '⌈')
    .replace(/&rceil;/g, '⌉')
    .replace(/&frasl;/g, '/')
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, code) => String.fromCharCode(parseInt(code, 16)));
}

/**
 * Returns a promise that resolves after `ms` milliseconds.
 *
 * @param {number} ms - Milliseconds to sleep.
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Recursively creates a directory if it does not already exist.
 *
 * @param {string} dirPath - Absolute or relative directory path.
 */
export function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

// ---------------------------------------------------------------------------
// GraphQL Fetcher
// ---------------------------------------------------------------------------

/**
 * Sends a GraphQL request to the LeetCode API with exponential-backoff
 * retry logic.
 *
 * @param {string}  query     - The GraphQL query string.
 * @param {object}  variables - Variables to pass with the query.
 * @param {number}  [retries] - Maximum number of retries (default from env).
 * @returns {Promise<object>} The parsed `data` property of the response.
 * @throws {Error} After all retries are exhausted.
 */
export async function fetchGraphQL(query, variables = {}, retries = MAX_RETRIES) {
  let lastError;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(LEETCODE_GRAPHQL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'leetcode-question-bank/1.0',
        },
        body: JSON.stringify({ query, variables }),
      });

      if (res.status === 429) {
        const wait = Math.pow(2, attempt) * 1000;
        console.warn(`⏳ Rate-limited (429). Retrying in ${wait}ms…`);
        await sleep(wait);
        continue;
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const json = await res.json();

      if (json.errors) {
        throw new Error(`GraphQL errors: ${JSON.stringify(json.errors)}`);
      }

      return json.data;
    } catch (err) {
      lastError = err;
      if (attempt < retries) {
        const wait = Math.pow(2, attempt) * 1000;
        console.warn(
          `⚠️  Attempt ${attempt + 1}/${retries + 1} failed: ${err.message}. Retrying in ${wait}ms…`
        );
        await sleep(wait);
      }
    }
  }

  throw new Error(
    `fetchGraphQL failed after ${retries + 1} attempts: ${lastError?.message}`
  );
}

// ---------------------------------------------------------------------------
// State Persistence
// ---------------------------------------------------------------------------

/**
 * @typedef {object} CollectionState
 * @property {Array<object>} discovered - Questions found during discovery.
 * @property {string[]}      pending    - Slugs still awaiting collection.
 * @property {string[]}      completed  - Slugs successfully collected.
 * @property {Array<object>} failed     - Slugs that failed collection.
 * @property {string|null}   lastUpdated - ISO 8601 timestamp of last update.
 */

/**
 * Loads the persisted collection state from disk.
 * Returns a default empty state if the file does not exist.
 *
 * @returns {CollectionState}
 */
export function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const raw = fs.readFileSync(STATE_FILE, 'utf-8');
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn(`⚠️  Could not load state file: ${err.message}`);
  }

  return {
    discovered: [],
    pending: [],
    completed: [],
    failed: [],
    lastUpdated: null,
  };
}

/**
 * Persists the collection state to disk.  Automatically sets `lastUpdated`.
 *
 * @param {CollectionState} state - The state object to save.
 */
export function saveState(state) {
  ensureDir(MANIFESTS_DIR);
  state.lastUpdated = new Date().toISOString();
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
}

// ---------------------------------------------------------------------------
// Category Resolution
// ---------------------------------------------------------------------------

/**
 * Determines the `{ category, subcategory }` for a question based on its
 * LeetCode tags, category title, and content.
 *
 * @param {Array<{ slug: string }>} topicTags     - LeetCode topic tags.
 * @param {string}                   categoryTitle - LeetCode category title
 *                                                   (e.g. "Algorithms", "Database").
 * @param {string}                   [content]     - Problem statement (used for
 *                                                   database subcategory inference).
 * @param {string}                   [title]       - Question title.
 * @returns {{ category: string, subcategory: string }}
 */
export function resolveCategory(topicTags = [], categoryTitle = '', content = '', title = '') {
  // ── Database questions ──────────────────────────────────────────────
  if (categoryTitle.toLowerCase() === 'database' ||
      topicTags.some((t) => (typeof t === 'string' ? slugify(t) === 'database' : t?.slug === 'database'))) {
    return {
      category: 'database',
      subcategory: inferDatabaseSubcategory(content, title),
    };
  }

  // ── DSA questions – pick the highest-priority matching subcategory ──
  const tagSlugs = topicTags.map((t) => {
    if (!t) return '';
    if (typeof t === 'string') return slugify(t);
    return t.slug || slugify(t.name || '');
  });

  // Collect all candidate subcategories from matching tags.
  /** @type {Set<string>} */
  const candidates = new Set();
  for (const slug of tagSlugs) {
    const mapping = TAG_TO_CATEGORY[slug];
    if (mapping) {
      candidates.add(mapping.subcategory);
    }
  }

  // Walk the priority list and return the first match.
  for (const sub of SUBCATEGORY_PRIORITY) {
    if (candidates.has(sub)) {
      return { category: 'dsa', subcategory: sub };
    }
  }

  // If we matched tags but none were in the priority list, take the first.
  if (candidates.size > 0) {
    return { category: 'dsa', subcategory: [...candidates][0] };
  }

  // No recognised tags at all.
  return { category: 'dsa', subcategory: 'miscellaneous' };
}

// ---------------------------------------------------------------------------
// File-Path Helpers
// ---------------------------------------------------------------------------

/**
 * Returns the absolute file path for a question JSON file.
 *
 * @param {string} category    - Top-level category (e.g. "dsa", "database").
 * @param {string} subcategory - Topic folder name (e.g. "arrays", "joins").
 * @param {string} slug        - URL-safe question slug.
 * @returns {string} Absolute path to `<QUESTIONS_DIR>/<category>/<subcategory>/<slug>.json`.
 */
export function getQuestionFilePath(category, subcategory, slug) {
  return path.join(QUESTIONS_DIR, category, subcategory, `${slug}.json`);
}
