/**
 * @file Unit tests for normalization utility functions.
 * Tests slugify, resolveCategory, and related helpers from utils.mjs.
 */
import { describe, it, expect } from 'vitest';
import { slugify, resolveCategory, inferDatabaseSubcategory } from '../scripts/utils.mjs';

// ---------------------------------------------------------------------------
// slugify
// ---------------------------------------------------------------------------
describe('slugify', () => {
  it('converts a title-case string to a kebab-case slug', () => {
    expect(slugify('Two Sum')).toBe('two-sum');
  });

  it('handles special characters by stripping them', () => {
    expect(slugify('Valid Parentheses (Easy)')).toBe('valid-parentheses-easy');
  });

  it('collapses consecutive hyphens', () => {
    expect(slugify('Merge  Two   Sorted  Lists')).toBe('merge-two-sorted-lists');
  });

  it('handles strings with numbers', () => {
    expect(slugify('3Sum Closest')).toBe('3sum-closest');
  });

  it('trims leading and trailing whitespace / hyphens', () => {
    expect(slugify('  Two Sum  ')).toBe('two-sum');
  });

  it('handles already-slugified input', () => {
    expect(slugify('two-sum')).toBe('two-sum');
  });

  it('returns empty string for empty input', () => {
    expect(slugify('')).toBe('');
  });
});

// ---------------------------------------------------------------------------
// resolveCategory
// ---------------------------------------------------------------------------
describe('resolveCategory', () => {
  it('maps Array/Hash Table tags to a DSA category', () => {
    const res = resolveCategory(['Array', 'Hash Table'], 'Algorithms');
    expect(res.category).toBe('dsa');
    expect(res.subcategory).toBe('hashing');
  });

  it('maps Database categoryTitle to a database category', () => {
    const res = resolveCategory(['Database'], 'Database');
    expect(res.category).toBe('database');
    expect(res.subcategory).toBe('select-filtering');
  });

  it('infers database joins subcategory when SQL contains JOIN', () => {
    const res = resolveCategory(['Database'], 'Database', 'Write a solution to join Person and Address tables using LEFT JOIN');
    expect(res.category).toBe('database');
    expect(res.subcategory).toBe('joins');
  });

  it('infers database window functions subcategory', () => {
    const res = resolveCategory(['Database'], 'Database', 'DENSE_RANK() OVER (ORDER BY salary DESC)');
    expect(res.category).toBe('database');
    expect(res.subcategory).toBe('window-functions');
  });

  it('maps Dynamic Programming + Math tags to dsa/dynamic-programming', () => {
    const res = resolveCategory(['Dynamic Programming', 'Math'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'dynamic-programming' });
  });

  it('falls back to dsa/miscellaneous when no tags are provided', () => {
    const res = resolveCategory([], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'miscellaneous' });
  });

  it('resolves Tree tag to dsa/trees', () => {
    const res = resolveCategory(['Tree', 'Binary Tree'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'trees' });
  });

  it('resolves Graph tag correctly', () => {
    const res = resolveCategory(['Graph', 'Breadth-First Search'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'graphs' });
  });

  it('resolves Linked List tag correctly', () => {
    const res = resolveCategory(['Linked List'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'linked-lists' });
  });

  it('resolves Stack tag correctly', () => {
    const res = resolveCategory(['Stack', 'Array'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'stacks-queues' });
  });

  it('resolves String tag correctly', () => {
    const res = resolveCategory(['String'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'strings' });
  });

  it('resolves Binary Search tag correctly', () => {
    const res = resolveCategory(['Binary Search', 'Array'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'binary-search' });
  });

  it('resolves Two Pointers tag correctly', () => {
    const res = resolveCategory(['Two Pointers', 'Array'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'two-pointers' });
  });

  it('resolves Sliding Window tag correctly', () => {
    const res = resolveCategory(['Sliding Window'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'sliding-window' });
  });

  it('resolves Backtracking tag correctly', () => {
    const res = resolveCategory(['Backtracking'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'recursion-backtracking' });
  });

  it('resolves Greedy tag correctly', () => {
    const res = resolveCategory(['Greedy'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'greedy' });
  });

  it('resolves Sorting tag correctly', () => {
    const res = resolveCategory(['Sorting', 'Array'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'sorting' });
  });

  it('resolves Heap / Priority Queue tag correctly', () => {
    const res = resolveCategory(['Heap (Priority Queue)'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'heaps' });
  });

  it('resolves Bit Manipulation tag correctly', () => {
    const res = resolveCategory(['Bit Manipulation'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'bit-manipulation' });
  });

  it('resolves Math-only tag correctly', () => {
    const res = resolveCategory(['Math'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'mathematics' });
  });

  it('resolves Trie tag correctly', () => {
    const res = resolveCategory(['Trie'], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'tries' });
  });

  it('works with GraphQL object tags format { name, slug }', () => {
    const res = resolveCategory([{ name: 'Two Pointers', slug: 'two-pointers' }], 'Algorithms');
    expect(res).toEqual({ category: 'dsa', subcategory: 'two-pointers' });
  });
});
