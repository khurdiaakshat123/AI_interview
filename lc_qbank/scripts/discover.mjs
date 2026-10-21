#!/usr/bin/env node

/**
 * @fileoverview Discovery script – enumerates ALL LeetCode questions.
 *
 * Queries the LeetCode GraphQL API for the algorithms (default) and database
 * categories, deduplicates results by titleSlug, marks paid-only questions as
 * 'skipped', and saves the rest as 'pending' in collection-state.json.
 *
 * Usage:
 *   node scripts/discover.mjs
 *
 * @module discover
 */

import {
  LEETCODE_GRAPHQL,
  sleep,
  fetchGraphQL,
  loadState,
  saveState,
  resolveCategory,
} from './utils.mjs';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Number of questions to fetch per page. */
const PAGE_SIZE = 100;

/** Delay in ms between paginated API calls. */
const REQUEST_DELAY_MS = 1000;

/** GraphQL query for listing questions. */
const LIST_QUERY = `
query problemsetQuestionList(
  $categorySlug: String,
  $limit: Int,
  $skip: Int,
  $filters: QuestionListFilterInput
) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      difficulty
      frontendQuestionId: questionFrontendId
      paidOnly: isPaidOnly
      title
      titleSlug
      topicTags { name slug }
      categoryTitle
    }
  }
}`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Optional limit from CLI args for testing. */
const limitIdx = process.argv.indexOf('--limit');
const maxToDiscover = limitIdx !== -1 ? parseInt(process.argv[limitIdx + 1], 10) : Infinity;

/**
 * Fetches questions for a given category slug by paginating through
 * the LeetCode GraphQL API.
 *
 * @param {string} categorySlug - '' for algorithms, 'database' for SQL, etc.
 * @returns {Promise<Array<object>>} All question stubs for the category.
 */
async function fetchAllForCategory(categorySlug) {
  const label = categorySlug || 'algorithms';
  /** @type {Array<object>} */
  const allQuestions = [];
  let skip = 0;
  let total = Infinity;

  while (skip < total && allQuestions.length < maxToDiscover) {
    const fetchLimit = Math.min(PAGE_SIZE, maxToDiscover - allQuestions.length);
    console.log(`  [${label}] Fetching page at offset ${skip} (limit ${fetchLimit})...`);

    try {
      const data = await fetchGraphQL(LIST_QUERY, {
        categorySlug,
        limit: fetchLimit,
        skip,
        filters: {},
      });

      const result = data?.problemsetQuestionList;
      if (!result) {
        console.error(`  [${label}] Unexpected response shape – stopping.`);
        break;
      }

      total = result.total;
      const questions = result.questions ?? [];
      allQuestions.push(...questions);

      console.log(
        `  [${label}] Received ${questions.length} questions ` +
          `(${allQuestions.length}/${total})`
      );

      skip += PAGE_SIZE;

      if (skip < total) {
        await sleep(REQUEST_DELAY_MS);
      }
    } catch (err) {
      console.error(`  [${label}] Error at offset ${skip}: ${err.message}`);
      // Retry once after a longer pause
      await sleep(REQUEST_DELAY_MS * 3);

      try {
        const data = await fetchGraphQL(LIST_QUERY, {
          categorySlug,
          limit: PAGE_SIZE,
          skip,
          filters: {},
        });

        const result = data?.problemsetQuestionList;
        if (result) {
          total = result.total;
          const questions = result.questions ?? [];
          allQuestions.push(...questions);
          skip += PAGE_SIZE;
        } else {
          console.error(`  [${label}] Retry also returned unexpected shape – skipping page.`);
          skip += PAGE_SIZE;
        }
      } catch (retryErr) {
        console.error(`  [${label}] Retry failed: ${retryErr.message} – skipping page.`);
        skip += PAGE_SIZE;
      }

      if (skip < total) {
        await sleep(REQUEST_DELAY_MS);
      }
    }
  }

  return allQuestions;
}

/**
 * Deduplicates questions by titleSlug, keeping the first occurrence.
 *
 * @param {Array<object>} questions - Combined list from all categories.
 * @returns {Map<string, object>} Map keyed by titleSlug.
 */
function deduplicateBySlug(questions) {
  /** @type {Map<string, object>} */
  const map = new Map();
  for (const q of questions) {
    if (!map.has(q.titleSlug)) {
      map.set(q.titleSlug, q);
    }
  }
  return map;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

/**
 * Entry point – runs the discovery pipeline.
 */
async function main() {
  console.log('=== LeetCode Discovery ===\n');

  // 1. Fetch algorithms questions (categorySlug: '')
  console.log('Fetching algorithms questions...');
  const algoQuestions = await fetchAllForCategory('');

  // 2. Fetch database questions
  console.log('\nFetching database questions...');
  const dbQuestions = await fetchAllForCategory('database');

  // 3. Merge & deduplicate
  const combined = [...algoQuestions, ...dbQuestions];
  const uniqueMap = deduplicateBySlug(combined);
  console.log(
    `\nMerged: ${combined.length} total -> ${uniqueMap.size} unique questions`
  );

  // 4. Load existing state (if any) and merge
  const state = await loadState();
  const existingSlugs = new Set(
    (state.questions ?? []).map((q) => q.titleSlug)
  );

  let newCount = 0;
  let skippedPaid = 0;

  /** Counters for the report. */
  const difficultyCount = { Easy: 0, Medium: 0, Hard: 0 };
  const categoryCount = {};
  let paidTotal = 0;
  let freeTotal = 0;

  for (const [slug, q] of uniqueMap) {
    // Update aggregate stats
    difficultyCount[q.difficulty] = (difficultyCount[q.difficulty] ?? 0) + 1;

    const cat = q.categoryTitle || 'Algorithms';
    categoryCount[cat] = (categoryCount[cat] ?? 0) + 1;

    if (q.paidOnly) {
      paidTotal++;
    } else {
      freeTotal++;
    }

    // Skip if already tracked
    if (existingSlugs.has(slug)) {
      continue;
    }

    // Determine initial status
    const status = q.paidOnly ? 'skipped' : 'pending';
    if (q.paidOnly) {
      skippedPaid++;
    }

    state.questions = state.questions ?? [];
    state.questions.push({
      titleSlug: slug,
      frontendQuestionId: q.frontendQuestionId,
      title: q.title,
      difficulty: q.difficulty,
      paidOnly: q.paidOnly,
      categoryTitle: q.categoryTitle || 'Algorithms',
      topicTags: (q.topicTags ?? []).map((t) => t.name),
      status,
      discoveredAt: new Date().toISOString(),
    });

    newCount++;
  }

  // 5. Persist state
  state.lastDiscoveryRun = new Date().toISOString();
  state.totalDiscovered = uniqueMap.size;
  await saveState(state);

  // 6. Report
  console.log('\n=== Discovery Report ===');
  console.log(`Total unique discovered : ${uniqueMap.size}`);
  console.log(`Newly added this run    : ${newCount}`);
  console.log(`Paid-only (skipped)     : ${skippedPaid}`);
  console.log(`\nBy difficulty:`);
  for (const [d, c] of Object.entries(difficultyCount)) {
    console.log(`  ${d.padEnd(8)} : ${c}`);
  }
  console.log(`\nPaid vs Free:`);
  console.log(`  Paid : ${paidTotal}`);
  console.log(`  Free : ${freeTotal}`);
  console.log(`\nBy category:`);
  for (const [cat, c] of Object.entries(categoryCount)) {
    console.log(`  ${cat.padEnd(16)} : ${c}`);
  }
  console.log('\nDiscovery complete. State saved to collection-state.json.');
}

main().catch((err) => {
  console.error('Fatal error in discover:', err);
  process.exit(1);
});
