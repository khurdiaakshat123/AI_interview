/**
 * @file Unit tests for deduplication logic.
 * Verifies that duplicate question IDs and slugs within the same
 * category are correctly detected.
 */
import { describe, it, expect } from 'vitest';

/**
 * Minimal deduplication detector.
 *
 * Scans an array of { file, questions[] } entries and returns any
 * duplicates found.  This mirrors the logic in scripts/deduplicate.mjs
 * so we can test it in isolation.
 *
 * @param {{ file: string, questions: Array<{ id: number, slug: string, category: string }> }[]} entries
 * @returns {{ duplicateIds: Array<{ id: number, files: string[] }>, duplicateSlugs: Array<{ slug: string, category: string, files: string[] }> }}
 */
function findDuplicates(entries) {
  /** @type {Map<number, string[]>} id → list of file paths */
  const idMap = new Map();
  /** @type {Map<string, string[]>} "category::slug" → list of file paths */
  const slugMap = new Map();

  for (const entry of entries) {
    for (const q of entry.questions) {
      // Track IDs
      const idFiles = idMap.get(q.id) || [];
      idFiles.push(entry.file);
      idMap.set(q.id, idFiles);

      // Track slugs within the same category
      const slugKey = `${q.category}::${q.slug}`;
      const slugFiles = slugMap.get(slugKey) || [];
      slugFiles.push(entry.file);
      slugMap.set(slugKey, slugFiles);
    }
  }

  const duplicateIds = [];
  for (const [id, files] of idMap) {
    if (files.length > 1) {
      duplicateIds.push({ id, files });
    }
  }

  const duplicateSlugs = [];
  for (const [key, files] of slugMap) {
    if (files.length > 1) {
      const [category, slug] = key.split('::');
      duplicateSlugs.push({ slug, category, files });
    }
  }

  return { duplicateIds, duplicateSlugs };
}

// ---------------------------------------------------------------------------
// findDuplicates
// ---------------------------------------------------------------------------
describe('findDuplicates', () => {
  it('returns empty lists when there are no duplicates', () => {
    const entries = [
      {
        file: 'questions/dsa/arrays/two-sum.json',
        questions: [{ id: 1, slug: 'two-sum', category: 'dsa/arrays' }],
      },
      {
        file: 'questions/dsa/strings/longest-substring.json',
        questions: [{ id: 3, slug: 'longest-substring', category: 'dsa/strings' }],
      },
    ];

    const { duplicateIds, duplicateSlugs } = findDuplicates(entries);
    expect(duplicateIds).toHaveLength(0);
    expect(duplicateSlugs).toHaveLength(0);
  });

  it('detects the same question ID appearing in two different files', () => {
    const entries = [
      {
        file: 'questions/dsa/arrays/two-sum.json',
        questions: [{ id: 1, slug: 'two-sum', category: 'dsa/arrays' }],
      },
      {
        file: 'questions/dsa/hashing/two-sum-copy.json',
        questions: [{ id: 1, slug: 'two-sum-v2', category: 'dsa/hashing' }],
      },
    ];

    const { duplicateIds } = findDuplicates(entries);
    expect(duplicateIds).toHaveLength(1);
    expect(duplicateIds[0].id).toBe(1);
    expect(duplicateIds[0].files).toHaveLength(2);
  });

  it('detects the same slug within the same category', () => {
    const entries = [
      {
        file: 'questions/dsa/arrays/two-sum.json',
        questions: [{ id: 1, slug: 'two-sum', category: 'dsa/arrays' }],
      },
      {
        file: 'questions/dsa/arrays/two-sum-dup.json',
        questions: [{ id: 2, slug: 'two-sum', category: 'dsa/arrays' }],
      },
    ];

    const { duplicateSlugs } = findDuplicates(entries);
    expect(duplicateSlugs).toHaveLength(1);
    expect(duplicateSlugs[0].slug).toBe('two-sum');
    expect(duplicateSlugs[0].category).toBe('dsa/arrays');
    expect(duplicateSlugs[0].files).toHaveLength(2);
  });

  it('allows the same slug in different categories (no duplicate)', () => {
    const entries = [
      {
        file: 'questions/dsa/arrays/two-sum.json',
        questions: [{ id: 1, slug: 'two-sum', category: 'dsa/arrays' }],
      },
      {
        file: 'questions/dsa/hashing/two-sum.json',
        questions: [{ id: 2, slug: 'two-sum', category: 'dsa/hashing' }],
      },
    ];

    const { duplicateSlugs } = findDuplicates(entries);
    expect(duplicateSlugs).toHaveLength(0);
  });

  it('handles multiple duplicates simultaneously', () => {
    const entries = [
      {
        file: 'file-a.json',
        questions: [
          { id: 1, slug: 'two-sum', category: 'dsa/arrays' },
          { id: 3, slug: 'three-sum', category: 'dsa/arrays' },
        ],
      },
      {
        file: 'file-b.json',
        questions: [
          { id: 1, slug: 'two-sum', category: 'dsa/arrays' },
          { id: 4, slug: 'four-sum', category: 'dsa/arrays' },
        ],
      },
      {
        file: 'file-c.json',
        questions: [
          { id: 3, slug: 'three-sum', category: 'dsa/arrays' },
        ],
      },
    ];

    const { duplicateIds, duplicateSlugs } = findDuplicates(entries);
    expect(duplicateIds).toHaveLength(2); // id 1 and id 3
    expect(duplicateSlugs).toHaveLength(2); // two-sum and three-sum in dsa/arrays
  });

  it('handles an empty entries array', () => {
    const { duplicateIds, duplicateSlugs } = findDuplicates([]);
    expect(duplicateIds).toHaveLength(0);
    expect(duplicateSlugs).toHaveLength(0);
  });
});
