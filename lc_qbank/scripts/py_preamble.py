"""
Preamble module for executing LeetCode solutions.
Sets up standard typing and data structure definitions, along with built-in LeetCode aliases.
"""
import sys
import math
import heapq
import bisect
import re
import itertools
import functools
import collections
from collections import Counter, defaultdict, deque, OrderedDict
from itertools import accumulate, pairwise, combinations, permutations, product, groupby
from functools import cache, lru_cache, cmp_to_key, reduce
import builtins
from typing import *

# Inject standard LeetCode typing into builtins
for name in [
    'List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union', 'Any',
    'Callable', 'Iterable', 'Sequence', 'DefaultDict', 'Deque'
]:
    if hasattr(builtins, name):
        continue
    val = globals().get(name)
    if val is not None:
        setattr(builtins, name, val)

# Common LeetCode constants and functions
builtins.inf = math.inf
builtins.nan = math.nan
builtins.Counter = Counter
builtins.defaultdict = defaultdict
builtins.deque = deque
builtins.OrderedDict = OrderedDict
builtins.heappop = heapq.heappop
builtins.heappush = heapq.heappush
builtins.heapify = heapq.heapify
builtins.heappushpop = heapq.heappushpop
builtins.heapreplace = heapq.heapreplace
builtins.bisect_left = bisect.bisect_left
builtins.bisect_right = bisect.bisect_right
builtins.insort_left = bisect.insort_left
builtins.insort_right = bisect.insort_right
builtins.accumulate = accumulate
builtins.pairwise = pairwise
builtins.cache = cache
builtins.lru_cache = lru_cache
builtins.gcd = math.gcd
builtins.lcm = math.lcm
builtins.comb = math.comb
builtins.perm = math.perm

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return f"TreeNode({self.val})"

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def __repr__(self):
        return f"ListNode({self.val})"

class Node:
    def __init__(self, val=0, left=None, right=None, next=None, random=None, neighbors=None, children=None):
        self.val = val
        self.left = left
        self.right = right
        self.next = next
        self.random = random
        self.neighbors = neighbors if neighbors is not None else []
        self.children = children if children is not None else []

for cls in [TreeNode, ListNode, Node]:
    setattr(builtins, cls.__name__, cls)
