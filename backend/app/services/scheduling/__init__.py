# backend/app/services/scheduling/__init__.py

# Import main classes and types from each module
from .timetable_job_orchestrator import OrchestratorOptions, TimetableJobOrchestrator
from .upload_ingestion_bridge import UploadIngestionSummary, UploadIngestionBridge
from .versioning_and_edit_service import ProposedEdit, VersioningAndEditService
from .admin_configuration_manager import (
    ConfigurationTemplate,
    ObjectiveFunction,
    ConstraintConfiguration,
    ConfigurationValidationResult,
    AdminConfigurationManager,
)
from .data_preparation_service import PreparedDataset, DataPreparationService
from .faculty_partitioning_service import (
    PartitionStrategy,
    DependencyType,
    PartitionNode,
    PartitionDependency,
    PartitionGroup,
    PartitioningResult,
    FacultyPartitioningService,
)
from .invigilator_assignment_service import (
    InvigilationAssignment,
    InvigilatorAssignmentService,
)
from .room_allocation_service import RoomAssignmentProposal, RoomAllocationService

# Optional: Define public API for the scheduling package
__all__ = [
    # From timetable_job_orchestrator
    "OrchestratorOptions",
    "TimetableJobOrchestrator",
    # From upload_ingestion_bridge
    "UploadIngestionSummary",
    "UploadIngestionBridge",
    # From versioning_and_edit_service
    "ProposedEdit",
    "VersioningAndEditService",
    # From admin_configuration_manager
    "ConfigurationTemplate",
    "ObjectiveFunction",
    "ConstraintConfiguration",
    "ConfigurationValidationResult",
    "AdminConfigurationManager",
    # From data_preparation_service
    "PreparedDataset",
    "DataPreparationService",
    # From faculty_partitioning_service
    "PartitionStrategy",
    "DependencyType",
    "PartitionNode",
    "PartitionDependency",
    "PartitionGroup",
    "PartitioningResult",
    "FacultyPartitioningService",
    # From invigilator_assignment_service
    "InvigilationAssignment",
    "InvigilatorAssignmentService",
    # From room_allocation_service
    "RoomAssignmentProposal",
    "RoomAllocationService",
]
