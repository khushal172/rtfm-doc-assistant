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
        parts = url.rstrip("/").split("github.com/")[-1].split("/")
        
        owner = parts[0]
        repo = parts[1]
        branch = None # No default, let GitHub decide
        
        if len(parts) >= 4 and parts[2] == "tree":
            branch = "/".join(parts[3:])
            
        return {"owner": owner, "repo": repo, "branch": branch}

    async def get_recursive_tree(self, owner: str, repo: str, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches the file tree. If branch is None, we still need to resolve it for the tree API."""
        if not branch:
            async with httpx.AsyncClient() as client:
                repo_url = f"https://api.github.com/repos/{owner}/{repo}"
                repo_res = await client.get(repo_url, headers=self.headers)
                branch = repo_res.json().get("default_branch", "main") if repo_res.status_code == 200 else "main"

        async with httpx.AsyncClient() as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"GitHub API error ({response.status_code}): {response.text}")
                raise Exception(f"Failed to fetch repo tree (branch: {branch}): {response.status_code}")
                
            data = response.json()
            return [item for item in data.get("tree", []) if item.get("type") == "blob"]

    async def download_repo_zip(self, owner: str, repo: str, branch: Optional[str] = None) -> bytes:
        """Downloads the entire repository as a ZIP archive. If API 403s, try public archive link."""
        # 1. Try official API (fastest, especially with token)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
        if branch:
            api_url += f"/{branch}"
            
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(api_url, headers=self.headers)
                if response.status_code == 200:
                    return response.content
                    
                # If rate limited (403), we try the public web archive URL
                if response.status_code in [403, 429]:
                    logger.warning(f"GitHub API Rate Limited (403/429). Attempting web-fallback for {owner}/{repo}...")
                    # Note: We guess branch 'master' then 'main' if None
                    fallback_branch = branch or "master"
                    web_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{fallback_branch}.zip"
                    
                    web_res = await client.get(web_url)
                    if web_res.status_code == 200:
                        return web_res.content
                        
                    if not branch: # Try main as second web guess
                        web_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
                        web_res = await client.get(web_url)
                        if web_res.status_code == 200:
                            return web_res.content
                
                logger.error(f"GitHub ZIP Download failed ({response.status_code}) for {api_url}: {response.text}")
                raise Exception(f"Failed to download repo ZIP (branch: {branch or 'default'}): {response.status_code}")
                
            except Exception as e:
                logger.error(f"ZIP Download encountered an error: {e}")
                raise e

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
