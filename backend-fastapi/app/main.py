import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from . import models, store, engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/workflows", response_model=models.CreateWorkflowResponse, status_code=201)
def create_workflow_endpoint(spec: models.WorkflowSpec):
    return store.create_workflow(spec)

@app.post("/api/workflows/{workflow_id}/run")
async def run_workflow_endpoint(workflow_id: str, run_request: models.RunWorkflowRequest, http_request: Request):
    workflow_spec = store.get_workflow(workflow_id)
    if not workflow_spec:
        raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

    async def event_generator():
        try:
            async for event in engine.run_workflow(
                spec=workflow_spec,
                input_text=run_request.input,
                force_llm_timeout=run_request.forceLLMTimeout,
            ):
                if await http_request.is_disconnected():
                    print(f"Client for workflow {workflow_id} disconnected.")
                    break
                # SSE format: data: <json_string>\n\n
                yield f"data: {event.json()}\n\n"
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error during workflow execution: {e}")
            error_event = models.WorkflowStatusEvent(type="workflowStatus", status="failed", message=str(e))
            yield f"data: {error_event.json()}\n\n"
        finally:
            print(f"Closing stream for workflow {workflow_id}.")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "Mini Workflow Runner Backend is running. See /docs for API details."}