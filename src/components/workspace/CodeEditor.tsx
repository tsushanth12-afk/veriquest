/* ==========================================================================
   VeriQuest Workspace — Monaco Verilog Editor (Warm Neumorphic Theme)
   ========================================================================== */

import React, { useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { Play, Send, RotateCcw, Save, Code2 } from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  onRun: () => void;
  onSubmit: () => void;
  onReset: () => void;
  isExecuting: boolean;
  filename?: string;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onChange,
  onRun,
  onSubmit,
  onReset,
  isExecuting,
  filename = 'solution.v',
}) => {
  const { addToast } = useApp();
  const editorRef = useRef<any>(null);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Define custom warm VeriQuest Monaco Theme matching Section 0 palette
    monaco.editor.defineTheme('veriquest-warm', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '716A63', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'C96F4A', fontStyle: 'bold' },
        { token: 'identifier', foreground: '302B27' },
        { token: 'type', foreground: 'B65D45', fontStyle: 'bold' },
        { token: 'number', foreground: '7D8765', fontStyle: 'bold' },
        { token: 'string', foreground: '8A6D3B' },
        { token: 'operator', foreground: 'C96F4A' },
        { token: 'delimiter', foreground: '716A63' },
      ],
      colors: {
        'editor.background': '#F7F1E8',
        'editor.foreground': '#302B27',
        'editorCursor.foreground': '#C96F4A',
        'editor.lineHighlightBackground': '#EFE7DC',
        'editorLineNumber.foreground': '#A89F91',
        'editorLineNumber.activeForeground': '#C96F4A',
        'editorIndentGuide.background': '#E2D9CB',
        'editorIndentGuide.activeBackground': '#C5BBAA',
        'editor.selectionBackground': '#E5D3C5',
        'editorGutter.background': '#F7F1E8',
      },
    });

    monaco.editor.setTheme('veriquest-warm');
  };

  const handleSave = () => {
    addToast({
      type: 'success',
      title: 'Draft Saved Locally',
      description: 'Your Verilog code has been stored in your session draft.',
    });
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--highlight)',
        overflow: 'hidden',
      }}
    >
      {/* Editor Top Bar — Warm Neumorphic Styling */}
      <div
        style={{
          height: '42px',
          backgroundColor: 'var(--surface)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          boxShadow: 'var(--shadow-raised-sm)',
          zIndex: 2,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Code2 size={15} style={{ color: 'var(--accent)' }} />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--text-main)',
              fontWeight: 600,
            }}
          >
            {filename}
          </span>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-muted)',
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--highlight)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            IEEE 1364-2005
          </span>
        </div>

        {/* Action Controls — Distinct Run vs Submit */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={onReset}
            disabled={isExecuting}
            className="neu-btn-ghost"
            title="Reset code to starter template"
            style={{
              padding: '4px 8px',
              height: '28px',
              fontSize: '11px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          <button
            onClick={handleSave}
            disabled={isExecuting}
            className="neu-btn-ghost"
            title="Save draft locally"
            style={{
              padding: '4px 8px',
              height: '28px',
              fontSize: '11px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <Save size={13} />
            <span>Save</span>
          </button>

          {/* RUN BUTTON: Non-scoring test against sample vectors */}
          <button
            onClick={onRun}
            disabled={isExecuting}
            className="neu-btn"
            title="Run against public testcase vectors (non-scoring)"
            style={{
              padding: '4px 12px',
              height: '28px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--text-main)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <Play size={13} style={{ color: 'var(--accent)' }} />
            <span style={{ fontWeight: 600 }}>Run</span>
          </button>

          {/* SUBMIT BUTTON: Scoring dispatch to backend verification cluster */}
          <button
            onClick={onSubmit}
            disabled={isExecuting}
            className="neu-btn neu-btn-primary"
            title="Submit to remote verification cluster (scoring & XP)"
            style={{
              padding: '4px 16px',
              height: '28px',
              fontSize: '12px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontWeight: 600,
            }}
          >
            <Send size={13} />
            <span>Submit</span>
          </button>
        </div>
      </div>

      {/* Monaco Editor Container */}
      <div style={{ flex: 1, minHeight: 0, backgroundColor: 'var(--highlight)' }}>
        <Editor
          height="100%"
          language="verilog"
          value={code}
          onChange={(val) => onChange(val || '')}
          onMount={handleEditorDidMount}
          theme="veriquest-warm"
          options={{
            fontFamily: "'JetBrains Mono', Consolas, monospace",
            fontSize: 13,
            lineHeight: 20,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            bracketPairColorization: { enabled: true },
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            folding: true,
            padding: { top: 12, bottom: 12 },
          }}
        />
      </div>
    </div>
  );
};
