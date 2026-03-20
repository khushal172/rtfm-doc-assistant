import httpx
import base64
from typing import List, Dict, Any, Optional
from app.logging_config import logger

class GithubService:
    """Provides utilities for fetching repository structure and content from GitHub."""
    def __init__(self, token: Optional[str] = None):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RTFM-Agent-Intelligence"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
            
    def parse_github_url(self, url: str) -> Dict[str, str]:
        """Extracts owner, repo, and branch from a GitHub URL."""
        # Simple parsing for github.com/owner/repo/tree/branch or github.com/owner/repo
        parts = url.rstrip("/").split("github.com/")[-1].split("/")
        
        owner = parts[0]
        repo = parts[1]
        branch = "main" # Default
        
        if len(parts) >= 4 and parts[2] == "tree":
            branch = parts[3]
            
        return {"owner": owner, "repo": repo, "branch": branch}

    async def get_recursive_tree(self, owner: str, repo: str, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches the recursive file tree for a repository, detecting the default branch if needed."""
        async with httpx.AsyncClient() as client:
            # 1. Resolve Branch if not provided
            if not branch or branch == "main":
                repo_url = f"https://api.github.com/repos/{owner}/{repo}"
                repo_res = await client.get(repo_url, headers=self.headers)
                if repo_res.status_code == 200:
                    branch = repo_res.json().get("default_branch", "main")
                else:
                    logger.warning(f"Could not fetch repo metadata for {owner}/{repo}. Defaulting to 'main'.")
                    branch = branch or "main"

            # 2. Fetch Tree
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"GitHub API error ({response.status_code}): {response.text}")
                raise Exception(f"Failed to fetch repo tree (branch: {branch}): {response.status_code}")
                
            data = response.json()
            # We only care about blobs (files), not trees (folders)
            return [item for item in data.get("tree", []) if item.get("type") == "blob"]

    async def download_repo_zip(self, owner: str, repo: str, branch: str = "main") -> bytes:
        """Downloads the entire repository as a ZIP archive."""
        url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"GitHub ZIP Download failed ({response.status_code}): {response.text}")
                raise Exception(f"Failed to download repo ZIP: {response.status_code}")
            return response.content

    def should_index(self, path: str) -> bool:
        """Filter to exclude noise and non-text files."""
        excluded_dirs = {
            "node_modules", "dist", ".git", "__pycache__", ".next", 
            "venv", ".venv", "env", ".env", "build", "out"
        }
        excluded_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", 
            ".pdf", ".exe", ".bin", ".zip", ".tar", ".gz", ".map"
        }
        
        parts = path.split("/")
        if any(p in excluded_dirs for p in parts):
            return False
            
        if any(path.lower().endswith(ext) for ext in excluded_extensions):
            return False
            
        return True
