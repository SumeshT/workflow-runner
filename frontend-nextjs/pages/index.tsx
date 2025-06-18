import { useState, useCallback, useEffect } from 'react';
import { WorkflowSpecSchema, WorkflowSpec, StreamEvent, LogEntry } from '../lib/types';
import JsonEditor from '../components/JsonEditor';
import LogViewer from '../components/LogViewer';

// Define the address of our FastAPI backend.
const API_BASE_URL = 'http://localhost:8000';

const defaultJson = `{
  "nodes": [
    {
      "id": "node-1",
      "type": "PromptNode",
      "data": {
        "template": "Translate the following to French: {{input}}. Give just the translation, no other text."
      }
    },
    {
      "id": "node-2",
      "type": "LLMNode",
      "data": {}
    }
  ]
}`;

export default function HomePage() {
  const [jsonText, setJsonText] = useState<string>(defaultJson);
  const [isJsonValid, setIsJsonValid] = useState<boolean>(true);
  const [inputText, setInputText] = useState<string>('Hello, world!');
  const [logs, setLogs] = useState<Array<LogEntry | { type: 'status'; message: string }>>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [forceTimeout, setForceTimeout] = useState<boolean>(false);

  useEffect(() => {
    try {
      WorkflowSpecSchema.parse(JSON.parse(jsonText));
      setIsJsonValid(true);
    } catch (e) {
      setIsJsonValid(false);
      console.error('Invalid JSON:', e);
    }
  }, [jsonText]);

  const handleRunWorkflow = useCallback(async () => {
    if (!isJsonValid) return;
    setIsRunning(true);
    setLogs([{ type: 'status', message: 'Creating workflow...' }]);

    try {
      const spec: WorkflowSpec = JSON.parse(jsonText);
      
      // Step 1: Create the workflow by calling the FastAPI backend
      const createResponse = await fetch(`${API_BASE_URL}/api/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec),
      });
      if (!createResponse.ok) throw new Error(`Failed to create workflow: ${await createResponse.text()}`);
      
      const { id } = await createResponse.json();
      setLogs([{ type: 'status', message: `Workflow created (ID: ${id}). Starting execution...` }]);
      
      // Step 2: Run the workflow and stream logs from the FastAPI backend
      const runResponse = await fetch(`${API_BASE_URL}/api/workflows/${id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: inputText, forceLLMTimeout: forceTimeout }),
      });
      if (!runResponse.body) throw new Error('Streaming response not available.');
      
      setLogs([]); // Clear logs for the new run
      const reader = runResponse.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const eventLines = chunk.split('\n\n').filter(line => line.startsWith('data: '));
        for (const line of eventLines) {
          const jsonString = line.replace('data: ', '');
          const event: StreamEvent = JSON.parse(jsonString);
          if ('type' in event && event.type === 'workflowStatus') {
            setLogs(prev => [...prev, { type: 'status', message: `[WORKFLOW] ${event.message}` }]);
          } else {
            setLogs(prev => [...prev, event as LogEntry]);
          }
        }
      }

    } catch (error) {
      setLogs(prev => [...prev, { type: 'status', message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}` }]);
    } finally {
      setIsRunning(false);
    }
  }, [jsonText, inputText, isJsonValid, forceTimeout]);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-cyan-400">Mini Workflow Runner</h1>
          <p className="text-gray-400 mt-2">Define a workflow in the FastAPI backend, run it, and watch the live logs.</p>
        </header>
        <main className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="flex flex-col space-y-4">
            <JsonEditor value={jsonText} onChange={setJsonText} />
            <input id="input" type="text" value={inputText} onChange={(e) => setInputText(e.target.value)} className="w-full bg-gray-800 border border-gray-600 rounded-md p-2 text-gray-100" />
            <div className="flex items-center space-x-4">
              <button onClick={handleRunWorkflow} disabled={!isJsonValid || isRunning} className="px-6 py-2 bg-cyan-600 text-white font-semibold rounded-md hover:bg-cyan-500 disabled:bg-gray-600">
                {isRunning ? 'Running...' : 'Run Workflow'}
              </button>
              <div className="flex items-center">
                <input type="checkbox" id="force-timeout" checked={forceTimeout} onChange={(e) => setForceTimeout(e.target.checked)} className="h-4 w-4 rounded border-gray-500 bg-gray-700 text-cyan-600"/>
                <label htmlFor="force-timeout" className="ml-2 text-sm text-gray-300">Force LLM Timeout</label>
              </div>
            </div>
          </div>
          <div>
            <LogViewer logs={logs} />
          </div>
        </main>
      </div>
    </div>
  );
}