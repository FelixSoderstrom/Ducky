# Ducky - Local Code Mentor with RAG-Powered Feedback

**A file-watching assistant that analyzes your codebase changes and provides real-time feedback on code quality, patterns, and best practices.**

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

## What It Does
- Monitors your codebase for changes via file watchers
- Maintains a local SQLite database of your code structure
- Uses RAG (Retrieval-Augmented Generation) to analyze code changes
- Provides contextual feedback on code quality and patterns
- Acts as a code review mentor, not an autocomplete tool

## Key Features
- **Local-first**: All data stays on your machine
- **Real-time analysis**: Immediate feedback on code changes
- **Context-aware**: Understands your entire codebase structure
- **Educational focus**: Explains *why* something is problematic
- **Non-intrusive**: Suggests improvements without writing code for you

## Architecture Overview
```
File System Changes → File Watcher → SQLite Database → RAG Analysis → LLM Feedback
```

## Use Cases
- **Code review automation** for solo developers
- **Learning tool** for junior developers
- **Consistency enforcement** across large codebases
- **Technical debt identification** in real-time

## Technical Stack
- File system monitoring
- SQLite for local code indexing
- RAG pipeline for contextual analysis
- LLM integration for feedback generation

---

## Detailed Documentation

### Problem Statement
Modern AI coding tools excel at code generation but often lead to poor practices when developers don't understand the generated code. Ducky bridges this gap by focusing on education and code quality rather than code generation.

### How It Works
1. **File Monitoring**: Watches your project directory for changes
2. **Code Indexing**: Maintains a searchable database of your codebase
3. **Change Analysis**: Uses RAG to understand the context of your changes
4. **Feedback Generation**: LLM analyzes changes against best practices
5. **Developer Notification**: Provides actionable feedback and explanations

### Development Status
This is the development branch. Working features are merged to main after testing.
To get a sneak peek of what coming around the corner, check out my [Miro Board](https://miro.com/app/board/uXjVIBdU1Lc=/)

### Philosophy
Ducky doesn't write code for you - it teaches you to write better code. The goal is to maintain developer agency while providing expert-level guidance on code quality and patterns.
