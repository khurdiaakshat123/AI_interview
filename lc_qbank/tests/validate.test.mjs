/**
 * @file Unit tests for JSON schema validation of question files.
 * Loads the actual schema from schemas/question.schema.json and validates
 * various question objects against it.
 */
import { describe, it, expect, beforeAll } from 'vitest';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('ajv').ValidateFunction} */
let validate;

beforeAll(() => {
  const schemaPath = path.resolve(__dirname, '..', 'schemas', 'question.schema.json');
  const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));

  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  validate = ajv.compile(schema);
});

/**
 * Returns a valid baseline question object compliant with schemas/question.schema.json.
 * @param {object} [overrides={}]
 * @returns {object} A valid question object.
 */
function makeValidQuestion(overrides = {}) {
  return {
    id: '1',
    slug: 'two-sum',
    title: 'Two Sum',
    category: 'dsa',
    subcategory: 'arrays',
    difficulty: 'Easy',
    tags: ['Array', 'Hash Table'],
    statement: 'Given an array of integers `nums` and an integer `target`...',
    constraints: ['2 <= nums.length <= 10^4'],
    examples: [
      {
        input: 'nums = [2,7,11,15], target = 9',
        output: '[0,1]',
        explanation: 'Because nums[0] + nums[1] == 9, we return [0, 1].',
      },
    ],
    starterCode: {
      javascript: 'var twoSum = function(nums, target) {};',
      python3: 'class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:',
    },
    publicTests: [
      {
        input: '[2,7,11,15]\n9',
        expectedOutput: '[0,1]',
      },
    ],
    sqlSchema: null,
    sqlSetup: null,
    expectedOutput: null,
    solution: null,
    hints: ['A really brute force way would be to search for all possible pairs of numbers but that would be too slow.'],
    testCases: [
      {
        input: '[2,7,11,15]\n9',
        expectedOutput: '[0,1]',
      },
    ],
    source: {
      name: 'LeetCode',
      url: 'https://leetcode.com/problems/two-sum/',
      licenseOrPermissionReference: 'Authorized collection',
      collectedAt: new Date().toISOString(),
      sourceUpdatedAt: null,
    },
    ...overrides,
  };
}

describe('Question schema validation', () => {
  it('accepts a valid DSA question', () => {
    const question = makeValidQuestion();
    const valid = validate(question);
    expect(valid, JSON.stringify(validate.errors)).toBe(true);
  });

  it('rejects a question missing the required "title" field', () => {
    const question = makeValidQuestion();
    delete question.title;
    const valid = validate(question);
    expect(valid).toBe(false);
    expect(validate.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ keyword: 'required', params: { missingProperty: 'title' } }),
      ])
    );
  });

  it('rejects a question missing the required "id" field', () => {
    const question = makeValidQuestion();
    delete question.id;
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects a question missing the required "slug" field', () => {
    const question = makeValidQuestion();
    delete question.slug;
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects a question missing the required "difficulty" field', () => {
    const question = makeValidQuestion();
    delete question.difficulty;
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects a question missing the required "category" field', () => {
    const question = makeValidQuestion();
    delete question.category;
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects an invalid difficulty value', () => {
    const question = makeValidQuestion({ difficulty: 'Impossible' });
    const valid = validate(question);
    expect(valid).toBe(false);
    expect(validate.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ keyword: 'enum' }),
      ])
    );
  });

  it('rejects an invalid category value', () => {
    const question = makeValidQuestion({ category: 'invalid-category' });
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('accepts a valid database question with sqlSchema', () => {
    const question = makeValidQuestion({
      id: '175',
      slug: 'combine-two-tables',
      title: 'Combine Two Tables',
      category: 'database',
      subcategory: 'joins',
      tags: ['Database'],
      starterCode: {
        mysql: 'SELECT firstName, lastName, city, state FROM Person LEFT JOIN Address ON Person.personId = Address.personId;',
      },
      sqlSchema: 'Create table If Not Exists Person (personId int, firstName varchar(255), lastName varchar(255));',
      sqlSetup: [
        "insert into Person (personId, lastName, firstName) values ('1', 'Wang', 'Allen')",
      ],
      source: {
        name: 'LeetCode',
        url: 'https://leetcode.com/problems/combine-two-tables/',
        licenseOrPermissionReference: 'Authorized collection',
        collectedAt: new Date().toISOString(),
        sourceUpdatedAt: null,
      },
    });
    const valid = validate(question);
    expect(valid, JSON.stringify(validate.errors)).toBe(true);
  });

  it('accepts a valid DSA question with starterCode', () => {
    const question = makeValidQuestion();
    const valid = validate(question);
    expect(valid).toBe(true);
    expect(question.starterCode).toBeDefined();
  });

  it('accepts an empty tags array', () => {
    const question = makeValidQuestion({ tags: [] });
    const valid = validate(question);
    expect(valid).toBe(true);
  });

  it('rejects when tags is not an array', () => {
    const question = makeValidQuestion({ tags: 'Array' });
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects when id is not a string', () => {
    const question = makeValidQuestion({ id: 123 });
    const valid = validate(question);
    expect(valid).toBe(false);
  });

  it('rejects additional unrecognized properties due to additionalProperties: false', () => {
    const question = makeValidQuestion({ unknownField: 'unexpected' });
    const valid = validate(question);
    expect(valid).toBe(false);
  });
});
