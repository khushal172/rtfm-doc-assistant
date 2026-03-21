import re
from typing import Dict, Any
from app.logging_config import logger

class GithubProcessor:
    """Parses code files to extract a structural skeleton (AST/Regex) to save tokens."""
    
    def extract_skeleton(self, code: str, file_path: str) -> str:
        """
        Extracts a structural skeleton of the code using RegEx heuristics.
        Returns a compressed version containing mainly imports, classes, and function signatures.
        """
        if not code or not code.strip():
            return ""

        skeleton_lines = []
        is_python = file_path.endswith(".py")
        is_js_ts = file_path.endswith((".js", ".jsx", ".ts", ".tsx"))

        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Python Structural Heuristics
            if is_python:
                if stripped.startswith(("import ", "from ", "class ", "def ", "@")):
                    skeleton_lines.append(line)
                    
            # JS/TS Structural Heuristics
            elif is_js_ts:
                if stripped.startswith(("import ", "export ", "class ", "function ", "interface ", "type ")):
                    skeleton_lines.append(line)
                elif "=>" in stripped and ("const " in stripped or "let " in stripped):
                    # Trying to catch arrow functions
                    skeleton_lines.append(line)
                    
            # Fallback for other languages or general docstrings/comments if needed
            else:
                # For unknown languages, we just take the first 50 lines as a naive skeleton,
                # or we could try to look for obvious keywords.
                if i < 50:
                    skeleton_lines.append(line)

        # If we couldn't extract anything meaningful, fallback to truncation
        if not skeleton_lines:
            truncated = "\n".join(lines[:30])
            return f"// [Truncated] \n{truncated}"

        return "\n".join(skeleton_lines)
