import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.models.models import (
    User, TimeWindow, RoleTopicProfile, QuestionBank, StructuredResume, generate_uuid, utc_now
)
from backend.app.agents.role_profile_agent import RoleProfileAgent
from backend.app.agents.review_agent import ReviewAgent
from backend.app.engines.scoring_engine import DEFAULT_SECTION_WEIGHTS

def seed_database(db: Session):
    # 1. Seed Demo User
    user = db.query(User).filter(User.email == "candidate@intervyn.ai").first()
    if not user:
        user = User(
            id=generate_uuid(),
            name="Alex Mercer",
            email="candidate@intervyn.ai",
            password_hash="pbkdf2_sha256$mock$hash",
            created_at=utc_now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Seed Time Windows & Role Profiles
    companies = [
        ("Google", "Software Engineer II (L4)", "Full-Time", "2-4 years"),
        ("Amazon", "Software Development Engineer I (SDE 1)", "Full-Time", "0-2 years"),
        ("Microsoft", "Full Stack Software Engineer", "Full-Time", "1-3 years"),
        ("Uber", "Backend & Distributed Systems Engineer", "Full-Time", "2-5 years"),
        ("Stripe", "Payments Infrastructure Engineer", "Full-Time", "2-5 years"),
    ]

    for comp, role_title, jtype, exp in companies:
        tw = db.query(TimeWindow).filter(TimeWindow.company == comp, TimeWindow.role == role_title).first()
        now = datetime.now(timezone.utc)
        if not tw:
            tw = TimeWindow(
                id=generate_uuid(),
                company=comp,
                role=role_title,
                window_length_days=7,
                window_start=now,
                window_end=now + timedelta(days=7),
                status="ACTIVE"
            )
            db.add(tw)
            db.commit()
            db.refresh(tw)

        prof = db.query(RoleTopicProfile).filter(RoleTopicProfile.company == comp, RoleTopicProfile.role == role_title).first()
        if not prof:
            data = RoleProfileAgent.generate_profile(comp, role_title, jtype, exp)
            prof = RoleTopicProfile(
                id=generate_uuid(),
                company=comp,
                role=role_title,
                job_type=jtype,
                experience_requirement=exp,
                required_skills=data["required_skills"],
                time_window_id=tw.id,
                subjects_json=data["subjects"],
                evidence_json=data["evidence"],
                created_at=utc_now(),
                refreshed_at=utc_now()
            )
            db.add(prof)
            db.commit()

    # 3. Seed Question Bank (Expanded Depth across DSA, SQL, System Design, Concurrency)
        questions_to_seed = [
        # --- DSA: 2D Array - DS (Hourglass Sum) (HackerRank Featured) ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Arrays & Matrices",
            "subtopic": "2D Array - DS (Hourglass Sum)",
            "question_type": "DSA",
            "difficulty": "easy",
            "title": "2D Array - DS",
            "prompt": """Given a 6x6 2D Array, `arr`:

    ```
    1 1 1 0 0 0
    0 1 0 0 0 0
    1 1 1 0 0 0
    0 0 0 0 0 0
    0 0 0 0 0 0
    0 0 0 0 0 0
    ```

    An hourglass in `arr` is a subset of values with indices falling in this pattern in `arr`'s graphical representation:
    ```
    a b c
      d
    e f g
    ```

    There are 16 hourglasses in `arr`. An hourglass sum is the sum of an hourglass' values. Calculate the hourglass sum for every hourglass in `arr`, then print the maximum hourglass sum. The array will always be 6x6.

    ### Example:
    `arr =`
    ```
    -9 -9 -9  1 1 1 
     0 -9  0  4 3 2
    -9 -9 -9  1 2 3
     0  0  8  6 6 0
     0  0  0 -2 0 0
     0  0  1  2 4 0
    ```

    The 16 hourglass sums are:
    `-63, -34, -9, 12, -10, 0, 28, 23, -27, -11, -2, 10, 9, 17, 25, 18`

    The highest hourglass sum is `28` from the hourglass beginning at row 1, column 2:
    ```
    0 4 3
      1
    8 6 6
    ```

    ### Function Description:
    Complete the function `hourglassSum` in the editor below.
    `hourglassSum` has the following parameter(s):
    - `int arr[6][6]`: an array of integers

    ### Returns:
    - `int`: the maximum hourglass sum

    ### Input Format:
    Each of the 6 lines of inputs contains 6 space-separated integers `arr[i][j]`.

    ### Constraints:
    - `-9 <= arr[i][j] <= 9`
    - `0 <= i, j <= 5`
    - Time Limit: 1.0 seconds
    - Memory Limit: 256 MB

    ### Sample Input:
    ```
    1 1 1 0 0 0
    0 1 0 0 0 0
    1 1 1 0 0 0
    0 0 2 4 4 0
    0 0 0 2 0 0
    0 0 1 2 4 0
    ```

    ### Sample Output:
    `19`

    ### Explanation:
    The hourglass which has the largest sum is:
    ```
    2 4 4
      2
    1 2 4
    ```""",
            "hint": "Iterate through row indices 0 to 3 and column indices 0 to 3. For each top-left corner (r, c), sum the 7 cells of the hourglass and update the global maximum.",
            "approach": "There are exactly (6 - 2) * (6 - 2) = 16 hourglasses. Initialize max_sum = -infinity. For each (r, c) from 0 to 3, calculate arr[r][c] + arr[r][c+1] + arr[r][c+2] + arr[r+1][c+1] + arr[r+2][c] + arr[r+2][c+1] + arr[r+2][c+2]. Return the maximum sum found.",
            "solution": "def hourglassSum(arr: list) -> int:\n    max_val = -float('inf')\n    for r in range(4):\n        for c in range(4):\n            total = (\n                arr[r][c] + arr[r][c+1] + arr[r][c+2] +\n                arr[r+1][c+1] +\n                arr[r+2][c] + arr[r+2][c+1] + arr[r+2][c+2]\n            )\n            if total > max_val:\n                max_val = total\n    return max_val",
            "starter_code": "def hourglassSum(arr: list) -> int:\n    # Write your code here\n    pass",
            "test_cases": [
                {
                    "input": [[[1, 1, 1, 0, 0, 0], [0, 1, 0, 0, 0, 0], [1, 1, 1, 0, 0, 0], [0, 0, 2, 4, 4, 0], [0, 0, 0, 2, 0, 0], [0, 0, 1, 2, 4, 0]]],
                    "expected_output": "19",
                    "is_hidden": False
                },
                {
                    "input": [[[-9, -9, -9, 1, 1, 1], [0, -9, 0, 4, 3, 2], [-9, -9, -9, 1, 2, 3], [0, 0, 8, 6, 6, 0], [0, 0, 0, -2, 0, 0], [0, 0, 1, 2, 4, 0]]],
                    "expected_output": "28",
                    "is_hidden": False
                },
                {
                    "input": [[[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]],
                    "expected_output": "0",
                    "is_hidden": False
                },
                {
                    "input": [[[-9, -9, -9, -9, -9, -9], [-9, -9, -9, -9, -9, -9], [-9, -9, -9, -9, -9, -9], [-9, -9, -9, -9, -9, -9], [-9, -9, -9, -9, -9, -9], [-9, -9, -9, -9, -9, -9]]],
                    "expected_output": "-63",
                    "is_hidden": True
                },
                {
                    "input": [[[9, 9, 9, 9, 9, 9], [9, 9, 9, 9, 9, 9], [9, 9, 9, 9, 9, 9], [9, 9, 9, 9, 9, 9], [9, 9, 9, 9, 9, 9], [9, 9, 9, 9, 9, 9]]],
                    "expected_output": "63",
                    "is_hidden": True
                },
                {
                    "input": [[[-1, -1, 0, -9, -2, -2], [-2, -1, -6, -8, -2, -5], [-1, -1, -1, -2, -3, -4], [-1, -9, -2, -4, -4, -5], [-7, -3, -3, -2, -9, -9], [-1, -3, -1, -2, -4, -5]]],
                    "expected_output": "-6",
                    "is_hidden": True
                },
                {
                    "input": [[[-1, 1, -1, 0, 0, 0], [0, -1, 0, 0, 0, 0], [-1, -1, -1, 0, 0, 0], [0, -9, 2, -4, -4, 0], [-7, 0, 0, -2, 0, 0], [0, 0, -1, -2, -4, 0]]],
                    "expected_output": "0",
                    "is_hidden": True
                },
                {
                    "input": [[[1, 1, 1, 0, 0, 0], [0, 1, 0, 0, 0, 0], [1, 1, 1, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]],
                    "expected_output": "7",
                    "is_hidden": True
                },
                {
                    "input": [[[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 1, 0], [0, 0, 0, 1, 1, 1]]],
                    "expected_output": "7",
                    "is_hidden": True
                },
                {
                    "input": [[[0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 1, 0], [0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]],
                    "expected_output": "7",
                    "is_hidden": True
                },
                {
                    "input": [[[1, 2, 3, 0, 0, 0], [0, 4, 0, 0, 0, 0], [5, 6, 7, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]],
                    "expected_output": "28",
                    "is_hidden": True
                },
                {
                    "input": [[[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 1, 2, 3, 0], [0, 0, 0, 4, 0, 0], [0, 0, 5, 6, 7, 0], [0, 0, 0, 0, 0, 0]]],
                    "expected_output": "28",
                    "is_hidden": True
                },
                {
                    "input": [[[-1, -2, -3, -4, -5, -6], [-7, -8, -9, -1, -2, -3], [-4, -5, -6, -7, -8, -9], [-1, -2, -3, -4, -5, -6], [-7, -8, -9, -1, -2, -3], [-4, -5, -6, -7, -8, -9]]],
                    "expected_output": "-29",
                    "is_hidden": True
                },
                {
                    "input": [[[5, 5, 5, 0, 0, 0], [0, 5, 0, 0, 0, 0], [5, 5, 5, 0, 0, 0], [0, 0, 0, 8, 8, 8], [0, 0, 0, 0, 8, 0], [0, 0, 0, 8, 8, 8]]],
                    "expected_output": "56",
                    "is_hidden": True
                },
                {
                    "input": [[[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 0, 1], [2, 3, 4, 5, 6, 7], [8, 9, 0, 1, 2, 3], [4, 5, 6, 7, 8, 9], [0, 1, 2, 3, 4, 5]]],
                    "expected_output": "44",
                    "is_hidden": True
                }
            ]
        },

        # --- DSA: Longest Substring Without Repeating Characters ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Sliding Window & Two Pointers",
            "subtopic": "Variable Window",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Longest Substring Without Repeating Characters",
            "prompt": "Given a string `s`, find the length of the **longest substring** without repeating characters.\n\n### Example 1:\n**Input:** `s = \"abcabcbb\"`\n**Output:** `3`\n**Explanation:** The answer is `\"abc\"`, with the length of 3.\n\n### Example 2:\n**Input:** `s = \"bbbbb\"`\n**Output:** `1`\n**Explanation:** The answer is `\"b\"`, with the length of 1.\n\n### Example 3:\n**Input:** `s = \"pwwkew\"`\n**Output:** `3`\n**Explanation:** The answer is `\"wke\"`, with the length of 3. Notice that the answer must be a substring, `\"pwke\"` is a subsequence and not a substring.\n\n### Constraints:\n- `0 <= s.length <= 5 * 10^4`\n- `s` consists of English letters, digits, symbols and spaces.\n- **Time Limit:** 2.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "Use a sliding window maintained by two pointers. Keep track of the last seen index of each character in a hash map.",
            "approach": "Maintain a variable-size sliding window `[left, right]`. As `right` expands, if `s[right]` was seen inside the current window, contract `left = max(left, last_seen[s[right]] + 1)`. Update max length at each step.",
            "solution": "def lengthOfLongestSubstring(s: str) -> int:\n    char_map = {}\n    left = 0\n    max_len = 0\n    for right, ch in enumerate(s):\n        if ch in char_map and char_map[ch] >= left:\n            left = char_map[ch] + 1\n        char_map[ch] = right\n        max_len = max(max_len, right - left + 1)\n    return max_len",
            "starter_code": "def lengthOfLongestSubstring(s: str) -> int:\n    # Write your solution here\n    pass",
            "test_cases": [
                {"input": "abcabcbb", "expected_output": "3", "is_hidden": False},
                {"input": "bbbbb", "expected_output": "1", "is_hidden": False},
                {"input": "pwwkew", "expected_output": "3", "is_hidden": False},
                {"input": "", "expected_output": "0", "is_hidden": True},
                {"input": " ", "expected_output": "1", "is_hidden": True},
                {"input": "au", "expected_output": "2", "is_hidden": True},
                {"input": "dvdf", "expected_output": "3", "is_hidden": True},
                {"input": "abba", "expected_output": "2", "is_hidden": True},
                {"input": "tmmzuxt", "expected_output": "5", "is_hidden": True},
                {"input": "abcdefghijklmnopqrstuvwxyz", "expected_output": "26", "is_hidden": True},
                {"input": "aab", "expected_output": "2", "is_hidden": True},
                {"input": "c", "expected_output": "1", "is_hidden": True},
                {"input": "123456789012345", "expected_output": "10", "is_hidden": True},
                {"input": "abcdeafghij", "expected_output": "10", "is_hidden": True},
                {"input": "a" * 1000 + "b" * 1000, "expected_output": "2", "is_hidden": True}
            ]
        },

        # --- DSA: Course Schedule ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Graphs & Shortest Path",
            "subtopic": "Topological Sort",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Course Schedule (Cycle Detection in Directed Graph)",
            "prompt": "There are a total of `numCourses` courses you have to take, labeled from `0` to `numCourses - 1`. You are given an array `prerequisites` where `prerequisites[i] = [a_i, b_i]` indicates that you **must** take course `b_i` first if you want to take course `a_i`.\n\nFor example, the pair `[0, 1]`, indicates that to take course `0` you have to first take course `1`.\n\nReturn `true` if you can finish all courses. Otherwise, return `false`.\n\n### Example 1:\n**Input:** `numCourses = 2, prerequisites = [[1,0]]`\n**Output:** `true`\n**Explanation:** There are a total of 2 courses to take. To take course 1 you should have finished course 0. So it is possible.\n\n### Example 2:\n**Input:** `numCourses = 2, prerequisites = [[1,0],[0,1]]`\n**Output:** `false`\n**Explanation:** There are a total of 2 courses to take. To take course 1 you should have finished course 0, and to take course 0 you should also have finished course 1. So it is impossible.\n\n### Constraints:\n- `1 <= numCourses <= 2000`\n- `0 <= prerequisites.length <= 5000`\n- `prerequisites[i].length == 2`\n- `0 <= a_i, b_i < numCourses`\n- All the pairs `prerequisites[i]` are unique.\n- **Time Limit:** 2.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "Model the courses as a directed graph. Can you finish all courses if and only if the graph has no directed cycle?",
            "approach": "Use Kahn's Algorithm (BFS with indegrees) or 3-color DFS (UNVISITED, VISITING, VISITED). Compute in-degrees of all vertices. Push all vertices with indegree 0 into a queue. Process and decrement neighbors; if processed nodes == numCourses, no cycle exists.",
            "solution": "from collections import deque, defaultdict\n\ndef canFinish(numCourses: int, prerequisites: list) -> bool:\n    adj = defaultdict(list)\n    indegree = [0] * numCourses\n    for dest, src in prerequisites:\n        adj[src].append(dest)\n        indegree[dest] += 1\n    queue = deque([i for i in range(numCourses) if indegree[i] == 0])\n    visited_count = 0\n    while queue:\n        curr = queue.popleft()\n        visited_count += 1\n        for nxt in adj[curr]:\n            indegree[nxt] -= 1\n            if indegree[nxt] == 0:\n                queue.append(nxt)\n    return visited_count == numCourses",
            "starter_code": "def canFinish(numCourses: int, prerequisites: list) -> bool:\n    # Return true if all courses can be finished\n    pass",
            "test_cases": [
                {"input": [2, [[1, 0]]], "expected_output": "true", "is_hidden": False},
                {"input": [2, [[1, 0], [0, 1]]], "expected_output": "false", "is_hidden": False},
                {"input": [3, [[0, 1], [1, 2]]], "expected_output": "true", "is_hidden": False},
                {"input": [1, []], "expected_output": "true", "is_hidden": True},
                {"input": [3, [[0, 1], [1, 2], [2, 0]]], "expected_output": "false", "is_hidden": True},
                {"input": [4, [[1, 0], [2, 0], [3, 1], [3, 2]]], "expected_output": "true", "is_hidden": True},
                {"input": [4, [[1, 0], [2, 1], [3, 2], [1, 3]]], "expected_output": "false", "is_hidden": True},
                {"input": [5, [[1, 0], [2, 1], [3, 2], [4, 3]]], "expected_output": "true", "is_hidden": True},
                {"input": [5, [[1, 0], [2, 1], [3, 2], [4, 3], [2, 4]]], "expected_output": "false", "is_hidden": True},
                {"input": [3, [[1, 0], [2, 0]]], "expected_output": "true", "is_hidden": True},
                {"input": [2, []], "expected_output": "true", "is_hidden": True},
                {"input": [4, [[0, 1], [2, 3], [1, 2], [3, 0]]], "expected_output": "false", "is_hidden": True},
                {"input": [6, [[1, 0], [2, 0], [3, 1], [4, 2], [5, 3], [5, 4]]], "expected_output": "true", "is_hidden": True},
                {"input": [3, [[0, 2], [1, 2], [2, 0]]], "expected_output": "false", "is_hidden": True},
                {"input": [5, [[1, 0], [0, 2], [2, 1]]], "expected_output": "false", "is_hidden": True}
            ]
        },

        # --- DSA: Search in Rotated Sorted Array ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Binary Search & Arrays",
            "subtopic": "Rotated Array Search",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Search in Rotated Sorted Array",
            "prompt": "There is an integer array `nums` sorted in ascending order (with **distinct** values).\n\nPrior to being passed to your function, `nums` is **possibly rotated** at an unknown pivot index `k` (`1 <= k < nums.length`) such that the resulting array is `[nums[k], nums[k+1], ..., nums[n-1], nums[0], nums[1], ..., nums[k-1]]` (0-indexed).\n\nGiven the array `nums` after the possible rotation and an integer `target`, return the index of `target` if it is in `nums`, or `-1` if it is not in `nums`.\n\nYou must write an algorithm with `O(log n)` runtime complexity.\n\n### Example 1:\n**Input:** `nums = [4,5,6,7,0,1,2], target = 0`\n**Output:** `4`\n**Explanation:** 0 is located at index 4 in the rotated array.\n\n### Example 2:\n**Input:** `nums = [4,5,6,7,0,1,2], target = 3`\n**Output:** `-1`\n**Explanation:** 3 is not in the array, so -1 is returned.\n\n### Example 3:\n**Input:** `nums = [1], target = 0`\n**Output:** `-1`\n**Explanation:** 0 is not in the single-element array.\n\n### Constraints:\n- `1 <= nums.length <= 5000`\n- `-10^4 <= nums[i] <= 10^4`\n- All values of `nums` are **unique**.\n- `nums` is an ascending array that is possibly rotated.\n- `-10^4 <= target <= 10^4`\n- **Time Limit:** 1.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "Notice that at least one half of the array (left or right) is always sorted in any rotated array.",
            "approach": "Standard binary search: compute mid. If nums[mid] == target, return mid. If left half is sorted (nums[low] <= nums[mid]), check if target is within [nums[low], nums[mid]]. If so, search left; else search right. Otherwise, the right half is sorted; check if target is in [nums[mid], nums[high]].",
            "solution": "def search(nums: list, target: int) -> int:\n    low, high = 0, len(nums) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[low] <= nums[mid]:\n            if nums[low] <= target < nums[mid]:\n                high = mid - 1\n            else:\n                low = mid + 1\n        else:\n            if nums[mid] < target <= nums[high]:\n                low = mid + 1\n            else:\n                high = mid - 1\n    return -1",
            "starter_code": "def search(nums: list, target: int) -> int:\n    # Return index or -1\n    pass",
            "test_cases": [
                {"input": [[4, 5, 6, 7, 0, 1, 2], 0], "expected_output": "4", "is_hidden": False},
                {"input": [[4, 5, 6, 7, 0, 1, 2], 3], "expected_output": "-1", "is_hidden": False},
                {"input": [[1], 0], "expected_output": "-1", "is_hidden": False},
                {"input": [[1], 1], "expected_output": "0", "is_hidden": True},
                {"input": [[1, 3], 3], "expected_output": "1", "is_hidden": True},
                {"input": [[1, 3], 1], "expected_output": "0", "is_hidden": True},
                {"input": [[3, 1], 1], "expected_output": "1", "is_hidden": True},
                {"input": [[3, 1], 3], "expected_output": "0", "is_hidden": True},
                {"input": [[5, 1, 3], 5], "expected_output": "0", "is_hidden": True},
                {"input": [[4, 5, 6, 7, 8, 1, 2], 8], "expected_output": "4", "is_hidden": True},
                {"input": [[6, 7, 1, 2, 3, 4, 5], 6], "expected_output": "0", "is_hidden": True},
                {"input": [[6, 7, 1, 2, 3, 4, 5], 3], "expected_output": "4", "is_hidden": True},
                {"input": [[2, 3, 4, 5, 6, 7, 1], 1], "expected_output": "6", "is_hidden": True},
                {"input": [[1, 2, 3, 4, 5, 6], 4], "expected_output": "3", "is_hidden": True},
                {"input": [[1, 2, 3, 4, 5, 6], 10], "expected_output": "-1", "is_hidden": True}
            ]
        },

        # --- DSA: Coin Change ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Dynamic Programming",
            "subtopic": "Unbounded Knapsack / Coin Change",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Coin Change (Minimum Coins Required)",
            "prompt": "You are given an integer array `coins` representing coins of different denominations and an integer `amount` representing a total amount of money.\n\nReturn the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return `-1`.\n\nYou may assume that you have an infinite number of each kind of coin.\n\n### Example 1:\n**Input:** `coins = [1,2,5], amount = 11`\n**Output:** `3`\n**Explanation:** 11 = 5 + 5 + 1 (3 coins total).\n\n### Example 2:\n**Input:** `coins = [2], amount = 3`\n**Output:** `-1`\n**Explanation:** It is impossible to make 3 with only denomination 2.\n\n### Example 3:\n**Input:** `coins = [1], amount = 0`\n**Output:** `0`\n**Explanation:** 0 coins are needed to make an amount of 0.\n\n### Constraints:\n- `1 <= coins.length <= 12`\n- `1 <= coins[i] <= 2^31 - 1`\n- `0 <= amount <= 10^4`\n- **Time Limit:** 1.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "Build up solutions bottom-up from 0 to amount. dp[i] = min(dp[i], dp[i - coin] + 1).",
            "approach": "Initialize a DP array of size amount + 1 with infinity, and dp[0] = 0. Iterate through all amounts from 1 to amount, and for each coin, if coin <= current amount, update dp[a] = min(dp[a], dp[a - coin] + 1). Return dp[amount] if != infinity else -1.",
            "solution": "def coinChange(coins: list, amount: int) -> int:\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for a in range(1, amount + 1):\n        for c in coins:\n            if a - c >= 0:\n                dp[a] = min(dp[a], dp[a - c] + 1)\n    return int(dp[amount]) if dp[amount] != float('inf') else -1",
            "starter_code": "def coinChange(coins: list, amount: int) -> int:\n    # Return minimum coins needed or -1\n    pass",
            "test_cases": [
                {"input": [[1, 2, 5], 11], "expected_output": "3", "is_hidden": False},
                {"input": [[2], 3], "expected_output": "-1", "is_hidden": False},
                {"input": [[1], 0], "expected_output": "0", "is_hidden": False},
                {"input": [[1], 1], "expected_output": "1", "is_hidden": True},
                {"input": [[1], 2], "expected_output": "2", "is_hidden": True},
                {"input": [[2, 5, 10, 1], 27], "expected_output": "4", "is_hidden": True},
                {"input": [[186, 419, 83, 408], 6249], "expected_output": "20", "is_hidden": True},
                {"input": [[1, 3, 5], 8], "expected_output": "2", "is_hidden": True},
                {"input": [[2, 4, 6], 7], "expected_output": "-1", "is_hidden": True},
                {"input": [[1, 5, 10, 25], 30], "expected_output": "2", "is_hidden": True},
                {"input": [[1, 5, 10, 25], 99], "expected_output": "9", "is_hidden": True},
                {"input": [[5, 10], 3], "expected_output": "-1", "is_hidden": True},
                {"input": [[10], 100], "expected_output": "10", "is_hidden": True},
                {"input": [[2, 5], 1], "expected_output": "-1", "is_hidden": True},
                {"input": [[1], 1000], "expected_output": "1000", "is_hidden": True}
            ]
        },

        # --- DSA: Number of Islands ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Graphs & Grid Traversal",
            "subtopic": "Connected Components",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Number of Islands",
            "prompt": "Given an `m x n` 2D binary grid `grid` which represents a map of `'1'`s (land) and `'0'`s (water), return the number of islands.\n\nAn **island** is surrounded by water and is formed by connecting adjacent lands horizontally or vertically. You may assume all four edges of the grid are all surrounded by water.\n\n### Example 1:\n**Input:** `grid = [[\"1\",\"1\",\"1\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"0\",\"0\"]]`\n**Output:** `1`\n**Explanation:** All 1s are connected horizontally or vertically into a single island.\n\n### Example 2:\n**Input:** `grid = [[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"1\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"1\",\"1\"]]`\n**Output:** `3`\n**Explanation:** There are 3 separated islands in the grid.\n\n### Constraints:\n- `m == grid.length`\n- `n == grid[i].length`\n- `1 <= m, n <= 300`\n- `grid[i][j]` is `'0'` or `'1'`.\n- **Time Limit:** 2.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "Traverse every cell in the grid. When encountering '1', trigger a BFS or DFS to sink/mark the connected island and increment counter.",
            "approach": "Iterate through all cells (r, c). When grid[r][c] == '1', increment island_count and run BFS/DFS to flip all horizontally and vertically adjacent '1's to '0' so they are not recounted.",
            "solution": "def numIslands(grid: list) -> int:\n    if not grid: return 0\n    rows, cols = len(grid), len(grid[0])\n    count = 0\n    def dfs(r, c):\n        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != '1':\n            return\n        grid[r][c] = '0'\n        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == '1':\n                count += 1\n                dfs(r, c)\n    return count",
            "starter_code": "def numIslands(grid: list) -> int:\n    # Return number of islands\n    pass",
            "test_cases": [
                {"input": [[["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]], "expected_output": "1", "is_hidden": False},
                {"input": [[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]], "expected_output": "3", "is_hidden": False},
                {"input": [[["1","1","1"],["0","1","0"],["1","1","1"]]], "expected_output": "1", "is_hidden": False},
                {"input": [[["1","0","1"],["0","1","0"],["1","0","1"]]], "expected_output": "5", "is_hidden": True},
                {"input": [[["0","0","0"],["0","0","0"],["0","0","0"]]], "expected_output": "0", "is_hidden": True},
                {"input": [[["1","1","1"],["1","1","1"],["1","1","1"]]], "expected_output": "1", "is_hidden": True},
                {"input": [[["1"]]], "expected_output": "1", "is_hidden": True},
                {"input": [[["0"]]], "expected_output": "0", "is_hidden": True},
                {"input": [[["1","0","1","0","1"]]], "expected_output": "3", "is_hidden": True},
                {"input": [[["1"],["0"],["1"],["0"],["1"]]], "expected_output": "3", "is_hidden": True},
                {"input": [[["1","1","0","0","0"],["0","1","0","0","1"],["1","0","0","1","1"],["0","0","0","0","0"],["1","0","1","1","0"]]], "expected_output": "5", "is_hidden": True},
                {"input": [[["1","1","1","1","1"],["1","0","0","0","1"],["1","0","1","0","1"],["1","0","0","0","1"],["1","1","1","1","1"]]], "expected_output": "2", "is_hidden": True},
                {"input": [[["1","0","0","0"],["0","1","0","0"],["0","0","1","0"],["0","0","0","1"]]], "expected_output": "4", "is_hidden": True},
                {"input": [[["0","1","0"],["1","0","1"],["0","1","0"]]], "expected_output": "4", "is_hidden": True}
            ]
        },

        # --- DSA: Trapping Rain Water ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Two Pointers & Monotonic Stack",
            "subtopic": "Elevation Water Trapping",
            "question_type": "DSA",
            "difficulty": "hard",
            "title": "Trapping Rain Water",
            "prompt": "Given `n` non-negative integers representing an elevation map where the width of each bar is `1`, compute how much water it can trap after raining.\n\n### Example 1:\n**Input:** `height = [0,1,0,2,1,0,1,3,2,1,2,1]`\n**Output:** `6`\n**Explanation:** The above elevation map is represented by array [0,1,0,2,1,0,1,3,2,1,2,1]. In this case, 6 units of rain water are being trapped.\n\n### Example 2:\n**Input:** `height = [4,2,0,3,2,5]`\n**Output:** `9`\n**Explanation:** Elevation map traps 9 total units of rain water.\n\n### Constraints:\n- `n == height.length`\n- `1 <= n <= 2 * 10^4`\n- `0 <= height[i] <= 10^5`\n- **Time Limit:** 2.0 seconds\n- **Memory Limit:** 256 MB",
            "hint": "The water trapped at index i is determined by min(max_left, max_right) - height[i]. Can you solve this in O(1) space with two pointers?",
            "approach": "Use two pointers left=0 and right=len-1 with max_left and max_right trackers. Whichever side is smaller dictates the water level because the other side is guaranteed to have an equal or taller boundary.",
            "solution": "def trap(height: list) -> int:\n    if not height: return 0\n    left, right = 0, len(height) - 1\n    left_max, right_max = height[left], height[right]\n    trapped = 0\n    while left < right:\n        if left_max < right_max:\n            left += 1\n            left_max = max(left_max, height[left])\n            trapped += left_max - height[left]\n        else:\n            right -= 1\n            right_max = max(right_max, height[right])\n            trapped += right_max - height[right]\n    return trapped",
            "starter_code": "def trap(height: list) -> int:\n    # Return units of trapped rain water\n    pass",
            "test_cases": [
                {"input": [[0,1,0,2,1,0,1,3,2,1,2,1]], "expected_output": "6", "is_hidden": False},
                {"input": [[4,2,0,3,2,5]], "expected_output": "9", "is_hidden": False},
                {"input": [[3,0,2,0,4]], "expected_output": "7", "is_hidden": False},
                {"input": [[2,0,2]], "expected_output": "2", "is_hidden": True},
                {"input": [[3,0,0,2,0,4]], "expected_output": "10", "is_hidden": True},
                {"input": [[1,2,3,4,5]], "expected_output": "0", "is_hidden": True},
                {"input": [[5,4,3,2,1]], "expected_output": "0", "is_hidden": True},
                {"input": [[0,0,0,0]], "expected_output": "0", "is_hidden": True},
                {"input": [[]], "expected_output": "0", "is_hidden": True},
                {"input": [[5]], "expected_output": "0", "is_hidden": True},
                {"input": [[5,2,1,2,1,5]], "expected_output": "14", "is_hidden": True},
                {"input": [[0,2,0]], "expected_output": "0", "is_hidden": True},
                {"input": [[4,2,3]], "expected_output": "1", "is_hidden": True},
                {"input": [[5,1,1,1,5]], "expected_output": "12", "is_hidden": True}
            ]
        }
    ]
    # 4. Seed Structured Resume for Quick-Start Candidate
    resume = db.query(StructuredResume).filter(StructuredResume.user_id == user.id).first()
    if not resume:
        resume = StructuredResume(
            id=generate_uuid(),
            user_id=user.id,
            candidate_name="Alex Mercer",
            candidate_email="alex.mercer@intervyn.ai",
            raw_text="Experienced Full Stack / Backend Engineer with expertise in Distributed Systems, Go, Python, FastAPI, and PostgreSQL.",
            sections_json={
                "work_experience": [
                    {
                        "id": "exp-1",
                        "company": "CloudScale Technologies",
                        "role": "Software Engineer II",
                        "duration": "2022 - Present",
                        "summary": "Designed multi-tenant microservices event pipeline handling 100k events/sec using Kafka and Go. Reduced p99 query latency from 220ms to 42ms.",
                        "overall_relevance": 0.95
                    }
                ],
                "projects": [
                    {
                        "project_id": "proj-raft",
                        "title": "Distributed Key-Value Store with Raft Consensus",
                        "description": "Implemented a distributed, fault-tolerant KV store in Go using Raft consensus algorithm with leader election, log replication, and snapshots.",
                        "technologies": ["Go", "Raft", "gRPC", "Protobuf", "Docker"],
                        "overall_relevance": 0.96,
                        "questioning_priority": 1,
                        "relevant_topics": ["Distributed Systems", "Consensus", "Concurrency", "Network I/O"],
                        "irrelevant_topics": ["CSS", "HTML"]
                    },
                    {
                        "project_id": "proj-fintech",
                        "title": "Idempotent Payment Settlement Gateway",
                        "description": "Engineered idempotent payment webhook processor using PostgreSQL optimistic locking, Kafka, and Redis caching.",
                        "technologies": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis"],
                        "overall_relevance": 0.90,
                        "questioning_priority": 2,
                        "relevant_topics": ["Database Transactions", "Idempotency", "Caching", "Event-Driven"],
                        "irrelevant_topics": ["SEO"]
                    }
                ],
                "skills": ["Distributed Systems", "Go", "Python", "FastAPI", "PostgreSQL", "Kafka", "Docker", "Algorithms"],
                "education": [
                    {"degree": "B.S. in Computer Science", "institution": "University of Tech", "grad_year": "2022"}
                ]
            },
            section_weights_json=DEFAULT_SECTION_WEIGHTS,
            created_at=utc_now()
        )
        db.add(resume)
        db.commit()

if __name__ == "__main__":
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
        print("Database seeded successfully!")
    finally:
        db.close()
