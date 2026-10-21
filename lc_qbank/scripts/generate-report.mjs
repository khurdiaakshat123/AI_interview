#!/usr/bin/env node

/**
 * @fileoverview Generates collection reports and refreshes manifests.
 *
 * Usage:
 *   node scripts/generate-report.mjs
 *
 * Outputs:
 *   manifests/questions-index.json   – searchable index of all questions
 *   manifests/source-manifest.json   – data-source documentation
 *   reports/collection-report.json   – machine-readable summary
 *   reports/collection-report.md     – human-readable Markdown report
 */

import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, relative, basename, sep } from 'node:path';
import {
  PROJECT_ROOT,
  QUESTIONS_DIR,
  MANIFESTS_DIR,
  REPORTS_DIR,
  SCHEMAS_DIR,
  ensureDir,
  loadState,
} from './utils.mjs';

/* ------------------------------------------------------------------ */
/*  File discovery                                                     */
/* ------------------------------------------------------------------ */

/**
 * Recursively finds all `.json` files under a directory.
 * @param {string} dir - Directory to scan
 * @returns {string[]} Absolute paths to JSON files
 */
function findJsonFiles(dir) {
  /** @type {string[]} */
  const results = [];

  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...findJsonFiles(fullPath));
      } else if (entry.isFile() && entry.name.endsWith('.json')) {
        results.push(fullPath);
      }
    }
  } catch {
    // Directory may not exist yet
  }

  return results;
}

/* ------------------------------------------------------------------ */
/*  Question loading                                                   */
/* ------------------------------------------------------------------ */

/**
 * @typedef {Object} QuestionEntry
 * @property {string} id
 * @property {string} slug
 * @property {string} title
 * @property {string} category
 * @property {string} subcategory
 * @property {string} difficulty
 * @property {string} path - Relative path from project root
 */

/**
 * Loads metadata from all question JSON files.
 * @param {string[]} files
 * @returns {{ entries: QuestionEntry[], errors: string[] }}
 */
function loadQuestions(files) {
  /** @type {QuestionEntry[]} */
  const entries = [];
  /** @type {string[]} */
  const errors = [];

  for (const filePath of files) {
    const relPath = relative(PROJECT_ROOT, filePath).split(sep).join('/');

    try {
      const raw = readFileSync(filePath, 'utf-8');
      const data = JSON.parse(raw);

      entries.push({
        id: String(data.id ?? ''),
        slug: data.slug ?? basename(filePath, '.json'),
        title: data.title ?? '',
        category: data.category ?? '',
        subcategory: data.subcategory ?? '',
        difficulty: data.difficulty ?? 'Unknown',
        path: relPath,
      });
    } catch (err) {
      errors.push(`${relPath}: ${/** @type {Error} */ (err).message}`);
    }
  }

  return { entries, errors };
}

/* ------------------------------------------------------------------ */
/*  Manifest generators                                                */
/* ------------------------------------------------------------------ */

/**
 * Generates `manifests/questions-index.json`.
 * @param {QuestionEntry[]} entries
 */
function generateQuestionsIndex(entries) {
  const index = {
    version: 1,
    generatedAt: new Date().toISOString(),
    totalQuestions: entries.length,
    questions: entries.map((e) => ({
      id: e.id,
      slug: e.slug,
      title: e.title,
      category: e.category,
      subcategory: e.subcategory,
      difficulty: e.difficulty,
      path: e.path,
    })),
  };

  const outPath = join(MANIFESTS_DIR, 'questions-index.json');
  writeFileSync(outPath, JSON.stringify(index, null, 2) + '\n', 'utf-8');
  console.log(`  ✔  ${relative(PROJECT_ROOT, outPath)}`);
}

/**
 * Generates `manifests/source-manifest.json`.
 */
function generateSourceManifest() {
  const manifest = {
    source: 'LeetCode',
    apiEndpoint: 'https://leetcode.com/graphql',
    collectionMethod: 'GraphQL API',
    permittedFields: [
      'id',
      'title',
      'titleSlug',
      'difficulty',
      'topicTags',
      'categoryTitle',
      'content',
      'hints',
      'similarQuestions',
      'stats',
      'isPaidOnly',
    ],
    authorizationReference:
      'Public API — no authentication required for problem metadata. Premium content may require a valid session.',
    lastCollectionTimestamp: new Date().toISOString(),
  };

  const outPath = join(MANIFESTS_DIR, 'source-manifest.json');
  writeFileSync(outPath, JSON.stringify(manifest, null, 2) + '\n', 'utf-8');
  console.log(`  ✔  ${relative(PROJECT_ROOT, outPath)}`);
}

/* ------------------------------------------------------------------ */
/*  Report generators                                                  */
/* ------------------------------------------------------------------ */

/**
 * Builds aggregated statistics from question entries.
 * @param {QuestionEntry[]} entries
 * @param {string[]} errors
 * @returns {object} Report JSON payload
 */
function buildReportData(entries, errors) {
  /** @type {Record<string, number>} */
  const byDifficulty = {};
  /** @type {Record<string, number>} */
  const byCategory = {};
  /** @type {Record<string, number>} */
  const bySubcategory = {};

  for (const e of entries) {
    byDifficulty[e.difficulty] = (byDifficulty[e.difficulty] ?? 0) + 1;
    byCategory[e.category] = (byCategory[e.category] ?? 0) + 1;

    const subKey = `${e.category}/${e.subcategory}`;
    bySubcategory[subKey] = (bySubcategory[subKey] ?? 0) + 1;
  }

  // Attempt to read total discovered from collection state
  let totalDiscovered = entries.length;
  try {
    const state = loadState();
    if (state && typeof state.totalDiscovered === 'number') {
      totalDiscovered = state.totalDiscovered;
    }
  } catch {
    // State file may not exist; fall back to collected count
  }

  const completionRate =
    totalDiscovered > 0
      ? ((entries.length / totalDiscovered) * 100).toFixed(1) + '%'
      : '100.0%';

  return {
    generatedAt: new Date().toISOString(),
    summary: {
      totalCollected: entries.length,
      totalDiscovered,
      completionRate,
      byDifficulty,
      byCategory,
      bySubcategory,
    },
    validation: {
      valid: entries.length - errors.length,
      invalid: errors.length,
      errors,
    },
    failures: [],
    gaps: [],
  };
}

/**
 * Generates `reports/collection-report.json`.
 * @param {object} reportData
 */
function generateReportJson(reportData) {
  const outPath = join(REPORTS_DIR, 'collection-report.json');
  writeFileSync(outPath, JSON.stringify(reportData, null, 2) + '\n', 'utf-8');
  console.log(`  ✔  ${relative(PROJECT_ROOT, outPath)}`);
}

/**
 * Generates `reports/collection-report.md` with human-readable tables.
 * @param {object} reportData
 */
function generateReportMarkdown(reportData) {
  const { summary, validation } = reportData;
  const lines = [];

  lines.push('# LeetCode Question Bank — Collection Report');
  lines.push('');
  lines.push(`> Generated at **${reportData.generatedAt}**`);
  lines.push('');

  /* ── Overview ──────────────────────────────────────────────────── */
  lines.push('## Overview');
  lines.push('');
  lines.push(`| Metric             | Value |`);
  lines.push(`| ------------------ | ----- |`);
  lines.push(`| Total Collected    | ${summary.totalCollected} |`);
  lines.push(`| Total Discovered   | ${summary.totalDiscovered} |`);
  lines.push(`| Completion Rate    | ${summary.completionRate} |`);
  lines.push('');

  /* ── By Difficulty ─────────────────────────────────────────────── */
  lines.push('## By Difficulty');
  lines.push('');
  lines.push('| Difficulty | Count |');
  lines.push('| ---------- | ----- |');
  for (const [diff, count] of Object.entries(summary.byDifficulty)) {
    lines.push(`| ${diff} | ${count} |`);
  }
  lines.push('');

  /* ── By Category ───────────────────────────────────────────────── */
  lines.push('## By Category');
  lines.push('');
  lines.push('| Category | Count |');
  lines.push('| -------- | ----- |');
  for (const [cat, count] of Object.entries(summary.byCategory)) {
    lines.push(`| ${cat} | ${count} |`);
  }
  lines.push('');

  /* ── By Subcategory ────────────────────────────────────────────── */
  lines.push('## By Subcategory');
  lines.push('');
  lines.push('| Subcategory | Count |');
  lines.push('| ----------- | ----- |');
  for (const [sub, count] of Object.entries(summary.bySubcategory)) {
    lines.push(`| ${sub} | ${count} |`);
  }
  lines.push('');

  /* ── Validation ────────────────────────────────────────────────── */
  lines.push('## Validation');
  lines.push('');
  lines.push(`| Status  | Count |`);
  lines.push(`| ------- | ----- |`);
  lines.push(`| Valid   | ${validation.valid} |`);
  lines.push(`| Invalid | ${validation.invalid} |`);
  lines.push('');

  if (validation.errors.length > 0) {
    lines.push('### Errors');
    lines.push('');
    for (const e of validation.errors) {
      lines.push(`- ${e}`);
    }
    lines.push('');
  }

  /* ── Footer ────────────────────────────────────────────────────── */
  lines.push('---');
  lines.push('*Report generated by `scripts/generate-report.mjs`*');
  lines.push('');

  const outPath = join(REPORTS_DIR, 'collection-report.md');
  writeFileSync(outPath, lines.join('\n'), 'utf-8');
  console.log(`  ✔  ${relative(PROJECT_ROOT, outPath)}`);
}

/* ------------------------------------------------------------------ */
/*  Main                                                               */
/* ------------------------------------------------------------------ */

/**
 * Entry point – scans questions, generates manifests and reports.
 */
async function main() {
  const verifyOnly = process.argv.includes('--verify-only');

  if (verifyOnly) {
    console.log('\nVerifying index and manifests…\n');
  } else {
    console.log('\nGenerating reports and manifests…\n');
    ensureDir(MANIFESTS_DIR);
    ensureDir(REPORTS_DIR);
  }

  /* Discover and load questions */
  const files = findJsonFiles(QUESTIONS_DIR);
  console.log(`  Found ${files.length} question file(s).\n`);

  const { entries, errors } = loadQuestions(files);

  /* Sort entries by ID for stable output */
  entries.sort((a, b) => {
    const numA = parseInt(a.id, 10);
    const numB = parseInt(b.id, 10);
    if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
    return a.id.localeCompare(b.id);
  });

  if (verifyOnly) {
    const indexPath = join(MANIFESTS_DIR, 'questions-index.json');
    try {
      const existingRaw = readFileSync(indexPath, 'utf-8');
      const existing = JSON.parse(existingRaw);

      if (existing.totalQuestions !== entries.length) {
        console.error(`❌ Index mismatch: index has ${existing.totalQuestions} questions, disk has ${entries.length}`);
        process.exit(1);
      }

      console.log(`✅ Index verified: ${entries.length} question(s) match on-disk files.\n`);
      process.exit(0);
    } catch (err) {
      console.error(`❌ Index verification failed: ${/** @type {Error} */ (err).message}`);
      process.exit(1);
    }
  }

  /* Generate outputs */
  generateQuestionsIndex(entries);
  generateSourceManifest();

  const reportData = buildReportData(entries, errors);
  generateReportJson(reportData);
  generateReportMarkdown(reportData);

  console.log(`\n✅  Done. ${entries.length} questions indexed.\n`);
}

main();
