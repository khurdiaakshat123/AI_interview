#!/usr/bin/env node

/**
 * @fileoverview Validates question JSON files against the schema.
 *
 * Usage:
 *   node scripts/validate.mjs [--fix] [--file <path>]
 *
 * Flags:
 *   --fix          Auto-fix minor issues (e.g., missing trailing newline)
 *   --file <path>  Validate a single file instead of the entire collection
 *
 * Exit code 1 when any validation error is found.
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, basename, dirname, sep } from 'node:path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import {
  PROJECT_ROOT,
  QUESTIONS_DIR,
  SCHEMAS_DIR,
  slugify,
} from './utils.mjs';

/* ------------------------------------------------------------------ */
/*  CLI argument parsing                                               */
/* ------------------------------------------------------------------ */

const args = process.argv.slice(2);
const fixMode = args.includes('--fix');
const fileIdx = args.indexOf('--file');
const singleFile = fileIdx !== -1 ? args[fileIdx + 1] : null;

/* ------------------------------------------------------------------ */
/*  Schema setup                                                       */
/* ------------------------------------------------------------------ */

/**
 * Loads and compiles the question JSON Schema.
 * @returns {import('ajv').ValidateFunction} Compiled AJV validator
 */
function loadSchema() {
  const schemaPath = join(SCHEMAS_DIR, 'question.schema.json');
  const raw = readFileSync(schemaPath, 'utf-8');
  const schema = JSON.parse(raw);

  const ajv = new Ajv({ allErrors: true, verbose: true, allowUnionTypes: true });
  addFormats(ajv);

  return ajv.compile(schema);
}

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
/*  Validation helpers                                                 */
/* ------------------------------------------------------------------ */

/**
 * @typedef {Object} ValidationResult
 * @property {string}   file    - Relative path to the file
 * @property {boolean}  valid   - Whether the file passed all checks
 * @property {string[]} errors  - List of error messages
 * @property {boolean}  fixed   - Whether any auto-fix was applied
 */

/**
 * Validates a single question JSON file.
 *
 * Checks performed:
 *  1. JSON parse correctness
 *  2. Schema validation via AJV
 *  3. File path ↔ category / subcategory consistency
 *  4. Filename ↔ slug consistency
 *
 * @param {string} filePath               - Absolute path to the file
 * @param {import('ajv').ValidateFunction} validate - Compiled AJV validator
 * @param {boolean} fix                   - Whether to attempt auto-fixes
 * @returns {ValidationResult}
 */
function validateFile(filePath, validate, fix) {
  const relPath = relative(PROJECT_ROOT, filePath).split(sep).join('/');
  /** @type {string[]} */
  const errors = [];
  let fixed = false;

  /* 1. Parse JSON -------------------------------------------------- */
  let raw;
  let data;
  try {
    raw = readFileSync(filePath, 'utf-8');
    data = JSON.parse(raw);
  } catch (err) {
    errors.push(`JSON parse error: ${/** @type {Error} */ (err).message}`);
    return { file: relPath, valid: false, errors, fixed };
  }

  /* 2. Schema validation ------------------------------------------- */
  const schemaValid = validate(data);
  if (!schemaValid && validate.errors) {
    for (const e of validate.errors) {
      const path = e.instancePath || '(root)';
      errors.push(`Schema: ${path} ${e.message}`);
    }
  }

  /* 3. Path ↔ category / subcategory ------------------------------- */
  // Expected layout: questions/<category>/<subcategory>/<slug>.json
  const relFromQuestions = relative(QUESTIONS_DIR, filePath).split(sep).join('/');
  const parts = relFromQuestions.split('/');

  if (parts.length >= 3) {
    const [dirCategory, dirSubcategory] = parts;

    if (data.category && data.category !== dirCategory) {
      errors.push(
        `Path mismatch: file is in category "${dirCategory}" but JSON has category "${data.category}"`
      );
    }

    if (data.subcategory && data.subcategory !== dirSubcategory) {
      errors.push(
        `Path mismatch: file is in subcategory "${dirSubcategory}" but JSON has subcategory "${data.subcategory}"`
      );
    }
  }

  /* 4. Filename ↔ slug --------------------------------------------- */
  const fileSlug = basename(filePath, '.json');
  if (data.slug && data.slug !== fileSlug) {
    errors.push(
      `Slug mismatch: filename implies slug "${fileSlug}" but JSON has slug "${data.slug}"`
    );
  }

  /* 5. Auto-fix minor issues --------------------------------------- */
  if (fix) {
    let rewrite = false;

    // Fix: ensure trailing newline
    if (raw && !raw.endsWith('\n')) {
      raw = raw + '\n';
      rewrite = true;
    }

    // Fix: re-format with consistent 2-space indent + trailing newline
    const formatted = JSON.stringify(data, null, 2) + '\n';
    if (raw !== formatted) {
      raw = formatted;
      rewrite = true;
    }

    if (rewrite) {
      writeFileSync(filePath, raw, 'utf-8');
      fixed = true;
    }
  }

  return { file: relPath, valid: errors.length === 0, errors, fixed };
}

/* ------------------------------------------------------------------ */
/*  Main                                                               */
/* ------------------------------------------------------------------ */

/**
 * Entry point – discovers files, validates, and prints a report.
 */
async function main() {
  const validate = loadSchema();

  /* Determine which files to validate */
  /** @type {string[]} */
  let files;

  if (singleFile) {
    const resolved = join(PROJECT_ROOT, singleFile);
    files = [resolved];
  } else {
    files = findJsonFiles(QUESTIONS_DIR);
  }

  if (files.length === 0) {
    console.log('No question files found.');
    process.exit(0);
  }

  console.log(`\nValidating ${files.length} file(s)…\n`);

  /** @type {ValidationResult[]} */
  const results = [];

  for (const f of files) {
    const result = validateFile(f, validate, fixMode);
    results.push(result);
  }

  /* Report --------------------------------------------------------- */
  const valid = results.filter((r) => r.valid);
  const invalid = results.filter((r) => !r.valid);
  const fixedCount = results.filter((r) => r.fixed).length;

  console.log('─'.repeat(60));
  console.log(`  Total files : ${results.length}`);
  console.log(`  Valid       : ${valid.length}`);
  console.log(`  Invalid     : ${invalid.length}`);
  if (fixMode) {
    console.log(`  Fixed       : ${fixedCount}`);
  }
  console.log('─'.repeat(60));

  if (invalid.length > 0) {
    console.log('\n❌  Errors by file:\n');
    for (const r of invalid) {
      console.log(`  ${r.file}`);
      for (const e of r.errors) {
        console.log(`    • ${e}`);
      }
      console.log();
    }
  } else {
    console.log('\n✅  All files are valid.\n');
  }

  process.exit(invalid.length > 0 ? 1 : 0);
}

main();
