#!/usr/bin/env node

/**
 * @fileoverview Collection script – fetches full details for every discovered
 * LeetCode question.
 *
 * Reads collection-state.json, processes each 'pending' question through the
 * LeetCode GraphQL API, saves the raw response into tmp/raw/{slug}.json, and
 * updates the question's status to 'completed' or 'failed'.
 *
 * Usage:
 *   node scripts/collect.mjs [--resume] [--limit N]
 *
 * Flags:
 *   --resume   Skip questions that already have a raw file on disk.
 *   --limit N  Only process N questions (useful for testing).
 *
 * @module collect
 */

import { writeFile, access } from 'node:fs/promises';
import { join } from 'node:path';
import {
  PROJECT_ROOT,
  sleep,
  ensureDir,
  fetchGraphQL,
  loadState,
  saveState,
} from './utils.mjs';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Delay between consecutive API calls (ms). */
const COLLECTION_DELAY_MS = 1500;

/** Directory for raw API responses. */
const RAW_DIR = join(PROJECT_ROOT, 'tmp', 'raw');

/** GraphQL query for full question details. */
const DETAIL_QUERY = `
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    categoryTitle
    topicTags { name slug }
    codeSnippets { lang langSlug code }
    sampleTestCase
    exampleTestcaseList
    mysqlSchemas
    hints
    stats
    metaData
  }
}`;

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

/**
 * Parses command-line flags.
 *
 * @returns {{ resume: boolean, limit: number | null }}
 */
function parseArgs() {
  const args = process.argv.slice(2);
  let resume = false;
  let limit = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--resume') {
      resume = true;
    } else if (args[i] === '--limit' && i + 1 < args.length) {
      limit = parseInt(args[++i], 10);
      if (Number.isNaN(limit) || limit <= 0) {
        console.error('Error: --limit must be a positive integer.');
        process.exit(1);
      }
    }
  }

  return { resume, limit };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Checks whether a raw file already exists on disk for the given slug.
 *
 * @param {string} slug - The question's titleSlug.
 * @returns {Promise<boolean>}
 */
async function rawFileExists(slug) {
  try {
    await access(join(RAW_DIR, `${slug}.json`));
    return true;
  } catch {
    return false;
  }
}

/**
 * Fetches full details for a single question and writes the raw JSON to disk.
 *
 * @param {string} slug - The question's titleSlug.
 * @returns {Promise<object>} The raw question data from the API.
 * @throws {Error} If the API returns an unexpected response.
 */
async function fetchAndSaveQuestion(slug) {
  const data = await fetchGraphQL(DETAIL_QUERY, { titleSlug: slug });

  if (!data?.question) {
    throw new Error(`API returned no question data for slug "${slug}"`);
  }

  await ensureDir(RAW_DIR);

  const filePath = join(RAW_DIR, `${slug}.json`);
  await writeFile(filePath, JSON.stringify(data.question, null, 2), 'utf-8');

  return data.question;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

/**
 * Entry point – runs the collection pipeline.
 */
async function main() {
  const { resume, limit } = parseArgs();

  console.log('=== LeetCode Collection ===');
  if (resume) console.log('  Mode: resume (skipping already-collected)');
  if (limit) console.log(`  Limit: ${limit} questions`);
  console.log();

  // 1. Load state
  const state = await loadState();
  const questions = state.questions ?? [];

  if (questions.length === 0) {
    console.log('No questions in state. Run discover.mjs first.');
    return;
  }

  // 2. Build work queue
  let pending = questions.filter((q) => q.status === 'pending');

  if (resume) {
    // Further filter: skip those whose raw file already exists
    const filtered = [];
    for (const q of pending) {
      if (await rawFileExists(q.titleSlug)) {
        // Mark as completed in state
        q.status = 'completed';
        q.collectedAt = new Date().toISOString();
      } else {
        filtered.push(q);
      }
    }
    pending = filtered;
    // Save state after resume filtering
    await saveState(state);
  }

  const totalToDo = limit ? Math.min(limit, pending.length) : pending.length;
  const totalInState = questions.length;

  console.log(`Pending: ${pending.length} | Processing: ${totalToDo}\n`);

  // 3. Collect
  let completed = 0;
  let failed = 0;

  for (let i = 0; i < totalToDo; i++) {
    const q = pending[i];
    const idx = i + 1;

    console.log(
      `[${idx}/${totalToDo}] Collecting: ${q.titleSlug} (${q.difficulty})`
    );

    try {
      await fetchAndSaveQuestion(q.titleSlug);
      q.status = 'completed';
      q.collectedAt = new Date().toISOString();
      completed++;
    } catch (err) {
      console.error(`  ✗ Failed: ${err.message}`);
      q.status = 'failed';
      q.error = err.message;
      q.failedAt = new Date().toISOString();
      failed++;
    }

    // Save state after EVERY question for resumability
    await saveState(state);

    // Delay before next request (skip delay after last item)
    if (i < totalToDo - 1) {
      await sleep(COLLECTION_DELAY_MS);
    }
  }

  // 4. Final report
  const remaining = questions.filter((q) => q.status === 'pending').length;
  const totalCompleted = questions.filter((q) => q.status === 'completed').length;
  const totalFailed = questions.filter((q) => q.status === 'failed').length;
  const totalSkipped = questions.filter((q) => q.status === 'skipped').length;

  console.log('\n=== Collection Report ===');
  console.log(`This run      : ${completed} completed, ${failed} failed`);
  console.log(`Overall state :`);
  console.log(`  Completed : ${totalCompleted}`);
  console.log(`  Failed    : ${totalFailed}`);
  console.log(`  Skipped   : ${totalSkipped}`);
  console.log(`  Remaining : ${remaining}`);
  console.log('\nCollection complete. State saved to collection-state.json.');
}

main().catch((err) => {
  console.error('Fatal error in collect:', err);
  process.exit(1);
});
