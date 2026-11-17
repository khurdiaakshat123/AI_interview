"""Regression tests for compiler, comparison and native debugger correctness.

Run from the repository root:
    python -m unittest backend.tests.test_execution_correctness -v
Native integration tests skip explicitly when their toolchain is absent.
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.app.engines.c_runner import CRunner
from backend.app.engines.comparison_engine import ComparisonContract as Compare
from backend.app.engines.debug_tracer import DebugTracer
from backend.app.engines.sandbox_runner import SandboxRunner as Runner, ToolchainUnavailableError
from backend.app.engines.sql_runner import SQLRunner


def case(inp, expected, **metadata):
    return dict(input=inp, expected_output=expected, **metadata)


class ComparisonTests(unittest.TestCase):
    def test_permutations_retain_inner_order_and_multiplicity(self):
        expected = [[1, 2], [2, 1]]
        self.assertTrue(Compare.compare([[2, 1], [1, 2]], expected, "permutations")[0])
        self.assertFalse(Compare.compare([[1, 2], [1, 2]], expected, "permutations")[0])

    def test_only_wire_boundary_is_decoded(self):
        for actual, expected in [('["001"]', '[1]'), ('["null"]', '[null]'),
                                 ('["false"]', '[false]'), ('[true]', '[1]'),
                                 ('[" A "]', '["A"]'), ('["ALLEN"]', '["Allen"]')]:
            with self.subTest(actual=actual):
                self.assertFalse(Compare.compare(actual, expected)[0])

    def test_existing_float_tolerance_and_explicit_contract_are_preserved(self):
        self.assertTrue(Compare.compare('1.000001', '1.0')[0])
        self.assertFalse(Compare.compare('1.01', '1.0')[0])
        self.assertFalse(Compare.compare('"1.000001"', '1.0')[0])
        self.assertTrue(Compare.compare('1.000001', '1.0', contract={'float_tolerance': 1e-5})[0])

    def test_question_and_metadata_ordering(self):
        self.assertTrue(Compare.compare('[1,0]', '[0,1]', 'two-sum')[0])
        self.assertFalse(Compare.compare('[1,0]', '[0,1]', 'unrelated')[0])
        self.assertTrue(Compare.compare('[[2,1]]', '[[1,2]]', 'subsets')[0])
        self.assertTrue(Compare.compare('[["eat","tea"],["bat"]]', '[["bat"],["tea","eat"]]', 'group-anagrams')[0])
        self.assertFalse(Compare.compare('[1,2]', '[2,1]', 'group-anagrams')[0])
        self.assertFalse(Compare.compare('[1,2]', '[2,1]', 'subsets', {'is_ordered': True})[0])


class ServiceContextTests(unittest.TestCase):
    def test_run_and_submit_pass_question_context_to_runner(self):
        from backend.app.engines.lc_service import LCQuestionService
        with patch.object(LCQuestionService, 'initialize'):
            # Use the real question-loading and metadata path, with an in-memory DB mock.
            qref = {'id': '1', 'slug': 'two-sum', 'path': 'questions/dsa/hashing/two-sum.json', 'subcategory': 'hashing'}
            with patch.object(LCQuestionService, '_by_id', {'1': qref}), \
                 patch.object(LCQuestionService, '_by_slug', {'two-sum': qref}), \
                 patch.object(Runner, 'evaluate_code', return_value={'is_correct': False, 'status': 'WRONG_ANSWER'}) as evaluate:
                LCQuestionService.run_code('1', 'solution', 'python')
                self.assertEqual(evaluate.call_args.kwargs['question_slug'], 'two-sum')
                LCQuestionService.submit_code(MagicMock(), 'test-user', '1', 'solution', 'python')
                self.assertEqual(evaluate.call_args.kwargs['question_slug'], 'two-sum')


class ParentJudgeTests(unittest.TestCase):
    def parse(self, rows, cases, slug=None):
        text = '---SANDBOX_RESULTS_START---\n' + json.dumps({'results': rows}) + '\n---SANDBOX_RESULTS_END---'
        return Runner._parse_sandbox_output(text, cases, '', question_slug=slug)

    def test_hidden_values_graded_before_redaction(self):
        for actual, status in [('[1,0]', 'ACCEPTED'), ('[7,8]', 'WRONG_ANSWER')]:
            row = dict(test_case_index=1, actual_output=actual, expected_output='forged', stdout='secret')
            r = self.parse([row], [case('secret input', '[0,1]', is_hidden=True)], 'two-sum')
            self.assertEqual(r['status'], status)
            rendered = json.dumps(r)
            self.assertNotIn('secret', rendered)
            self.assertNotIn(actual, rendered)
            self.assertNotIn('[0,1]', rendered)

    def test_results_cannot_choose_expected_or_omit_cases(self):
        rows = [dict(test_case_index=1, actual_output='2', expected_output='2', passed=True)]
        self.assertEqual(self.parse(rows, [case('', '1')])['status'], 'WRONG_ANSWER')
        self.assertEqual(self.parse(rows, [case('', '2'), case('', '2')])['status'], 'RUNTIME_ERROR')
        self.assertEqual(self.parse([dict(test_case_index=2, actual_output='2')], [case('', '2')])['status'], 'RUNTIME_ERROR')

    def test_custom_inputs_do_not_require_expected_but_errors_fail(self):
        for value, correct in [('42', True), ('Runtime Error: failure', False)]:
            r = self.parse([dict(test_case_index=1, actual_output=value)], [case('', '', is_custom=True)])
            self.assertEqual(r['is_correct'], correct)


class SQLTests(unittest.TestCase):
    def test_typed_text_is_not_null_or_numeric(self):
        for a, b in [('null', None), ('none', None), ('001', 1), ('  A', 'A'), ('ALLEN', 'Allen')]:
            self.assertFalse(SQLRunner.compare_cells(a, b), (a, b))

    def test_expected_json_preserves_types_and_ascii_null_remains_supported(self):
        for headers in [['value'], {'Result': ['value']}]:
            rows = [['null']] if isinstance(headers, list) else {'Result': [['null']]}
            expected = json.dumps(dict(headers=headers, rows=rows))
            self.assertTrue(SQLRunner.compare_results(['VALUE'], [('null',)], expected)[0])
            self.assertFalse(SQLRunner.compare_results(['value'], [(None,)], expected)[0])
        ascii_table = '+-------+\n| value |\n+-------+\n| null |\n+-------+'
        self.assertTrue(SQLRunner.compare_results(['value'], [(None,)], ascii_table)[0])
        self.assertFalse(SQLRunner.compare_results(['value'], [('null',)], ascii_table)[0])

    def test_sql_literal_null_does_not_pass_a_null_answer(self):
        fixture = json.dumps({'headers': {'T': ['k']}, 'rows': {'T': [[1]]}})
        expected = json.dumps({'headers': ['value'], 'rows': [[None]]})
        self.assertFalse(SQLRunner.evaluate("SELECT 'null' AS value FROM T", [case(fixture, expected)])['is_correct'])
        self.assertTrue(SQLRunner.evaluate('SELECT NULL AS value FROM T', [case(fixture, expected)])['is_correct'])

    def test_joined_delete_uses_schema_and_null_safe_full_row(self):
        fixture = json.dumps({'headers': {'Other': ['x'], 'People': ['key_code', 'email', 'note']},
                              'rows': {'Other': [[1]], 'People': [[1, 'a', None], [2, 'a', None], [3, 'b', None]]}})
        expected = json.dumps({'headers': ['key_code', 'email', 'note'], 'rows': [[1, 'a', None], [3, 'b', None]]})
        sql = 'DELETE p1 FROM People p1 JOIN People p2 ON p1.email=p2.email WHERE p1.key_code > p2.key_code'
        r = SQLRunner.evaluate(sql, [case(fixture, expected)], dialect='mysql')
        self.assertTrue(r['is_correct'], r)

    def test_joined_delete_can_target_a_later_joined_table(self):
        fixture = json.dumps({'headers': {'A': ['k'], 'B': ['k', 'label']},
                              'rows': {'A': [[2]], 'B': [[1, 'keep'], [2, 'remove']]}})
        expected = json.dumps({'headers': ['k', 'label'], 'rows': [[1, 'keep']]})
        r = SQLRunner.evaluate('DELETE b FROM A a JOIN B b ON a.k=b.k', [case(fixture, expected)])
        self.assertTrue(r['is_correct'], r)


class TypeScriptTests(unittest.TestCase):
    def test_missing_compiler_is_explicit(self):
        with patch.dict(os.environ, {'INTERVYN_TSC_PATH': '/nonexistent/typescript/tsc'}):
            with self.assertRaises(ToolchainUnavailableError):
                Runner.typecheck_typescript('function solve(): number { return 1; }')
            r = Runner.evaluate_code('function solve(): number { return 1; }', 'typescript', [case('', '1')])
            if shutil.which('node'):
                self.assertEqual(r['status'], 'TOOLCHAIN_UNAVAILABLE')

    def test_type_errors_rejected_and_real_typescript_emitted(self):
        try:
            compiled, source_map = Runner.compile_typescript('enum Color { Red, Blue }\nfunction solve(): number { return Color.Blue; }')
        except ToolchainUnavailableError as exc:
            self.skipTest(str(exc))
        self.assertIn('Color', compiled)
        self.assertIn('mappings', source_map)
        self.assertIsNotNone(Runner.typecheck_typescript('function solve(): number { return "wrong"; }'))


LANGUAGES = {
    'c': ('gcc', 'int add(int a, int b) {\n printf("hello");\n int ans=a+b;\n return ans;\n}'),
    'cpp': ('g++', 'class Solution {public:\n int add(int a,int b) {\n cout << "hello";\n int ans=a+b;\n return ans;\n }\n};'),
    'java': ('javac', 'class Solution {\n public int add(int a,int b) {\n System.out.print("hello");\n int ans=a+b;\n return ans;\n }\n}'),
    'javascript': ('node', 'function add(a,b) {\n console.log("hello");\n const ans=a+b;\n return ans;\n}'),
    'typescript': ('node', 'function add(a:number,b:number):number {\n console.log("hello");\n const ans:number=a+b;\n return ans;\n}'),
    'python': ('python', 'class Solution:\n def add(self,a,b):\n  print("hello")\n  return a+b'),
}


class NativeIntegrationTests(unittest.TestCase):
    def available(self, lang, debug=False):
        compiler = LANGUAGES[lang][0]
        if not shutil.which(compiler) or (debug and lang in ('c', 'cpp') and not shutil.which('gdb')):
            self.skipTest('Required ' + lang + ' toolchain is unavailable')
        if lang == 'typescript':
            try:
                Runner.compile_typescript('function solve(): number { return 1; }')
            except ToolchainUnavailableError as exc:
                self.skipTest(str(exc))

    def test_all_runners_grade_real_hidden_results(self):
        for lang, (_, code) in LANGUAGES.items():
            with self.subTest(language=lang):
                self.available(lang)
                cases = [case('2\n3', '5', is_hidden=True), case('4\n6', '10', is_hidden=True)]
                r = Runner.evaluate_code(code, lang, cases)
                self.assertTrue(r['is_correct'], r)
                wrong = Runner.evaluate_code(code, lang, [case('2\n3', '9', is_hidden=True)])
                self.assertFalse(wrong['is_correct'], wrong)

    def test_strings_retain_json_types_whitespace_and_case(self):
        templates = {
            'c': 'char* solve(int n) { return %s; }',
            'cpp': 'class Solution {public: string solve(int n) { return %s; }};',
            'java': 'class Solution {public String solve(int n) { return %s; }}',
            'javascript': 'function solve(n) { return %s; }',
            'typescript': 'function solve(n:number):string { return %s; }',
            'python': 'def solve(n):\n return %s',
        }
        for lang, template in templates.items():
            with self.subTest(language=lang):
                self.available(lang)
                value = ' null '
                code = template % json.dumps(value)
                self.assertTrue(Runner.evaluate_code(code, lang, [case('1', json.dumps(value))])['is_correct'])
                self.assertFalse(Runner.evaluate_code(code, lang, [case('1', 'null')])['is_correct'])

    def test_question_contract_applies_in_every_runner(self):
        codes = {
            'c': 'int* solve(int n,int* returnSize) { static int a[]={1,0}; *returnSize=2; return a; }',
            'cpp': 'class Solution {public: vector<int> solve(int n) { return {1,0}; }};',
            'java': 'class Solution {public int[] solve(int n) { return new int[]{1,0}; }}',
            'javascript': 'function solve(n) { return [1,0]; }',
            'typescript': 'function solve(n:number):number[] { return [1,0]; }',
            'python': 'def solve(n):\n return [1,0]',
        }
        for lang, code in codes.items():
            with self.subTest(language=lang):
                self.available(lang)
                self.assertTrue(Runner.evaluate_code(code, lang, [case('1', '[0,1]')], question_slug='two-sum')['is_correct'])
                self.assertFalse(Runner.evaluate_code(code, lang, [case('1', '[0,1]')], question_slug='unrelated')['is_correct'])

    def test_native_control_characters_remain_valid_json(self):
        codes = {
            'cpp': 'class Solution { public: string solve(int n) { return string(1,char(7)); } };',
            'java': 'class Solution { public String solve(int n) { return String.valueOf((char)7); } }',
        }
        for lang, code in codes.items():
            with self.subTest(language=lang):
                self.available(lang, debug=True)
                r = Runner.evaluate_code(code, lang, [case('1', json.dumps(chr(7)))])
                self.assertTrue(r['is_correct'], r)
                traced = DebugTracer.trace(code, lang, '1', 40)
                self.assertEqual(traced['status'], 'SUCCESS', traced)
                self.assertEqual(traced['return_value'], chr(7))

    def test_pandas_column_alignment_and_actual_values_are_preserved(self):
        fixture = json.dumps({'headers': {'Person': ['name', 'city']}, 'rows': {'Person': [['Allen', None]]}})
        expected = '+-------+------+\n| name | city |\n+-------+------+\n| Allen | null |\n+-------+------+'
        for transform, correct in [("person[['city', 'name']]", True), ("person.assign(name='ALLEN')", False),
                                   ("person.assign(city='null')", False)]:
            code = 'import pandas as pd\ndef solve(person: pd.DataFrame) -> pd.DataFrame:\n return ' + transform
            r = Runner.evaluate_code(code, 'python', [case(fixture, expected)])
            self.assertEqual(r['is_correct'], correct, r)

    def test_javascript_arrays_are_visible_and_typescript_lines_are_mapped(self):
        code = 'function solve(nums:number[]):number {\n const other:number[] = nums.map(x => x+1);\n return other[0];\n}'
        self.available('typescript', debug=True)
        r = DebugTracer.trace(code, 'typescript', '[4,5]', 40)
        self.assertEqual(r['status'], 'SUCCESS', r)
        self.assertEqual(r['return_value'], 5)
        self.assertTrue(any(step['variables'].get('nums') == [4,5] for step in r['steps']), r)
        self.assertTrue(any(step['line'] == 3 for step in r['steps']), r)

    def test_native_debugger_timeout_is_not_success(self):
        code = 'function solve(n) { while(true) {} }'
        self.available('javascript', debug=True)
        with patch.object(DebugTracer, 'TIMEOUT_SECONDS', 0.8):
            r = DebugTracer.trace(code, 'javascript', '1', 350)
        self.assertIn(r['status'], ('TIMEOUT', 'STEP_LIMIT'), r)
        self.assertIsNone(r['return_value'])

    def test_all_debuggers_return_actual_result_and_stdout(self):
        for lang, (_, code) in LANGUAGES.items():
            with self.subTest(language=lang):
                self.available(lang, debug=True)
                r = DebugTracer.trace(code, lang, '2\n3', 40)
                self.assertEqual(r['status'], 'SUCCESS', r)
                self.assertEqual(r['return_value'], 5, r)
                self.assertIn('hello', r['stdout'])
                self.assertTrue(r['steps'], r)
                self.assertTrue(all(1 <= step['line'] <= len(code.splitlines()) for step in r['steps']))

    def test_native_debugger_step_limit_is_not_success(self):
        for lang, (_, code) in LANGUAGES.items():
            if lang == 'python':
                continue
            with self.subTest(language=lang):
                self.available(lang, debug=True)
                r = DebugTracer.trace(code, lang, '2\n3', 1)
                self.assertEqual(r['status'], 'STEP_LIMIT', r)
                self.assertIsNone(r['return_value'])
                self.assertTrue(r['max_steps_reached'])

    def test_native_debugger_runtime_errors_do_not_become_success(self):
        codes = {
            'c': 'int solve(int n) {\n int* p = 0;\n return *p;\n}',
            'cpp': 'class Solution {public: int solve(int n) {\n throw 1;\n return n;\n}};',
            'java': 'class Solution { public int solve(int n) {\n throw new RuntimeException("boom");\n}}',
            'javascript': 'function solve(n) {\n throw new Error("boom");\n}',
            'typescript': 'function solve(n:number):number {\n throw new Error("boom");\n}',
        }
        for lang, code in codes.items():
            with self.subTest(language=lang):
                self.available(lang, debug=True)
                r = DebugTracer.trace(code, lang, '1', 40)
                self.assertEqual(r['status'], 'RUNTIME_ERROR', r)
                self.assertIsNone(r['return_value'])


@unittest.skipUnless(shutil.which('gcc') or shutil.which('clang'), 'C compiler unavailable')
class COutputTests(unittest.TestCase):
    def run_c(self, code, inp, expected):
        r = Runner.evaluate_code(code, 'c', [case(inp, expected)])
        self.assertTrue(r['is_correct'], r)
        return r['test_case_results'][0]['actual_output']

    def test_matrix_output_parameters_and_wide_rows(self):
        code = '''int** solve(int** matrix, int matrixSize, int* matrixColSize,
                              int* returnSize, int** returnColumnSizes) {
            *returnSize=matrixSize; *returnColumnSizes=matrixColSize; return matrix;
        }'''
        matrix = [list(range(3000)), [7], []]
        actual = self.run_c(code, json.dumps(matrix), json.dumps(matrix))
        self.assertEqual(json.loads(actual), matrix)

    def test_long_array_return_is_not_truncated_or_freed_as_owned(self):
        code = 'int *solve(int* nums, int numsSize, int* returnSize) { *returnSize=numsSize; return nums; }'
        values = list(range(6000))
        actual = self.run_c(code, json.dumps(values), json.dumps(values))
        self.assertEqual(json.loads(actual), values)

    def test_long_linked_list_and_tree(self):
        values = list(range(5000))
        for name in ('ListNode', 'TreeNode'):
            with self.subTest(structure=name):
                actual = self.run_c('struct ' + name + '* solve(struct ' + name + '* root) { return root; }',
                                    json.dumps(values), json.dumps(values))
                self.assertEqual(json.loads(actual), values)

    def test_long_string_and_json_escapes(self):
        code = 'char* solve(int n) { char* s=malloc(n+4); for(int i=0;i<n;i++) s[i]=\'x\'; s[n]=34; s[n+1]=92; s[n+2]=10; s[n+3]=0; return s; }'
        expected = 'x' * 9000 + '"\\\n'
        actual = self.run_c(code, '9000', json.dumps(expected))
        self.assertEqual(json.loads(actual), expected)


if __name__ == '__main__':
    unittest.main()
