interface JsonEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export default function JsonEditor({ value, onChange }: JsonEditorProps) {
  return (
    <textarea
      id="spec"
      rows={15}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full bg-gray-800 border border-gray-600 rounded-md p-3 font-mono text-sm text-gray-100 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
      placeholder="Paste your workflow JSON here..."
    />
  );
}