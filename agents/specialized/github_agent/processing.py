"""
Processing logic for GitHub repository analysis.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
import asyncio
from pathlib import Path

from .schemas import (
    RepoContext, CodeFragment, IssueInfo,
    CommitInfo, RepositoryKnowledge
)

logger = logging.getLogger(__name__)

class GitHubProcessor:
    """Processor for GitHub repository analysis."""
    
    def __init__(self, api_token: str, session: Optional[aiohttp.ClientSession] = None):
        """Initialize processor."""
        self.api_token = api_token
        self.api_base = "https://api.github.com"
        self.session = session or aiohttp.ClientSession(headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {api_token}"
        })
    
    async def analyze_repository(
        self,
        owner: str,
        repo: str,
        analysis_config: Dict[str, Any]
    ) -> RepositoryKnowledge:
        """Analyze a GitHub repository."""
        try:
            # Get repository context
            context = await self._get_repo_context(owner, repo)
            
            # Parallel analysis tasks
            tasks = []
            
            if analysis_config.get("analyze_code", True):
                tasks.append(self._analyze_code(owner, repo))
            
            if analysis_config.get("analyze_issues", True):
                tasks.append(self._analyze_issues(owner, repo))
                
            if analysis_config.get("analyze_commits", True):
                tasks.append(self._analyze_commits(owner, repo))
            
            # Execute tasks
            results = await asyncio.gather(*tasks)
            
            # Aggregate results
            knowledge = RepositoryKnowledge(
                context=context,
                key_files=results[0] if analysis_config.get("analyze_code") else [],
                important_issues=results[1] if analysis_config.get("analyze_issues") else [],
                significant_commits=results[2] if analysis_config.get("analyze_commits") else []
            )
            
            # Generate insights
            knowledge.insights = await self._generate_insights(knowledge)
            
            # Calculate confidence
            knowledge.confidence_score = self._calculate_confidence(knowledge)
            
            return knowledge
            
        except Exception as e:
            logger.error(f"Error analyzing repository {owner}/{repo}: {str(e)}")
            raise
    
    async def _get_repo_context(self, owner: str, repo: str) -> RepoContext:
        """Get repository context information."""
        async with self.session.get(f"{self.api_base}/repos/{owner}/{repo}") as response:
            data = await response.json()
            
            return RepoContext(
                owner=owner,
                name=repo,
                description=data.get("description"),
                stars=data.get("stargazers_count", 0),
                forks=data.get("forks_count", 0),
                last_update=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                topics=data.get("topics", []),
                languages=await self._get_languages(owner, repo)
            )
    
    async def _analyze_code(self, owner: str, repo: str) -> List[CodeFragment]:
        """Analyze repository code."""
        fragments = []
        
        # Get default branch
        async with self.session.get(f"{self.api_base}/repos/{owner}/{repo}") as response:
            data = await response.json()
            default_branch = data["default_branch"]
        
        # Get tree
        async with self.session.get(
            f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        ) as response:
            tree = await response.json()
            
            for item in tree["tree"]:
                if item["type"] == "blob" and self._is_code_file(item["path"]):
                    # Get file content
                    async with self.session.get(item["url"]) as file_response:
                        file_data = await file_response.json()
                        
                        fragments.append(CodeFragment(
                            path=item["path"],
                            content=file_data["content"],
                            language=self._detect_language(item["path"]),
                            start_line=1,
                            end_line=len(file_data["content"].splitlines()),
                            commit_hash=file_data.get("sha", ""),
                            last_modified=datetime.now(),  # TODO: Get real last modified
                            author="",  # TODO: Get real author
                            relevance_score=self._calculate_file_relevance(item["path"], file_data["content"])
                        ))
        
        return fragments
    
    async def _analyze_issues(self, owner: str, repo: str) -> List[IssueInfo]:
        """Analyze repository issues."""
        issues = []
        
        async with self.session.get(
            f"{self.api_base}/repos/{owner}/{repo}/issues?state=all"
        ) as response:
            data = await response.json()
            
            for issue in data:
                issues.append(IssueInfo(
                    number=issue["number"],
                    title=issue["title"],
                    body=issue["body"] or "",
                    state=issue["state"],
                    author=issue["user"]["login"],
                    created_at=datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")),
                    closed_at=datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00")) if issue["closed_at"] else None,
                    labels=[label["name"] for label in issue["labels"]],
                    comments=[]  # TODO: Get comments if needed
                ))
        
        return issues
    
    async def _analyze_commits(self, owner: str, repo: str) -> List[CommitInfo]:
        """Analyze repository commits."""
        commits = []
        
        async with self.session.get(
            f"{self.api_base}/repos/{owner}/{repo}/commits"
        ) as response:
            data = await response.json()
            
            for commit in data:
                commits.append(CommitInfo(
                    hash=commit["sha"],
                    message=commit["commit"]["message"],
                    author=commit["commit"]["author"]["name"],
                    date=datetime.fromisoformat(commit["commit"]["author"]["date"].replace("Z", "+00:00")),
                    files_changed=[],  # TODO: Get changed files if needed
                    stats={},  # TODO: Get stats if needed
                    relevance_score=self._calculate_commit_relevance(commit["commit"]["message"])
                ))
        
        return commits
    
    async def _get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get repository languages."""
        async with self.session.get(
            f"{self.api_base}/repos/{owner}/{repo}/languages"
        ) as response:
            return await response.json()
    
    async def _generate_insights(self, knowledge: RepositoryKnowledge) -> List[Dict[str, Any]]:
        """Generate insights from repository knowledge."""
        insights = []
        
        # Example insights
        if knowledge.context.stars > 1000:
            insights.append({
                "type": "popularity",
                "content": f"Popular repository with {knowledge.context.stars} stars"
            })
        
        if len(knowledge.important_issues) > 0:
            open_issues = sum(1 for i in knowledge.important_issues if i.state == "open")
            insights.append({
                "type": "maintenance",
                "content": f"Active maintenance with {open_issues} open issues"
            })
        
        return insights
    
    def _calculate_confidence(self, knowledge: RepositoryKnowledge) -> float:
        """Calculate confidence score for repository knowledge."""
        scores = []
        
        # Context completeness
        context_score = 0.8 if knowledge.context.description else 0.5
        scores.append(context_score)
        
        # Code analysis
        if knowledge.key_files:
            scores.append(sum(f.relevance_score for f in knowledge.key_files) / len(knowledge.key_files))
        
        # Commit analysis
        if knowledge.significant_commits:
            scores.append(sum(c.relevance_score for c in knowledge.significant_commits) / len(knowledge.significant_commits))
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _is_code_file(self, path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {".py", ".js", ".java", ".cpp", ".go", ".rs", ".ts"}
        return Path(path).suffix in code_extensions
    
    def _detect_language(self, path: str) -> str:
        """Detect programming language from file path."""
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".java": "Java",
            ".cpp": "C++",
            ".go": "Go",
            ".rs": "Rust",
            ".ts": "TypeScript"
        }
        return ext_to_lang.get(Path(path).suffix, "Unknown")
    
    def _calculate_file_relevance(self, path: str, content: str) -> float:
        """Calculate relevance score for a file."""
        # Simple heuristic based on file location and size
        score = 0.5
        
        if "test" in path.lower():
            score -= 0.1
        if "example" in path.lower():
            score += 0.1
        if len(content) > 1000:
            score += 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_commit_relevance(self, message: str) -> float:
        """Calculate relevance score for a commit."""
        # Simple heuristic based on commit message
        score = 0.5
        
        if "fix" in message.lower():
            score += 0.1
        if "feature" in message.lower():
            score += 0.2
        if "refactor" in message.lower():
            score += 0.1
        
        return min(max(score, 0.0), 1.0)
