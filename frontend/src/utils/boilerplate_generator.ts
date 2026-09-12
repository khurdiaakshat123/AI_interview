import { Question } from '../types';

export interface SupportedLanguage {
  id: string;
  label: string;
  monacoLang: string;
  extension: string;
}

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  { id: 'cpp20', label: 'C++ (C++20)', monacoLang: 'cpp', extension: 'cpp' },
  { id: 'cpp17', label: 'C++ (C++17)', monacoLang: 'cpp', extension: 'cpp' },
  { id: 'cpp23', label: 'C++ (C++23)', monacoLang: 'cpp', extension: 'cpp' },
  { id: 'c', label: 'C (GCC 11)', monacoLang: 'c', extension: 'c' },
  { id: 'java', label: 'Java (OpenJDK 17/21)', monacoLang: 'java', extension: 'java' },
  { id: 'python', label: 'Python 3 (v3.11/3.14)', monacoLang: 'python', extension: 'py' },
  { id: 'javascript', label: 'JavaScript (Node.js)', monacoLang: 'javascript', extension: 'js' },
  { id: 'typescript', label: 'TypeScript', monacoLang: 'typescript', extension: 'ts' },
  { id: 'go', label: 'Go', monacoLang: 'go', extension: 'go' },
  { id: 'rust', label: 'Rust', monacoLang: 'rust', extension: 'rs' },
  { id: 'csharp', label: 'C# (.NET 8)', monacoLang: 'csharp', extension: 'cs' },
  { id: 'sql', label: 'PostgreSQL / SQL', monacoLang: 'sql', extension: 'sql' }
];

interface ExtractedSignature {
  functionName: string;
  params: { name: string; type: string }[];
  returnType: string;
}

/**
 * Extracts function signature details from question prompt, title, or starter code.
 */
function extractSignature(question: Question): ExtractedSignature {
  const starter = question.starter_code || '';
  
  // Try to parse Python def func(arg1: type, arg2: type) -> return_type:
  const pyMatch = starter.match(/def\s+([a-zA-Z_]\w*)\s*\((.*?)\)(?:\s*->\s*([a-zA-Z_\[\],\s]*))?:/);
  if (pyMatch) {
    const fnName = pyMatch[1];
    const rawParams = pyMatch[2] ? pyMatch[2].split(',') : [];
    const params = rawParams.map(p => {
      const parts = p.split(':');
      const name = parts[0]?.trim() || 'arg';
      const type = parts[1]?.trim() || 'any';
      return { name, type };
    }).filter(p => p.name && p.name !== 'self');
    const returnType = pyMatch[3]?.trim() || 'any';
    return { functionName: fnName, params, returnType };
  }

  // Fallback: derive function name from title
  const title = question.title || question.subtopic || 'solution';
  const cleanTitle = title
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .map((word, i) => i === 0 ? word.toLowerCase() : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');
  const fnName = cleanTitle || 'solve';

  return {
    functionName: fnName,
    params: [{ name: 'input_data', type: 'any' }],
    returnType: 'any'
  };
}

function toCppType(pyType: string): string {
  const t = pyType.toLowerCase().trim();
  if (t === 'int') return 'int';
  if (t === 'float') return 'double';
  if (t === 'str' || t === 'string') return 'string';
  if (t === 'bool' || t === 'boolean') return 'bool';
  if (t.includes('list[int]') || t.includes('vector<int>')) return 'vector<int>';
  if (t.includes('list[str]') || t.includes('list[string]')) return 'vector<string>';
  if (t.includes('list[list[int]]')) return 'vector<vector<int>>';
  if (t.includes('list') || t.includes('vector')) return 'vector<int>';
  return 'string';
}

function toJavaType(pyType: string): string {
  const t = pyType.toLowerCase().trim();
  if (t === 'int') return 'int';
  if (t === 'float') return 'double';
  if (t === 'str' || t === 'string') return 'String';
  if (t === 'bool' || t === 'boolean') return 'boolean';
  if (t.includes('list[int]') || t.includes('int[]')) return 'int[]';
  if (t.includes('list[str]') || t.includes('string[]')) return 'String[]';
  if (t.includes('list[list[int]]')) return 'int[][]';
  if (t.includes('list')) return 'int[]';
  return 'String';
}

function toCType(pyType: string): string {
  const t = pyType.toLowerCase().trim();
  if (t === 'int') return 'int';
  if (t === 'float') return 'double';
  if (t === 'str' || t === 'string') return 'char*';
  if (t === 'bool' || t === 'boolean') return 'bool';
  if (t.includes('list') || t.includes('array')) return 'int*';
  return 'char*';
}

export function generateBoilerplate(languageId: string, question: Question): string {
  if (question.question_type.toUpperCase() === 'SQL') {
    return `-- Write your PostgreSQL query below\nSELECT \n    \nFROM \nWHERE ;\n`;
  }

  const sig = extractSignature(question);
  const fn = sig.functionName;

  switch (languageId) {
    case 'cpp17':
    case 'cpp20':
    case 'cpp23': {
      const cppRet = toCppType(sig.returnType);
      const cppParams = sig.params.map(p => `${toCppType(p.type)} ${p.name}`).join(', ');
      return `#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    ${cppRet} ${fn}(${cppParams}) {
        // Write your solution here
        
        return ${cppRet === 'string' ? '""' : cppRet === 'bool' ? 'false' : cppRet.includes('vector') ? '{}' : '0'};
    }
};
`;
    }

    case 'c': {
      const cRet = toCType(sig.returnType);
      const cParams = sig.params.map(p => `${toCType(p.type)} ${p.name}`).join(', ');
      return `#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>

/**
 * Function: ${fn}
 * Return the required result according to problem specification.
 */
${cRet} ${fn}(${cParams || 'void'}) {
    // Write your solution here
    
    return ${cRet === 'char*' ? 'NULL' : cRet === 'bool' ? 'false' : '0'};
}
`;
    }

    case 'java': {
      const javaRet = toJavaType(sig.returnType);
      const javaParams = sig.params.map(p => `${toJavaType(p.type)} ${p.name}`).join(', ');
      return `import java.util.*;
import java.io.*;

class Solution {
    public ${javaRet} ${fn}(${javaParams}) {
        // Write your solution here
        
        return ${javaRet === 'String' ? '""' : javaRet === 'boolean' ? 'false' : javaRet.includes('[]') ? 'new int[]{}' : '0'};
    }
}
`;
    }

    case 'python': {
      if (question.starter_code && question.starter_code.trim()) {
        return question.starter_code.trim();
      }
      const pyParams = sig.params.map(p => `${p.name}: ${p.type || 'any'}`).join(', ');
      return `from typing import List, Dict, Optional, Set
import collections
import math

class Solution:
    def ${fn}(self${pyParams ? ', ' + pyParams : ''}) -> ${sig.returnType || 'any'}:
        # Write your solution here
        pass
`;
    }

    case 'javascript': {
      const jsParams = sig.params.map(p => p.name).join(', ');
      const jsDocParams = sig.params.map(p => ` * @param {${p.type}} ${p.name}`).join('\n');
      return `/**
${jsDocParams}
 * @return {${sig.returnType}}
 */
function ${fn}(${jsParams}) {
    // Write your solution here
    
}
`;
    }

    case 'typescript': {
      const tsParams = sig.params.map(p => `${p.name}: ${p.type === 'int' ? 'number' : p.type === 'str' ? 'string' : 'any'}`).join(', ');
      const tsRet = sig.returnType === 'int' ? 'number' : sig.returnType === 'str' ? 'string' : 'any';
      return `function ${fn}(${tsParams}): ${tsRet} {
    // Write your solution here
    
    return ${tsRet === 'string' ? '""' : tsRet === 'number' ? '0' : 'null'};
}
`;
    }

    case 'go': {
      const goParams = sig.params.map(p => `${p.name} string`).join(', ');
      return `package main

import (
    "fmt"
)

func ${fn}(${goParams}) int {
    // Write your solution here
    
    return 0
}
`;
    }

    case 'rust': {
      return `impl Solution {
    pub fn ${fn.replace(/([A-Z])/g, '_$1').toLowerCase()}(s: String) -> i32 {
        // Write your solution here
        
        0
    }
}
`;
    }

    case 'csharp': {
      const csRet = toJavaType(sig.returnType);
      const csParams = sig.params.map(p => `${toJavaType(p.type)} ${p.name}`).join(', ');
      const csFn = fn.charAt(0).toUpperCase() + fn.slice(1);
      return `using System;
using System.Collections.Generic;

public class Solution {
    public ${csRet} ${csFn}(${csParams}) {
        // Write your solution here
        
        return ${csRet === 'String' ? '""' : csRet === 'boolean' ? 'false' : '0'};
    }
}
`;
    }

    default:
      return question.starter_code || `# Write your solution here\n`;
  }
}
