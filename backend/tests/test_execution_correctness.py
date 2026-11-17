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
from datetime import date, datetime
from decimal import Decimal

from backend.app.engines.c_runner import CRunner
from backend.app.engines.comparison_engine import ComparisonContract as Compare
from backend.app.engines.debug_tracer import DebugTracer
from backend.app.engines.sandbox_runner import SandboxRunner as Runner, ToolchainUnavailableError
from backend.app.engines.sql_runner import SQLRunner
from backend.app.engines.execution_serialization import dump_answer, pack_dataframe, unpack_dataframe


class ExecutionSerializationTests(unittest.TestCase):
    def test_decimal_and_numpy_answers_keep_numeric_types(self):
        import numpy as np
        self.assertEqual(json.loads(dump_answer(np.int64(6))), 6)
        self.assertIs(json.loads(dump_answer(np.bool_(True))), True)
        self.assertEqual(dump_answer(Decimal('9007199254740993')), '9007199254740993')
        self.assertEqual(dump_answer(Decimal('1.234567890123456789')), '1.234567890123456789')
        self.assertEqual(json.loads(dump_answer([np.int64(1), Decimal('1.5'), '001'])), [1, 1.5, '001'])
        self.assertEqual(json.loads(dump_answer(np.array([1,2]))), [1,2])
        class CustomInteger(np.int64):
            pass
        self.assertEqual(json.loads(dump_answer(CustomInteger(6))), 6)

    def test_dataframe_roundtrip_preserves_dates_and_scalar_values(self):
        import pandas as pd
        import numpy as np
        values = [date(2020,1,1), datetime(2020,1,1,12,30),
                  pd.Timestamp('2020-01-01T01:02:03.123456789+00:00'),
                  Decimal('1.234567890123456789'), np.int64(9007199254740993),
                  np.bool_(True), None, 'null', b'bytes',
                  np.datetime64('2020-01-01T00:00:00.123456789', 'ns'), np.timedelta64(123456789, 'ns'), pd.NA]
        frame = pd.DataFrame({'value': values}, dtype=object)
        wire = json.loads(json.dumps(pack_dataframe(frame), allow_nan=False))
        restored = unpack_dataframe(wire)
        for before, after in zip(values[:-1], restored['value'].tolist()[:-1]):
            self.assertEqual(str(before), str(after))
        self.assertIs(type(restored.iloc[0,0]), date)
        self.assertIsInstance(restored.iloc[2,0], pd.Timestamp)
        self.assertIsInstance(restored.iloc[3,0], Decimal)
        self.assertIsNone(restored.iloc[-1,0])

    def test_literal_cells_cannot_be_mistaken_for_transport_tags(self):
        import pandas as pd
        original = {'value': ['date', '2020-01-01'], 'kind': 'decimal'}
        frame = pd.DataFrame({'value': [original]}, dtype=object)
        restored = unpack_dataframe(json.loads(json.dumps(pack_dataframe(frame))))
        self.assertEqual(restored.iloc[0,0], original)


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
        self.assertEqual(self.parse([dict(test_case_index=1)], [case('', 'null')])['status'], 'RUNTIME_ERROR')
        self.assertEqual(self.parse([dict(test_case_index=True, actual_output='null')], [case('', 'null')])['status'], 'RUNTIME_ERROR')
        self.assertTrue(self.parse([dict(test_case_index=1, actual_output=None)], [case('', 'null')])['is_correct'])

    def test_custom_inputs_do_not_require_expected_but_errors_fail(self):
        for value, correct in [('42', True), ('Runtime Error: failure', False)]:
            r = self.parse([dict(test_case_index=1, actual_output=value)], [case('', '', is_custom=True)])
            self.assertEqual(r['is_correct'], correct)


class SQLTests(unittest.TestCase):
    def test_ascii_numeric_text_uses_output_column_type(self):
        for label in ('123', '001', 'true', '1e3', '-12.50', '"123"', '[1,2]', '{"x":1}', '""', '"null"'):
            with self.subTest(label=label):
                fixture = json.dumps({'headers': {'T': ['label']}, 'rows': {'T': [[label]]}})
                expected = SQLRunner.format_ascii_table(['label'], [(label,)])
                r = SQLRunner.evaluate('SELECT label FROM T', [case(fixture, expected)])
                self.assertTrue(r['is_correct'], r)
        fixture = json.dumps({'headers': {'T': ['label']}, 'rows': {'T': [['123']]}})
        expected = json.dumps({'headers': ['label'], 'rows': [['123']]})
        cast = SQLRunner.evaluate('SELECT CAST(label AS BIGINT) AS label FROM T', [case(fixture, expected)])
        self.assertFalse(cast['is_correct'], cast)

    def test_ascii_numeric_columns_remain_numeric(self):
        fixture = json.dumps({'headers': {'T': ['amount']}, 'rows': {'T': [[123]]}})
        expected = SQLRunner.format_ascii_table(['amount'], [(123,)])
        r = SQLRunner.evaluate('SELECT amount FROM T', [case(fixture, expected)])
        self.assertTrue(r['is_correct'], r)
        typed_expected = json.dumps({'headers': ['amount'], 'rows': [[123]]})
        cast = SQLRunner.evaluate('SELECT CAST(amount AS VARCHAR) AS amount FROM T', [case(fixture, typed_expected)])
        self.assertFalse(cast['is_correct'], cast)

    def test_ascii_aggregate_and_ordering_behavior_is_preserved(self):
        fixture = json.dumps({'headers': {'T': ['amount']}, 'rows': {'T': [[1], [2], [3]]}})
        expected = SQLRunner.format_ascii_table(['total'], [(6,)])
        r = SQLRunner.evaluate('SELECT SUM(amount) AS total FROM T', [case(fixture, expected)])
        self.assertTrue(r['is_correct'], r)
        ordered = SQLRunner.format_ascii_table(['amount'], [(1,), (2,), (3,)])
        wrong = SQLRunner.evaluate('SELECT amount FROM T ORDER BY amount DESC', [case(fixture, ordered)])
        self.assertFalse(wrong['is_correct'], wrong)

    def test_ascii_computed_columns_do_not_inherit_input_types(self):
        fixture = json.dumps({'headers': {'T': ['event_date']}, 'rows': {'T': [['2020-01-01']]}})
        expected = SQLRunner.format_ascii_table(['event_date'], [(2020,)])
        query = 'SELECT EXTRACT(YEAR FROM event_date) AS event_date FROM T'
        self.assertTrue(SQLRunner.evaluate(query, [case(fixture, expected)])['is_correct'])

    def test_explicit_legacy_column_type_cannot_be_changed_by_candidate_cast(self):
        fixture = json.dumps({'headers': {'T': ['amount']}, 'rows': {'T': [[123]]}})
        expected = SQLRunner.format_ascii_table(['amount'], [(123,)])
        cases = [case(fixture, expected, expected_column_kinds=['number'])]
        self.assertTrue(SQLRunner.evaluate('SELECT amount FROM T', cases)['is_correct'])
        self.assertFalse(SQLRunner.evaluate('SELECT CAST(amount AS VARCHAR) AS amount FROM T', cases)['is_correct'])

    def test_ascii_boolean_and_structured_outputs_keep_native_types(self):
        for actual, expected in [(True, 'True'), ([1,2], '[1,2]'), ({'x': 1}, '{"x":1}')]:
            with self.subTest(actual=actual):
                table = '+-------+\n| value |\n+-------+\n| ' + expected + ' |\n+-------+'
                self.assertTrue(SQLRunner.compare_results(['value'], [(actual,)], table)[0])
        fixture = json.dumps({'headers': {'T': ['flag']}, 'rows': {'T': [[True], [False]]}})
        expected = SQLRunner.format_ascii_table(['flag'], [(True,), (False,)])
        self.assertTrue(SQLRunner.evaluate('SELECT flag = 1 AS flag FROM T', [case(fixture, expected)])['is_correct'])
        average = SQLRunner.format_ascii_table(['average'], [(0.5,)])
        self.assertTrue(SQLRunner.evaluate('SELECT AVG(flag) AS average FROM T', [case(fixture, average)])['is_correct'])

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

    def test_python_numeric_library_answers_are_graded_as_numbers(self):
        examples = [
            ('import numpy as np\ndef solve(nums):\n return np.sum(nums)', '[1,2,3]', '6'),
            ('import numpy as np\ndef solve(n):\n return np.bool_(n)', '1', 'true'),
            ('from decimal import Decimal\ndef solve(n):\n return Decimal("1.5")', '1', '1.5'),
            ('from decimal import Decimal\ndef solve(n):\n return Decimal("9007199254740993")', '1', '9007199254740993'),
        ]
        for code, inp, expected in examples:
            with self.subTest(code=code):
                self.assertTrue(Runner.evaluate_code(code, 'python', [case(inp, expected)])['is_correct'])
                self.assertFalse(Runner.evaluate_code(code, 'python', [case(inp, json.dumps(expected))])['is_correct'])

    def test_pandas_dates_timestamps_and_decimals_keep_their_values(self):
        import pandas as pd
        from backend.app.engines.db_fixture_normalizer import df_to_ascii_table
        fixture = json.dumps({'headers': {'T': ['n']}, 'rows': {'T': [[1]]}})
        constructors = ['date(2020,1,1)', 'pd.Timestamp("2020-01-01T00:00:00.123456789")', 'Decimal("1.5")']
        for expression in constructors:
            with self.subTest(expression=expression):
                original = eval(expression, {'date': date, 'pd': pd, 'Decimal': Decimal})
                expected = df_to_ascii_table(pd.DataFrame({'value': [original]}))
                code = 'import pandas as pd\nfrom datetime import date\nfrom decimal import Decimal\ndef solve(t):\n return pd.DataFrame({"value":[' + expression + ']})'
                result = Runner.evaluate_code(code, 'python', [case(fixture, expected)])
                self.assertTrue(result['is_correct'], result)
                self.assertNotIn('_table_output', result['test_case_results'][0])
                wrong = Runner.evaluate_code(code, 'python', [case(fixture, df_to_ascii_table(pd.DataFrame({'value': ['wrong']})))])
                self.assertFalse(wrong['is_correct'], wrong)

    def test_typescript_module_and_script_semantics_are_preserved(self):
        self.available('typescript')
        examples = [
            ('export function solve(n:number):number { return this===undefined?1:0; }', '1'),
            ('export const solve=(n:number):number=>this===undefined?1:0;', '1'),
            ('function solve(n:number):number { return this===undefined?1:0; }', '0'),
            ('function solve(n:number):number { return n; } export=solve;', '7'),
        ]
        for code, expected in examples:
            with self.subTest(code=code):
                result = Runner.evaluate_code(code, 'typescript', [case('7', expected)])
                self.assertTrue(result['is_correct'], result)
                traced = DebugTracer.trace(code, 'typescript', '7', 40)
                self.assertEqual(traced['status'], 'SUCCESS', traced)
                self.assertEqual(traced['return_value'], int(expected))

    def test_script_strict_directives_and_sloppy_functions_are_preserved(self):
        for lang, signature in [('javascript', 'function solve(n)'), ('typescript', 'function solve(n:number):number')]:
            self.available(lang)
            for prefix in ['"use strict";\n', '/* license */\n"use strict"\n', '"other";\n"use strict";\n']:
                with self.subTest(language=lang, prefix=prefix):
                    code = prefix + signature + ' { return this===undefined?1:0; }'
                    result = Runner.evaluate_code(code, lang, [case('1', '1')])
                    self.assertTrue(result['is_correct'], result)
        code = 'function solve(n) { "use strict"; return helper(); }\nfunction helper() { return this===undefined?1:0; }'
        self.assertTrue(Runner.evaluate_code(code, 'javascript', [case('1', '0')])['is_correct'])
        for expression in ['!= "x"', 'in {}', 'instanceof Object', '.length']:
            code = '"use strict"\n' + expression + ';\nfunction solve(n) {return this===undefined?1:0;}'
            self.assertTrue(Runner.evaluate_code(code, 'javascript', [case('1', '0')])['is_correct'], code)

    def test_debug_api_serializes_java_nonfinite_locals(self):
        self.available('java', debug=True)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.app.api.lc_practice import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        code = ('class Solution {\n public int solve(int n) {\n'
                ' double positive=Double.POSITIVE_INFINITY;\n'
                ' double negative=Double.NEGATIVE_INFINITY;\n'
                ' double invalid=Double.NaN;\n'
                ' float invalidFloat=Float.NaN;\n'
                ' double[] values={positive,negative,invalid};\n'
                ' return n;\n }}')
        response = client.post('/api/practice/lc/questions/two-sum/debug',
                               json={'code': code, 'language': 'java', 'custom_input': '7'})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['return_value'], 7)
        snapshots = [step['variables'] for step in result['steps'] if 'values' in step['variables']]
        self.assertTrue(snapshots, result)
        self.assertEqual(snapshots[-1]['positive'], {'__type__': 'float', 'value': 'Infinity'})
        self.assertEqual(snapshots[-1]['invalidFloat'], {'__type__': 'float', 'value': 'NaN'})
        json.dumps(result, allow_nan=False)

    def test_python_debug_nonfinite_values_are_json_safe(self):
        code = 'def solve(n):\n value=float("inf")\n return n'
        result = DebugTracer.trace(code, 'python', '7', 40)
        self.assertEqual(result['status'], 'SUCCESS', result)
        self.assertEqual(result['return_value'], 7)
        json.dumps(result, allow_nan=False)

    def test_python_debug_binds_standard_annotated_inputs(self):
        examples = [
            ('class Solution:\n def solve(self, nums: List[int]) -> int:\n  return nums[0]', '[7]', 7),
            ('from __future__ import annotations\nclass Solution:\n def solve(self, nums: List[int]) -> int:\n  return nums[0]', '[7]', 7),
            ('from __future__ import annotations\nclass Solution:\n def solve(self, nums: list) -> int:\n  return nums[0]', '[7]', 7),
            ('class Solution:\n def solve(self, root: Optional[TreeNode]) -> int:\n  return root.val', '[7]', 7),
            ('class Solution:\n def solve(self, head: Optional[ListNode]) -> int:\n  return head.next.val', '[7,8]', 8),
            ('class Solution:\n def solve(self, a: Optional[ListNode], b: Optional[ListNode]) -> int:\n  return a.val+b.val', '[7]\n[8]', 15),
        ]
        for code, inp, expected in examples:
            with self.subTest(code=code):
                result = DebugTracer.trace(code, 'python', inp, 40)
                self.assertEqual(result['status'], 'SUCCESS', result)
                self.assertEqual(result['return_value'], expected)
                self.assertTrue(all(s['line'] <= len(code.splitlines()) for s in result['steps']))

    def test_stdout_before_exceptions_and_runtime_verdicts_are_preserved(self):
        examples = {
            'python': 'def solve(n):\n print("before")\n raise ValueError("boom")',
            'javascript': 'function solve(n) { console.log("before"); throw new Error("boom"); }',
            'java': 'class Solution {public int solve(int n) {System.out.print("before"); throw new RuntimeException("boom");}}',
            'cpp': 'class Solution {public: int solve(int n) {cout << "before"; throw 1;}};',
        }
        for lang, code in examples.items():
            with self.subTest(language=lang):
                self.available(lang, debug=True)
                result = Runner.evaluate_code(code, lang, [case('1', '1')])
                self.assertEqual(result['status'], 'RUNTIME_ERROR', result)
                self.assertIn('before', result['test_case_results'][0]['stdout'])
                traced = DebugTracer.trace(code, lang, '1', 40)
                self.assertEqual(traced['status'], 'RUNTIME_ERROR', traced)
                self.assertIn('before', traced['stdout'])

    def test_javascript_logging_does_not_execute_tojson_or_fail_on_cycles(self):
        self.available('javascript')
        code = 'function solve(n) { let changed=0; console.log({toJSON(){changed++;return "bad";}}); return changed; }'
        self.assertTrue(Runner.evaluate_code(code, 'javascript', [case('1', '0')])['is_correct'])
        code = 'function solve(n) { const value={}; value.self=value; console.log(value); return n; }'
        result = Runner.evaluate_code(code, 'javascript', [case('7', '7')])
        self.assertTrue(result['is_correct'], result)
        self.assertIn('Circular', result['test_case_results'][0]['stdout'])

    def test_python_design_operations_keep_output_and_numeric_results(self):
        code = ('class Counter:\n def __init__(self,n):\n  print("init")\n  self.n=n\n'
                ' def add(self,n):\n  print("add")\n  self.n+=n\n'
                ' def value(self):\n  print("value")\n  return self.n')
        inp = '["Counter","add","value"]\n[[1],[2],[]]'
        result = Runner.evaluate_code(code, 'python', [case(inp, '[null,null,3]')])
        self.assertTrue(result['is_correct'], result)
        self.assertEqual(result['test_case_results'][0]['stdout'], 'init\nadd\nvalue\n')

    def test_javascript_and_typescript_arrow_entrypoints(self):
        for lang, examples in {
            'javascript': ['const answer=(n)=>n+1;', 'const answer=n=>n+1;', 'class Solution {answer=(n)=>n+1;}'],
            'typescript': ['export const answer=(n:number):number=>n+1;', 'class Solution {answer=(n:number):number=>n+1;}'],
        }.items():
            self.available(lang, debug=True)
            for code in examples:
                with self.subTest(language=lang, code=code):
                    result = Runner.evaluate_code(code, lang, [case('7', '8')])
                    self.assertTrue(result['is_correct'], result)
                    traced = DebugTracer.trace(code, lang, '7', 40)
                    self.assertEqual(traced['status'], 'SUCCESS', traced)
                    self.assertEqual(traced['return_value'], 8)

    def test_python_run_and_debug_select_the_same_declared_method(self):
        code = ('class Solution:\n def solve(self,n):\n  return self.aaa(n)+1\n'
                ' def aaa(self,n):\n  return n')
        self.assertTrue(Runner.evaluate_code(code, 'python', [case('7', '8')])['is_correct'])
        traced = DebugTracer.trace(code, 'python', '7', 40)
        self.assertEqual(traced['status'], 'SUCCESS', traced)
        self.assertEqual(traced['return_value'], 8)

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

    def test_java_overloaded_methods_have_distinct_breakpoints(self):
        self.available('java', debug=True)
        code = ('class Solution {\n'
                ' public int solve(int n) { return solve(n,2); }\n'
                ' private int solve(int a,int b) { return a+b; }\n'
                '}')
        traced = DebugTracer.trace(code, 'java', '3', 40)
        self.assertEqual(traced['status'], 'SUCCESS', traced)
        self.assertEqual(traced['return_value'], 5)
        self.assertTrue(any(step['line'] == 2 and step['variables'].get('n') == 3 for step in traced['steps']), traced)
        self.assertTrue(any(step['line'] == 3 and step['variables'].get('a') == 3 and
                            step['variables'].get('b') == 2 for step in traced['steps']), traced)

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


class CInputTests(unittest.TestCase):
    def test_quoted_assignment_text_is_one_argument(self):
        self.assertEqual(CRunner.split_input('"a, b=c"\n7'), ['"a, b=c"', '7'])
        self.assertEqual(CRunner.split_input('s="a, b=c", n=7'), ['"a, b=c"', '7'])

    def test_nested_values_and_escaped_quotes_preserve_argument_boundaries(self):
        quoted = json.dumps('a, b="c", next=d\\e')
        values = '[' + quoted + ',"second, n=3"]'
        self.assertEqual(CRunner.split_input('items = ' + values + ', limit = 7'), [values, '7'])
        self.assertEqual(CRunner.split_input(quoted + ', 7'), [quoted, '7'])

    def test_existing_labeled_and_unlabeled_inputs_are_preserved(self):
        for raw in ('nums = [2,7], target = 9', 'nums = [2,7]\ntarget = 9', '[2,7]\n9', '[2,7],9'):
            with self.subTest(raw=raw):
                self.assertEqual(CRunner.split_input(raw), ['[2,7]', '9'])
        self.assertEqual(CRunner.split_input('s = "", n = 0'), ['""', '0'])
        matrix = '[\r\n [1,2],\r\n [3,4]\r\n]'
        self.assertEqual(CRunner.split_input('matrix=' + matrix + '\r\nn=2'), [matrix, '2'])


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

    def test_qualified_array_returns_and_parameters(self):
        for return_type in ('const int*', 'int const *', 'volatile int*', 'const volatile int*', 'const int* const'):
            with self.subTest(return_type=return_type):
                code = return_type + ' solve(const int* nums, int numsSize, int* const returnSize) {' \
                    ' int* a=malloc(numsSize*sizeof(int)); for(int i=0;i<numsSize;i++) a[i]=nums[i];' \
                    ' *returnSize=numsSize; return a; }'
                actual = self.run_c(code, '[7,8]', '[7,8]')
                self.assertEqual(json.loads(actual), [7,8])

    def test_qualified_matrix_return_preserves_pointer_depth(self):
        for return_type in ('int** const', 'int* const*', 'const int**', 'const volatile int* const*'):
            with self.subTest(return_type=return_type):
                code = (return_type + ' solve(int* returnSize, int** const returnColumnSizes) {'
                        ' int** out=malloc(sizeof(int*)); out[0]=malloc(2*sizeof(int));'
                        ' out[0][0]=7; out[0][1]=8; *returnSize=1;'
                        ' *returnColumnSizes=malloc(sizeof(int)); **returnColumnSizes=2;'
                        ' return (' + return_type + ')out; }')
                self.assertEqual(json.loads(self.run_c(code, '', '[[7,8]]')), [[7,8]])

    def test_quoted_assignment_text_reaches_c_function_unchanged(self):
        code = 'int solve(char* s, int n) { return strcmp(s,"a, b=c")==0 ? n : 0; }'
        self.run_c(code, '"a, b=c"\n7', '7')
        self.run_c(code, 's = "a, b=c", n = 7', '7')

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
