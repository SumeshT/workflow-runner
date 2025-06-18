import uuid
from typing import Union
from .models import WorkflowSpec, CreateWorkflowResponse

_workflows: dict[str, WorkflowSpec] = {}

def create_workflow(spec: WorkflowSpec) -> CreateWorkflowResponse:
    workflow_id = str(uuid.uuid4())
    _workflows[workflow_id] = spec
    print(f"[Store] Created workflow {workflow_id}")
    return CreateWorkflowResponse(id=workflow_id, spec=spec)

def get_workflow(workflow_id: str) -> Union[WorkflowSpec, None]:
    """Retrieves a workflow by its ID."""
    return _workflows.get(workflow_id)