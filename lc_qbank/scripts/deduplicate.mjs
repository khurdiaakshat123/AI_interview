#!/usr/bin/env node

/**
 * @fileoverview Finds and reports duplicate questions in the collection.
 *
 * Usage:
 *   node scripts/deduplicate.mjs [--remove]
 *
 * Flags:
 *   --remove  Remove true duplicates (same ID), keeping the copy in the
 *             correct category path. Without this flag the script only reports.
 */

import { readFileSync, unlinkSync, readdirSync, statSync } from 'node:fs';
import { join, relative, basename, sep } from 'node:path';
import {
  PROJECT_ROOT,
  QUESTIONS_DIR,
} from './utils.mjs';

/* ------------------------------------------------------------------ */
/*  CLI argument parsing                                               */
/* ------------------------------------------------------------------ */

const removeMode = process.argv.includes('--remove');

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

  const entries = readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findJsonFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.json')) {
      results.push(fullPath);
    }
  }

  return results;
}

/* ------------------------------------------------------------------ */
/*  Duplicate detection                                                */
/* ------------------------------------------------------------------ */

/**
 * @typedef {Object} QuestionInfo
 * @property {string} id          - Question ID
 * @property {string} slug        - Question slug
 * @property {string} title       - Question title
 * @property {string} category    - Category from JSON
 * @property {string} subcategory - Subcategory from JSON
 * @property {string} filePath    - Absolute file path
 * @property {string} relPath     - Relative path from project root
 * @property {string} dirCategory - Category derived from directory path
 */

/**
 * Loads metadata from all question files.
 * @param {string[]} files - Absolute paths to question JSON files
 * @returns {QuestionInfo[]}
 */
function loadAllQuestions(files) {
  /** @type {QuestionInfo[]} */
  const questions = [];

  for (const filePath of files) {
    try {
      const raw = readFileSync(filePath, 'utf-8');
      const data = JSON.parse(raw);

      const relFromQuestions = relative(QUESTIONS_DIR, filePath).split(sep).join('/');
      const parts = relFromQuestions.split('/');
      const dirCategory = parts.length >= 3 ? parts[0] : '';

      questions.push({
        id: String(data.id ?? ''),
        slug: data.slug ?? '',
        title: data.title ?? '',
        category: data.category ?? '',
        subcategory: data.subcategory ?? '',
        filePath,
        relPath: relative(PROJECT_ROOT, filePath).split(sep).join('/'),
        dirCategory,
      });
    } catch {
      console.warn(`⚠  Skipping unparseable file: ${relative(PROJECT_ROOT, filePath)}`);
    }
  }

  return questions;
}

/**
 * Determines if a question file sits in its "correct" category directory.
 * @param {QuestionInfo} q
 * @returns {boolean}
 */
function isInCorrectPath(q) {
  return q.dirCategory === q.category;
}

/* ------------------------------------------------------------------ */
/*  Main                                                               */
/* ------------------------------------------------------------------ */

/**
 * Entry point – scans files, detects duplicates, and optionally removes them.
 */
async function main() {
  const files = findJsonFiles(QUESTIONS_DIR);

  if (files.length === 0) {
    console.log('No question files found.');
    process.exit(0);
  }

  const questions = loadAllQuestions(files);
  console.log(`\nScanned ${questions.length} question file(s).\n`);

  let hasDuplicates = false;

  /* ── 1. Same ID in multiple files ─────────────────────────────── */
  /** @type {Map<string, QuestionInfo[]>} */
  const byId = new Map();
  for (const q of questions) {
    if (!q.id) continue;
    const list = byId.get(q.id) ?? [];
    list.push(q);
    byId.set(q.id, list);
  }

  const duplicateIds = [...byId.entries()].filter(([, v]) => v.length > 1);

  if (duplicateIds.length > 0) {
    hasDuplicates = true;
    console.log('─'.repeat(60));
    console.log('  🔴  Duplicate IDs\n');

    for (const [id, dupes] of duplicateIds) {
      console.log(`  ID ${id} appears in ${dupes.length} files:`);
      for (const d of dupes) {
        console.log(`    • ${d.relPath}`);
      }

      if (removeMode) {
        // Keep the copy in the correct category path
        const correct = dupes.find(isInCorrectPath) ?? dupes[0];
        const toRemove = dupes.filter((d) => d !== correct);

        for (const d of toRemove) {
          unlinkSync(d.filePath);
          console.log(`    ✂  Removed ${d.relPath}`);
        }
        console.log(`    ✔  Kept    ${correct.relPath}`);
      }
      console.log();
    }
  }

  /* ── 2. Same slug in different directories ────────────────────── */
  /** @type {Map<string, QuestionInfo[]>} */
  const bySlug = new Map();
  for (const q of questions) {
    if (!q.slug) continue;
    const list = bySlug.get(q.slug) ?? [];
    list.push(q);
    bySlug.set(q.slug, list);
  }

  const duplicateSlugs = [...bySlug.entries()].filter(([, v]) => {
    // Only flag if same slug appears in different categories
    const categories = new Set(v.map((d) => d.category));
    return v.length > 1 && categories.size < v.length;
  });

  if (duplicateSlugs.length > 0) {
    hasDuplicates = true;
    console.log('─'.repeat(60));
    console.log('  🟡  Same slug in different locations (same category)\n');

    for (const [slug, dupes] of duplicateSlugs) {
      console.log(`  Slug "${slug}":`);
      for (const d of dupes) {
        console.log(`    • ${d.relPath}  (category: ${d.category})`);
      }
      console.log();
    }
  }

  /* ── 3. Same title but different IDs ──────────────────────────── */
  /** @type {Map<string, QuestionInfo[]>} */
  const byTitle = new Map();
  for (const q of questions) {
    if (!q.title) continue;
    const normTitle = q.title.trim().toLowerCase();
    const list = byTitle.get(normTitle) ?? [];
    list.push(q);
    byTitle.set(normTitle, list);
  }

  const duplicateTitles = [...byTitle.entries()].filter(([, v]) => {
    const ids = new Set(v.map((d) => d.id));
    return v.length > 1 && ids.size > 1;
  });

  if (duplicateTitles.length > 0) {
    hasDuplicates = true;
    console.log('─'.repeat(60));
    console.log('  🟠  Same title with different IDs\n');

    for (const [title, dupes] of duplicateTitles) {
      console.log(`  Title "${dupes[0].title}":`);
      for (const d of dupes) {
        console.log(`    • ID ${d.id} — ${d.relPath}`);
      }
      console.log();
    }
  }

  /* ── Summary ──────────────────────────────────────────────────── */
  console.log('─'.repeat(60));
  if (!hasDuplicates) {
    console.log('\n✅  No duplicates found.\n');
  } else {
    console.log(`\n  Duplicate IDs      : ${duplicateIds.length}`);
    console.log(`  Slug collisions    : ${duplicateSlugs.length}`);
    console.log(`  Title mismatches   : ${duplicateTitles.length}`);
    if (!removeMode) {
      console.log('\n  Run with --remove to delete true duplicates (same ID).\n');
    }
    console.log();
  }
}

main();
