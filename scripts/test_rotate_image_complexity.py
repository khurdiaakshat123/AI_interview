# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.app.engines.lc_service import LCQuestionService

LCQuestionService._is_initialized = False
LCQuestionService.initialize()

rotate_img = LCQuestionService.get_question('rotate-image', db=None)
print('Rotate Image Time:', rotate_img.get('timeComplexity'))
print('Rotate Image Space:', rotate_img.get('spaceComplexity'))
print('Rotate Image Approach:', rotate_img.get('approach'))

assert rotate_img.get('timeComplexity') in ['O(n²)', 'O(n^2)'], f"Wrong time: {rotate_img.get('timeComplexity')}"
assert rotate_img.get('spaceComplexity') == 'O(1)', f"Wrong space: {rotate_img.get('spaceComplexity')}"
assert 'transpos' in (rotate_img.get('approach') or '').lower(), f"Missing approach: {rotate_img.get('approach')}"

# Check list_questions representation
all_qs = LCQuestionService.list_questions(db=None).get('questions', [])
idx_q = [q for q in all_qs if q.get('slug') == 'rotate-image'][0]
print('Index Rotate Image Time:', idx_q.get('timeComplexity'))
print('Index Rotate Image Space:', idx_q.get('spaceComplexity'))
assert idx_q.get('timeComplexity') in ['O(n²)', 'O(n^2)']
assert idx_q.get('spaceComplexity') == 'O(1)'

print('ALL ROTATE IMAGE COMPLEXITY CHECKS PASSED 100%!')
