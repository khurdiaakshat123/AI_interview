#!/usr/bin/env node

/**
 * @fileoverview Automated statement rephrasing pipeline.
 *
 * Rewrites problem statement narratives across DSA and Database questions
 * while strictly preserving:
 *   - Mathematical and algorithmic equivalence
 *   - Function signatures, parameter names, and return types
 *   - Constraints, examples, and test cases
 *   - Markdown tables, SQL schemas, images, and code blocks
 *
 * Supports:
 *   - Google Gemini API (GEMINI_API_KEY)
 *   - OpenAI API (OPENAI_API_KEY)
 *   - Local OpenAI-compatible API / Ollama
 *   - Dry-run and single-file testing
 *
 * Usage:
 *   node scripts/rephrase-statements.mjs --file questions/dsa/arrays/1-bit-and-2-bit-characters.json --dry-run
 *   node scripts/rephrase-statements.mjs --category database --limit 5
 *   node scripts/rephrase-statements.mjs --resume
 */

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, resolve, extname } from 'node:path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import dotenv from 'dotenv';
import {
  PROJECT_ROOT,
  QUESTIONS_DIR,
  MANIFESTS_DIR,
  SCHEMAS_DIR,
  ensureDir,
} from './utils.mjs';

dotenv.config();

/* ------------------------------------------------------------------ */
/*  Constants & Config                                                */
/* ------------------------------------------------------------------ */

const PROGRESS_FILE = join(MANIFESTS_DIR, 'rewrite-progress.json');

const SYSTEM_PROMPT = `You are an expert technical editor, computer science educator, and software engineer.
Your task is to rewrite the problem description of a coding interview or database challenge to provide completely original wording.

CRITICAL REQUIREMENTS:
1. DO NOT change the problem's mathematical intent, algorithmic logic, or rules in any way.
2. DO NOT change any parameter names, variable names, function names, class names, or return types (e.g., if it uses 'nums', 'target', 'k', do not change them).
3. DO NOT change any constraints, mathematical boundaries, complexity requirements, or time/space limitations.
4. DO NOT change any example inputs, outputs, explanations, or test data.
5. PRESERVE all Markdown table structures, ASCII diagrams, SQL schema definitions, and image references (e.g., ![...](./assets/...)).
6. REWRITE the introductory story, explanation, and instructions from scratch using clear, elegant, and unambiguous language.
7. Ensure zero ambiguity in the requirements.
8. Output ONLY the updated Markdown problem statement. Do not add conversational prefixes, markdown code fence wraps around the whole response, or meta-commentary.`;

/* ------------------------------------------------------------------ */
/*  CLI Argument Parsing                                              */
/* ------------------------------------------------------------------ */

const args = process.argv.slice(2);

function getArgValue(flag) {
  const idx = args.indexOf(flag);
  return idx !== -1 && idx + 1 < args.length ? args[idx + 1] : null;
}

const isDryRun = args.includes('--dry-run');
const isResume = args.includes('--resume');
const isForce = args.includes('--force');
const targetFile = getArgValue('--file');
const targetSlug = getArgValue('--slug');
const targetCategory = getArgValue('--category'); // 'dsa' | 'database'
const limitArg = getArgValue('--limit');
const limit = limitArg ? parseInt(limitArg, 10) : Infinity;
const modelName = getArgValue('--model') || process.env.REWRITE_MODEL || 'gemini-1.5-flash';

const geminiApiKey = process.env.GEMINI_API_KEY || getArgValue('--gemini-key');
const openaiApiKey = process.env.OPENAI_API_KEY || getArgValue('--openai-key');
const baseUrl = process.env.LLM_BASE_URL || getArgValue('--base-url');

/* ------------------------------------------------------------------ */
/*  Schema Validator Setup                                            */
/* ------------------------------------------------------------------ */

function setupValidator() {
  const schemaPath = join(SCHEMAS_DIR, 'question.schema.json');
  const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));
  const ajv = new Ajv({ allErrors: true, verbose: true, allowUnionTypes: true });
  addFormats(ajv);
  return ajv.compile(schema);
}

const validateQuestion = setupValidator();

/* ------------------------------------------------------------------ */
/*  Progress Tracking                                                 */
/* ------------------------------------------------------------------ */

function loadProgress() {
  if (existsSync(PROGRESS_FILE)) {
    try {
      return JSON.parse(readFileSync(PROGRESS_FILE, 'utf-8'));
    } catch {
      // Fallback if corrupted
    }
  }
  return {
    totalProcessed: 0,
    completed: {}, // slug -> timestamp
    failed: {},    // slug -> error
    lastRun: null,
  };
}

function saveProgress(progress) {
  ensureDir(MANIFESTS_DIR);
  progress.lastRun = new Date().toISOString();
  writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2), 'utf-8');
}

/* ------------------------------------------------------------------ */
/*  File Discovery                                                    */
/* ------------------------------------------------------------------ */

function findQuestionFiles(dir) {
  let results = [];
  const entries = readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== 'assets') {
      results = results.concat(findQuestionFiles(fullPath));
    } else if (entry.isFile() && extname(entry.name) === '.json') {
      results.push(fullPath);
    }
  }
  return results;
}

/* ------------------------------------------------------------------ */
/*  LLM Providers                                                     */
/* ------------------------------------------------------------------ */

async function callGemini(prompt, apiKey) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${apiKey}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: {
        parts: [{ text: SYSTEM_PROMPT }],
      },
      contents: [
        {
          parts: [{ text: prompt }],
        },
      ],
      generationConfig: {
        temperature: 0.2,
      },
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Gemini API error (${response.status}): ${errorBody}`);
  }

  const data = await response.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) {
    throw new Error('Gemini API returned empty text');
  }
  return cleanOutput(text);
}

async function callOpenAICompatible(prompt, apiKey, endpoint) {
  const url = endpoint || 'https://api.openai.com/v1/chat/completions';
  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      model: modelName.startsWith('gemini') ? 'gpt-4o-mini' : modelName,
      temperature: 0.2,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: prompt },
      ],
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`OpenAI API error (${response.status}): ${errorBody}`);
  }

  const data = await response.json();
  const text = data?.choices?.[0]?.message?.content;
  if (!text) {
    throw new Error('OpenAI API returned empty response');
  }
  return cleanOutput(text);
}

function cleanOutput(text) {
  let cleaned = text.trim();
  // Strip enclosing ```markdown ... ``` if the LLM wrapped everything in it
  if (cleaned.startsWith('```markdown') && cleaned.endsWith('```')) {
    cleaned = cleaned.slice(11, -3).trim();
  } else if (cleaned.startsWith('```') && cleaned.endsWith('```')) {
    cleaned = cleaned.slice(3, -3).trim();
  }
  return cleaned;
}

/**
 * Dispatches prompt to the appropriate LLM provider.
 */
async function generateRewrittenStatement(question) {
  const prompt = `Please rephrase the following problem statement. Keep all variables, constraints, examples, tables, and images unchanged. Only rephrase the explanatory narrative into clear, fresh, professional wording:

---
Title: ${question.title}
Category: ${question.category} / ${question.subcategory}
Difficulty: ${question.difficulty}

Original Statement:
${question.statement}
---`;

  if (geminiApiKey) {
    return await callGemini(prompt, geminiApiKey);
  } else if (openaiApiKey || baseUrl) {
    return await callOpenAICompatible(prompt, openaiApiKey, baseUrl);
  } else {
    throw new Error('No LLM API key provided. Set GEMINI_API_KEY or OPENAI_API_KEY in .env or pass via CLI.');
  }
}

/* ------------------------------------------------------------------ */
/*  Main Processing Pipeline                                          */
/* ------------------------------------------------------------------ */

async function main() {
  console.log('═'.repeat(60));
  console.log('  LeetCode Question Bank Statement Rephrasing Pipeline');
  console.log('═'.repeat(60));

  // Check API keys
  if (!isDryRun && !geminiApiKey && !openaiApiKey && !baseUrl) {
    console.error('\n⚠️  Error: No API key detected.');
    console.error('Please configure GEMINI_API_KEY or OPENAI_API_KEY in .env, or use --gemini-key / --openai-key.');
    console.error('Example:');
    console.error('  node scripts/rephrase-statements.mjs --file questions/dsa/arrays/1-bit-and-2-bit-characters.json --dry-run\n');
    process.exit(1);
  }

  // Find candidate files
  let files = [];
  if (targetFile) {
    files = [resolve(PROJECT_ROOT, targetFile)];
  } else {
    files = findQuestionFiles(QUESTIONS_DIR);
  }

  // Filter by category if specified
  if (targetCategory) {
    files = files.filter((f) => f.includes(`${targetCategory}`));
  }

  // Filter by slug if specified
  if (targetSlug) {
    files = files.filter((f) => f.endsWith(`${targetSlug}.json`));
  }

  const progress = loadProgress();

  // Filter out completed if resuming
  if (isResume && !isForce) {
    files = files.filter((f) => {
      const slug = f.replace(/.*[\\/]([^\\/]+)\.json$/, '$1');
      return !progress.completed[slug];
    });
  }

  // Apply limit
  if (files.length > limit) {
    files = files.slice(0, limit);
  }

  console.log(`\nFound ${files.length} question(s) to process.`);
  if (isDryRun) console.log('Mode: DRY-RUN (no changes will be written)');

  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < files.length; i++) {
    const filePath = files[i];
    const relPath = filePath.replace(PROJECT_ROOT + '\\', '').replace(PROJECT_ROOT + '/', '');

    let question;
    try {
      question = JSON.parse(readFileSync(filePath, 'utf-8'));
    } catch (err) {
      console.error(`[${i + 1}/${files.length}] Failed to parse ${relPath}: ${err.message}`);
      failCount++;
      continue;
    }

    console.log(`\n[${i + 1}/${files.length}] Rephrasing: ${question.slug} (${question.category}/${question.subcategory})`);

    try {
      const rewrittenStatement = await generateRewrittenStatement(question);

      if (!rewrittenStatement || rewrittenStatement.length < 20) {
        throw new Error('Generated statement is suspiciously short');
      }

      if (isDryRun) {
        console.log('\n--- BEFORE ---');
        console.log(question.statement.slice(0, 300) + '...');
        console.log('\n--- AFTER ---');
        console.log(rewrittenStatement.slice(0, 300) + '...');
        successCount++;
        continue;
      }

      // Update question and validate schema
      const updatedQuestion = {
        ...question,
        statement: rewrittenStatement,
      };

      const isValid = validateQuestion(updatedQuestion);
      if (!isValid) {
        const errorDetails = JSON.stringify(validateQuestion.errors, null, 2);
        throw new Error(`Schema validation failed:\n${errorDetails}`);
      }

      // Write updated file
      writeFileSync(filePath, JSON.stringify(updatedQuestion, null, 2) + '\n', 'utf-8');

      // Record progress
      progress.completed[question.slug] = new Date().toISOString();
      delete progress.failed[question.slug];
      progress.totalProcessed++;
      saveProgress(progress);

      console.log(`  ✅ Successfully updated and validated ${relPath}`);
      successCount++;

      // Brief delay to prevent hitting rate limits
      await new Promise((r) => setTimeout(r, 600));
    } catch (err) {
      console.error(`  ❌ Failed for ${question.slug}: ${err.message}`);
      progress.failed[question.slug] = err.message;
      saveProgress(progress);
      failCount++;
    }
  }

  console.log('\n' + '═'.repeat(60));
  console.log(`Pipeline finished: ${successCount} succeeded, ${failCount} failed.`);
  console.log('═'.repeat(60));
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
