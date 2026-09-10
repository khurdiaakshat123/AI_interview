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
        # Time Window
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

        # Role Topic Profile
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

    # 3. Seed Question Bank
    if db.query(QuestionBank).count() == 0:
        questions_to_seed = [
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
                    {"input": "Standard employee department rows", "expected_output": "Matches top 3 ranked distinct salaries per department", "is_hidden": False}
                ]
            },
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
                "solution": "[\"B\", \"C\"]",
                "starter_code": None,
                "test_cases": []
            }
        ]

        for q_data in questions_to_seed:
            is_valid, report = ReviewAgent.audit_question(q_data)
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
