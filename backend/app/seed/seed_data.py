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
        # --- DSA: Sliding Window & Two Pointers ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Sliding Window & Two Pointers",
            "subtopic": "Variable Window",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Longest Substring Without Repeating Characters",
            "prompt": "Given a string `s`, find the length of the longest substring without repeating characters.\n\n### Example 1:\n```\nInput: s = \"abcabcbb\"\nOutput: 3\nExplanation: The answer is \"abc\", with the length of 3.\n```\n\n### Example 2:\n```\nInput: s = \"bbbbb\"\nOutput: 1\n```",
            "hint": "Use a sliding window maintained by two pointers. Keep track of the last seen index of each character in a hash map.",
            "approach": "Maintain a variable-size sliding window `[left, right]`. As `right` expands, if `s[right]` was seen inside the current window, contract `left = max(left, last_seen[s[right]] + 1)`. Update max length at each step.",
            "solution": "def lengthOfLongestSubstring(s: str) -> int:\n    char_map = {}\n    left = 0\n    max_len = 0\n    for right, ch in enumerate(s):\n        if ch in char_map and char_map[ch] >= left:\n            left = char_map[ch] + 1\n        char_map[ch] = right\n        max_len = max(max_len, right - left + 1)\n    return max_len",
            "starter_code": "def lengthOfLongestSubstring(s: str) -> int:\n    # Write your solution here\n    pass",
            "test_cases": [
                {"input": "abcabcbb", "expected_output": "3", "is_hidden": False},
                {"input": "bbbbb", "expected_output": "1", "is_hidden": False},
                {"input": "pwwkew", "expected_output": "3", "is_hidden": True},
                {"input": "", "expected_output": "0", "is_hidden": True}
            ]
        },
        # --- DSA: Graphs & Cycles ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Graphs & Shortest Path",
            "subtopic": "Topological Sort",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Course Schedule (Cycle Detection in Directed Graph)",
            "prompt": "There are a total of `numCourses` courses labeled from `0` to `numCourses - 1`. You are given an array `prerequisites` where `prerequisites[i] = [a, b]` indicates you must take course `b` first if you want to take course `a`.\n\nReturn `True` if you can finish all courses. Otherwise, return `False`.",
            "hint": "Model the courses as a directed graph. Can you finish all courses if and only if the graph has no directed cycle?",
            "approach": "Use Kahn's Algorithm (BFS with indegrees) or 3-color DFS (UNVISITED, VISITING, VISITED). Compute in-degrees of all vertices. Push all vertices with indegree 0 into a queue. Process and decrement neighbors; if processed nodes == numCourses, no cycle exists.",
            "solution": "from collections import deque, defaultdict\n\ndef canFinish(numCourses: int, prerequisites: list) -> bool:\n    adj = defaultdict(list)\n    indegree = [0] * numCourses\n    for dest, src in prerequisites:\n        adj[src].append(dest)\n        indegree[dest] += 1\n    queue = deque([i for i in range(numCourses) if indegree[i] == 0])\n    visited_count = 0\n    while queue:\n        curr = queue.popleft()\n        visited_count += 1\n        for nxt in adj[curr]:\n            indegree[nxt] -= 1\n            if indegree[nxt] == 0:\n                queue.append(nxt)\n    return visited_count == numCourses",
            "starter_code": "def canFinish(numCourses: int, prerequisites: list) -> bool:\n    # Return True if all courses can be finished\n    pass",
            "test_cases": [
                {"input": [2, [[1, 0]]], "expected_output": "True", "is_hidden": False},
                {"input": [2, [[1, 0], [0, 1]]], "expected_output": "False", "is_hidden": False},
                {"input": [3, [[0, 1], [1, 2]]], "expected_output": "True", "is_hidden": True}
            ]
        },
        # --- DSA: Binary Search ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Binary Search & Arrays",
            "subtopic": "Rotated Array Search",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Search in Rotated Sorted Array",
            "prompt": "Given integer array `nums` sorted in ascending order (with distinct values), which is possibly rotated at an unknown pivot index, and a target integer `target`, return the index of `target` if it is in `nums`, or `-1` if not. The runtime complexity must be O(log n).",
            "hint": "Notice that at least one half of the array (left or right) is always sorted in any rotated array.",
            "approach": "Standard binary search: compute mid. If nums[mid] == target, return mid. If left half is sorted (nums[low] <= nums[mid]), check if target is within [nums[low], nums[mid]]. If so, search left; else search right. Otherwise, the right half is sorted; check if target is in [nums[mid], nums[high]].",
            "solution": "def search(nums: list, target: int) -> int:\n    low, high = 0, len(nums) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[low] <= nums[mid]:\n            if nums[low] <= target < nums[mid]:\n                high = mid - 1\n            else:\n                low = mid + 1\n        else:\n            if nums[mid] < target <= nums[high]:\n                low = mid + 1\n            else:\n                high = mid - 1\n    return -1",
            "starter_code": "def search(nums: list, target: int) -> int:\n    # Return index or -1\n    pass",
            "test_cases": [
                {"input": [[4, 5, 6, 7, 0, 1, 2], 0], "expected_output": "4", "is_hidden": False},
                {"input": [[4, 5, 6, 7, 0, 1, 2], 3], "expected_output": "-1", "is_hidden": False},
                {"input": [[1], 0], "expected_output": "-1", "is_hidden": True},
                {"input": [[1, 3], 3], "expected_output": "1", "is_hidden": True}
            ]
        },
        # --- DSA: Dynamic Programming ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Dynamic Programming",
            "subtopic": "Unbounded Knapsack / Coin Change",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Coin Change (Minimum Coins Required)",
            "prompt": "You are given an integer array `coins` representing coins of different denominations and an integer `amount` representing a total amount of money. Return the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return `-1`.",
            "hint": "Build up solutions bottom-up from 0 to amount. dp[i] = min(dp[i], dp[i - coin] + 1).",
            "approach": "Initialize a DP array of size amount + 1 with infinity, and dp[0] = 0. Iterate through all amounts from 1 to amount, and for each coin, if coin <= current amount, update dp[a] = min(dp[a], dp[a - coin] + 1). Return dp[amount] if != infinity else -1.",
            "solution": "def coinChange(coins: list, amount: int) -> int:\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for a in range(1, amount + 1):\n        for c in coins:\n            if a - c >= 0:\n                dp[a] = min(dp[a], dp[a - c] + 1)\n    return int(dp[amount]) if dp[amount] != float('inf') else -1",
            "starter_code": "def coinChange(coins: list, amount: int) -> int:\n    # Return minimum coins needed or -1\n    pass",
            "test_cases": [
                {"input": [[1, 2, 5], 11], "expected_output": "3", "is_hidden": False},
                {"input": [[2], 3], "expected_output": "-1", "is_hidden": False},
                {"input": [[1], 0], "expected_output": "0", "is_hidden": True}
            ]
        },
        # --- DSA: Matrix BFS / DFS ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Graphs & Grid Traversal",
            "subtopic": "Connected Components",
            "question_type": "DSA",
            "difficulty": "medium",
            "title": "Number of Islands",
            "prompt": "Given an `m x n` 2D binary grid `grid` which represents a map of `'1'`s (land) and `'0'`s (water), return the number of islands. An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically.",
            "hint": "Traverse every cell in the grid. When encountering '1', trigger a BFS or DFS to sink/mark the connected island and increment counter.",
            "approach": "Iterate through all cells (r, c). When grid[r][c] == '1', increment island_count and run BFS/DFS to flip all horizontally and vertically adjacent '1's to '0' so they are not recounted.",
            "solution": "def numIslands(grid: list) -> int:\n    if not grid: return 0\n    rows, cols = len(grid), len(grid[0])\n    count = 0\n    def dfs(r, c):\n        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != '1':\n            return\n        grid[r][c] = '0'\n        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == '1':\n                count += 1\n                dfs(r, c)\n    return count",
            "starter_code": "def numIslands(grid: list) -> int:\n    # Return number of islands\n    pass",
            "test_cases": [
                {"input": [[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]], "expected_output": "3", "is_hidden": False},
                {"input": [[["1","1","1"],["0","1","0"],["1","1","1"]]], "expected_output": "1", "is_hidden": False}
            ]
        },
        # --- DSA: Two Pointers / Trapping Rain Water ---
        {
            "subject": "Data Structures & Algorithms",
            "topic": "Two Pointers & Monotonic Stack",
            "subtopic": "Elevation Water Trapping",
            "question_type": "DSA",
            "difficulty": "hard",
            "title": "Trapping Rain Water",
            "prompt": "Given `n` non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.\n\nExample: `height = [0,1,0,2,1,0,1,3,2,1,2,1]` returns `6`.",
            "hint": "The water trapped at index i is determined by min(max_left, max_right) - height[i]. Can you solve this in O(1) space with two pointers?",
            "approach": "Use two pointers left=0 and right=len-1 with max_left and max_right trackers. Whichever side is smaller dictates the water level because the other side is guaranteed to have an equal or taller boundary.",
            "solution": "def trap(height: list) -> int:\n    if not height: return 0\n    left, right = 0, len(height) - 1\n    left_max, right_max = height[left], height[right]\n    trapped = 0\n    while left < right:\n        if left_max < right_max:\n            left += 1\n            left_max = max(left_max, height[left])\n            trapped += left_max - height[left]\n        else:\n            right -= 1\n            right_max = max(right_max, height[right])\n            trapped += right_max - height[right]\n    return trapped",
            "starter_code": "def trap(height: list) -> int:\n    # Return units of trapped rain water\n    pass",
            "test_cases": [
                {"input": [[0,1,0,2,1,0,1,3,2,1,2,1]], "expected_output": "6", "is_hidden": False},
                {"input": [[4,2,0,3,2,5]], "expected_output": "9", "is_hidden": False}
            ]
        },
        # --- SQL: Department Top Salaries ---
        {
            "subject": "Core Fundamentals (OS, CN, DBMS, SQL)",
            "topic": "SQL & Query Optimization",
            "subtopic": "Window Functions",
            "question_type": "SQL",
            "difficulty": "medium",
            "title": "Department Top Three Highest Salaries",
            "prompt": "Write an SQL query to find employees who earn the top three highest unique salaries in each department from the `Employee` and `Department` tables.\n\nSchema:\n`Employee(id INT, name VARCHAR, salary INT, departmentId INT)`\n`Department(id INT, name VARCHAR)`",
            "hint": "Consider using the DENSE_RANK() window function partitioned by departmentId ordered by salary descending.",
            "approach": "Use a Common Table Expression (CTE) with `DENSE_RANK() OVER (PARTITION BY departmentId ORDER BY salary DESC) AS rnk`. Filter where `rnk <= 3` and join with `Department`.",
            "solution": "WITH RankedSalaries AS (\n    SELECT \n        d.name AS Department,\n        e.name AS Employee,\n        e.salary AS Salary,\n        DENSE_RANK() OVER (PARTITION BY e.departmentId ORDER BY e.salary DESC) as rnk\n    FROM Employee e\n    JOIN Department d ON e.departmentId = d.id\n)\nSELECT Department, Employee, Salary\nFROM RankedSalaries\nWHERE rnk <= 3;",
            "starter_code": "SELECT Department, Employee, Salary FROM ...",
            "test_cases": [
                {"input": "Standard employee department rows", "expected_output": "Matches top 3 ranked distinct salaries per department", "is_hidden": False},
                {"input": "Empty or single employee per department", "expected_output": "Handles single employee departments properly", "is_hidden": True}
            ]
        },
        # --- SQL: Consecutive Logins ---
        {
            "subject": "Core Fundamentals (OS, CN, DBMS, SQL)",
            "topic": "SQL & Query Optimization",
            "subtopic": "Sequential Date Analysis",
            "question_type": "SQL",
            "difficulty": "medium",
            "title": "Active Users with Consecutive Logins",
            "prompt": "Write an SQL query to find the `id` and `name` of active users who visited the platform for three or more consecutive days.\n\nSchema:\n`Users(id INT, name VARCHAR)`\n`Logins(id INT, login_date DATE)`",
            "hint": "You can use LEAD() window function or self-joins with DATE_ADD() to test if login dates form consecutive sequences.",
            "approach": "Deduplicate user logins per day with DISTINCT. Use LEAD(login_date, 2) OVER (PARTITION BY id ORDER BY login_date) and check if DATEDIFF(lead_2, login_date) == 2.",
            "solution": "WITH DistinctLogins AS (\n    SELECT DISTINCT id, login_date\n    FROM Logins\n),\nSequenced AS (\n    SELECT id, login_date,\n           LEAD(login_date, 2) OVER (PARTITION BY id ORDER BY login_date) AS lead_date\n    FROM DistinctLogins\n)\nSELECT DISTINCT u.id, u.name\nFROM Sequenced s\nJOIN Users u ON s.id = u.id\nWHERE DATEDIFF(s.lead_date, s.login_date) = 2;",
            "starter_code": "SELECT DISTINCT u.id, u.name FROM ...",
            "test_cases": [
                {"input": "Logins with 3-day consecutive activity", "expected_output": "Returns users meeting the 3-day sequence", "is_hidden": False},
                {"input": "User with multiple non-consecutive logins", "expected_output": "Filters out non-consecutive visitors", "is_hidden": True}
            ]
        },
        # --- SQL: Aggregations & Products ---
        {
            "subject": "Core Fundamentals (OS, CN, DBMS, SQL)",
            "topic": "SQL & Query Optimization",
            "subtopic": "Relational Division & Grouping",
            "question_type": "SQL",
            "difficulty": "medium",
            "title": "Customers Who Bought All Products in Catalog",
            "prompt": "Write an SQL query to report the `customer_id` from the `Customer` table who bought all the products listed in the `Product` table.\n\nSchema:\n`Customer(customer_id INT, product_key INT)`\n`Product(product_key INT)`",
            "hint": "Compare the count of distinct products bought by each customer to the total distinct products in the Product catalog.",
            "approach": "GROUP BY customer_id and filter in the HAVING clause where COUNT(DISTINCT product_key) equals (SELECT COUNT(*) FROM Product).",
            "solution": "SELECT customer_id\nFROM Customer\nGROUP BY customer_id\nHAVING COUNT(DISTINCT product_key) = (SELECT COUNT(*) FROM Product);",
            "starter_code": "SELECT customer_id FROM Customer ...",
            "test_cases": [
                {"input": "Customers with partial vs full product ownership", "expected_output": "Only customers with full product coverage", "is_hidden": False},
                {"input": "No customers matching full catalog", "expected_output": "Returns empty result set gracefully", "is_hidden": True}
            ]
        },
        # --- System Design: Cache Stampede ---
        {
            "subject": "System Design & Distributed Systems",
            "topic": "Distributed Storage & Caching",
            "subtopic": "Cache Eviction & Stampede",
            "question_type": "MCQ",
            "difficulty": "medium",
            "title": "Mitigating Cache Stampede (Thundering Herd)",
            "prompt": "A high-traffic e-commerce flash sale endpoint relies on Redis caching. When the cache key for the main catalog expires under 100,000 requests/second, thousands of concurrent requests miss the cache simultaneously and overwhelm PostgreSQL. Which technique effectively prevents this cache stampede?",
            "options_json": [
                "A. Switch from Redis to Memcached with larger memory",
                "B. Mutex / Distributed Locking with probabilistic early expiration (XFetch algorithm)",
                "C. Disable TTL and let cache keys persist forever without invalidation",
                "D. Increase PostgreSQL maximum connections pool to 100,000"
            ],
            "hint": "Think about how to allow only a single worker to recompute the cache while other requests either wait or serve slightly stale data.",
            "approach": "Probabilistic early expiration (XFetch) or distributed mutex locking allows exactly one background thread to regenerate the cache before or upon expiration.",
            "solution": "B. Mutex / Distributed Locking with probabilistic early expiration (XFetch algorithm)",
            "starter_code": None,
            "test_cases": []
        },
        # --- System Design: Kafka Partitioning & Ordering ---
        {
            "subject": "System Design & Distributed Systems",
            "topic": "High-Throughput Messaging & Queues",
            "subtopic": "Kafka Partitioning & Ordering",
            "question_type": "MSQ",
            "difficulty": "hard",
            "title": "Guaranteed Message Ordering in Distributed Event Brokers",
            "prompt": "Select ALL statements that are TRUE regarding message ordering and partitioning guarantees in Apache Kafka:",
            "options_json": [
                "A. Kafka guarantees total ordering across all partitions within a topic.",
                "B. Kafka guarantees strict FIFO ordering only within a single partition.",
                "C. Messages with identical non-null keys are always hashed and routed to the same partition (assuming partition count is static).",
                "D. Adding new partitions to an existing topic preserves key-to-partition routing for all subsequent writes."
            ],
            "hint": "Remember that Kafka is partitioned by design; total ordering across independent partitions is not guaranteed.",
            "approach": "Kafka guarantees FIFO ordering per-partition. Messages with the same key go to the same partition via murmur2 hash, unless partition count changes.",
            "solution": "B, C",
            "starter_code": None,
            "test_cases": []
        },
        # --- System Design: Consistent Hashing ---
        {
            "subject": "System Design & Distributed Systems",
            "topic": "Distributed Storage & Caching",
            "subtopic": "Consistent Hashing & Dynamic Sharding",
            "question_type": "MCQ",
            "difficulty": "medium",
            "title": "Data Rebalancing in Consistent Hashing Rings",
            "prompt": "In a distributed key-value store using Consistent Hashing with virtual nodes (tokens), when an additional physical storage node is added to a cluster of N nodes with K total keys, how many keys on average must be migrated?",
            "options_json": [
                "A. K / (N + 1) keys on average",
                "B. All K keys must be rehashed across the cluster",
                "C. Exactly K / 2 keys",
                "D. Zero keys, because consistent hashing prevents any data movement"
            ],
            "hint": "The primary benefit of consistent hashing over standard hash mod N is that only keys belonging to the immediate neighbor intervals of the new tokens are moved.",
            "approach": "In consistent hashing, adding a node only affects the keys in the intervals acquired by the new node's virtual tokens, resulting in approximately K / (N + 1) keys migrated.",
            "solution": "A. K / (N + 1) keys on average",
            "starter_code": None,
            "test_cases": []
        },
        # --- System Design: Saga vs 2PC ---
        {
            "subject": "System Design & Distributed Systems",
            "topic": "Distributed Transactions & Consistency",
            "subtopic": "Saga Pattern vs 2PC",
            "question_type": "MCQ",
            "difficulty": "hard",
            "title": "Saga Pattern in Distributed Microservice Workflows",
            "prompt": "Why do high-scale distributed microservice architectures prefer the Saga pattern over Two-Phase Commit (2PC) for cross-service transactions?",
            "options_json": [
                "A. 2PC holds locks across independent network services until commit, causing severe latency and coordinator bottlenecks, whereas Sagas use local transactions and compensating actions",
                "B. Sagas provide immediate ACID isolation without eventual consistency",
                "C. 2PC cannot be implemented with relational databases",
                "D. Sagas eliminate the need for error handling or rollback mechanisms"
            ],
            "hint": "Think about lock duration and coordinator availability in distributed network environments.",
            "approach": "2PC requires holding locks across distributed services during voting and commit phases, creating single-point-of-failure risks and high latency. Sagas break the transaction into local steps with compensating rollbacks.",
            "solution": "A. 2PC holds locks across independent network services until commit, causing severe latency and coordinator bottlenecks, whereas Sagas use local transactions and compensating actions",
            "starter_code": None,
            "test_cases": []
        },
        # --- Operating Systems: Deadlocks ---
        {
            "subject": "Core Fundamentals (OS, CN, DBMS, SQL)",
            "topic": "Operating Systems & Concurrency",
            "subtopic": "Deadlock Necessary Conditions",
            "question_type": "MCQ",
            "difficulty": "medium",
            "title": "Coffman Conditions for Deadlock",
            "prompt": "Which of the following is NOT one of the four Coffman conditions necessary for a deadlock to occur in an operating system?",
            "options_json": [
                "A. Mutual Exclusion",
                "B. Hold and Wait",
                "C. Preemption Permitted",
                "D. Circular Wait"
            ],
            "hint": "Remember that for a deadlock to persist, resources cannot be forcibly confiscated from a process.",
            "approach": "The four Coffman conditions are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. 'Preemption Permitted' breaks deadlocks rather than enabling them.",
            "solution": "C. Preemption Permitted",
            "starter_code": None,
            "test_cases": []
        },
        # --- Operating Systems: Concurrency Control ---
        {
            "subject": "Core Fundamentals (OS, CN, DBMS, SQL)",
            "topic": "Operating Systems & Concurrency",
            "subtopic": "Optimistic vs Pessimistic Concurrency",
            "question_type": "MSQ",
            "difficulty": "hard",
            "title": "Optimistic Concurrency Control (OCC) Characteristics",
            "prompt": "Select ALL statements that are TRUE regarding Optimistic Concurrency Control (OCC):",
            "options_json": [
                "A. OCC operates without row/table locks during the read phase, making it highly effective in read-heavy environments with low collision probability.",
                "B. OCC transactions validate changes against version numbers or timestamps at commit time, aborting and retrying if conflicts are detected.",
                "C. OCC guarantees zero transaction aborts even when thousands of workers simultaneously write to the same single row.",
                "D. In high-conflict write scenarios, OCC throughput can degrade below pessimistic locking due to continuous rollback and retry thrashing."
            ],
            "hint": "Consider what happens when multiple concurrent threads attempt to modify the same resource simultaneously under OCC vs lock-based systems.",
            "approach": "OCC avoids lock overhead during reads, verifies versions at validation/commit, and aborts on conflict. Under extreme write contention, repeated rollbacks cause severe thrashing.",
            "solution": "A, B, D",
            "starter_code": None,
            "test_cases": []
        }
    ]

    for q_data in questions_to_seed:
        existing = db.query(QuestionBank).filter(QuestionBank.title == q_data["title"]).first()
        is_valid, report = ReviewAgent.audit_question(q_data)
        if not existing:
            q = QuestionBank(
                id=generate_uuid(),
                subject=q_data["subject"],
                topic=q_data["topic"],
                subtopic=q_data["subtopic"],
                question_type=q_data["question_type"],
                difficulty=q_data["difficulty"],
                title=q_data.get("title"),
                prompt=q_data["prompt"],
                hint=q_data.get("hint"),
                approach=q_data.get("approach"),
                solution=q_data.get("solution"),
                options_json=q_data.get("options_json"),
                test_cases_json=q_data.get("test_cases", []),
                starter_code=q_data.get("starter_code"),
                status="PUBLISHED" if is_valid else "REVIEWING",
                review_report_json=report,
                question_generator_version=1,
                created_at=utc_now()
            )
            db.add(q)
            db.commit()
        else:
            # Upgrade existing question to PUBLISHED if test cases now pass
            if existing.status != "PUBLISHED" and is_valid:
                existing.status = "PUBLISHED"
                existing.test_cases_json = q_data.get("test_cases", [])
                existing.review_report_json = report
                db.commit()

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
