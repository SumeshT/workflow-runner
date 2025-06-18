import uuid
from datetime import datetime
from typing import Literal, Union, List, Optional, Annotated
from pydantic import BaseModel, Field, model_validator, conlist

# --- Base Node Schemas ---
class PromptNodeData(BaseModel):
    template: str
    # Using model_validator instead of the old field validator for consistency
    @model_validator(mode='after')
    def template_must_contain_input(self):
        if '{{input}}' not in self.template:
            raise ValueError("Template must include '{{input}}' placeholder.")
        return self

class LLMNodeData(BaseModel):
    pass

# --- Discriminated Union for Nodes ---
class PromptNode(BaseModel):
    id: str
    type: Literal['PromptNode']
    data: PromptNodeData

class LLMNode(BaseModel):
    id: str
    type: Literal['LLMNode']
    data: LLMNodeData

# We create an Annotated type that applies the discriminator directly to the Union.
WorkflowNode = Annotated[
    Union[PromptNode, LLMNode],
    Field(discriminator='type')
]

# --- Main Workflow Specification ---
class WorkflowSpec(BaseModel):
    # Now, the list simply contains the already-discriminated WorkflowNode type.
    nodes: conlist(WorkflowNode, min_length=2, max_length=2)

    @model_validator(mode='after')
    def check_node_order(self):
        nodes = self.nodes
        if nodes:
            # We can now check the type directly on the parsed models
            if not (isinstance(nodes[0], PromptNode) and isinstance(nodes[1], LLMNode)):
                raise ValueError("Nodes must be in the order: PromptNode, then LLMNode.")
        return self

# --- API and Runtime Models ---
class CreateWorkflowResponse(BaseModel):
    id: str
    spec: WorkflowSpec

class RunWorkflowRequest(BaseModel):
    input: str

class LogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    nodeId: str
    status: Literal['running', 'success', 'failure', 'retrying', 'info']
    message: str
    output: Optional[str] = None
    error: Optional[str] = None

class WorkflowStatusEvent(BaseModel):
    type: Literal['workflowStatus']
    status: Literal['completed', 'failed']
    message: str

StreamEvent = Union[LogEntry, WorkflowStatusEvent]