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
    
    struct TreeNode* queue[4096];
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
    free(s);
    return root;
}

/* Formatters */
static void c_format_int(int v, char* buf, size_t buf_sz) { snprintf(buf, buf_sz, "%d", v); }
static void c_format_long(long long v, char* buf, size_t buf_sz) { snprintf(buf, buf_sz, "%lld", v); }
static void c_format_double(double v, char* buf, size_t buf_sz) { snprintf(buf, buf_sz, "%.5f", v); }
static void c_format_bool(bool v, char* buf, size_t buf_sz) { snprintf(buf, buf_sz, "%s", v ? "true" : "false"); }
static void c_format_string(const char* s, char* buf, size_t buf_sz) {
    if (!s) { snprintf(buf, buf_sz, "\"\""); return; }
    snprintf(buf, buf_sz, "\"%s\"", s);
}

static void c_format_int_array(const int* arr, int sz, char* buf, size_t buf_sz) {
    if (!arr || sz <= 0) { snprintf(buf, buf_sz, "[]"); return; }
    size_t off = snprintf(buf, buf_sz, "[");
    for (int i = 0; i < sz && off < buf_sz - 20; i++) {
        if (i > 0) off += snprintf(buf + off, buf_sz - off, ",");
        off += snprintf(buf + off, buf_sz - off, "%d", arr[i]);
    }
    snprintf(buf + off, buf_sz - off, "]");
}

static void c_format_matrix(int** mat, int rows, const int* cols, char* buf, size_t buf_sz) {
    if (!mat || rows <= 0) { snprintf(buf, buf_sz, "[]"); return; }
    size_t off = snprintf(buf, buf_sz, "[");
    for (int i = 0; i < rows && off < buf_sz - 40; i++) {
        if (i > 0) off += snprintf(buf + off, buf_sz - off, ",");
        char row_buf[1024];
        c_format_int_array(mat[i], cols ? cols[i] : 0, row_buf, sizeof(row_buf));
        off += snprintf(buf + off, buf_sz - off, "%s", row_buf);
    }
    snprintf(buf + off, buf_sz - off, "]");
}

static void c_format_listnode(struct ListNode* head, char* buf, size_t buf_sz) {
    if (!head) { snprintf(buf, buf_sz, "[]"); return; }
    size_t off = snprintf(buf, buf_sz, "[");
    struct ListNode* curr = head;
    bool first = true;
    while (curr && off < buf_sz - 20) {
        if (!first) off += snprintf(buf + off, buf_sz - off, ",");
        off += snprintf(buf + off, buf_sz - off, "%d", curr->val);
        first = false;
        curr = curr->next;
    }
    snprintf(buf + off, buf_sz - off, "]");
}

static void c_format_treenode(struct TreeNode* root, char* buf, size_t buf_sz) {
    if (!root) { snprintf(buf, buf_sz, "[]"); return; }
    struct TreeNode* queue[4096];
    int head = 0, tail = 0;
    queue[tail++] = root;
    
    char* vals[4096];
    int val_count = 0;
    while (head < tail && val_count < 4000) {
        struct TreeNode* curr = queue[head++];
        if (curr) {
            char* nb = (char*)malloc(32);
            snprintf(nb, 32, "%d", curr->val);
            vals[val_count++] = nb;
            queue[tail++] = curr->left;
            queue[tail++] = curr->right;
        } else {
            vals[val_count++] = c_strdup("null");
        }
    }
    while (val_count > 0 && strcmp(vals[val_count - 1], "null") == 0) {
        free(vals[--val_count]);
    }
    size_t off = snprintf(buf, buf_sz, "[");
    for (int i = 0; i < val_count && off < buf_sz - 20; i++) {
        if (i > 0) off += snprintf(buf + off, buf_sz - off, ",");
        off += snprintf(buf + off, buf_sz - off, "%s", vals[i]);
        free(vals[i]);
    }
    snprintf(buf + off, buf_sz - off, "]");
}

static void c_escape_json(const char* src, char* dst, size_t dst_sz) {
    size_t j = 0;
    for (size_t i = 0; src[i] && j < dst_sz - 4; i++) {
        if (src[i] == '"' || src[i] == '\\') {
            dst[j++] = '\\';
            dst[j++] = src[i];
        } else if (src[i] == '\n') {
            dst[j++] = '\\';
            dst[j++] = 'n';
        } else if (src[i] == '\r') {
            dst[j++] = '\\';
            dst[j++] = 'r';
        } else if (src[i] == '\t') {
            dst[j++] = '\\';
            dst[j++] = 't';
        } else {
            dst[j++] = src[i];
        }
    }
    dst[j] = '\0';
}
'''

C_HARNESS_PREAMBLE = C_HEADERS + "\n" + C_STRUCT_LISTNODE + "\n" + C_STRUCT_TREENODE + "\n" + C_HARNESS_HELPERS

class CRunner:
    @classmethod
    def split_input(cls, raw: str) -> List[str]:
        raw = raw.strip()
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
            r'(?:^|[\n;])\s*([a-zA-Z0-9_* ]+?)\s+([a-zA-Z_]\w*)\s*\(([\s\S]*?)\)\s*\{',
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
                if "returnSize" in p_name or ("int*" in p_type_clean and "return" in p_name.lower()):
                    decls.append(f"        int ret_sz_{tc_idx} = 0;")
                    call_args.append(f"&ret_sz_{tc_idx}")
                    p_idx += 1
                    continue
                # Check for out-parameters: returnColumnSizes
                if "returnColumnSizes" in p_name or ("int**" in p_type_clean and "column" in p_name.lower()):
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
                    fmt_stmt = f"        c_format_int_array({first_arg_name[0]}, {first_arg_name[1]}, act_buf, sizeof(act_buf));"
                elif first_arg_type == "matrix":
                    fmt_stmt = f"        c_format_matrix({first_arg_name[0]}, {first_arg_name[1]}, {first_arg_name[2]}, act_buf, sizeof(act_buf));"
                else:
                    fmt_stmt = '        snprintf(act_buf, sizeof(act_buf), "void");'
            elif "int*" in ret_clean:
                call_stmt = f"        int* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_int_array(ret_val, ret_sz_{tc_idx}, act_buf, sizeof(act_buf));\n        if (ret_val) free(ret_val);"
            elif "int**" in ret_clean:
                call_stmt = f"        int** ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_matrix(ret_val, ret_sz_{tc_idx}, ret_col_sz_{tc_idx}, act_buf, sizeof(act_buf));"
            elif "char*" in ret_clean:
                call_stmt = f"        char* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_string(ret_val, act_buf, sizeof(act_buf));"
            elif "listnode" in ret_type.lower():
                call_stmt = f"        struct ListNode* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_listnode(ret_val, act_buf, sizeof(act_buf));"
            elif "treenode" in ret_type.lower():
                call_stmt = f"        struct TreeNode* ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_treenode(ret_val, act_buf, sizeof(act_buf));"
            elif "bool" in ret_clean:
                call_stmt = f"        bool ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_bool(ret_val, act_buf, sizeof(act_buf));"
            elif "double" in ret_clean or "float" in ret_clean:
                call_stmt = f"        double ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_double(ret_val, act_buf, sizeof(act_buf));"
            elif "long" in ret_clean:
                call_stmt = f"        long long ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_long(ret_val, act_buf, sizeof(act_buf));"
            else:
                call_stmt = f"        int ret_val = {func_name}({args_str});"
                fmt_stmt = f"        c_format_int(ret_val, act_buf, sizeof(act_buf));"

            case_str = f"""    /* Case {tc_idx + 1} */
    {{
        char act_buf[4096];
        char esc_act[8192];
{decls_str}
        clock_t t0 = clock();
{call_stmt}
        double elapsed_ms = ((double)(clock() - t0) / CLOCKS_PER_SEC) * 1000.0;
{fmt_stmt}
        c_escape_json(act_buf, esc_act, sizeof(esc_act));
        if ({tc_idx} > 0) fputs(",\\n", out_file);
        fprintf(out_file, "    {{\\\"test_case_index\\\": {tc_idx + 1}, \\\"actual_output\\\": \\\"%s\\\", \\\"runtime_ms\\\": %.3f}}", esc_act, elapsed_ms);
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

            comp = subprocess.run([gcc, "-std=c11", "-O2", "-pipe", src_file, "-o", exe_file], capture_output=True, text=True)
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
