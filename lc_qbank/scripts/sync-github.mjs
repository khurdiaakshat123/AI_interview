#!/usr/bin/env node

/**
 * @fileoverview Synchronizes the local question bank with GitHub.
 *
 * Usage:
 *   node scripts/sync-github.mjs --dry-run   (default — show what would happen)
 *   node scripts/sync-github.mjs --sync      (stage, commit, pull --rebase, push)
 *
 * Safety guarantees:
 *   • Never force-pushes
 *   • Never deletes files automatically (reports them for manual review)
 *   • Aborts and reports on rebase conflicts
 */

import { execSync } from 'node:child_process';
import { PROJECT_ROOT } from './utils.mjs';

/* ------------------------------------------------------------------ */
/*  CLI argument parsing                                               */
/* ------------------------------------------------------------------ */

const args = process.argv.slice(2);
const syncMode = args.includes('--sync');
const dryRunMode = args.includes('--dry-run') || !syncMode;

/* ------------------------------------------------------------------ */
/*  Git helpers                                                        */
/* ------------------------------------------------------------------ */

/**
 * Runs a git command synchronously in the project root.
 * @param {string} cmd - Full command string (without "git" prefix)
 * @param {object} [opts]
 * @param {boolean} [opts.ignoreError=false] - If true, swallow non-zero exits
 * @returns {string} stdout trimmed
 */
function git(cmd, { ignoreError = false } = {}) {
  try {
    return execSync(`git ${cmd}`, {
      cwd: PROJECT_ROOT,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch (err) {
    if (ignoreError) return '';
    throw err;
  }
}

/**
 * Checks whether the current directory is inside a git repository.
 * @returns {boolean}
 */
function isGitRepo() {
  try {
    git('rev-parse --is-inside-work-tree');
    return true;
  } catch {
    return false;
  }
}

/* ------------------------------------------------------------------ */
/*  Change detection                                                   */
/* ------------------------------------------------------------------ */

/**
 * @typedef {Object} ChangeSet
 * @property {string[]} added     - New (untracked + staged-new) files
 * @property {string[]} modified  - Modified files
 * @property {string[]} deleted   - Deleted files
 */

/**
 * Detects changes in tracked directories.
 * @returns {ChangeSet}
 */
function detectChanges() {
  // Ensure the index is up to date
  git('status --porcelain', { ignoreError: true });

  const statusOutput = git('status --porcelain');
  const lines = statusOutput ? statusOutput.split('\n') : [];

  /** @type {string[]} */
  const added = [];
  /** @type {string[]} */
  const modified = [];
  /** @type {string[]} */
  const deleted = [];

  const trackedDirs = ['questions/', 'manifests/', 'reports/', 'schemas/'];

  for (const line of lines) {
    if (!line || line.length < 4) continue;

    const status = line.substring(0, 2);
    const file = line.substring(3).trim();

    // Only consider files in tracked directories
    const inTracked = trackedDirs.some((d) => file.startsWith(d));
    if (!inTracked) continue;

    if (status.includes('?')) {
      added.push(file);
    } else if (status.includes('D')) {
      deleted.push(file);
    } else if (status.includes('M') || status.includes('A')) {
      // 'A' in index = staged new file, 'M' = modified
      if (status.trim() === 'A') {
        added.push(file);
      } else {
        modified.push(file);
      }
    } else {
      modified.push(file);
    }
  }

  return { added, modified, deleted };
}

/* ------------------------------------------------------------------ */
/*  Commit message generation                                          */
/* ------------------------------------------------------------------ */

/**
 * Builds a descriptive commit message based on the changes detected.
 * @param {ChangeSet} changes
 * @returns {string}
 */
function buildCommitMessage(changes) {
  const parts = [];

  if (changes.added.length > 0) {
    // Determine predominant category
    const dsaCount = changes.added.filter((f) => f.startsWith('questions/dsa/')).length;
    const dbCount = changes.added.filter((f) => f.startsWith('questions/database/')).length;
    const manifestCount = changes.added.filter((f) => f.startsWith('manifests/')).length;
    const questionCount = changes.added.filter((f) => f.startsWith('questions/')).length;

    if (questionCount > 0) {
      if (dsaCount > 0 && dbCount === 0) {
        parts.push(`Add ${questionCount} new DSA question${questionCount > 1 ? 's' : ''}`);
      } else if (dbCount > 0 && dsaCount === 0) {
        parts.push(`Add ${questionCount} new database question${questionCount > 1 ? 's' : ''}`);
      } else {
        parts.push(`Add ${questionCount} new question${questionCount > 1 ? 's' : ''}`);
      }
    }

    if (manifestCount > 0) {
      parts.push('update manifests');
    }
  }

  if (changes.modified.length > 0) {
    const modQuestions = changes.modified.filter((f) => f.startsWith('questions/')).length;
    const modManifests = changes.modified.filter((f) => f.startsWith('manifests/')).length;

    if (modQuestions > 0) {
      parts.push(`Update ${modQuestions} question${modQuestions > 1 ? 's' : ''}`);
    }
    if (modManifests > 0 && !parts.some((p) => p.includes('manifest'))) {
      parts.push('update manifests');
    }
  }

  if (parts.length === 0) {
    return 'Update question bank';
  }

  // Capitalize first segment, join with " and "
  const msg = parts.join(' and ');
  return msg.charAt(0).toUpperCase() + msg.slice(1);
}

/* ------------------------------------------------------------------ */
/*  Validation                                                         */
/* ------------------------------------------------------------------ */

/**
 * Runs the validation script. Returns true if validation passed.
 * @returns {boolean}
 */
function runValidation() {
  try {
    execSync('node scripts/validate.mjs', {
      cwd: PROJECT_ROOT,
      encoding: 'utf-8',
      stdio: 'inherit',
    });
    return true;
  } catch {
    return false;
  }
}

/* ------------------------------------------------------------------ */
/*  Main                                                               */
/* ------------------------------------------------------------------ */

/**
 * Entry point – detects changes, validates, and optionally syncs with GitHub.
 */
async function main() {
  console.log(`\nMode: ${syncMode ? '🔄 SYNC' : '👁  DRY-RUN'}\n`);

  /* 1. Check git repo ---------------------------------------------- */
  if (!isGitRepo()) {
    console.error('❌  Not inside a git repository. Aborting.');
    process.exit(1);
  }

  const branch = git('branch --show-current', { ignoreError: true }) || 'main';
  console.log(`  Branch : ${branch}`);

  /* 2. Run validation ---------------------------------------------- */
  console.log('\n  Running validation…');
  const validationOk = runValidation();
  if (!validationOk) {
    console.error('\n❌  Validation failed. Fix errors before syncing.');
    if (syncMode) process.exit(1);
  }

  /* 3. Detect changes ---------------------------------------------- */
  const changes = detectChanges();
  const totalChanges = changes.added.length + changes.modified.length + changes.deleted.length;

  console.log(`\n  Changes detected: ${totalChanges}`);
  console.log(`    New      : ${changes.added.length}`);
  console.log(`    Modified : ${changes.modified.length}`);
  console.log(`    Deleted  : ${changes.deleted.length}`);

  if (totalChanges === 0) {
    console.log('\n✅  Nothing to sync.\n');
    process.exit(0);
  }

  /* 4. Report deletions for manual review -------------------------- */
  if (changes.deleted.length > 0) {
    console.log('\n  ⚠  Deleted files (require manual review):');
    for (const f of changes.deleted) {
      console.log(`    • ${f}`);
    }
    console.log('  These will NOT be staged automatically.\n');
  }

  /* 5. Dry-run mode ------------------------------------------------ */
  if (dryRunMode) {
    console.log('\n  📋  Would commit the following:');
    for (const f of [...changes.added, ...changes.modified]) {
      console.log(`    + ${f}`);
    }
    const msg = buildCommitMessage(changes);
    console.log(`\n  Commit message: "${msg}"`);
    console.log('\n  Run with --sync to execute.\n');
    process.exit(0);
  }

  /* 6. Sync mode --------------------------------------------------- */
  console.log('\n  Staging changes…');

  // Stage tracked directories (excluding deleted files)
  const stageDirs = ['questions/', 'manifests/', 'reports/', 'schemas/'];
  for (const dir of stageDirs) {
    git(`add ${dir}`, { ignoreError: true });
  }

  // Build commit message
  const commitMsg = buildCommitMessage(changes);
  console.log(`  Commit message: "${commitMsg}"`);

  // Commit
  try {
    git(`commit -m "${commitMsg.replace(/"/g, '\\"')}"`);
    console.log('  ✔  Committed.');
  } catch (err) {
    console.error('  ❌  Commit failed:', /** @type {Error} */ (err).message);
    process.exit(1);
  }

  // Pull with rebase if remote tracking exists
  console.log('  Checking remote status…');
  try {
    git(`pull --rebase origin ${branch}`);
    console.log('  ✔  Rebased successfully.');
  } catch (err) {
    const errMsg = /** @type {Error} */ (err).message || '';
    if (errMsg.includes('CONFLICT') || errMsg.includes('conflict')) {
      console.error('\n  ❌  Rebase conflict detected. Aborting rebase…');
      git('rebase --abort', { ignoreError: true });
      console.error('  Please resolve conflicts manually and try again.\n');
      process.exit(1);
    } else {
      console.log('  ℹ  Remote branch not yet present or already up to date.');
    }
  }

  // Push
  console.log(`  Pushing to origin/${branch}…`);
  try {
    git(`push -u origin ${branch}`);
    console.log('  ✔  Pushed successfully.');
  } catch (err) {
    console.error('  ❌  Push failed:', /** @type {Error} */ (err).message);
    console.error('  Never force-pushing. Please resolve manually.\n');
    process.exit(1);
  }

  console.log('\n✅  Sync complete.\n');
}

main();
