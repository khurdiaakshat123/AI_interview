# LeetCode Question Bank — GitHub JSON Repository

A structured, resilient JSON question bank collected from LeetCode, organized by topic and category. Each question is normalized into an individual JSON file, validated against a strict JSON Schema, and indexed in manifest files.

The GitHub repository serves as the single source of truth for downstream coding interview and learning platforms.

## Repository Structure

```text
leetcode-question-bank/
├── questions/
│   ├── dsa/
│   │   ├── arrays/
│   │   ├── strings/
│   │   ├── hashing/
│   │   ├── two-pointers/
│   │   ├── sliding-window/
│   │   ├── binary-search/
│   │   ├── linked-lists/
│   │   ├── stacks-queues/
│   │   ├── trees/
│   │   ├── heaps/
│   │   ├── graphs/
│   │   ├── recursion-backtracking/
│   │   ├── greedy/
│   │   ├── dynamic-programming/
│   │   ├── tries/
│   │   ├── bit-manipulation/
│   │   └── mathematics/
│   └── database/
│       ├── select-filtering/
│       ├── joins/
│       ├── aggregation/
│       ├── subqueries/
│       ├── cte/
│       ├── window-functions/
│       ├── date-time/
│       ├── string-functions/
│       ├── null-handling/
│       └── set-operations/
├── schemas/
│   └── question.schema.json
├── manifests/
│   ├── questions-index.json
│   ├── collection-state.json
│   └── source-manifest.json
├── scripts/
│   ├── discover.mjs
│   ├── collect.mjs
│   ├── normalize.mjs
│   ├── validate.mjs
│   ├── deduplicate.mjs
│   ├── sync-github.mjs
│   ├── generate-report.mjs
│   └── utils.mjs
├── reports/
│   ├── collection-report.json
│   └── collection-report.md
├── tests/
│   ├── normalize.test.mjs
│   ├── validate.test.mjs
│   └── deduplicate.test.mjs
├── .github/
│   └── workflows/
│       └── validate-json.yml
├── .env.example
├── .gitignore
├── package.json
└── README.md
```

## Setup

```bash
# Clone the repository
git clone https://github.com/Sanchit586/leetcode-question-bank.git
cd leetcode-question-bank

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
```

### Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `LEETCODE_API_URL` | `https://leetcode.com/graphql` | LeetCode GraphQL API endpoint |
| `GITHUB_REPO_OWNER` | `Sanchit586` | Target GitHub repository owner |
| `GITHUB_REPO_NAME` | `leetcode-question-bank` | Target GitHub repository name |
| `GITHUB_BRANCH` | `main` | Target branch |
| `COLLECTION_BATCH_SIZE` | `50` | Pagination page size |
| `COLLECTION_DELAY_MS` | `1500` | Rate-limit delay between requests |
| `COLLECTION_MAX_RETRIES` | `3` | Maximum retry attempts with exponential backoff |

## Pipeline Commands

### 1. Discovery
Discovers question inventory via LeetCode's GraphQL API and writes to `manifests/collection-state.json`:
```bash
npm run discover
# Or discover a sample subset for testing:
node scripts/discover.mjs --limit 10
```

### 2. Collection
Fetches full problem details with checkpointing after every item:
```bash
npm run collect
# Options:
node scripts/collect.mjs --limit 10   # Collect only 10 questions
node scripts/collect.mjs --resume     # Skip already-collected raw files
```

### 3. Normalization
Converts raw API data into Markdown and structured schema-compliant JSON files:
```bash
npm run normalize
# Options:
node scripts/normalize.mjs --force             # Re-normalize all files
node scripts/normalize.mjs --slug two-sum      # Normalize specific question
```

### 4. Validation
Validates all JSON files against `schemas/question.schema.json` and directory structure rules:
```bash
npm run validate
# Auto-fix minor issues:
node scripts/validate.mjs --fix
```

### 5. Deduplication
Audits for duplicate IDs or filename collisions:
```bash
npm run deduplicate
# Remove true duplicates keeping the authoritative category path:
node scripts/deduplicate.mjs --remove
```

### 6. Reports & Manifests
Generates `manifests/questions-index.json`, `manifests/source-manifest.json`, and reports:
```bash
npm run report
# CI verification mode:
node scripts/generate-report.mjs --verify-only
```

### 7. GitHub Synchronization
Synchronizes question files safely with GitHub:
```bash
# Preview changes (Dry run):
npm run sync:dry-run

# Commit and push changes:
npm run sync
```

### 8. Run All Tests
```bash
npm test
```

## JSON Schema Specification

Every question is stored in its own file (`questions/<category>/<subcategory>/<slug>.json`) and strictly validated against `schemas/question.schema.json`:

```json
{
  "id": "1",
  "slug": "two-sum",
  "title": "Two Sum",
  "category": "dsa",
  "subcategory": "hashing",
  "difficulty": "Easy",
  "tags": ["Array", "Hash Table"],
  "statement": "Markdown formatted problem statement...",
  "constraints": ["2 <= nums.length <= 10^4"],
  "examples": [
    {
      "input": "nums = [2,7,11,15], target = 9",
      "output": "[0,1]",
      "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
    }
  ],
  "starterCode": {
    "javascript": "/**\n * @param {number[]} nums\n...",
    "python3": "class Solution:\n    def twoSum..."
  },
  "publicTests": [
    {
      "input": "[2,7,11,15]\n9",
      "expectedOutput": "[0,1]"
    }
  ],
  "sqlSchema": null,
  "sqlSetup": null,
  "expectedOutput": null,
  "solution": null,
  "hints": ["A really brute force way would be to search for all possible pairs..."],
  "stats": {
    "totalAccepted": "2.1M",
    "totalSubmission": "4.2M",
    "acRate": "50.1%"
  },
  "source": {
    "name": "LeetCode",
    "url": "https://leetcode.com/problems/two-sum/",
    "licenseOrPermissionReference": "Authorized collection",
    "collectedAt": "2026-10-16T19:17:50.371Z",
    "sourceUpdatedAt": null
  }
}
```

## Continuous Integration

The repository includes a GitHub Actions workflow (`.github/workflows/validate-json.yml`) that runs on every push and pull request to `main`:
1. Installs dependencies (`npm ci`)
2. Validates all question JSON files (`npm run validate`)
3. Checks for duplicate IDs (`npm run deduplicate`)
4. Runs full unit test suite (`npm test`)
5. Verifies index integrity against disk files (`node scripts/generate-report.mjs --verify-only`)

## License

MIT
