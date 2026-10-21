#!/usr/bin/env node

/**
 * @fileoverview Normalization script – converts raw collected LeetCode data
 * into the project's final JSON schema.
 *
 * For each raw file in tmp/raw/, this script:
 *   1. Converts HTML content → Markdown (via turndown)
 *   2. Extracts constraints and examples from the content
 *   3. Resolves category/subcategory via shared utility
 *   4. Builds starter-code, stats, SQL, and test-case objects
 *   5. Writes the normalized JSON to questions/{cat}/{subcat}/{slug}.json
 *
 * Usage:
 *   node scripts/normalize.mjs [--force] [--slug <slug>]
 *
 * Flags:
 *   --force        Re-normalize all questions (even if output file exists).
 *   --slug <slug>  Normalize only the specified question.
 *
 * @module normalize
 */

import { readFile, readdir, writeFile, access } from 'node:fs/promises';
import { existsSync, writeFileSync } from 'node:fs';
import { join, basename, extname } from 'node:path';
import TurndownService from 'turndown';
import {
  PROJECT_ROOT,
  QUESTIONS_DIR,
  ensureDir,
  resolveCategory,
  getQuestionFilePath,
  unescapeHtml,
} from './utils.mjs';
import { generateTestCases } from './test-engine.mjs';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Directory containing raw API responses. */
const RAW_DIR = join(PROJECT_ROOT, 'tmp', 'raw');

// ---------------------------------------------------------------------------
// Turndown setup
// ---------------------------------------------------------------------------

const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
});

// Preserve <pre> blocks as fenced code blocks
turndown.addRule('pre', {
  filter: 'pre',
  replacement(content, node) {
    const code = node.querySelector('code');
    const lang = code?.getAttribute('class')?.replace('language-', '') ?? '';
    const text = code ? code.textContent : node.textContent;
    return `\n\`\`\`${lang}\n${text.trim()}\n\`\`\`\n`;
  },
});

// Inline <code> → backticks
turndown.addRule('code', {
  filter(node) {
    return node.nodeName === 'CODE' && !node.closest('pre');
  },
  replacement(content) {
    return `\`${content}\``;
  },
});

// <sup> → superscript notation
turndown.addRule('sup', {
  filter: 'sup',
  replacement(content) {
    return `^(${content})`;
  },
});

// <sub> → subscript notation
turndown.addRule('sub', {
  filter: 'sub',
  replacement(content) {
    return `_(${content})`;
  },
});

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

/**
 * Parses command-line flags.
 *
 * @returns {{ force: boolean, slug: string | null }}
 */
function parseArgs() {
  const args = process.argv.slice(2);
  let force = false;
  let slug = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--force') {
      force = true;
    } else if (args[i] === '--slug' && i + 1 < args.length) {
      slug = args[++i];
    }
  }

  return { force, slug };
}

// ---------------------------------------------------------------------------
// Content extraction helpers
// ---------------------------------------------------------------------------

/**
 * Extracts constraints from the HTML content.
 * Looks for a <ul> list following a "Constraints:" heading or bold label.
 *
 * @param {string} html - The raw HTML content string.
 * @returns {string[]} Array of constraint strings.
 */
function extractConstraints(html) {
  if (!html) return [];

  // Match "Constraints:" followed by <ul>...</ul>
  const constraintsMatch = html.match(/Constraints:?[\s\S]*?<ul>([\s\S]*?)<\/ul>/i);
  if (!constraintsMatch) return [];

  const listHtml = constraintsMatch[1];
  const items = [];
  const liRegex = /<li>([\s\S]*?)<\/li>/gi;
  let m;

  while ((m = liRegex.exec(listHtml)) !== null) {
    const text = unescapeHtml(m[1].replace(/<[^>]+>/g, '').trim());
    if (text) items.push(text);
  }

  return items;
}

/**
 * Extracts examples from the HTML content.
 * Looks for "Example N:" or "Example:" sections and pulls input, output, explanation.
 *
 * @param {string} html - The raw HTML content string.
 * @returns {Array<{input: string, output: string, explanation: string|null}>}
 */
function extractExamples(html) {
  if (!html) return [];

  const examples = [];

  // Split by "Example N:" or "Example:" with any HTML wrapping tags (avoids matching example-block / example-io)
  const exampleBlocks = html.split(/(?:<[^>]*>)?\s*Example(?:\s+\d+\s*:?|:)\s*(?:<\/[^>]*>)?/i);

  for (let i = 1; i < exampleBlocks.length; i++) {
    const block = exampleBlocks[i];
    const example = { input: '', output: '', explanation: null };

    // Extract Input (with or without colon)
    const inputMatch = block.match(
      /(?:<strong>|<b>)?\s*Input:?\s*(?:<\/strong>|<\/b>)?\s*([\s\S]*?)(?=(?:<strong>|<b>)?\s*Output:?|$)/i
    );
    if (inputMatch) {
      example.input = unescapeHtml(inputMatch[1].replace(/<[^>]+>/g, '').trim());
    }

    // Extract Output (with or without colon)
    const outputMatch = block.match(
      /(?:<strong>|<b>)?\s*Output:?\s*(?:<\/strong>|<\/b>)?\s*([\s\S]*?)(?=(?:<strong>|<b>)?\s*Explanation:?|<\/pre>|<p>|<\/div>|$)/i
    );
    if (outputMatch) {
      example.output = unescapeHtml(outputMatch[1].replace(/<[^>]+>/g, '').trim());
    }

    // Extract Explanation (optional)
    const explainMatch = block.match(
      /(?:<strong>|<b>)?\s*Explanation:?\s*(?:<\/strong>|<\/b>)?\s*([\s\S]*?)(?=<\/pre>|<p>|<\/div>|$)/i
    );
    if (explainMatch) {
      const exp = unescapeHtml(explainMatch[1].replace(/<[^>]+>/g, '').trim());
      example.explanation = exp || null;
    }

    if (example.input || example.output) {
      examples.push(example);
    }
  }

  return examples;
}

/**
 * Safely parses a JSON string, returning null on failure.
 *
 * @param {string|null|undefined} str - JSON string to parse.
 * @returns {object|null}
 */
function safeParse(str) {
  if (!str) return null;
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Normalization logic
// ---------------------------------------------------------------------------

/**
 * Downloads all remote images from problem statement and rewrites links to local relative paths.
 *
 * @param {string} content - Markdown problem statement
 * @param {string} category - Top-level category
 * @param {string} subcategory - Subcategory folder name
 * @param {string} slug - Question slug
 * @returns {Promise<string>} Statement with local image links
 */
async function processAndDownloadImages(content, category, subcategory, slug) {
  if (!content) return '';

  const assetsDir = join(QUESTIONS_DIR, category, subcategory, 'assets');
  let updatedContent = content;

  // Match markdown images and raw image URLs
  const imgUrlRegex = /(?:https?:\/\/assets\.leetcode\.com\/[^\s"')]+|https?:\/\/[^\s"')]+\.(?:png|jpg|jpeg|svg|gif))/gi;
  const matches = [...new Set(content.match(imgUrlRegex) || [])];

  if (matches.length === 0) return updatedContent;

  await ensureDir(assetsDir);

  for (let i = 0; i < matches.length; i++) {
    const remoteUrl = matches[i];
    try {
      const urlObj = new URL(remoteUrl);
      let ext = extname(urlObj.pathname).toLowerCase();
      if (!ext || !['.png', '.jpg', '.jpeg', '.gif', '.svg'].includes(ext)) {
        ext = '.png';
      }

      const filename = `${slug}-${i + 1}${ext}`;
      const localFilePath = join(assetsDir, filename);

      // Download if not already cached
      if (!existsSync(localFilePath)) {
        const res = await fetch(remoteUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          },
        });
        if (res.ok) {
          const buffer = Buffer.from(await res.arrayBuffer());
          writeFileSync(localFilePath, buffer);
        }
      }

      // Rewrite URL in content to relative path
      const relativePath = `./assets/${filename}`;
      updatedContent = updatedContent.replaceAll(remoteUrl, relativePath);
    } catch (err) {
      console.warn(`  ⚠️ Could not download image ${remoteUrl}: ${err.message}`);
    }
  }

  return updatedContent;
}

/**
 * Normalizes a single raw question object into the final schema.
 *
 * @param {object} raw - The raw question data from the API.
 * @returns {Promise<object>} The normalized question object.
 */
async function normalizeQuestion(raw) {
  const tags = (raw.topicTags ?? []).map((t) => t.name);
  const { category, subcategory } = resolveCategory(tags, raw.categoryTitle, raw.content, raw.title);

  // Convert HTML content to Markdown
  let statement = raw.content ? turndown.turndown(raw.content) : '';

  // Download images and rewrite statement image links
  statement = await processAndDownloadImages(statement, category, subcategory, raw.titleSlug);

  // Extract structured data from HTML
  const constraints = extractConstraints(raw.content);
  const examples = extractExamples(raw.content);

  // Build starter code map
  let starterCode = null;
  if (raw.codeSnippets && raw.codeSnippets.length > 0) {
    starterCode = {};
    for (const snippet of raw.codeSnippets) {
      starterCode[snippet.langSlug] = snippet.code;
    }
  }

  // Parse public test cases (official public test cases with verified outputs)
  let publicTests = null;
  if (Array.isArray(raw.exampleTestcaseList) && raw.exampleTestcaseList.length > 0) {
    const list = raw.exampleTestcaseList
      .map((tc, idx) => {
        const out = examples[idx]?.output || null;
        if (!tc || !out) return null;
        return {
          input: unescapeHtml(tc.trim()),
          expectedOutput: unescapeHtml(out.trim()),
        };
      })
      .filter(Boolean);
    if (list.length > 0) publicTests = list;
  }

  if (!publicTests || publicTests.length === 0) {
    if (examples.length > 0) {
      const list = examples
        .filter((e) => e.input && e.output)
        .map((e) => ({
          input: unescapeHtml(e.input.trim()),
          expectedOutput: unescapeHtml(e.output.trim()),
        }));
      if (list.length > 0) publicTests = list;
    }
  }

  // Generate 20 comprehensive test cases
  const testCases = generateTestCases(raw, examples, constraints, category);

  // Handle SQL/database questions
  let sqlSchema = null;
  let sqlSetup = null;
  if (raw.mysqlSchemas && raw.mysqlSchemas.length > 0) {
    const createStatements = [];
    const insertStatements = [];

    for (const schema of raw.mysqlSchemas) {
      const trimmed = schema.trim();
      if (/^CREATE\s+TABLE/i.test(trimmed)) {
        createStatements.push(trimmed);
      } else if (/^INSERT\s+INTO/i.test(trimmed)) {
        insertStatements.push(trimmed);
      } else if (trimmed) {
        // Other SQL statements – group with CREATE as schema definition
        createStatements.push(trimmed);
      }
    }

    if (createStatements.length > 0) {
      sqlSchema = createStatements.join('\n\n');
    }
    if (insertStatements.length > 0) {
      sqlSetup = insertStatements;
    }
  }

  return {
    id: String(raw.questionFrontendId),
    slug: raw.titleSlug,
    title: raw.title,
    category,
    subcategory,
    difficulty: raw.difficulty,
    tags,
    statement,
    constraints,
    examples,
    starterCode,
    publicTests,
    testCases,
    sqlSchema,
    sqlSetup,
    expectedOutput: null,
    solution: null,
    hints: raw.hints ?? [],
    source: {
      name: 'LeetCode',
      url: `https://leetcode.com/problems/${raw.titleSlug}/`,
      licenseOrPermissionReference: 'Authorized collection',
      collectedAt: new Date().toISOString(),
      sourceUpdatedAt: null,
    },
  };
}

/**
 * Checks whether a file exists at the given path.
 *
 * @param {string} filePath - Absolute path.
 * @returns {Promise<boolean>}
 */
async function fileExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Writes the normalized question JSON to the correct output path.
 * Handles slug collisions by appending the question id.
 *
 * @param {object} normalized - The normalized question object.
 * @returns {Promise<string>} The relative output path.
 */
async function writeNormalized(normalized) {
  const dir = join(QUESTIONS_DIR, normalized.category, normalized.subcategory);
  await ensureDir(dir);

  let filename = `${normalized.slug}.json`;
  let filePath = join(dir, filename);

  // Handle slug collision – file exists with a different question id
  if (await fileExists(filePath)) {
    try {
      const existing = JSON.parse(await readFile(filePath, 'utf-8'));
      if (existing.id !== normalized.id) {
        filename = `${normalized.slug}-${normalized.id}.json`;
        filePath = join(dir, filename);
      }
    } catch {
      // If we can't read the existing file, overwrite
    }
  }

  await writeFile(filePath, JSON.stringify(normalized, null, 2), 'utf-8');

  // Return a relative path for logging
  return `questions/${normalized.category}/${normalized.subcategory}/${filename}`;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

/**
 * Entry point – runs the normalization pipeline.
 */
async function main() {
  const { force, slug } = parseArgs();

  console.log('=== LeetCode Normalization ===');
  if (force) console.log('  Mode: force (re-normalizing all)');
  if (slug) console.log(`  Single slug: ${slug}`);
  console.log();

  // 1. List raw files to process
  let rawFiles;
  try {
    rawFiles = await readdir(RAW_DIR);
    rawFiles = rawFiles.filter((f) => f.endsWith('.json'));
  } catch (err) {
    console.error(`Cannot read raw directory (${RAW_DIR}): ${err.message}`);
    console.error('Run collect.mjs first to populate tmp/raw/.');
    process.exit(1);
  }

  // Filter to single slug if requested
  if (slug) {
    rawFiles = rawFiles.filter((f) => basename(f, '.json') === slug);
    if (rawFiles.length === 0) {
      console.error(`No raw file found for slug "${slug}".`);
      process.exit(1);
    }
  }

  const total = rawFiles.length;
  console.log(`Found ${total} raw file(s) to process.\n`);

  // Counters
  let normalized = 0;
  let skipped = 0;
  let failures = 0;
  const categoryCounts = {};

  for (let i = 0; i < rawFiles.length; i++) {
    const file = rawFiles[i];
    const fileSlug = basename(file, '.json');

    try {
      // Read raw JSON
      const rawContent = await readFile(join(RAW_DIR, file), 'utf-8');
      const raw = JSON.parse(rawContent);

      // Check if output already exists (unless --force)
      if (!force) {
        const tags = (raw.topicTags ?? []).map((t) => t.name);
        const { category, subcategory } = resolveCategory(tags, raw.categoryTitle);
        const outPath = join(QUESTIONS_DIR, category, subcategory, `${raw.titleSlug}.json`);

        if (await fileExists(outPath)) {
          skipped++;
          continue;
        }
      }

      // Normalize
      const norm = await normalizeQuestion(raw);
      const relPath = await writeNormalized(norm);

      // Track category stats
      const catKey = `${norm.category}/${norm.subcategory}`;
      categoryCounts[catKey] = (categoryCounts[catKey] ?? 0) + 1;

      normalized++;
      console.log(
        `[${i + 1}/${total}] Normalized: ${fileSlug} -> ${relPath}`
      );
    } catch (err) {
      failures++;
      console.error(`[${i + 1}/${total}] ✗ Failed: ${fileSlug} – ${err.message}`);
    }
  }

  // Report
  console.log('\n=== Normalization Report ===');
  console.log(`Total processed : ${total}`);
  console.log(`Normalized      : ${normalized}`);
  console.log(`Skipped (exist) : ${skipped}`);
  console.log(`Failures        : ${failures}`);

  if (Object.keys(categoryCounts).length > 0) {
    console.log('\nBy category/subcategory:');
    const sorted = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
    for (const [cat, count] of sorted) {
      console.log(`  ${cat.padEnd(30)} : ${count}`);
    }
  }

  console.log('\nNormalization complete.');
}

main().catch((err) => {
  console.error('Fatal error in normalize:', err);
  process.exit(1);
});
