import re
from typing import Tuple, List

class TranscriptNormalizer:
    """
    Technical Speech-to-Text and Typo Autocorrection Engine.
    Pre-processes candidate responses to map common browser speech recognition
    phonetic sound-alikes, garbled transcriptions, and typing slips into precise
    engineering terminology before evaluation.
    """

    # Exact phrase replacements (case-insensitive regex patterns)
    PHONETIC_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
        # PostgreSQL variations
        (re.compile(r'\bpost\s*grass\s*sql\b', re.IGNORECASE), 'PostgreSQL'),
        (re.compile(r'\bpost\s*grass\b', re.IGNORECASE), 'Postgres'),
        (re.compile(r'\bpostgress\s*sql\b', re.IGNORECASE), 'PostgreSQL'),
        (re.compile(r'\bpostgress\b', re.IGNORECASE), 'Postgres'),
        (re.compile(r'\bpost\s*grey\s*sql\b', re.IGNORECASE), 'PostgreSQL'),
        
        # Supabase variations
        (re.compile(r'\bsuperb\s+is\s+a\s+database\b', re.IGNORECASE), 'Supabase as a database'),
        (re.compile(r'\bsuperb\s+is\b', re.IGNORECASE), 'Supabase'),
        (re.compile(r'\bsupervis\b', re.IGNORECASE), 'Supabase'),
        (re.compile(r'\bsupa\s*base\b', re.IGNORECASE), 'Supabase'),

        # Web scraping & files
        (re.compile(r'\bwebs?\s*grapes?\b', re.IGNORECASE), 'web scrapes'),
        (re.compile(r'\bweb\s*grape\b', re.IGNORECASE), 'web scrape'),
        (re.compile(r'\bweb\s*scrapping\b', re.IGNORECASE), 'web scraping'),
        (re.compile(r'\bcse\s*files?\b', re.IGNORECASE), 'CSV files'),
        (re.compile(r'\bcse\s*file\b', re.IGNORECASE), 'CSV file'),
        (re.compile(r'\bpills?\s+the\s+missing\b', re.IGNORECASE), 'fills the missing'),

        # DuckDuckGo variations
        (re.compile(r'\bduck\s*duck\s*go\s*light\b', re.IGNORECASE), 'DuckDuckGo Lite'),
        (re.compile(r'\bduck\s*duck\s*go\s*lite\b', re.IGNORECASE), 'DuckDuckGo Lite'),
        (re.compile(r'\bd\s*go\s*light\b', re.IGNORECASE), 'DDG Lite'),
        (re.compile(r'\bd\s*go\s*lite\b', re.IGNORECASE), 'DDG Lite'),
        (re.compile(r'\bcold\s+website\b', re.IGNORECASE), 'called website'),

        # Code quality & structures
        (re.compile(r'\bwells?\s*drug\b', re.IGNORECASE), 'well structured'),
        (re.compile(r'\bwell\s*struck\s*tured\b', re.IGNORECASE), 'well structured'),
        (re.compile(r'\bhurastics?\s*scores?\b', re.IGNORECASE), 'heuristic score'),
        (re.compile(r'\bhurastics?\b', re.IGNORECASE), 'heuristic'),
        (re.compile(r'\bheurstic\b', re.IGNORECASE), 'heuristic'),

        # Vector DBs & Search
        (re.compile(r'\bpine?\s*co(?:rn|ne)\b', re.IGNORECASE), 'Pinecone'),
        (re.compile(r'\bchro?ma\s*db\b', re.IGNORECASE), 'ChromaDB'),
        (re.compile(r'\bfaiss\b', re.IGNORECASE), 'FAISS'),
        (re.compile(r'\breasearch\b', re.IGNORECASE), 'research'),

        # Distributed Systems, Caching & Cloud
        (re.compile(r'\b(?:read|red)\s+is\b', re.IGNORECASE), 'Redis'),
        (re.compile(r'\breadis\b', re.IGNORECASE), 'Redis'),
        (re.compile(r'\braddis\b', re.IGNORECASE), 'Redis'),
        (re.compile(r'\bmongo\s*d\s*b\b', re.IGNORECASE), 'MongoDB'),
        (re.compile(r'\bmungodb\b', re.IGNORECASE), 'MongoDB'),
        (re.compile(r'\bkafka\s*q\b', re.IGNORECASE), 'Kafka queue'),
        (re.compile(r'\bcooberneties\b', re.IGNORECASE), 'Kubernetes'),
        (re.compile(r'\bkube\s*netics\b', re.IGNORECASE), 'Kubernetes'),
        (re.compile(r'\bdoc\s*ker\b', re.IGNORECASE), 'Docker'),
        (re.compile(r'\bg\s*r\s*p\s*c\b', re.IGNORECASE), 'gRPC'),
        (re.compile(r'\bgraph\s*q\s*l\b', re.IGNORECASE), 'GraphQL'),
        (re.compile(r'\bc\s*r\s*d\s*t\b', re.IGNORECASE), 'CRDT'),
        (re.compile(r'\bcr\s*dts\b', re.IGNORECASE), 'CRDTs'),
        (re.compile(r'\brough\s*consensus\b', re.IGNORECASE), 'Raft consensus'),
        (re.compile(r'\braft\s*concentus\b', re.IGNORECASE), 'Raft consensus'),
        (re.compile(r'\bpack\s*sauce\b', re.IGNORECASE), 'Paxos'),
        (re.compile(r'\bpack\s*sos\b', re.IGNORECASE), 'Paxos'),
        (re.compile(r'\belisen\s*tree\b', re.IGNORECASE), 'LSM-tree'),
        (re.compile(r'\bl\s*s\s*m\s*tree\b', re.IGNORECASE), 'LSM-tree'),
        (re.compile(r'\bwal\s*log\b', re.IGNORECASE), 'WAL log'),
        (re.compile(r'\bwrite\s*a\s*head\s*log\b', re.IGNORECASE), 'Write-Ahead Log'),
        (re.compile(r'\bfast\s*a\s*p\s*i\b', re.IGNORECASE), 'FastAPI'),
        (re.compile(r'\bflask\s*a\s*p\s*i\b', re.IGNORECASE), 'Flask API'),
        (re.compile(r'\btype\s*script\b', re.IGNORECASE), 'TypeScript'),
        (re.compile(r'\bjava\s*script\b', re.IGNORECASE), 'JavaScript'),
        (re.compile(r'\bn\s*c\s*c\s*l\b', re.IGNORECASE), 'NCCL'),
        (re.compile(r'\bnv\s*me\b', re.IGNORECASE), 'NVMe'),
        (re.compile(r'\broce\s*v\s*2\b', re.IGNORECASE), 'RoCEv2'),
        (re.compile(r'\binfini\s*band\b', re.IGNORECASE), 'InfiniBand'),
        (re.compile(r'\bproto\s*buf\b', re.IGNORECASE), 'Protobuf'),
        (re.compile(r'\bprotocol\s*buffers?\b', re.IGNORECASE), 'Protocol Buffers'),

        # Edge Proxies, Gateways & Security sound-alikes
        (re.compile(r'\bcloud\s*player\b', re.IGNORECASE), 'Cloudflare'),
        (re.compile(r'\bcloud\s*flare\b', re.IGNORECASE), 'Cloudflare'),
        (re.compile(r'\bin\s+the\s+next\b', re.IGNORECASE), 'Nginx'),
        (re.compile(r'\bengine\s*x\b', re.IGNORECASE), 'Nginx'),
        (re.compile(r'\bin\s*gin\s*x\b', re.IGNORECASE), 'Nginx'),
        (re.compile(r'\b(?:bohat|bo\s*hat|birds)\s+(?:sitting|hitting)\b', re.IGNORECASE), 'bots hitting'),
        (re.compile(r'\ball\s+the\s+birds\b', re.IGNORECASE), 'all the bots'),
        (re.compile(r'\bconsisting\s+or\b', re.IGNORECASE), 'consisting of'),

        # Metrics, SLAs & Latency sound-alikes
        (re.compile(r'\bp\s*99\b|\bp\s*ninety\s*nine\b', re.IGNORECASE), 'p99'),
        (re.compile(r'\bp\s*95\b|\bp\s*ninety\s*five\b', re.IGNORECASE), 'p95'),
        (re.compile(r'\b(\d+)\s*(?:mill?i\s*sec(?:onds?)?|ms)\b', re.IGNORECASE), r'\1ms'),
        (re.compile(r'\bmill?i\s*sec(?:onds?)?\b|\bm\s*s\b', re.IGNORECASE), 'ms'),

        # Resiliency, Messaging & Microservices
        (re.compile(r'\bload\s*balancer?\b|\bload\s*balancing\b', re.IGNORECASE), 'load balancer'),
        (re.compile(r'\brate\s*limit(?:ing|er)?\b', re.IGNORECASE), 'rate limiting'),
        (re.compile(r'\btoken\s*bucket\b', re.IGNORECASE), 'token bucket'),
        (re.compile(r'\bleaky\s*bucket\b', re.IGNORECASE), 'leaky bucket'),
        (re.compile(r'\bcircuit\s*breaker\b', re.IGNORECASE), 'circuit breaker'),
        (re.compile(r'\bdead\s*letter\s*q(?:ueue)?\b|\bd\s*l\s*q\b', re.IGNORECASE), 'dead letter queue'),
        (re.compile(r'\bthundering\s*herd\b|\bcache\s*stampede\b', re.IGNORECASE), 'cache stampede'),
        (re.compile(r'\bkafka\s*partition(?:ing|s)?\b', re.IGNORECASE), 'Kafka partitioning'),
        (re.compile(r'\bconsistent\s*hashing\b', re.IGNORECASE), 'consistent hashing'),
        (re.compile(r'\bvirtual\s*nodes?\b', re.IGNORECASE), 'virtual nodes'),
        (re.compile(r'\btwo\s*phase\s*commit\b|\b2\s*p\s*c\b', re.IGNORECASE), 'Two-Phase Commit (2PC)'),
        (re.compile(r'\bsaga\s*pattern\b', re.IGNORECASE), 'Saga pattern'),
        (re.compile(r'\boptimistic\s*locking\b', re.IGNORECASE), 'optimistic locking'),
        (re.compile(r'\bpessimistic\s*locking\b', re.IGNORECASE), 'pessimistic locking'),

        # SQL & Database terminology
        (re.compile(r'\bdense\s*rank\b', re.IGNORECASE), 'DENSE_RANK'),
        (re.compile(r'\brow\s*number\b', re.IGNORECASE), 'ROW_NUMBER'),
        (re.compile(r'\bwindow\s*functions?\b', re.IGNORECASE), 'window function'),
        (re.compile(r'\bcommon\s*table\s*expression\b|\bc\s*t\s*e\b', re.IGNORECASE), 'CTE'),

        # DSA Algorithms & Data Structures
        (re.compile(r'\btopological\s*sort\b', re.IGNORECASE), 'topological sort'),
        (re.compile(r'\bkahn(?:\'?s)?\s*algorithm\b', re.IGNORECASE), "Kahn's algorithm"),
        (re.compile(r'\bcycle\s*detection\b', re.IGNORECASE), 'cycle detection'),
        (re.compile(r'\bmonoton(?:ic)?\s*stack\b', re.IGNORECASE), 'monotonic stack'),
        (re.compile(r'\bsliding\s*window\b', re.IGNORECASE), 'sliding window'),
        (re.compile(r'\btwo\s*pointers?\b', re.IGNORECASE), 'two pointers'),
        (re.compile(r'\bbinary\s*search\b', re.IGNORECASE), 'binary search'),
        (re.compile(r'\bdynamic\s*programming\b|\bd\s*p\b', re.IGNORECASE), 'dynamic programming'),
    ]

    @classmethod
    def normalize(cls, raw_text: str) -> Tuple[str, bool]:
        """
        Cleans technical speech-to-text sound-alikes and common typos.
        Returns: (normalized_text, was_modified)
        """
        if not raw_text or not raw_text.strip():
            return raw_text, False

        cleaned = raw_text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
        for pattern, replacement in cls.PHONETIC_REPLACEMENTS:
            cleaned = pattern.sub(replacement, cleaned)

        # Normalize multiple spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
        was_modified = (cleaned != raw_text.strip())
        return cleaned, was_modified
