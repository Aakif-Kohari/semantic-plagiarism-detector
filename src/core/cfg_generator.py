"""
src/core/cfg_generator.py
-------------------------
Control Flow Graph (CFG) Generator for Source Code Plagiarism Detection.

Parses Python source code into normalized Control Flow Graphs where nodes
represent basic blocks (sequences of statements without branches) and edges
represent control flow (jumps, branches, loops). This allows detection of
algorithmic cloning even when variable names or syntax are obfuscated.
"""

import ast
import logging
import hashlib
from typing import List, Dict, Any, Tuple, Set, Optional

logger = logging.getLogger(__name__)


class BasicBlock:
    """Represents a basic block in the Control Flow Graph."""

    def __init__(self, block_id: int):
        self.id = block_id
        self.statements: List[str] = []  # Normalized statement types
        self.successors: List[int] = []  # IDs of successor blocks

    def add_statement(self, stmt_type: str) -> None:
        """Add a normalized statement type to the block."""
        self.statements.append(stmt_type)

    def add_successor(self, block_id: int) -> None:
        """Add a successor block ID."""
        if block_id not in self.successors:
            self.successors.append(block_id)

    def get_signature(self) -> str:
        """Generate a structural signature for the block."""
        return "_".join(self.statements) if self.statements else "EMPTY"


class CFGGenerator(ast.NodeVisitor):
    """AST Visitor that generates a Control Flow Graph from Python source code."""

    def __init__(self):
        self.blocks: Dict[int, BasicBlock] = {}
        self.current_block_id = 0
        self.block_counter = 0

    def _new_block(self) -> int:
        """Create a new basic block and return its ID."""
        self.block_counter += 1
        self.blocks[self.block_counter] = BasicBlock(self.block_counter)
        return self.block_counter

    def _link(self, from_id: int, to_id: int) -> None:
        """Add an edge between two blocks."""
        if from_id in self.blocks and to_id in self.blocks:
            self.blocks[from_id].add_successor(to_id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and create entry blocks."""
        entry_block = self._new_block()
        self.blocks[entry_block].add_statement("FUNC_DEF")

        prev_block = entry_block
        for stmt in node.body:
            stmt_block = self._new_block()
            stmt_type = type(stmt).__name__
            self.blocks[stmt_block].add_statement(stmt_type)
            self._link(prev_block, stmt_block)
            prev_block = stmt_block

    def visit_If(self, node: ast.If) -> None:
        """Visit If statements and create branching blocks."""
        # This is a simplified CFG generation. Real CFGs split at every branch.
        # Here we just mark the block as containing an IF statement.
        self.blocks[self.current_block_id].add_statement("IF")
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Visit For loops."""
        self.blocks[self.current_block_id].add_statement("FOR")
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Visit While loops."""
        self.blocks[self.current_block_id].add_statement("WHILE")
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Visit Return statements."""
        self.blocks[self.current_block_id].add_statement("RETURN")

    def generic_visit(self, node: ast.AST) -> None:
        """Generic visitor for other statement types."""
        stmt_type = type(node).__name__
        if self.current_block_id in self.blocks:
            self.blocks[self.current_block_id].add_statement(stmt_type)
        super().generic_visit(node)


def generate_cfg(source_code: str) -> Dict[int, BasicBlock]:
    """Generate a Control Flow Graph from Python source code.

    Args:
        source_code: Python source code string.

    Returns:
        Dictionary mapping block IDs to BasicBlock objects.
    """
    try:
        tree = ast.parse(source_code)
        generator = CFGGenerator()

        # Create initial entry block
        generator.current_block_id = generator._new_block()
        generator.blocks[generator.current_block_id].add_statement("ENTRY")

        generator.visit(tree)

        logger.info("Generated CFG with %d basic blocks.", len(generator.blocks))
        return generator.blocks

    except SyntaxError as e:
        logger.error("Failed to parse source code for CFG: %s", e)
        return {}
    except Exception as e:
        logger.error("Unexpected error generating CFG: %s", e)
        return {}


def cfg_to_adjacency_list(blocks: Dict[int, BasicBlock]) -> Dict[int, List[int]]:
    """Convert CFG blocks to a simple adjacency list representation."""
    adj_list = {}
    for block_id, block in blocks.items():
        adj_list[block_id] = block.successors
    return adj_list


def compute_cfg_hash(blocks: Dict[int, BasicBlock]) -> str:
    """Compute a structural hash of the CFG.

    Generates a deterministic hash based on block signatures and edge structure,
    ignoring variable names and specific literal values.
    """
    if not blocks:
        return ""

    # Build a canonical string representation of the CFG
    # Sort blocks by ID to ensure determinism
    canonical_parts = []
    for block_id in sorted(blocks.keys()):
        block = blocks[block_id]
        sig = block.get_signature()
        successors = sorted(block.successors)
        canonical_parts.append(f"B{block_id}({sig})->{successors}")

    canonical_str = "|".join(canonical_parts)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
