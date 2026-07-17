# -*- coding: utf-8 -*-
"""
tools/analysis/dependencies.py

Dependency graph analysis.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Set, Dict, List
from .types import DependencyStats, AnalysisScope, AnalysisLevel


class DependencyAnalyzer:
    """
    Analyze dependency graph.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> DependencyStats:
        """Analyze dependency statistics."""
        stats = DependencyStats()

        if scope != AnalysisScope.SCENE:
            return stats

        # Build dependency graph
        graph = self._build_dependency_graph()
        stats.total_connections = len(graph['connections'])

        # Detect cycles (simplified)
        stats.total_cycles = self._detect_cycles(graph)

        # Depth analysis
        depths = self._compute_depths(graph)
        if depths:
            stats.max_depth = max(depths.values())
            stats.average_depth = sum(depths.values()) / len(depths) if depths else 0.0

        # Isolated nodes
        isolated = [n for n in graph['nodes'] if n not in graph['incoming'] and n not in graph['outgoing']]
        stats.isolated_nodes = len(isolated)

        if level == AnalysisLevel.DEEP:
            stats.details['nodes'] = graph['nodes'][:20]
            stats.details['connections'] = graph['connections'][:20]

        return stats

    def _build_dependency_graph(self) -> Dict:
        """Build a simple dependency graph."""
        nodes = cmds.ls(long=True)
        connections = []
        incoming = set()
        outgoing = set()

        for node in nodes:
            # Get connections
            conn = cmds.listConnections(node, plugs=True, connections=True) or []
            for i in range(0, len(conn), 2):
                src = conn[i]
                dst = conn[i+1]
                connections.append((src, dst))
                incoming.add(dst)
                outgoing.add(src)

        return {
            'nodes': nodes,
            'connections': connections,
            'incoming': incoming,
            'outgoing': outgoing,
        }

    def _detect_cycles(self, graph: Dict) -> int:
        """Detect cycles in the dependency graph (simplified)."""
        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()
        cycles = 0

        def dfs(node):
            nonlocal cycles
            if node in rec_stack:
                cycles += 1
                return
            if node in visited:
                return
            visited.add(node)
            rec_stack.add(node)
            # Find outgoing connections
            for src, dst in graph['connections']:
                if src == node:
                    dfs(dst)
            rec_stack.remove(node)

        for node in graph['nodes']:
            if node not in visited:
                dfs(node)

        return cycles

    def _compute_depths(self, graph: Dict) -> Dict[str, int]:
        """Compute depth of each node in the dependency graph."""
        depths = {}
        # Topological sort (simplified)
        for node in graph['nodes']:
            if node not in graph['incoming']:
                depths[node] = 0

        changed = True
        while changed:
            changed = False
            for src, dst in graph['connections']:
                if src in depths and dst not in depths:
                    depths[dst] = depths[src] + 1
                    changed = True

        # All remaining nodes get a default depth
        for node in graph['nodes']:
            if node not in depths:
                depths[node] = 0

        return depths