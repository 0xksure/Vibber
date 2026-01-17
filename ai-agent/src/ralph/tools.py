"""
Tools for Ralph Wiggum Agent

Provides tools the AI agent can use during task execution:
- File operations (read, write, edit)
- Code execution (bash commands)
- Git operations
- Search operations
"""

import asyncio
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.ralph.models import FileChange, ToolCall

logger = structlog.get_logger()


class RalphToolkit:
    """
    Toolkit providing tools for the Ralph agent.

    Tools are designed to be safe and sandboxed:
    - File operations restricted to working directory
    - Commands have timeout limits
    - Dangerous operations require explicit flags
    """

    def __init__(
        self,
        working_directory: str = ".",
        allow_shell_commands: bool = True,
        command_timeout: int = 60,
    ):
        self.working_dir = Path(working_directory).resolve()
        self.allow_shell = allow_shell_commands
        self.command_timeout = command_timeout
        self.file_changes: List[FileChange] = []

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for the AI model"""
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file. Use this to understand existing code before making changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to working directory)"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line number (1-indexed, optional)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Ending line number (optional)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file (relative to working directory)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "edit_file",
                "description": "Edit a file by replacing specific text. Use for targeted changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file"
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Exact text to find and replace"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "Text to replace with"
                        },
                        "replace_all": {
                            "type": "boolean",
                            "description": "Replace all occurrences (default: false, only first)"
                        }
                    },
                    "required": ["path", "old_text", "new_text"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in a directory with optional pattern matching.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (default: current directory)"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to filter files (e.g., '*.py', '**/*.ts')"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively (default: false)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "search_files",
                "description": "Search for text pattern in files. Returns matching lines with context.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Text or regex pattern to search for"
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search in (default: current)"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Filter files by glob pattern (e.g., '*.py')"
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Number of context lines to show (default: 2)"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "run_command",
                "description": "Run a shell command. Use for running tests, linting, building, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 60, max: 300)"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "git_status",
                "description": "Get git status showing modified, staged, and untracked files.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "git_diff",
                "description": "Get git diff showing changes in files.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Specific file to diff (optional)"
                        },
                        "staged": {
                            "type": "boolean",
                            "description": "Show staged changes (default: false)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "git_commit",
                "description": "Create a git commit with staged changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message"
                        },
                        "add_all": {
                            "type": "boolean",
                            "description": "Stage all changes before committing (default: false)"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "create_directory",
                "description": "Create a directory (including parent directories).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to create"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file or empty directory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to delete"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "complete_task",
                "description": "Signal that the task is complete. Only call this when ALL requirements are met and tests pass.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Summary of what was accomplished"
                        }
                    },
                    "required": ["summary"]
                }
            },
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolCall:
        """Execute a tool and return the result"""
        import time
        start_time = time.time()

        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
        )

        try:
            method = getattr(self, f"_tool_{tool_name}", None)
            if not method:
                tool_call.error = f"Unknown tool: {tool_name}"
            else:
                result = await method(**arguments)
                tool_call.result = result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            tool_call.error = str(e)

        tool_call.duration_ms = int((time.time() - start_time) * 1000)
        return tool_call

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate a path within working directory"""
        resolved = (self.working_dir / path).resolve()
        # Security: Ensure path is within working directory
        if not str(resolved).startswith(str(self.working_dir)):
            raise ValueError(f"Path {path} is outside working directory")
        return resolved

    async def _tool_read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read file contents"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return {"error": f"File not found: {path}"}

        if not full_path.is_file():
            return {"error": f"Not a file: {path}"}

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")

            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]
                content = "\n".join(lines)

            return {
                "path": path,
                "content": content,
                "lines": len(content.split("\n")),
                "size": len(content),
            }
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

    async def _tool_write_file(
        self,
        path: str,
        content: str
    ) -> Dict[str, Any]:
        """Write content to file"""
        full_path = self._resolve_path(path)

        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Track if it's a new file or modification
            action = "modify" if full_path.exists() else "create"
            old_lines = 0
            if full_path.exists():
                old_content = full_path.read_text(encoding="utf-8", errors="replace")
                old_lines = len(old_content.split("\n"))

            # Write the file
            full_path.write_text(content, encoding="utf-8")
            new_lines = len(content.split("\n"))

            # Track change
            self.file_changes.append(FileChange(
                path=path,
                action=action,
                content_preview=content[:200],
                lines_added=new_lines if action == "create" else max(0, new_lines - old_lines),
                lines_removed=0 if action == "create" else max(0, old_lines - new_lines),
            ))

            return {
                "success": True,
                "path": path,
                "action": action,
                "lines": new_lines,
            }
        except Exception as e:
            return {"error": f"Failed to write file: {e}"}

    async def _tool_edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False
    ) -> Dict[str, Any]:
        """Edit file by replacing text"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return {"error": f"File not found: {path}"}

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")

            if old_text not in content:
                return {
                    "error": f"Text not found in file",
                    "searched_for": old_text[:100],
                }

            if replace_all:
                new_content = content.replace(old_text, new_text)
                count = content.count(old_text)
            else:
                new_content = content.replace(old_text, new_text, 1)
                count = 1

            full_path.write_text(new_content, encoding="utf-8")

            # Track change
            self.file_changes.append(FileChange(
                path=path,
                action="modify",
                content_preview=new_text[:200],
            ))

            return {
                "success": True,
                "path": path,
                "replacements": count,
            }
        except Exception as e:
            return {"error": f"Failed to edit file: {e}"}

    async def _tool_list_files(
        self,
        path: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """List files in directory"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return {"error": f"Directory not found: {path}"}

        try:
            if pattern:
                if recursive:
                    files = list(full_path.glob(f"**/{pattern}"))
                else:
                    files = list(full_path.glob(pattern))
            else:
                if recursive:
                    files = [f for f in full_path.rglob("*") if f.is_file()]
                else:
                    files = [f for f in full_path.iterdir()]

            # Convert to relative paths and sort
            relative_files = []
            for f in files[:100]:  # Limit results
                try:
                    rel = f.relative_to(self.working_dir)
                    relative_files.append({
                        "path": str(rel),
                        "is_dir": f.is_dir(),
                        "size": f.stat().st_size if f.is_file() else 0,
                    })
                except ValueError:
                    pass

            relative_files.sort(key=lambda x: x["path"])

            return {
                "path": path,
                "files": relative_files,
                "total": len(relative_files),
                "truncated": len(files) > 100,
            }
        except Exception as e:
            return {"error": f"Failed to list files: {e}"}

    async def _tool_search_files(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: Optional[str] = None,
        context_lines: int = 2
    ) -> Dict[str, Any]:
        """Search for pattern in files"""
        full_path = self._resolve_path(path)

        try:
            # Use grep if available, fall back to Python
            if self.allow_shell:
                grep_cmd = f"grep -rn"
                if context_lines:
                    grep_cmd += f" -C {context_lines}"
                if file_pattern:
                    grep_cmd += f" --include='{file_pattern}'"
                grep_cmd += f" '{pattern}' {full_path}"

                result = await self._run_shell_command(grep_cmd, timeout=30)
                if result.get("stdout"):
                    matches = result["stdout"].split("\n")[:50]
                    return {
                        "pattern": pattern,
                        "matches": matches,
                        "total": len(matches),
                    }

            # Fallback: Python-based search
            matches = []
            search_regex = re.compile(pattern, re.IGNORECASE)

            for file_path in full_path.rglob(file_pattern or "*"):
                if not file_path.is_file():
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if search_regex.search(line):
                            rel_path = file_path.relative_to(self.working_dir)
                            matches.append({
                                "file": str(rel_path),
                                "line": i + 1,
                                "content": line.strip()[:200],
                            })
                            if len(matches) >= 50:
                                break
                except Exception:
                    pass
                if len(matches) >= 50:
                    break

            return {
                "pattern": pattern,
                "matches": matches,
                "total": len(matches),
            }
        except Exception as e:
            return {"error": f"Search failed: {e}"}

    async def _tool_run_command(
        self,
        command: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Run shell command"""
        if not self.allow_shell:
            return {"error": "Shell commands are disabled"}

        # Limit timeout
        timeout = min(timeout, 300)

        # Block dangerous commands
        dangerous = ["rm -rf /", "mkfs", "> /dev/", "dd if="]
        for d in dangerous:
            if d in command:
                return {"error": f"Dangerous command blocked: {d}"}

        return await self._run_shell_command(command, timeout)

    async def _run_shell_command(
        self,
        command: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Internal shell command execution"""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "error": f"Command timed out after {timeout}s",
                    "exit_code": -1,
                }

            return {
                "stdout": stdout.decode("utf-8", errors="replace")[:10000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5000],
                "exit_code": proc.returncode,
                "success": proc.returncode == 0,
            }
        except Exception as e:
            return {"error": f"Command execution failed: {e}"}

    async def _tool_git_status(self) -> Dict[str, Any]:
        """Get git status"""
        return await self._run_shell_command("git status --porcelain && git status -sb")

    async def _tool_git_diff(
        self,
        path: Optional[str] = None,
        staged: bool = False
    ) -> Dict[str, Any]:
        """Get git diff"""
        cmd = "git diff"
        if staged:
            cmd += " --staged"
        if path:
            cmd += f" -- {path}"
        return await self._run_shell_command(cmd)

    async def _tool_git_commit(
        self,
        message: str,
        add_all: bool = False
    ) -> Dict[str, Any]:
        """Create git commit"""
        if add_all:
            add_result = await self._run_shell_command("git add -A")
            if not add_result.get("success", True):
                return {"error": f"Git add failed: {add_result.get('stderr', '')}"}

        # Escape message for shell
        safe_message = message.replace("'", "'\\''")
        return await self._run_shell_command(f"git commit -m '{safe_message}'")

    async def _tool_create_directory(self, path: str) -> Dict[str, Any]:
        """Create directory"""
        full_path = self._resolve_path(path)
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"error": f"Failed to create directory: {e}"}

    async def _tool_delete_file(self, path: str) -> Dict[str, Any]:
        """Delete file or empty directory"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return {"error": f"Path not found: {path}"}

        try:
            if full_path.is_file():
                full_path.unlink()
                self.file_changes.append(FileChange(
                    path=path,
                    action="delete",
                ))
                return {"success": True, "path": path, "type": "file"}
            elif full_path.is_dir():
                full_path.rmdir()  # Only removes empty directories
                return {"success": True, "path": path, "type": "directory"}
        except Exception as e:
            return {"error": f"Failed to delete: {e}"}

    async def _tool_complete_task(self, summary: str) -> Dict[str, Any]:
        """Signal task completion"""
        return {
            "signal": "COMPLETE",
            "summary": summary,
            "completion_promise": "<promise>COMPLETE</promise>",
        }

    def get_file_changes(self) -> List[FileChange]:
        """Get list of file changes made"""
        changes = self.file_changes.copy()
        self.file_changes.clear()
        return changes
