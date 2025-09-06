# scheduling_engine/genetic_algorithm/chromosome.py

"""
Chromosome representation for variable selectors.
Based on the research paper's GP representation for evolving priority functions.
"""

from typing import Dict, List, Optional, Any, Union, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import random
import copy
import math

from ..config import get_logger, GP_TERMINAL_SET, GP_FUNCTION_SET
from ..core.problem_model import ExamSchedulingProblem

logger = get_logger("ga.chromosome")


class GPNode(ABC):
    """Abstract base class for GP tree nodes"""

    def __init__(self, node_id: Optional[UUID] = None):
        self.id = node_id or uuid4()
        self.parent: Optional["GPNode"] = None
        self.depth: int = 0

    @abstractmethod
    def evaluate(self, terminals: Dict[str, float]) -> float:
        """Evaluate node with given terminal values"""
        pass

    @abstractmethod
    def get_subtree_size(self) -> int:
        """Get size of subtree rooted at this node"""
        pass

    @abstractmethod
    def copy(self) -> "GPNode":
        """Create deep copy of subtree"""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert to readable string representation"""
        pass


class TerminalNode(GPNode):
    """Terminal node representing a GP terminal (ES, PT, W, etc.)"""

    def __init__(self, terminal: str, node_id: Optional[UUID] = None):
        super().__init__(node_id)
        if terminal not in GP_TERMINAL_SET:
            raise ValueError(f"Invalid terminal: {terminal}")
        self.terminal = terminal

    def evaluate(self, terminals: Dict[str, float]) -> float:
        """Return terminal value"""
        return terminals.get(self.terminal, 0.0)

    def get_subtree_size(self) -> int:
        return 1

    def copy(self) -> "TerminalNode":
        return TerminalNode(self.terminal, uuid4())

    def to_string(self) -> str:
        return self.terminal


class FunctionNode(GPNode):
    """Function node representing a GP function (+, -, *, etc.)"""

    def __init__(
        self,
        function: str,
        children: Optional[List[GPNode]] = None,
        node_id: Optional[UUID] = None,
    ):
        super().__init__(node_id)
        if function not in GP_FUNCTION_SET:
            raise ValueError(f"Invalid function: {function}")

        self.function = function
        self.children: List[GPNode] = children or []
        self.arity = self._get_function_arity(function)

        # Set parent relationships
        for child in self.children:
            child.parent = self

    def _get_function_arity(self, function: str) -> int:
        """Get number of arguments for function"""
        binary_functions = ["+", "-", "*", "%", "max", "min"]
        if function in binary_functions:
            return 2
        return 2  # Default to binary

    def evaluate(self, terminals: Dict[str, float]) -> float:
        """Evaluate function with children"""
        if len(self.children) != self.arity:
            return 0.0

        child_values = [child.evaluate(terminals) for child in self.children]

        try:
            if self.function == "+":
                return child_values[0] + child_values[1]
            elif self.function == "-":
                return child_values[0] - child_values[1]
            elif self.function == "*":
                return child_values[0] * child_values[1]
            elif self.function == "%":
                # Protected division to avoid division by zero
                if abs(child_values[1]) < 1e-10:
                    return 1.0
                return child_values[0] / child_values[1]
            elif self.function == "max":
                return max(child_values[0], child_values[1])
            elif self.function == "min":
                return min(child_values[0], child_values[1])
            else:
                return 0.0
        except (ZeroDivisionError, OverflowError, ValueError):
            return 0.0

    def get_subtree_size(self) -> int:
        return 1 + sum(child.get_subtree_size() for child in self.children)

    def copy(self) -> "FunctionNode":
        copied_children = [child.copy() for child in self.children]
        return FunctionNode(self.function, copied_children, uuid4())

    def to_string(self) -> str:
        if len(self.children) == 2:
            return f"({self.children[0].to_string()} {self.function} {self.children[1].to_string()})"
        else:
            child_strs = [child.to_string() for child in self.children]
            return f"{self.function}({', '.join(child_strs)})"


@dataclass
class ExamPriorityGene:
    """
    Gene representing priority calculation for a specific exam.
    Contains GP tree for calculating exam priority.
    """

    exam_id: UUID
    priority_tree: GPNode
    cached_priority: Optional[float] = None

    def calculate_priority(self, terminals: Dict[str, float]) -> float:
        """Calculate priority for exam using GP tree"""
        try:
            priority = self.priority_tree.evaluate(terminals)
            # Ensure finite priority value
            if math.isnan(priority) or math.isinf(priority):
                priority = 0.0
            self.cached_priority = priority
            return priority
        except Exception as e:
            logger.warning(f"Error calculating priority for exam {self.exam_id}: {e}")
            self.cached_priority = 0.0
            return 0.0

    def copy(self) -> "ExamPriorityGene":
        """Create deep copy of gene"""
        return ExamPriorityGene(
            exam_id=self.exam_id,
            priority_tree=self.priority_tree.copy(),
            cached_priority=None,
        )


class VariableSelectorChromosome:
    """
    Chromosome representing a variable selector for CP-SAT.
    Based on research paper's variable ordering representation.

    Contains GP trees for calculating priorities of decision variables (exams).
    """

    def __init__(
        self,
        chromosome_id: Optional[UUID] = None,
        genes: Optional[List[ExamPriorityGene]] = None,
    ):
        self.id = chromosome_id or uuid4()
        self.genes: List[ExamPriorityGene] = genes or []

        # Fitness and evaluation
        self.fitness: float = 0.0
        self.objective_value: float = float("inf")
        self.evaluation_count: int = 0

        # GA metadata
        self.generation: int = 0
        self.parent_ids: List[UUID] = []
        self.mutation_history: List[str] = []

        # Performance tracking
        self.solving_time: float = 0.0
        self.solution_quality: float = 0.0
        self.source: str
        logger.debug(f"Created chromosome {self.id} with {len(self.genes)} genes")

    def add_gene(self, gene: ExamPriorityGene) -> None:
        """Add gene to chromosome"""
        self.genes.append(gene)

    def get_gene_for_exam(self, exam_id: UUID) -> Optional[ExamPriorityGene]:
        """Get gene for specific exam"""
        for gene in self.genes:
            if gene.exam_id == exam_id:
                return gene
        return None

    def calculate_exam_priorities(
        self, problem: ExamSchedulingProblem
    ) -> Dict[UUID, float]:
        """
        Calculate priorities for all exams using GP trees.
        This is the core variable selector functionality.
        """
        priorities = {}

        for gene in self.genes:
            exam = problem.exams.get(gene.exam_id)
            if not exam:
                continue

            # Extract GP terminals for this exam
            terminals = problem.extract_gp_terminals(gene.exam_id)

            # Calculate priority using GP tree
            priority = gene.calculate_priority(terminals)
            priorities[gene.exam_id] = priority

        return priorities

    def get_variable_ordering(
        self, problem: ExamSchedulingProblem, descending: bool = True
    ) -> List[UUID]:
        """
        Get ordered list of exam IDs based on calculated priorities.
        This determines the variable selection order for CP-SAT.
        """
        priorities = self.calculate_exam_priorities(problem)

        # Sort exams by priority
        sorted_exams = sorted(
            priorities.items(), key=lambda x: x[1], reverse=descending
        )

        return [exam_id for exam_id, _ in sorted_exams]

    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get statistics about GP trees in chromosome"""
        total_nodes = sum(gene.priority_tree.get_subtree_size() for gene in self.genes)

        # Count node types
        terminal_counts = {terminal: 0 for terminal in GP_TERMINAL_SET}
        function_counts = {function: 0 for function in GP_FUNCTION_SET}

        for gene in self.genes:
            self._count_nodes_recursive(
                gene.priority_tree, terminal_counts, function_counts
            )

        return {
            "total_genes": len(self.genes),
            "total_nodes": total_nodes,
            "average_tree_size": total_nodes / max(len(self.genes), 1),
            "terminal_usage": terminal_counts,
            "function_usage": function_counts,
        }

    def _count_nodes_recursive(
        self,
        node: GPNode,
        terminal_counts: Dict[str, int],
        function_counts: Dict[str, int],
    ) -> None:
        """Recursively count nodes in GP tree"""
        if isinstance(node, TerminalNode):
            terminal_counts[node.terminal] += 1
        elif isinstance(node, FunctionNode):
            function_counts[node.function] += 1
            for child in node.children:
                self._count_nodes_recursive(child, terminal_counts, function_counts)

    def validate_chromosome(self) -> Dict[str, List[str]]:
        """Validate chromosome structure"""
        errors = []
        warnings = []

        if not self.genes:
            errors.append("Chromosome has no genes")

        # Check for duplicate exam IDs
        exam_ids = [gene.exam_id for gene in self.genes]
        if len(set(exam_ids)) != len(exam_ids):
            errors.append("Chromosome has duplicate exam genes")

        # Validate GP trees
        for i, gene in enumerate(self.genes):
            if not gene.priority_tree:
                errors.append(f"Gene {i} has no priority tree")
                continue

            tree_size = gene.priority_tree.get_subtree_size()
            if tree_size > 50:  # Arbitrary limit
                warnings.append(f"Gene {i} has large tree (size {tree_size})")

        return {"errors": errors, "warnings": warnings}

    def copy(self) -> "VariableSelectorChromosome":
        """Create deep copy of chromosome"""
        copied_genes = [gene.copy() for gene in self.genes]

        new_chromosome = VariableSelectorChromosome(
            chromosome_id=uuid4(), genes=copied_genes
        )

        # Copy metadata (but not fitness - that needs to be re-evaluated)
        new_chromosome.generation = self.generation
        new_chromosome.parent_ids = self.parent_ids.copy()
        new_chromosome.mutation_history = self.mutation_history.copy()

        return new_chromosome

    def to_dict(self) -> Dict[str, Any]:
        """Convert chromosome to dictionary for serialization"""
        return {
            "id": str(self.id),
            "fitness": self.fitness,
            "objective_value": self.objective_value,
            "evaluation_count": self.evaluation_count,
            "generation": self.generation,
            "parent_ids": [str(pid) for pid in self.parent_ids],
            "mutation_history": self.mutation_history,
            "solving_time": self.solving_time,
            "solution_quality": self.solution_quality,
            "gene_count": len(self.genes),
            "tree_statistics": self.get_tree_statistics(),
            "genes": [
                {
                    "exam_id": str(gene.exam_id),
                    "priority_tree": gene.priority_tree.to_string(),
                    "cached_priority": gene.cached_priority,
                    "tree_size": gene.priority_tree.get_subtree_size(),
                }
                for gene in self.genes
            ],
        }

    @classmethod
    def create_random(
        cls, problem: ExamSchedulingProblem, max_tree_depth: int = 5
    ) -> "VariableSelectorChromosome":
        """
        Create random chromosome with GP trees for all exams.
        Uses ramped half-and-half initialization as in research paper.
        """
        chromosome = cls()

        for exam_id in problem.exams.keys():
            # Create random GP tree for this exam
            priority_tree = cls._create_random_tree(max_tree_depth)

            gene = ExamPriorityGene(exam_id=exam_id, priority_tree=priority_tree)

            chromosome.add_gene(gene)

        logger.debug(f"Created random chromosome with {len(chromosome.genes)} genes")
        return chromosome

    @classmethod
    def _create_random_tree(cls, max_depth: int, current_depth: int = 0) -> GPNode:
        """Create random GP tree using ramped half-and-half"""

        # If at max depth or random terminal selection, create terminal
        if current_depth >= max_depth or (current_depth > 0 and random.random() < 0.3):
            terminal = random.choice(GP_TERMINAL_SET)
            return TerminalNode(terminal)

        # Create function node
        function = random.choice(GP_FUNCTION_SET)
        function_node = FunctionNode(function)

        # Create children
        arity = function_node.arity
        for _ in range(arity):
            child = cls._create_random_tree(max_depth, current_depth + 1)
            child.parent = function_node
            child.depth = current_depth + 1
            function_node.children.append(child)

        return function_node

    def get_complexity_measure(self) -> float:
        """Calculate complexity measure for chromosome"""
        total_complexity = 0.0

        for gene in self.genes:
            tree_size = gene.priority_tree.get_subtree_size()
            depth = self._calculate_tree_depth(gene.priority_tree)

            # Complexity based on size and depth
            gene_complexity = tree_size * (1.0 + depth * 0.1)
            total_complexity += gene_complexity

        return total_complexity / max(len(self.genes), 1)

    def _calculate_tree_depth(self, node: GPNode) -> int:
        """Calculate maximum depth of GP tree"""
        if isinstance(node, TerminalNode):
            return 1
        elif isinstance(node, FunctionNode):
            if not node.children:
                return 1
            return 1 + max(self._calculate_tree_depth(child) for child in node.children)
        return 1
