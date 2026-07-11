"""
KnowledgeGraph — in-memory entity-relation graph extracted from memories.

Nodes: entities (person names, POI names, topics) found in memory content.
Edges: co-occurrence in the same memory → relation "mentioned_together".

No heavy dependencies — uses pure Python dicts.

community_detection() groups nodes by shared edge density (greedy approach).

Activated as part of GraphRAG when ENABLE_GRAPHRAG=true.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Node:
    entity: str
    sources: list[str] = field(default_factory=list)  # memory_ids


@dataclass
class Edge:
    a: str
    b: str
    weight: float = 1.0


class KnowledgeGraph:
    """
    Directed weighted graph stored as adjacency dict.
    Entity names are lowercased for normalisation.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[tuple[str, str], Edge] = {}

    def add_memory(self, memory_id: str, content: str) -> None:
        """Extract entities from content and add edges for co-occurring pairs."""
        entities = self._extract_entities(content)
        for ent in entities:
            if ent not in self._nodes:
                self._nodes[ent] = Node(entity=ent)
            self._nodes[ent].sources.append(memory_id)
        for i, a in enumerate(entities):
            for b in entities[i + 1:]:
                key = (a, b) if a < b else (b, a)
                if key in self._edges:
                    self._edges[key].weight += 1.0
                else:
                    self._edges[key] = Edge(a=key[0], b=key[1], weight=1.0)

    def neighbours(self, entity: str) -> list[str]:
        entity = entity.lower()
        result = []
        for (a, b), _ in self._edges.items():
            if a == entity:
                result.append(b)
            elif b == entity:
                result.append(a)
        return result

    def related_memory_ids(self, entity: str, depth: int = 1) -> set[str]:
        """Return memory IDs reachable from entity within `depth` hops."""
        visited: set[str] = set()
        frontier = {entity.lower()}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for ent in frontier:
                node = self._nodes.get(ent)
                if node:
                    visited.update(node.sources)
                    next_frontier.update(self.neighbours(ent))
            frontier = next_frontier - visited
        return visited

    def community_detection(self) -> dict[str, int]:
        """
        Greedy label propagation: assign community IDs to entities.
        Returns dict {entity: community_id}.
        ponytail: O(n²) — fine for small graphs (<1k nodes).
        """
        communities: dict[str, int] = {e: i for i, e in enumerate(self._nodes)}
        changed = True
        while changed:
            changed = False
            for ent in list(self._nodes):
                nbrs = self.neighbours(ent)
                if not nbrs:
                    continue
                counts: dict[int, int] = defaultdict(int)
                for n in nbrs:
                    counts[communities.get(n, -1)] += 1
                dominant = max(counts, key=lambda k: counts[k])
                if communities[ent] != dominant:
                    communities[ent] = dominant
                    changed = True
        return communities

    @staticmethod
    def _extract_entities(text: str) -> list[str]:
        """
        Simple heuristic: capitalised words and known POI keywords.
        ponytail: upgrade to spaCy NER if entity quality matters.
        """
        tokens = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
        lowered = list(dict.fromkeys(t.lower() for t in tokens))  # dedupe preserving order
        return lowered
