/**
 * @fileoverview Test Engine for generating and verifying test cases per problem.
 * Ensures every test case has a verified, non-null expected output free of HTML entities.
 * @module test-engine
 */

import { unescapeHtml } from './utils.mjs';

/**
 * Reference solvers for popular / standard algorithmic problems to compute
 * 100% verified expected outputs on custom edge/scale test cases.
 */
const solvers = {
  'two-sum': (inp) => {
    try {
      const [arrStr, tStr] = inp.split('\n');
      const nums = JSON.parse(arrStr);
      const target = parseInt(tStr, 10);
      const map = new Map();
      for (let i = 0; i < nums.length; i++) {
        const complement = target - nums[i];
        if (map.has(complement)) return JSON.stringify([map.get(complement), i]);
        map.set(nums[i], i);
      }
      return null;
    } catch {
      return null;
    }
  },

  'build-an-array-with-stack-operations': (inp) => {
    try {
      const [arrStr, nStr] = inp.split('\n');
      const target = JSON.parse(arrStr);
      const n = parseInt(nStr, 10);
      if (!Array.isArray(target) || isNaN(n) || n < 1) return null;
      const res = [];
      let curr = 1;
      for (const t of target) {
        if (t > n || t < curr) return null;
        while (curr < t) {
          res.push('Push');
          res.push('Pop');
          curr++;
        }
        res.push('Push');
        curr++;
      }
      return JSON.stringify(res);
    } catch {
      return null;
    }
  },

  'valid-parentheses': (inp) => {
    try {
      const s = JSON.parse(inp);
      if (typeof s !== 'string') return null;
      const stack = [];
      const map = { ')': '(', '}': '{', ']': '[' };
      for (const ch of s) {
        if (ch === '(' || ch === '{' || ch === '[') stack.push(ch);
        else if (stack.pop() !== map[ch]) return 'false';
      }
      return stack.length === 0 ? 'true' : 'false';
    } catch {
      return null;
    }
  },

  'palindrome-number': (inp) => {
    try {
      const s = inp.trim();
      if (s.startsWith('-')) return 'false';
      return s === s.split('').reverse().join('') ? 'true' : 'false';
    } catch {
      return null;
    }
  },

  'roman-to-integer': (inp) => {
    try {
      const s = JSON.parse(inp);
      if (typeof s !== 'string') return null;
      const val = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
      let total = 0;
      for (let i = 0; i < s.length; i++) {
        if (i + 1 < s.length && val[s[i]] < val[s[i + 1]]) total -= val[s[i]];
        else total += val[s[i]];
      }
      return String(total);
    } catch {
      return null;
    }
  },

  'climbing-stairs': (inp) => {
    try {
      const n = parseInt(inp.trim(), 10);
      if (isNaN(n) || n < 1) return null;
      if (n <= 2) return String(n);
      let a = 1, b = 2;
      for (let i = 3; i <= n; i++) {
        const c = a + b;
        a = b;
        b = c;
      }
      return String(b);
    } catch {
      return null;
    }
  },

  'single-number': (inp) => {
    try {
      const nums = JSON.parse(inp);
      if (!Array.isArray(nums) || nums.length === 0) return null;
      let res = 0;
      for (const num of nums) res ^= num;
      return String(res);
    } catch {
      return null;
    }
  },

  'contains-duplicate': (inp) => {
    try {
      const nums = JSON.parse(inp);
      if (!Array.isArray(nums)) return null;
      const set = new Set(nums);
      return set.size !== nums.length ? 'true' : 'false';
    } catch {
      return null;
    }
  },

  'move-zeroes': (inp) => {
    try {
      const nums = JSON.parse(inp);
      if (!Array.isArray(nums)) return null;
      const res = nums.filter((x) => x !== 0);
      while (res.length < nums.length) res.push(0);
      return JSON.stringify(res);
    } catch {
      return null;
    }
  },

  'fizz-buzz': (inp) => {
    try {
      const n = parseInt(inp.trim(), 10);
      if (isNaN(n) || n < 1) return null;
      const res = [];
      for (let i = 1; i <= n; i++) {
        if (i % 15 === 0) res.push('FizzBuzz');
        else if (i % 3 === 0) res.push('Fizz');
        else if (i % 5 === 0) res.push('Buzz');
        else res.push(String(i));
      }
      return JSON.stringify(res);
    } catch {
      return null;
    }
  },

  'reverse-string': (inp) => {
    try {
      const s = JSON.parse(inp);
      if (!Array.isArray(s)) return null;
      return JSON.stringify([...s].reverse());
    } catch {
      return null;
    }
  },

  'longest-substring-without-repeating-characters': (inp) => {
    try {
      const s = JSON.parse(inp);
      if (typeof s !== 'string') return null;
      let maxLen = 0, left = 0;
      const set = new Set();
      for (let right = 0; right < s.length; right++) {
        while (set.has(s[right])) {
          set.delete(s[left++]);
        }
        set.add(s[right]);
        maxLen = Math.max(maxLen, right - left + 1);
      }
      return String(maxLen);
    } catch {
      return null;
    }
  },

  'longest-palindromic-substring': (inp) => {
    try {
      const s = JSON.parse(inp);
      if (typeof s !== 'string') return null;
      if (!s || s.length <= 1) return JSON.stringify(s);
      let start = 0, maxLen = 1;
      function expand(l, r) {
        while (l >= 0 && r < s.length && s[l] === s[r]) {
          if (r - l + 1 > maxLen) {
            start = l;
            maxLen = r - l + 1;
          }
          l--;
          r++;
        }
      }
      for (let i = 0; i < s.length; i++) {
        expand(i, i);
        expand(i, i + 1);
      }
      return JSON.stringify(s.substring(start, start + maxLen));
    } catch {
      return null;
    }
  },

  'median-of-two-sorted-arrays': (inp) => {
    try {
      const [aStr, bStr] = inp.split('\n');
      const a = JSON.parse(aStr);
      const b = JSON.parse(bStr);
      if (!Array.isArray(a) || !Array.isArray(b)) return null;
      const merged = [...a, ...b].sort((x, y) => x - y);
      const mid = Math.floor(merged.length / 2);
      if (merged.length % 2 === 1) return merged[mid].toFixed(5);
      return ((merged[mid - 1] + merged[mid]) / 2).toFixed(5);
    } catch {
      return null;
    }
  },

  'add-two-numbers': (inp) => {
    try {
      const [aStr, bStr] = inp.split('\n');
      const l1 = JSON.parse(aStr);
      const l2 = JSON.parse(bStr);
      if (!Array.isArray(l1) || !Array.isArray(l2)) return null;
      const res = [];
      let carry = 0, i = 0, j = 0;
      while (i < l1.length || j < l2.length || carry) {
        const sum = (l1[i] || 0) + (l2[j] || 0) + carry;
        res.push(sum % 10);
        carry = Math.floor(sum / 10);
        i++; j++;
      }
      return JSON.stringify(res);
    } catch {
      return null;
    }
  },
};

/**
 * Generates verified test cases for a question.
 * GUARANTEES:
 * 1. Every test case has a non-null, valid, non-empty expectedOutput.
 * 2. All HTML entities (&quot;, &lt;, etc.) are decoded.
 * 3. Never produces dummy candidate inputs with null outputs.
 *
 * @param {object} raw - Raw question API object
 * @param {Array<{input: string, output: string, explanation: string|null}>} examples - Extracted examples
 * @param {string[]} constraints - Extracted constraints
 * @param {string} category - Category ('dsa' or 'database')
 * @returns {Array<{input: string, expectedOutput: string}>} Array of test cases with verified outputs
 */
export function generateTestCases(raw, examples = [], constraints = [], category = 'dsa') {
  const testCases = [];
  const seenInputs = new Set();

  function addTest(input, expectedOutput) {
    if (!input || typeof input !== 'string') return;
    if (expectedOutput === null || expectedOutput === undefined) return;
    const trimmedInput = unescapeHtml(input).trim();
    const trimmedOutput = unescapeHtml(String(expectedOutput)).trim();
    if (trimmedInput.length === 0 || trimmedOutput.length === 0 || trimmedOutput === 'null') return;
    if (seenInputs.has(trimmedInput)) return;
    seenInputs.add(trimmedInput);
    testCases.push({
      input: trimmedInput,
      expectedOutput: trimmedOutput,
    });
  }

  // 1. Add official judge test cases from exampleTestcaseList with their matching example outputs
  if (Array.isArray(raw.exampleTestcaseList)) {
    for (let i = 0; i < raw.exampleTestcaseList.length; i++) {
      const judgeInput = raw.exampleTestcaseList[i];
      const matchingOutput = examples[i]?.output;
      if (judgeInput && matchingOutput) {
        addTest(judgeInput, matchingOutput);
      }
    }
  }

  // 2. Add descriptive examples from problem statement
  for (const ex of examples) {
    if (ex.input && ex.output) {
      addTest(ex.input, ex.output);
    }
  }

  // 3. For supported questions with reference solvers, generate additional verified edge/scale test cases
  const solver = solvers[raw.titleSlug];
  if (solver) {
    let candidates = [];

    if (raw.titleSlug === 'build-an-array-with-stack-operations') {
      candidates = [
        '[1]\n1',
        '[1,2]\n2',
        '[1,3]\n4',
        '[2,3]\n4',
        '[1,4]\n4',
        '[2,4]\n4',
        '[3,4]\n4',
        '[4]\n4',
        '[1,2,3]\n4',
        '[1,3,4]\n4',
        '[2,3,4]\n4',
        '[1,2,4]\n4',
        '[1,5]\n5',
        '[2,5]\n5',
        '[1,2,3,4,5]\n5',
      ];
    } else if (raw.titleSlug === 'two-sum') {
      candidates = [
        '[0,0]\n0',
        '[-1,1]\n0',
        '[-10,-20,-30]\n-50',
        '[3,2,4]\n6',
        '[3,3]\n6',
        '[1,1,1,1,1,4,7]\n11',
        '[1,2,3,4,5,6,7,8,9,10]\n19',
        '[10,9,8,7,6,5,4,3,2,1]\n5',
        '[-1000000000,1000000000]\n0',
        '[-5,-4,-3,-2,-1]\n-9',
        '[100,-100,50,-50,25,-25]\n0',
        '[1,5,9,13,17,21]\n30',
        '[2,4,6,8,10]\n14',
      ];
    } else if (raw.titleSlug === 'valid-parentheses') {
      candidates = [
        '""',
        '"()"',
        '"()[]{}"',
        '"(]"',
        '"([)]"',
        '"{[]}"',
        '"((("',
        '")))"',
        '"((()))"',
        '"({[()]}())"',
      ];
    } else if (raw.titleSlug === 'palindrome-number') {
      candidates = [
        '0',
        '1',
        '10',
        '11',
        '121',
        '-121',
        '1221',
        '12321',
        '1000021',
        '123456789987654321',
      ];
    } else if (raw.titleSlug === 'climbing-stairs') {
      candidates = ['1', '2', '3', '4', '5', '6', '7', '8', '10', '15', '20', '30'];
    } else if (raw.titleSlug === 'single-number') {
      candidates = [
        '[1]',
        '[2,2,1]',
        '[4,1,2,1,2]',
        '[-1,-1,2]',
        '[0,1,0]',
        '[99,1,99]',
      ];
    } else if (raw.titleSlug === 'contains-duplicate') {
      candidates = [
        '[1]',
        '[1,2,3,1]',
        '[1,2,3,4]',
        '[1,1,1,3,3,4,3,2,4,2]',
        '[0,0]',
        '[-1,-2,-3]',
      ];
    } else if (raw.titleSlug === 'move-zeroes') {
      candidates = [
        '[0]',
        '[1]',
        '[0,1,0,3,12]',
        '[0,0,1]',
        '[1,0,0]',
        '[1,2,3]',
      ];
    } else if (raw.titleSlug === 'fizz-buzz') {
      candidates = ['1', '3', '5', '15', '20', '30'];
    }

    for (const c of candidates) {
      const out = solver(c);
      if (out !== null && out !== undefined) {
        addTest(c, out);
      }
    }
  }

  // Ensure testCases strictly contains only valid items
  return testCases.filter((tc) => tc.input && tc.expectedOutput && tc.expectedOutput !== 'null');
}
