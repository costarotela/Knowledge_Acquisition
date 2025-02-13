"""
Specialized agent for GitHub repository analysis and knowledge extraction.
"""
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import asyncio
from datetime import datetime
import base64
from pathlib import Path
import re

from ..base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult

logger = logging.getLogger(__name__)

class GitHubAgent(KnowledgeAgent):
    """Agent specialized in extracting knowledge from GitHub repositories."""
    
    def __init__(self, *args, **kwargs):
        """Initialize GitHub agent."""
        super().__init__(*args, **kwargs)
        
        # GitHub settings
        self.api_token = self.config.get("github_token")
        self.api_base = "https://api.github.com"
        self.max_files = self.config.get("max_files", 100)
        self.excluded_files = self.config.get("excluded_files", [
            "node_modules", "__pycache__", ".git",
            "*.pyc", "*.pyo", "*.pyd", "*.so"
        ])
        
        # Analysis settings
        self.analyze_commits = self.config.get("analyze_commits", True)
        self.analyze_issues = self.config.get("analyze_issues", True)
        self.analyze_docs = self.config.get("analyze_docs", True)
        
        # Initialize session
        self.session = None
    
    async def initialize(self) -> bool:
        """Initialize agent resources."""
        try:
            # Create aiohttp session with GitHub token
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {self.api_token}"
            }
            self.session = aiohttp.ClientSession(headers=headers)
            return await super().initialize()
        except Exception as e:
            logger.error(f"Error initializing GitHub agent: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.session:
            await self.session.close()
        await super().cleanup()
    
    async def _process_extraction(self, task: Task) -> TaskResult:
        """Process GitHub repository extraction."""
        try:
            url = task.input_data["source_url"]
            extraction_type = task.input_data["extraction_type"]
            
            # Parse repository info
            owner, repo = self._parse_github_url(url)
            if not owner or not repo:
                return TaskResult(
                    success=False,
                    error="Invalid GitHub URL"
                )
            
            # Extract based on type
            if extraction_type == "code_analysis":
                knowledge = await self._extract_code_knowledge(owner, repo)
            elif extraction_type == "documentation":
                knowledge = await self._extract_documentation(owner, repo)
            elif extraction_type == "activity":
                knowledge = await self._extract_activity(owner, repo)
            else:
                return TaskResult(
                    success=False,
                    error=f"Unsupported extraction type: {extraction_type}"
                )
            
            if not knowledge:
                return TaskResult(
                    success=False,
                    error="Failed to extract knowledge"
                )
            
            # Store knowledge
            success = await self._store_knowledge(
                knowledge["items"],
                knowledge["confidence_scores"]
            )
            
            if not success:
                return TaskResult(
                    success=False,
                    error="Failed to store knowledge"
                )
            
            return TaskResult(
                success=True,
                data=knowledge,
                metrics={
                    "files_analyzed": knowledge["metadata"]["files_analyzed"],
                    "total_code_size": knowledge["metadata"]["total_code_size"],
                    "avg_confidence": sum(knowledge["confidence_scores"].values()) / len(knowledge["confidence_scores"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in GitHub extraction: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _extract_code_knowledge(
        self,
        owner: str,
        repo: str
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from repository code."""
        try:
            # Get repository contents
            contents = await self._get_repository_contents(owner, repo)
            if not contents:
                return None
            
            knowledge_items = []
            confidence_scores = {}
            total_size = 0
            files_analyzed = 0
            
            # Process each file
            for file_info in contents:
                if files_analyzed >= self.max_files:
                    break
                
                if not self._should_analyze_file(file_info["path"]):
                    continue
                
                # Get file content
                content = await self._get_file_content(owner, repo, file_info["path"])
                if not content:
                    continue
                
                # Analyze code
                analysis = await self._analyze_code_file(content, file_info)
                if analysis:
                    item_index = len(knowledge_items)
                    knowledge_items.append(analysis["item"])
                    confidence_scores[f"item_{item_index}"] = analysis["confidence"]
                    total_size += len(content)
                    files_analyzed += 1
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores,
                "metadata": {
                    "files_analyzed": files_analyzed,
                    "total_code_size": total_size,
                    "repository": f"{owner}/{repo}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting code knowledge: {e}")
            return None
    
    async def _extract_documentation(
        self,
        owner: str,
        repo: str
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from repository documentation."""
        try:
            knowledge_items = []
            confidence_scores = {}
            
            # Get README
            readme = await self._get_readme(owner, repo)
            if readme:
                knowledge_items.append({
                    "type": "documentation",
                    "subtype": "readme",
                    "content": readme["content"],
                    "path": "README.md",
                    "metadata": {
                        "size": readme["size"],
                        "last_updated": readme["last_updated"]
                    }
                })
                confidence_scores["item_0"] = 0.9
            
            # Get Wiki pages if available
            wiki_pages = await self._get_wiki_pages(owner, repo)
            for i, page in enumerate(wiki_pages):
                knowledge_items.append({
                    "type": "documentation",
                    "subtype": "wiki",
                    "content": page["content"],
                    "path": page["path"],
                    "metadata": {
                        "title": page["title"],
                        "last_updated": page["last_updated"]
                    }
                })
                confidence_scores[f"item_{i + 1}"] = 0.85
            
            # Get API documentation
            api_docs = await self._get_api_docs(owner, repo)
            for i, doc in enumerate(api_docs):
                knowledge_items.append({
                    "type": "documentation",
                    "subtype": "api",
                    "content": doc["content"],
                    "path": doc["path"],
                    "metadata": {
                        "version": doc.get("version"),
                        "endpoints": doc.get("endpoints", [])
                    }
                })
                confidence_scores[f"item_{len(wiki_pages) + i + 1}"] = 0.95
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores,
                "metadata": {
                    "files_analyzed": len(knowledge_items),
                    "total_size": sum(item["metadata"]["size"] for item in knowledge_items if "size" in item["metadata"]),
                    "repository": f"{owner}/{repo}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting documentation: {e}")
            return None
    
    async def _extract_activity(
        self,
        owner: str,
        repo: str
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from repository activity."""
        try:
            knowledge_items = []
            confidence_scores = {}
            item_index = 0
            
            # Get commit history
            if self.analyze_commits:
                commits = await self._get_commits(owner, repo)
                commit_analysis = self._analyze_commits(commits)
                knowledge_items.append({
                    "type": "activity",
                    "subtype": "commits",
                    "content": commit_analysis["summary"],
                    "metadata": {
                        "total_commits": len(commits),
                        "contributors": commit_analysis["contributors"],
                        "activity_pattern": commit_analysis["pattern"]
                    }
                })
                confidence_scores[f"item_{item_index}"] = 0.9
                item_index += 1
            
            # Get issues and PRs
            if self.analyze_issues:
                issues = await self._get_issues(owner, repo)
                issue_analysis = self._analyze_issues(issues)
                knowledge_items.append({
                    "type": "activity",
                    "subtype": "issues",
                    "content": issue_analysis["summary"],
                    "metadata": {
                        "open_issues": issue_analysis["open"],
                        "closed_issues": issue_analysis["closed"],
                        "labels": issue_analysis["labels"]
                    }
                })
                confidence_scores[f"item_{item_index}"] = 0.85
                item_index += 1
            
            # Get release information
            releases = await self._get_releases(owner, repo)
            if releases:
                release_analysis = self._analyze_releases(releases)
                knowledge_items.append({
                    "type": "activity",
                    "subtype": "releases",
                    "content": release_analysis["summary"],
                    "metadata": {
                        "total_releases": len(releases),
                        "latest_version": release_analysis["latest"],
                        "release_pattern": release_analysis["pattern"]
                    }
                })
                confidence_scores[f"item_{item_index}"] = 0.95
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores,
                "metadata": {
                    "repository": f"{owner}/{repo}",
                    "analysis_date": datetime.now().isoformat(),
                    "components_analyzed": len(knowledge_items)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting activity: {e}")
            return None
    
    async def _get_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = ""
    ) -> List[Dict[str, Any]]:
        """Get repository contents recursively."""
        try:
            contents = []
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return contents
                
                data = await response.json()
                
                if isinstance(data, list):
                    for item in data:
                        if item["type"] == "file":
                            contents.append(item)
                        elif item["type"] == "dir":
                            subcontents = await self._get_repository_contents(
                                owner, repo, item["path"]
                            )
                            contents.extend(subcontents)
            
            return contents
            
        except Exception as e:
            logger.error(f"Error getting repository contents: {e}")
            return []
    
    async def _get_file_content(
        self,
        owner: str,
        repo: str,
        path: str
    ) -> Optional[str]:
        """Get content of a specific file."""
        try:
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if data["encoding"] == "base64":
                    return base64.b64decode(data["content"]).decode("utf-8")
                
                return None
            
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None
    
    def _should_analyze_file(self, path: str) -> bool:
        """Check if file should be analyzed."""
        try:
            # Check against excluded patterns
            for pattern in self.excluded_files:
                if "*" in pattern:
                    if Path(path).match(pattern):
                        return False
                elif pattern in path:
                    return False
            
            # Check file extension
            ext = Path(path).suffix.lower()
            return ext in [".py", ".js", ".java", ".cpp", ".h", ".cs", ".go", ".rs"]
            
        except Exception:
            return False
    
    async def _analyze_code_file(
        self,
        content: str,
        file_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a code file."""
        try:
            # Extract code structure
            structure = self._extract_code_structure(content)
            
            # Calculate metrics
            metrics = self._calculate_code_metrics(content)
            
            # Create knowledge item
            item = {
                "type": "code",
                "path": file_info["path"],
                "language": self._detect_language(file_info["path"]),
                "structure": structure,
                "metrics": metrics,
                "metadata": {
                    "size": file_info["size"],
                    "sha": file_info["sha"],
                    "last_updated": file_info.get("last_updated")
                }
            }
            
            # Calculate confidence
            confidence = self._calculate_code_confidence(metrics)
            
            return {
                "item": item,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error analyzing code file: {e}")
            return None
    
    def _extract_code_structure(self, content: str) -> Dict[str, Any]:
        """Extract code structure (classes, functions, etc.)."""
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "global_variables": []
        }
        
        try:
            lines = content.split("\n")
            
            # Simple regex-based extraction
            class_pattern = r"class\s+(\w+)"
            function_pattern = r"(?:def|function)\s+(\w+)"
            import_pattern = r"(?:import|from|require)\s+(.+)"
            
            for line in lines:
                # Extract classes
                class_match = re.search(class_pattern, line)
                if class_match:
                    structure["classes"].append(class_match.group(1))
                
                # Extract functions
                func_match = re.search(function_pattern, line)
                if func_match:
                    structure["functions"].append(func_match.group(1))
                
                # Extract imports
                import_match = re.search(import_pattern, line)
                if import_match:
                    structure["imports"].append(import_match.group(1).strip())
            
            return structure
            
        except Exception as e:
            logger.error(f"Error extracting code structure: {e}")
            return structure
    
    def _calculate_code_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate code metrics."""
        try:
            lines = content.split("\n")
            
            # Basic metrics
            metrics = {
                "total_lines": len(lines),
                "code_lines": 0,
                "comment_lines": 0,
                "blank_lines": 0,
                "complexity": 0
            }
            
            in_multiline_comment = False
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    metrics["blank_lines"] += 1
                    continue
                
                # Handle comments
                if line.startswith("#") or line.startswith("//"):
                    metrics["comment_lines"] += 1
                elif "/*" in line and "*/" in line:
                    metrics["comment_lines"] += 1
                elif "/*" in line:
                    in_multiline_comment = True
                    metrics["comment_lines"] += 1
                elif "*/" in line:
                    in_multiline_comment = False
                    metrics["comment_lines"] += 1
                elif in_multiline_comment:
                    metrics["comment_lines"] += 1
                else:
                    metrics["code_lines"] += 1
                
                # Simple complexity metric
                if any(keyword in line for keyword in ["if", "for", "while", "case"]):
                    metrics["complexity"] += 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating code metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_code_confidence(self, metrics: Dict[str, Any]) -> float:
        """Calculate confidence score for code analysis."""
        try:
            score = 1.0
            
            # Check code size
            if metrics["code_lines"] < 10:
                score *= 0.7
            elif metrics["code_lines"] > 1000:
                score *= 0.8
            
            # Check documentation
            doc_ratio = metrics["comment_lines"] / max(metrics["code_lines"], 1)
            if doc_ratio < 0.1:
                score *= 0.9
            elif doc_ratio > 0.4:
                score *= 0.95
            
            # Check complexity
            if metrics["complexity"] > 20:
                score *= 0.8
            
            return max(0.1, min(1.0, score))
            
        except Exception:
            return 0.5
    
    def _detect_language(self, path: str) -> str:
        """Detect programming language from file path."""
        ext = Path(path).suffix.lower()
        
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".java": "Java",
            ".cpp": "C++",
            ".h": "C/C++",
            ".cs": "C#",
            ".go": "Go",
            ".rs": "Rust"
        }
        
        return language_map.get(ext, "Unknown")
    
    def _parse_github_url(self, url: str) -> tuple:
        """Parse GitHub URL into owner and repository."""
        try:
            # Handle different URL formats
            patterns = [
                r"github\.com/([^/]+)/([^/]+)",
                r"api\.github\.com/repos/([^/]+)/([^/]+)",
                r"raw\.githubusercontent\.com/([^/]+)/([^/]+)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1), match.group(2)
            
            return None, None
            
        except Exception:
            return None, None
