import { z } from 'zod';

// These schemas are for frontend validation before sending to the backend.
const PromptNodeDataSchema = z.object({
  template: z.string().includes('{{input}}'),
});
const LLMNodeDataSchema = z.object({});
const NodeSchema = z.union([
  z.object({ id: z.string(), type: z.literal('PromptNode'), data: PromptNodeDataSchema }),
  z.object({ id: z.string(), type: z.literal('LLMNode'), data: LLMNodeDataSchema }),
]);
export const WorkflowSpecSchema = z.object({
  nodes: z.array(NodeSchema).length(2).refine(
    (nodes) => nodes[0].type === 'PromptNode' && nodes[1].type === 'LLMNode',
    "Nodes must be PromptNode then LLMNode."
  ),
});

// These types are for handling data received from the backend stream.
export type LogStatus = 'running' | 'success' | 'failure' | 'retrying' | 'info';
export interface LogEntry {
  timestamp: string;
  nodeId: string;
  status: LogStatus;
  message: string;
  output?: any;
  error?: string;
}
export interface WorkflowStatusEvent {
    type: 'workflowStatus';
    status: 'completed' | 'failed';
    message: string;
}
export type StreamEvent = LogEntry | WorkflowStatusEvent;
export type WorkflowSpec = z.infer<typeof WorkflowSpecSchema>;