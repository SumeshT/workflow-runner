import { useEffect, useRef } from 'react';
import { LogEntry } from '../lib/types';

interface LogViewerProps {
  logs: Array<LogEntry | { type: 'status'; message: string }>;
}

const getStatusColor = (status?: LogEntry['status']) => {
  switch (status) {
    case 'running': return 'text-yellow-400';
    case 'success': return 'text-green-400';
    case 'failure': return 'text-red-400';
    case 'retrying': return 'text-orange-400';
    default: return 'text-cyan-400';
  }
};

export default function LogViewer({ logs }: LogViewerProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={logContainerRef} className="h-96 bg-gray-950/50 border border-gray-700 rounded-md p-4 overflow-y-auto font-mono text-xs">
      {logs.length === 0 && <p className="text-gray-500">Awaiting workflow execution...</p>}
      {logs.map((log, index) => {
        if ('type' in log && log.type === 'status') {
          return (<div key={index} className="whitespace-pre-wrap text-blue-400 font-bold">{log.message}</div>);
        }
        const entry = log as LogEntry;
        const statusColor = getStatusColor(entry.status);
        return (
          <div key={index} className="mb-2 last:mb-0">
            <span className="text-gray-500 mr-2">{new Date(entry.timestamp).toLocaleTimeString()}</span>
            <span className="text-purple-400 mr-2">[{entry.nodeId}]</span>
            <span className={`font-bold mr-2 ${statusColor}`}>{entry.status.toUpperCase()}</span>
            <span className="text-gray-300 whitespace-pre-wrap">{entry.message}</span>
            {entry.output && (<div className="pl-4 mt-1 text-gray-400 bg-gray-800/50 p-2 rounded">Output: {JSON.stringify(entry.output)}</div>)}
            {entry.error && (<div className="pl-4 mt-1 text-red-300 bg-red-900/20 p-2 rounded">Error: {entry.error}</div>)}
          </div>
        );
      })}
    </div>
  );
}