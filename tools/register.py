"""Registro central das ferramentas iniciais (seção 15.1)."""
from tools.artifacts.minio_tools import ArtifactList, ArtifactRead, ArtifactWrite
from tools.base import registry
from tools.code.code_tools import CodeFormat, CodePatch, CodeSearch
from tools.containers.container_tools import ContainerBuild, ContainerRunSandbox
from tools.database.db_tools import DatabaseInspectSchema, DatabaseValidateMigration
from tools.repository.git_tools import (
    RepositoryCommit,
    RepositoryCreateBranch,
    RepositoryDiff,
    RepositoryRead,
)
from tools.security.scanners import (
    SecurityRunSast,
    SecurityScanContainer,
    SecurityScanDependencies,
    SecurityScanSecrets,
)
from tools.testing.runners import (
    QualityRunComplexity,
    QualityRunLint,
    QualityRunTypeCheck,
    TestRunE2E,
    TestRunIntegration,
    TestRunUnit,
)
from tools.workflow.workflow_tools import (
    DiagramGenerate,
    DocumentationGenerate,
    StandardsSearch,
    WorkflowCompleteTask,
    WorkflowReportFinding,
    WorkflowRequestApproval,
)


def register_all() -> None:
    for tool in [
        RepositoryRead(), RepositoryDiff(), RepositoryCreateBranch(), RepositoryCommit(),
        ArtifactRead(), ArtifactWrite(), ArtifactList(),
        CodeSearch(), CodePatch(), CodeFormat(),
        TestRunUnit, TestRunIntegration, TestRunE2E,
        QualityRunLint, QualityRunTypeCheck, QualityRunComplexity,
        SecurityRunSast, SecurityScanDependencies, SecurityScanSecrets, SecurityScanContainer,
        ContainerBuild(), ContainerRunSandbox(),
        DatabaseInspectSchema(), DatabaseValidateMigration(),
        DocumentationGenerate(), DiagramGenerate(), StandardsSearch(),
        WorkflowRequestApproval(), WorkflowReportFinding(), WorkflowCompleteTask(),
    ]:
        registry.register(tool)
