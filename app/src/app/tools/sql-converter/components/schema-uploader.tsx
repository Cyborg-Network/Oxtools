"use client";

import { useState, useCallback } from "react";
import { UploadCloud, FileCode, AlertCircle } from "lucide-react";
import { parseDDL } from "../lib/parser";
import type { ParsedSchema } from "../types";

interface SchemaUploaderProps {
  onSchemaLoaded: (schema: ParsedSchema) => void;
}

export function SchemaUploader({ onSchemaLoaded }: SchemaUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const processText = useCallback(
    (text: string, source: "file" | "paste") => {
      if (!text.trim()) return;
      const parsed = parseDDL(text);
      if (parsed.tableCount === 0) {
        setError(
          `No valid CREATE TABLE statements found in the ${source === "file" ? "file" : "text"}.`
        );
        return;
      }
      setError(null);
      onSchemaLoaded(parsed);
    },
    [onSchemaLoaded]
  );

  const processFile = useCallback(
    async (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["sql", "ddl", "txt"].includes(ext || "")) {
        setError("Only .sql, .ddl, or .txt files are accepted.");
        return;
      }
      setIsLoading(true);
      try {
        const text = await file.text();
        processText(text, "file");
      } catch {
        setError("Could not read the file. Try pasting the DDL directly.");
      } finally {
        setIsLoading(false);
      }
    },
    [processText]
  );

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Load your database schema
        </h2>
        <p className="text-sm text-muted-foreground">
          Required before generating SQL. Supports MySQL, PostgreSQL, SQLite DDL.
        </p>
      </div>

      {/* Drop zone */}
      <label
        className={`relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200 cursor-pointer ${
          dragActive
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border bg-muted/10 hover:border-primary/40 hover:bg-muted/30"
        } ${isLoading ? "opacity-50 pointer-events-none" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".sql,.ddl,.txt"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) processFile(file);
          }}
        />
        <div className="p-4 bg-primary/10 rounded-full text-primary">
          <UploadCloud className="w-7 h-7" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            {isLoading ? "Reading file..." : "Drag & drop your .sql or .ddl file here"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">or click to browse</p>
        </div>
      </label>

      {/* Divider */}
      <div className="relative flex items-center gap-3">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs font-semibold uppercase text-muted-foreground">or paste DDL</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Paste area */}
      <div className="space-y-3">
        <div className="rounded-xl border border-input overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
          <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder={"CREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  email VARCHAR(255) NOT NULL\n);"}
            className="w-full h-32 p-4 bg-muted/20 text-sm font-mono resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>

        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            {error ? (
              <>
                <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
                <span className="text-destructive text-xs">{error}</span>
              </>
            ) : (
              <>
                <FileCode className="w-4 h-4" />
                <span className="text-xs">Paste raw CREATE TABLE statements</span>
              </>
            )}
          </div>
          <button
            onClick={() => processText(textInput, "paste")}
            disabled={!textInput.trim()}
            className="px-5 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-full shadow hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Parse Schema
          </button>
        </div>
      </div>
    </div>
  );
}