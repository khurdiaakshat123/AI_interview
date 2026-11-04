"""
Centralized Broad Topic Mapping for MCQ Question Bank.
Single Source of Truth mapping 39 original subparts to 9 stable broad-topic IDs.
"""

import os
import json
from typing import Dict, List, Any, Optional

MAP_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../mcq_qbank/broad_topics_map.json")
)

def load_broad_topics_map() -> Dict[str, Any]:
    with open(MAP_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_CACHE: Optional[Dict[str, Any]] = None

def get_mapping() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        _CACHE = load_broad_topics_map()
    return _CACHE

def get_broad_topics() -> List[Dict[str, Any]]:
    return get_mapping().get("broad_topics", [])

def get_subpart_to_topic_lookup() -> Dict[str, Dict[str, Any]]:
    lookup = {}
    for bt in get_broad_topics():
        for sp in bt.get("subparts", []):
            lookup[sp["id"]] = {
                "broad_topic_id": bt["id"],
                "broad_topic_name": bt["name"],
                "short_name": bt.get("short_name", bt["name"]),
                "color": bt.get("color", "accent"),
                "icon": bt.get("icon", "BookOpen"),
                "subpart_id": sp["id"],
                "subpart_name": sp["name"]
            }
    return lookup

def get_subparts_for_broad_topic(topic_id: str) -> List[str]:
    for bt in get_broad_topics():
        if bt["id"] == topic_id:
            return [sp["id"] for sp in bt.get("subparts", [])]
    return []

def validate_all_subparts(discovered_subparts: List[str]) -> Dict[str, Any]:
    lookup = get_subpart_to_topic_lookup()
    discovered_set = set(discovered_subparts)
    mapped_set = set(lookup.keys())
    
    missing = discovered_set - mapped_set
    extra = mapped_set - discovered_set
    
    is_valid = len(missing) == 0 and len(extra) == 0
    return {
        "valid": is_valid,
        "total_mapped_subparts": len(mapped_set),
        "total_discovered_subparts": len(discovered_set),
        "missing_in_mapping": list(missing),
        "extra_in_mapping": list(extra),
        "broad_topic_count": len(get_broad_topics())
    }
