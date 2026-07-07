import os
import subprocess
import config
from services.helper_service import safe_join_project_path

class BaseAgentTool:
    def execute(self, args: dict, project_path: str) -> str:
        raise NotImplementedError("Each tool must implement execute")

class ReadFileTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        path = args.get('path', '').strip()
        try:
            filepath = safe_join_project_path(project_path, path)
        except ValueError as e:
            return f"Error: {str(e)}"
        if not os.path.exists(filepath):
            return f"Error: File not found: {path}"
        if os.path.isdir(filepath):
            return f"Error: {path} is a directory. Use LIST_DIR instead."
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f"--- Content of {path} ---\n{content}\n----------------"
        except Exception as e:
            return f"Error reading file: {str(e)}"

class WriteFileTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        path = args.get('path', '').strip()
        content = args.get('content', '')
        try:
            filepath = safe_join_project_path(project_path, path)
        except ValueError as e:
            return f"Error: {str(e)}"
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Success: File written successfully to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class ListDirTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        path = args.get('path', '').strip()
        try:
            target_path = safe_join_project_path(project_path, path)
        except ValueError as e:
            return f"Error: {str(e)}"
        if not os.path.exists(target_path):
            return f"Error: Directory not found: {path}"
        try:
            entries = []
            for entry in os.scandir(target_path):
                if entry.name in config.EXCLUDE_DIRS or entry.name in config.EXCLUDE_FILES:
                    continue
                rel = os.path.relpath(entry.path, project_path)
                entries.append(f"{'[DIR]' if entry.is_dir() else '[FILE]'} {rel}")
            return "\n".join(sorted(entries)) if entries else "Empty directory"
        except Exception as e:
            return f"Error listing directory: {str(e)}"

class SearchFilesTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        query = args.get('query', '').strip()
        if not query:
            return "Error: Empty search query"
        results = []
        query_lower = query.lower()
        try:
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in config.EXCLUDE_DIRS]
                for f in files:
                    if f in config.EXCLUDE_FILES:
                        continue
                    rel_path = os.path.relpath(os.path.join(root, f), project_path)
                    if query_lower in rel_path.lower():
                        results.append(f"Match in filename: {rel_path}")
                    filepath = os.path.join(root, f)
                    if os.path.getsize(filepath) > 500000: # Skip files larger than 500KB
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file_obj:
                            content = file_obj.read()
                            if query_lower in content.lower():
                                lines = content.split('\n')
                                for idx, line in enumerate(lines):
                                    if query_lower in line.lower():
                                        results.append(f"{rel_path}:{idx+1}: {line.strip()[:120]}")
                    except:
                        pass
            return "\n".join(results[:50]) if results else "No matches found"
        except Exception as e:
            return f"Error searching files: {str(e)}"

class RunCommandTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        command = args.get('command', '').strip()
        if not command:
            return "Error: Empty command"
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = f"Exit code: {res.returncode}\n"
            if res.stdout:
                output += f"STDOUT:\n{res.stdout}\n"
            if res.stderr:
                output += f"STDERR:\n{res.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

class FinishTool(BaseAgentTool):
    def execute(self, args: dict, project_path: str) -> str:
        return "Agent finished tasks successfully!"

class ToolRegistry:
    _tools = {
        'READ_FILE': ReadFileTool(),
        'WRITE_FILE': WriteFileTool(),
        'LIST_DIR': ListDirTool(),
        'SEARCH_FILES': SearchFilesTool(),
        'RUN_COMMAND': RunCommandTool(),
        'FINISH': FinishTool()
    }

    @classmethod
    def execute_tool(cls, tool_name: str, args: dict, project_path: str) -> str:
        tool = cls._tools.get(tool_name)
        if not tool:
            return f"Error: Unknown tool {tool_name}"
        return tool.execute(args, project_path)
