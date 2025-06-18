import asyncio
import random
import httpx
from typing import AsyncGenerator
from .models import WorkflowSpec, LogEntry, WorkflowStatusEvent, StreamEvent
import os

MAX_RETRIES = 1
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

def _create_log(node_id: str, status, message: str, **kwargs) -> LogEntry:
    return LogEntry(nodeId=node_id, status=status, message=message, **kwargs)

# --- THIS IS THE MAIN CHANGE ---
async def _call_llm(prompt: str) -> str:
    """
    Calls the Google Gemini API.
    The `force_timeout` parameter is now ignored, as we are making a real call.
    """
    print(f"[LLM Gemini] Calling API with prompt: '{prompt[:50]}...'")

    # The request body must match the format required by the Gemini API.
    request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    # We use an async client to make the web request without blocking our server.
    async with httpx.AsyncClient() as client:
        try:
            # Make the POST request to the Gemini API URL.
            # We set a timeout of 30 seconds.
            response = await client.post(GEMINI_API_URL, json=request_body, timeout=30.0)
            
            # This will raise an error if the status code is 4xx or 5xx (e.g., 400, 401, 500).
            response.raise_for_status()
            
            # Parse the JSON response from the API.
            data = response.json()
            
            # Safely extract the text from the nested response structure.
            # The structure is: response -> candidates -> [0] -> content -> parts -> [0] -> text
            generated_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return generated_text.strip()

        except httpx.TimeoutException:
            # Handle cases where the API call takes too long.
            print("[LLM Gemini] Error: Request timed out.")
            raise TimeoutError("The request to the Gemini API timed out.")
        except httpx.HTTPStatusError as e:
            # Handle errors from the API itself (like bad requests or auth errors).
            print(f"[LLM Gemini] Error: API returned status {e.response.status_code}. Body: {e.response.text}")
            raise Exception(f"Gemini API error: {e.response.status_code} - {e.response.text}")
        except (KeyError, IndexError) as e:
            # Handle cases where the response format is not what we expect.
            print(f"[LLM Gemini] Error: Could not parse response from API. Raw: {data}")
            raise Exception(f"Failed to parse Gemini API response: {e}")


# The run_workflow function remains EXACTLY THE SAME.
# This is the beauty of good abstraction! We only had to change the
# implementation of _call_llm, not the main orchestration logic.
async def run_workflow(spec: WorkflowSpec, input_text: str, force_llm_timeout: bool) -> AsyncGenerator[StreamEvent, None]:
    # Step 1: PromptNode
    prompt_node = spec.nodes[0]
    yield _create_log(prompt_node.id, "running", "Generating prompt...")
    try:
        current_output = prompt_node.data.template.replace("{{input}}", input_text)
        yield _create_log(prompt_node.id, "success", "Prompt generated successfully.", output=current_output)
    except Exception as e:
        yield _create_log(prompt_node.id, "failure", "Failed to generate prompt.", error=str(e))
        yield WorkflowStatusEvent(type="workflowStatus", status="failed", message="Workflow failed at PromptNode.")
        return

    # Step 2: LLMNode with Retry
    llm_node = spec.nodes[1]
    success = False
    for attempt in range(MAX_RETRIES + 1):
        yield _create_log(llm_node.id, "running", f"Calling Gemini API (Attempt {attempt + 1}/{MAX_RETRIES + 1})...")
        try:
            # NOTE: We no longer use `force_llm_timeout` here. The real call can fail on its own.
            # You could add logic here to force a failure for testing if needed.
            current_output = await _call_llm(current_output)
            yield _create_log(llm_node.id, "success", "Gemini API call successful.", output=current_output)
            success = True
            break
        except Exception as e:
            if attempt < MAX_RETRIES:
                yield _create_log(llm_node.id, "retrying", f"API call failed: {e}. Retrying...")
                # Add a small delay before retrying
                await asyncio.sleep(2)
            else:
                yield _create_log(llm_node.id, "failure", f"API call failed after {MAX_RETRIES + 1} attempts.", error=str(e))

    if success:
        yield WorkflowStatusEvent(type="workflowStatus", status="completed", message="Workflow completed successfully.")
    else:
        yield WorkflowStatusEvent(type="workflowStatus", status="failed", message="Workflow failed at LLMNode.")