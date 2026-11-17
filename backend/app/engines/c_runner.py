import os
import sys
import json
import re
import shutil
import tempfile
import subprocess
import time
import psutil
from typing import Dict, Any, List, Optional, Tuple

C_HEADERS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
#include <limits.h>
#include <time.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdint.h>
'''

C_STRUCT_LISTNODE = r'''
struct ListNode {
    int val;
    struct ListNode *next;
};
'''

C_STRUCT_TREENODE = r'''
struct TreeNode {
    int val;
    struct TreeNode *left;
    struct TreeNode *right;
};
'''

C_HARNESS_HELPERS = r'''
/* Safe strdup implementation */
static char* c_strdup(const char* s) {
    if (!s) return NULL;
    size_t len = strlen(s);
    char* copy = (char*)malloc(len + 1);
    if (copy) { memcpy(copy, s, len + 1); }
    return copy;
}

/* Trim whitespace */
static char* c_trim(char* s) {
    while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') s++;
    if (*s == 0) return s;
    char* end = s + strlen(s) - 1;
    while (end > s && (*end == ' ' || *end == '\t' || *end == '\n' || *end == '\r')) {
        *end = 0;
        end--;
    }
    return s;
}

/* Parse 1D int array: "[2, 7, 11, 15]" */
static int* c_parse_int_array(const char* raw, int* out_sz) {
    *out_sz = 0;
    if (!raw) return NULL;
    char* s = c_strdup(raw);
    char* p = strchr(s, '[');
    char* end = strrchr(s, ']');
    if (!p || !end || end <= p) { free(s); return NULL; }
    *end = '\0';
    p++;
    
    int cap = 16;
    int* arr = (int*)malloc(sizeof(int) * cap);
    int count = 0;
    
    char* token = strtok(p, ",");
    while (token) {
        char* t = c_trim(token);
        if (*t) {
            if (count >= cap) {
                cap *= 2;
                arr = (int*)realloc(arr, sizeof(int) * cap);
            }
            arr[count++] = (int)strtol(t, NULL, 10);
        }
        token = strtok(NULL, ",");
    }
    free(s);
    *out_sz = count;
    return arr;
}

/* Parse 2D int array: "[[1,2,3],[4,5,6]]" */
static int** c_parse_matrix(const char* raw, int* out_rows, int** out_cols) {
    *out_rows = 0;
    *out_cols = NULL;
    if (!raw) return NULL;
    char* s = c_strdup(raw);
    char* p = strchr(s, '[');
    char* end = strrchr(s, ']');
    if (!p || !end || end <= p) { free(s); return NULL; }
    
    int row_cap = 8;
    int** mat = (int**)malloc(sizeof(int*) * row_cap);
    int* cols = (int*)malloc(sizeof(int) * row_cap);
    int rows = 0;
    
    char* cur = p + 1;
    while (*cur && cur < end) {
        char* r_start = strchr(cur, '[');
        if (!r_start || r_start >= end) break;
        char* r_end = strchr(r_start, ']');
        if (!r_end || r_end > end) break;
        
        int len = (int)(r_end - r_start + 1);
        char* row_buf = (char*)malloc(len + 1);
        strncpy(row_buf, r_start, len);
        row_buf[len] = '\0';
        
        int r_sz = 0;
        int* r_arr = c_parse_int_array(row_buf, &r_sz);
        free(row_buf);
        
        if (rows >= row_cap) {
            row_cap *= 2;
            mat = (int**)realloc(mat, sizeof(int*) * row_cap);
            cols = (int*)realloc(cols, sizeof(int) * row_cap);
        }
        mat[rows] = r_arr;
        cols[rows] = r_sz;
        rows++;
        cur = r_end + 1;
    }
    free(s);
    *out_rows = rows;
    *out_cols = cols;
    return mat;
}

/* Parse string: "\"hello\"" or "hello" */
static char* c_parse_string(const char* raw) {
    if (!raw) return c_strdup("");
    char* s = c_strdup(raw);
    char* t = c_trim(s);
    if (*t == '"' || *t == '\'') {
        t++;
        char* end = strrchr(t, '"');
        if (!end) end = strrchr(t, '\'');
        if (end) *end = '\0';
    }
    char* res = c_strdup(t);
    free(s);
    return res;
}

/* Parse string array: "[\"flower\",\"flow\",\"flight\"]" */
static char** c_parse_string_array(const char* raw, int* out_sz) {
    *out_sz = 0;
    if (!raw) return NULL;
    char* s = c_strdup(raw);
    char* p = strchr(s, '[');
    char* end = strrchr(s, ']');
    if (!p || !end || end <= p) { free(s); return NULL; }
    *end = '\0';
    p++;
    
    int cap = 8;
    char** arr = (char**)malloc(sizeof(char*) * cap);
    int count = 0;
    
    char* cur = p;
    while (*cur) {
        while (*cur == ' ' || *cur == ',' || *cur == '\t' || *cur == '\n' || *cur == '\r') cur++;
        if (!*cur) break;
        if (*cur == '"' || *cur == '\'') {
            char quote = *cur++;
            char* qstart = cur;
            while (*cur && *cur != quote) {
                if (*cur == '\\' && *(cur + 1)) cur += 2;
                else cur++;
            }
            int len = (int)(cur - qstart);
            char* item = (char*)malloc(len + 1);
            strncpy(item, qstart, len);
            item[len] = '\0';
            if (*cur == quote) cur++;
            
            if (count >= cap) {
                cap *= 2;
                arr = (char**)realloc(arr, sizeof(char*) * cap);
            }
            arr[count++] = item;
        } else {
            char* start = cur;
            while (*cur && *cur != ',') cur++;
            int len = (int)(cur - start);
            char* item = (char*)malloc(len + 1);
            strncpy(item, start, len);
            item[len] = '\0';
            if (count >= cap) {
                cap *= 2;
                arr = (char**)realloc(arr, sizeof(char*) * cap);
            }
            arr[count++] = c_trim(item);
            if (*cur == ',') cur++;
        }
    }
    free(s);
    *out_sz = count;
    return arr;
}

/* Parse ListNode: "[1, 2, 3, 4, 5]" */
static struct ListNode* c_parse_listnode(const char* raw) {
    int sz = 0;
    int* arr = c_parse_int_array(raw, &sz);
    if (!arr || sz == 0) { free(arr); return NULL; }
    struct ListNode dummy;
    dummy.next = NULL;
    struct ListNode* tail = &dummy;
    for (int i = 0; i < sz; i++) {
        struct ListNode* node = (struct ListNode*)malloc(sizeof(struct ListNode));
        node->val = arr[i];
        node->next = NULL;
        tail->next = node;
        tail = node;
    }
    free(arr);
    return dummy.next;
}

/* Parse TreeNode: "[4, 2, 7, 1, 3]" */
static struct TreeNode* c_parse_treenode(const char* raw) {
    if (!raw) return NULL;
    char* s = c_strdup(raw);
    char* p = strchr(s, '[');
    char* end = strrchr(s, ']');
    if (!p || !end || end <= p) { free(s); return NULL; }
    *end = '\0';
    p++;
    
    char* token = strtok(p, ",");
    if (!token) { free(s); return NULL; }
    char* t = c_trim(token);
    if (strcmp(t, "null") == 0 || !*t) { free(s); return NULL; }
    
    struct TreeNode* root = (struct TreeNode*)malloc(sizeof(struct TreeNode));
    root->val = (int)strtol(t, NULL, 10);
    root->left = NULL;
    root->right = NULL;
    
    size_t queue_cap = strlen(raw) + 1;
    struct TreeNode** queue = (struct TreeNode**)malloc(queue_cap * sizeof(*queue));
    if (!queue) exit(3);
    int head = 0, tail = 0;
    queue[tail++] = root;
    
    while (head < tail) {
        struct TreeNode* curr = queue[head++];
        token = strtok(NULL, ",");
        if (!token) break;
        t = c_trim(token);
        if (strcmp(t, "null") != 0 && *t) {
            curr->left = (struct TreeNode*)malloc(sizeof(struct TreeNode));
            curr->left->val = (int)strtol(t, NULL, 10);
            curr->left->left = NULL;
            curr->left->right = NULL;
            queue[tail++] = curr->left;
        }
        token = strtok(NULL, ",");
        if (!token) break;
        t = c_trim(token);
        if (strcmp(t, "null") != 0 && *t) {
            curr->right = (struct TreeNode*)malloc(sizeof(struct TreeNode));
            curr->right->val = (int)strtol(t, NULL, 10);
            curr->right->left = NULL;
            curr->right->right = NULL;
            queue[tail++] = curr->right;
        }
    }
    free(queue);
    free(s);
    return root;
}

/* Dynamically sized output: allocation failure is an execution error, never truncation. */
typedef struct { char* data; size_t len, cap; } CBuffer;
static void c_reserve(CBuffer* b, size_t extra) {
    if (extra > SIZE_MAX - b->len - 1) exit(3);
    size_t need = b->len + extra + 1;
    if (need <= b->cap) return;
    size_t cap = b->cap ? b->cap : 64;
    while (cap < need) { if (cap > SIZE_MAX / 2) { cap = need; break; } cap *= 2; }
    char* data = (char*)realloc(b->data, cap);
    if (!data) exit(3);
    b->data = data; b->cap = cap;
    b->data[b->len] = 0;
}
static void c_append(CBuffer* b, const char* text) {
    size_t len = strlen(text); c_reserve(b, len);
    memcpy(b->data + b->len, text, len + 1); b->len += len;
}
static void c_printf(CBuffer* b, const char* fmt, ...) {
    va_list args, copy; va_start(args, fmt); va_copy(copy, args);
    int len = vsnprintf(NULL, 0, fmt, copy); va_end(copy);
    if (len < 0) exit(3);
    c_reserve(b, (size_t)len);
    vsnprintf(b->data + b->len, b->cap - b->len, fmt, args);
    b->len += (size_t)len; va_end(args);
}
static void c_escape_json(const char* src, CBuffer* dst) {
    for (const unsigned char* p = (const unsigned char*)src; *p; p++) {
        if (*p == '"' || *p == '\\') { c_append(dst, "\\"); c_printf(dst, "%c", *p); }
        else if (*p < 32) c_printf(dst, "\\u%04x", *p);
        else c_printf(dst, "%c", *p);
    }
    c_reserve(dst, 0);
}
static void c_format_int(int v, CBuffer* b) { c_printf(b, "%d", v); }
static void c_format_long(long long v, CBuffer* b) { c_printf(b, "%lld", v); }
static void c_format_double(double v, CBuffer* b) {
    if (!isfinite(v)) exit(3);
    c_printf(b, "%.17g", v);
}
static void c_format_bool(bool v, CBuffer* b) { c_append(b, v ? "true" : "false"); }
static void c_format_string(const char* v, CBuffer* b) {
    if (!v) { c_append(b, "null"); return; }
    c_append(b, "\""); c_escape_json(v, b); c_append(b, "\"");
}
static void c_format_int_array(const int* arr, int sz, CBuffer* b) {
    if (sz < 0 || (sz && !arr)) exit(3);
    c_append(b, "[");
    for (int i = 0; i < sz; i++) { if (i) c_append(b, ","); c_printf(b, "%d", arr[i]); }
    c_append(b, "]");
}
static void c_format_matrix(int** mat, int rows, const int* cols, CBuffer* b) {
    if (rows < 0 || (rows && (!mat || !cols))) exit(3);
    c_append(b, "[");
    for (int i = 0; i < rows; i++) {
        if (i) c_append(b, ","); c_format_int_array(mat[i], cols[i], b);
    }
    c_append(b, "]");
}
static void c_format_listnode(struct ListNode* head, CBuffer* b) {
    struct ListNode *slow = head, *fast = head;
    while (fast && fast->next) {
        slow = slow->next; fast = fast->next->next; if (slow == fast) exit(3);
    }
    c_append(b, "["); bool first = true;
    for (; head; head = head->next) {
        if (!first) c_append(b, ","); first = false; c_printf(b, "%d", head->val);
    }
    c_append(b, "]");
}
static void c_format_treenode(struct TreeNode* root, CBuffer* b) {
    size_t head = 0, tail = 0, cap = 16, last = 0;
    size_t seen_cap = 32, seen_count = 0;
    struct TreeNode** seen = (struct TreeNode**)calloc(seen_cap, sizeof(*seen));
    struct TreeNode** queue = (struct TreeNode**)malloc(cap * sizeof(*queue));
    if (!queue || !seen) exit(3);
    queue[tail++] = root;
    c_append(b, "[");
    while (head < tail) {
        struct TreeNode* node = queue[head++];
        if (head > 1) c_append(b, ",");
        if (!node) { c_append(b, "null"); continue; }
        if (seen_count * 2 >= seen_cap) {
            if (seen_cap > SIZE_MAX / 2 / sizeof(*seen)) exit(3);
            size_t old_cap = seen_cap; seen_cap *= 2;
            struct TreeNode** grown = (struct TreeNode**)calloc(seen_cap, sizeof(*seen));
            if (!grown) exit(3);
            for (size_t i = 0; i < old_cap; i++) if (seen[i]) {
                size_t slot = ((uintptr_t)seen[i] >> 3) & (seen_cap - 1);
                while (grown[slot]) slot = (slot + 1) & (seen_cap - 1);
                grown[slot] = seen[i];
            }
            free(seen); seen = grown;
        }
        size_t slot = ((uintptr_t)node >> 3) & (seen_cap - 1);
        while (seen[slot] && seen[slot] != node) slot = (slot + 1) & (seen_cap - 1);
        if (seen[slot]) exit(3); /* A cycle or shared node is not a binary tree. */
        seen[slot] = node; seen_count++;
        c_printf(b, "%d", node->val); last = b->len;
        if (tail + 2 > cap) {
            if (cap > SIZE_MAX / 2 / sizeof(*queue)) exit(3);
            cap *= 2; void* next = realloc(queue, cap * sizeof(*queue));
            if (!next) exit(3); queue = (struct TreeNode**)next;
        }
        queue[tail++] = node->left; queue[tail++] = node->right;
    }
    b->len = last ? last : 1; b->data[b->len] = 0;
    c_append(b, "]"); free(queue); free(seen);
}

'''

C_HARNESS_PREAMBLE = C_HEADERS + "\n" + C_STRUCT_LISTNODE + "\n" + C_STRUCT_TREENODE + "\n" + C_HARNESS_HELPERS

class CRunner:
    @classmethod
    def split_input(cls, raw: str) -> List[str]:
        raw = re.sub(r'(?:^|[\n,])\s*[a-zA-Z_]\w*\s*=\s*', '\n', raw).strip()
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if len(lines) == 1 and (',' in lines[0] or '=' in lines[0]):
            pattern = r"(?:^|[\n,])\s*([a-zA-Z_]\w*)\s*=\s*"
            if re.search(pattern, lines[0]):
                splits = re.split(pattern, lines[0])
                vals = []
                for i in range(2, len(splits), 2):
                    vals.append(splits[i].strip().rstrip(","))
                if vals:
                    return vals
            parts, cur, depth = [], [], 0
            for ch in lines[0]:
                if ch in '[{(': depth += 1
                elif ch in ']})': depth -= 1
                if ch == ',' and depth == 0:
                    parts.append(''.join(cur).strip())
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                parts.append(''.join(cur).strip())
            return parts
        return lines

    @classmethod
    def detect_c_signature(cls, code: str, expected_func: Optional[str] = None) -> Optional[Tuple[str, str, List[Tuple[str, str]]]]:
        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        
        matches = list(re.finditer(
            r'(?:^|[\n;}])\s*([a-zA-Z0-9_* ]+?[\s*])([a-zA-Z_]\w*)\s*\(([\s\S]*?)\)\s*\{',
            clean_code
        ))
        
        candidates = []
        forbidden = {"if", "while", "for", "switch", "catch", "return", "else", "case", "default", "sizeof", "main"}
        
        for m in matches:
            raw_ret = m.group(1).strip()
            func_name = m.group(2).strip()
            raw_params = m.group(3).strip()
            
            if func_name in forbidden:
                continue
            if re.search(r'\b(typedef|enum|union)\b', raw_ret):
                continue
            if re.search(r'\bstruct\b', raw_ret) and '*' not in raw_ret:
                continue
            if not any(raw_ret.startswith(k) for k in ("int", "void", "char", "bool", "float", "double", "long", "struct", "short", "unsigned", "signed")) and not raw_ret.endswith('*'):
                continue
                
            raw_ret = re.sub(r'\b(static|inline|extern)\s+', '', raw_ret).strip()
            
            param_list = []
            if raw_params and raw_params.strip() != "void":
                depth = 0
                cur = []
                pstrs = []
                for ch in raw_params:
                    if ch in '<({[': depth += 1
                    elif ch in '>)}]': depth -= 1
                    if ch == ',' and depth == 0:
                        pstrs.append(''.join(cur).strip())
                        cur = []
                    else:
                        cur.append(ch)
                if cur:
                    pstrs.append(''.join(cur).strip())
                for p in pstrs:
                    p = p.strip()
                    if not p: continue
                    parts = p.rsplit(None, 1)
                    if len(parts) == 2:
                        p_type, p_name = parts[0].strip(), parts[1].strip()
                        while p_name.startswith('*'):
                            p_type += '*'
                            p_name = p_name[1:].strip()
                        param_list.append((p_type, p_name))
                    else:
                        param_list.append((p, 'arg'))
            candidates.append((raw_ret, func_name, param_list))
            
        if expected_func:
            for c in candidates:
                if c[1] == expected_func:
                    return c
        return candidates[-1] if candidates else None

    @classmethod
    def build_c_harness(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        ret_type: str,
        func_name: str,
        params: List[Tuple[str, str]]
    ) -> str:
        cases_code = []
        for tc_idx, tc in enumerate(test_cases):
            raw_input = tc.get("input", "")
            inp_lines = cls.split_input(raw_input)
            
            inp_idx = 0
            p_idx = 0
            decls = []
            call_args = []
            first_arg_name = None
            first_arg_type = None
            
            while p_idx < len(params):
                p_type, p_name = params[p_idx]
                p_type_clean = p_type.replace(' ', '')
                
                # Check for out-parameters: returnSize
                if p_type_clean == "int*" and p_name.lower() == "returnsize":
                    decls.append(f"        int ret_sz_{tc_idx} = 0;")
                    call_args.append(f"&ret_sz_{tc_idx}")
                    p_idx += 1
                    continue
                # Check for out-parameters: returnColumnSizes
                if p_type_clean == "int**" and p_name.lower() == "returncolumnsizes":
                    decls.append(f"        int* ret_col_sz_{tc_idx} = NULL;")
                    call_args.append(f"&ret_col_sz_{tc_idx}")
                    p_idx += 1
                    continue
                
                val_str = inp_lines[inp_idx] if inp_idx < len(inp_lines) else ""
                safe_val = val_str.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                
                # Check for 2D matrix: int** matrix, int matrixSize, int* matrixColSize
                if "int**" in p_type_clean and p_idx + 2 < len(params) and "size" in params[p_idx + 1][1].lower():
                    arg_var = f"mat_{tc_idx}_{inp_idx}"
                    rows_var = f"{arg_var}_rows"
                    cols_var = f"{arg_var}_cols"
                    decls.append(f'        int {rows_var} = 0;')
                    decls.append(f'        int* {cols_var} = NULL;')
                    decls.append(f'        int** {arg_var} = c_parse_matrix("{safe_val}", &{rows_var}, &{cols_var});')
                    call_args.append(arg_var)
                    call_args.append(rows_var)
                    call_args.append(cols_var)
                    if first_arg_name is None:
                        first_arg_name = (arg_var, rows_var, cols_var)
                        first_arg_type = "matrix"
                    inp_idx += 1
                    p_idx += 3
                    continue
                
                # Check for 1D int array: int* nums, int numsSize
                if "int*" in p_type_clean and p_idx + 1 < len(params) and "size" in params[p_idx + 1][1].lower():
                    arg_var = f"arr_{tc_idx}_{inp_idx}"
                    sz_var = f"{arg_var}_sz"
                    decls.append(f'        int {sz_var} = 0;')
                    decls.append(f'        int* {arg_var} = c_parse_int_array("{safe_val}", &{sz_var});')
                    call_args.append(arg_var)
                    call_args.append(sz_var)
                    if first_arg_name is None:
                        first_arg_name = (arg_var, sz_var)
                        first_arg_type = "int_array"
                    inp_idx += 1
                    p_idx += 2
                    continue
                
                # Check for string array: char** strs, int strsSize
                if ("char**" in p_type_clean or "char*[]" in p_type_clean) and p_idx + 1 < len(params) and "size" in params[p_idx + 1][1].lower():
                    arg_var = f"strs_{tc_idx}_{inp_idx}"
                    sz_var = f"{arg_var}_sz"
                    decls.append(f'        int {sz_var} = 0;')
                    decls.append(f'        char** {arg_var} = c_parse_string_array("{safe_val}", &{sz_var});')
                    call_args.append(arg_var)
                    call_args.append(sz_var)
                    inp_idx += 1
                    p_idx += 2
                    continue
                
                # Other individual parameters
                arg_var = f"arg_{tc_idx}_{inp_idx}"
                if "char*" in p_type_clean:
                    decls.append(f'        char* {arg_var} = c_parse_string("{safe_val}");')
                    call_args.append(arg_var)
                elif "listnode" in p_type.lower():
                    decls.append(f'        struct ListNode* {arg_var} = c_parse_listnode("{safe_val}");')
                    call_args.append(arg_var)
                elif "treenode" in p_type.lower():
                    decls.append(f'        struct TreeNode* {arg_var} = c_parse_treenode("{safe_val}");')
                    call_args.append(arg_var)
                elif "bool" in p_type_clean:
                    decls.append(f'        bool {arg_var} = (strcmp("{safe_val}", "true") == 0 || strcmp("{safe_val}", "1") == 0);')
                    call_args.append(arg_var)
                elif "double" in p_type_clean or "float" in p_type_clean:
                    decls.append(f'        double {arg_var} = strtod("{safe_val}", NULL);')
                    call_args.append(arg_var)
                elif "long" in p_type_clean:
                    decls.append(f'        long long {arg_var} = strtoll("{safe_val}", NULL, 10);')
                    call_args.append(arg_var)
                elif "int" in p_type_clean:
                    decls.append(f'        int {arg_var} = (int)strtol("{safe_val}", NULL, 10);')
                    call_args.append(arg_var)
                else:
                    decls.append(f'        char* {arg_var} = c_parse_string("{safe_val}");')
                    call_args.append(arg_var)
                
                if first_arg_name is None:
                    first_arg_name = (arg_var,)
                    first_arg_type = p_type
                inp_idx += 1
                p_idx += 1
            
            args_str = ", ".join(call_args)
            decls_str = "\n".join(decls)
            ret_clean = ret_type.replace(' ', '')
            
            if ret_clean == "void":
                call_stmt = f"        {func_name}({args_str});"
                if first_arg_type == "int_array":
                    fmt_stmt = f"        c_format_int_array({first_arg_name[0]}, {first_arg_name[1]}, &act_buf);"
                elif first_arg_type == "matrix":
                    fmt_stmt = f"        c_format_matrix({first_arg_name[0]}, {first_arg_name[1]}, {first_arg_name[2]}, &act_buf);"
                else:
                    fmt_stmt = '        c_append(&act_buf, "null");'
            elif ret_clean == "int*":
                call_stmt = f"        int* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_int_array(ret_val, ret_sz_{tc_idx}, &act_buf);"
            elif ret_clean == "int**":
                call_stmt = f"        int** ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_matrix(ret_val, ret_sz_{tc_idx}, ret_col_sz_{tc_idx}, &act_buf);"
            elif "char*" in ret_clean:
                call_stmt = f"        char* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_string(ret_val, &act_buf);"
            elif "listnode" in ret_type.lower():
                call_stmt = f"        struct ListNode* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_listnode(ret_val, &act_buf);"
            elif "treenode" in ret_type.lower():
                call_stmt = f"        struct TreeNode* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_treenode(ret_val, &act_buf);"
            elif "bool" in ret_clean:
                call_stmt = f"        bool ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_bool(ret_val, &act_buf);"
            elif "double" in ret_clean or "float" in ret_clean:
                call_stmt = f"        double ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_double(ret_val, &act_buf);"
            elif "long" in ret_clean:
                call_stmt = f"        long long ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_long(ret_val, &act_buf);"
            else:
                call_stmt = f"        int ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_int(ret_val, &act_buf);"

            case_str = f"""    /* Case {tc_idx + 1} */
    {{
        CBuffer act_buf = {{0}};
        CBuffer esc_act = {{0}};
{decls_str}
        clock_t t0 = clock();
{call_stmt}
        double elapsed_ms = ((double)(clock() - t0) / CLOCKS_PER_SEC) * 1000.0;
{fmt_stmt}
        c_escape_json(act_buf.data, &esc_act);
        if ({tc_idx} > 0) fputs(",\\n", out_file);
        fprintf(out_file, "    {{\\\"test_case_index\\\": {tc_idx + 1}, \\\"actual_output\\\": \\\"%s\\\", \\\"runtime_ms\\\": %.3f}}", esc_act.data, elapsed_ms);
        free(act_buf.data); free(esc_act.data);
    }}"""
            cases_code.append(case_str)

        all_cases = "\n".join(cases_code)
        main_code = f"""
int main(int argc, char** argv) {{
    if (argc < 2) return 1;
    FILE* out_file = fopen(argv[1], "w");
    if (!out_file) return 2;
    fprintf(out_file, "{{\\\"results\\\": [\\n");
{all_cases}
    fprintf(out_file, "\\n]}}\\n");
    fclose(out_file);
    return 0;
}}
"""
        has_list = bool(re.search(r'\bstruct\s+ListNode\s*\{', code))
        has_tree = bool(re.search(r'\bstruct\s+TreeNode\s*\{', code))

        pre_parts = [C_HEADERS]
        if not has_list:
            pre_parts.append(C_STRUCT_LISTNODE)
        if not has_tree:
            pre_parts.append(C_STRUCT_TREENODE)

        return "\n".join(pre_parts) + "\n\n" + code + "\n\n" + C_HARNESS_HELPERS + "\n\n" + main_code

    @classmethod
    def execute(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout_seconds: float = 10.0,
        expected_func: Optional[str] = None
    ) -> Dict[str, Any]:
        gcc = shutil.which("gcc") or shutil.which("clang")
        if not gcc:
            return {
                "status": "TOOLCHAIN_UNAVAILABLE",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "C compiler binary (gcc/clang) not found on server.",
                "compiler_output": "Toolchain error: GCC or Clang compiler binary is not installed.",
                "error": "Compiler binary not found.",
                "runtime_ms": None,
                "memory_mb": None,
                "test_case_results": []
            }

        # Check for standalone main() submission
        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        if re.search(r'\bint\s+main\s*\(', clean_code):
            return {
                "status": "COMPILATION_ERROR",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Function-based solution required: Please provide the required function implementation for this problem rather than a standalone main() function.",
                "compiler_output": "Compilation Error: Function-based solution contract required. Standalone main() is not permitted for function-graded DSA problems.",
                "error": "Function-based solution required.",
                "runtime_ms": None,
                "memory_mb": None,
                "test_case_results": []
            }

        sig = cls.detect_c_signature(code, expected_func=expected_func)
        if not sig:
            return {
                "status": "COMPILATION_ERROR",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Could not detect C solution function. Please ensure function signature matches problem requirements.",
                "compiler_output": "Compilation Error: No callable solution function found in submitted C code.",
                "error": "Solution function not found.",
                "runtime_ms": None,
                "memory_mb": None,
                "test_case_results": []
            }

        ret_type, func_name, params = sig

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            src_file = os.path.join(tmpdir, "solution.c")
            exe_file = os.path.join(tmpdir, "solution.exe" if sys.platform == "win32" else "solution")
            res_file = os.path.join(tmpdir, "results.json")

            harness = cls.build_c_harness(code, test_cases, ret_type, func_name, params)
            with open(src_file, "w", encoding="utf-8") as f:
                f.write(harness)

            comp = subprocess.run([gcc, "-std=c11", "-O2", "-pipe", src_file, "-o", exe_file, "-lm"], capture_output=True, text=True)
            if comp.returncode != 0:
                clean_err = comp.stderr.replace(tmpdir, "").replace("\\", "/").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "C Compilation Error.",
                    "compiler_output": clean_err,
                    "error": clean_err,
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

            # Execute process with resource telemetry
            start_t = time.perf_counter()
            peak_rss = 0
            timeout_expired = False
            
            try:
                proc = subprocess.Popen(
                    [exe_file, res_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Memory monitoring
                def monitor():
                    nonlocal peak_rss
                    try:
                        p = psutil.Process(proc.pid)
                        while proc.poll() is None:
                            try:
                                rss = p.memory_info().rss
                                if rss > peak_rss: peak_rss = rss
                            except Exception:
                                break
                            time.sleep(0.01)
                    except Exception:
                        pass
                
                import threading
                th = threading.Thread(target=monitor, daemon=True)
                th.start()
                
                try:
                    stdout, stderr = proc.communicate(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    timeout_expired = True
                    proc.kill()
                    stdout, stderr = proc.communicate()
                th.join(timeout=0.1)
                
            except Exception as e:
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Execution error: {str(e)}",
                    "compiler_output": str(e),
                    "error": str(e),
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

            proc_rt = round((time.perf_counter() - start_t) * 1000, 2)
            proc_mem = round(peak_rss / (1024.0 * 1024.0), 2) if peak_rss > 0 else None

            if timeout_expired:
                return {
                    "status": "TLE",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Time Limit Exceeded: Code ran longer than {timeout_seconds}s",
                    "compiler_output": "Time Limit Exceeded (TLE)",
                    "error": "Time Limit Exceeded (TLE)",
                    "runtime_ms": round(timeout_seconds * 1000, 2),
                    "memory_mb": proc_mem,
                    "test_case_results": []
                }

            if proc.returncode != 0:
                clean_err = (stderr or stdout or f"Process crashed with exit code {proc.returncode}").strip()
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "C Runtime Error (Crash / Segmentation Fault).",
                    "compiler_output": clean_err,
                    "error": clean_err,
                    "runtime_ms": proc_rt,
                    "memory_mb": proc_mem,
                    "test_case_results": []
                }

            if not os.path.exists(res_file):
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "Execution completed without producing structured test results.",
                    "compiler_output": stdout[:300] if stdout else "No output produced.",
                    "error": stdout[:300] if stdout else "No output produced.",
                    "runtime_ms": proc_rt,
                    "memory_mb": proc_mem,
                    "test_case_results": []
                }

            try:
                with open(res_file, "r", encoding="utf-8") as f:
                    res_data = json.load(f)
                raw_results = res_data.get("results", [])
            except Exception as e:
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Failed to parse C execution results: {str(e)}",
                    "compiler_output": str(e),
                    "error": str(e),
                    "runtime_ms": proc_rt,
                    "memory_mb": proc_mem,
                    "test_case_results": []
                }

            return {
                "_raw_c_results": raw_results,
                "proc_rt": proc_rt,
                "proc_mem": proc_mem,
                "user_stdout": stdout
            }
