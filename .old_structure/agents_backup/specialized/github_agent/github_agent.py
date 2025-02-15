"""
Specialized agent for GitHub repository analysis and knowledge extraction.
"""
from typing import Dict, Any, Optional
import logging
from pathlib import Path

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings

from ..base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult
from .processing import GitHubProcessor
from .reasoning import GitHubReasoning
from .knowledge_manager import GitHubKnowledgeManager
from .schemas import RepositoryKnowledge

logger = logging.getLogger(__name__)

class GitHubAgent(KnowledgeAgent):
    """Agent specialized in extracting knowledge from GitHub repositories."""
    
    def __init__(self, *args, **kwargs):
        """Initialize GitHub agent."""
        super().__init__(*args, **kwargs)
        
        # GitHub settings
        self.api_token = self.config.get("github_token")
        self.max_files = self.config.get("max_files", 100)
        self.excluded_files = self.config.get("excluded_files", [
            "node_modules", "__pycache__", ".git",
            "*.pyc", "*.pyo", "*.pyd", "*.so"
        ])
        
        # Analysis settings
        self.analyze_commits = self.config.get("analyze_commits", True)
        self.analyze_issues = self.config.get("analyze_issues", True)
        self.analyze_docs = self.config.get("analyze_docs", True)
        
        # Initialize components
        self.processor = None
        self.reasoning = None
        self.knowledge_manager = None
        
        # LLM settings
        self.llm = ChatOpenAI(
            model_name=self.config.get("model_name", "gpt-4"),
            temperature=self.config.get("temperature", 0)
        )
        self.embeddings = OpenAIEmbeddings()
    
    async def initialize(self) -> bool:
        """Initialize agent resources."""
        try:
            # Create processor
            self.processor = GitHubProcessor(self.api_token)
            
            # Create reasoning engine
            self.reasoning = GitHubReasoning(self.llm)
            
            # Create knowledge manager
            vector_store_path = Path(self.config.get(
                "vector_store_path",
                "./knowledge_store/github"
            ))
            vector_store_path.mkdir(parents=True, exist_ok=True)
            
            self.knowledge_manager = GitHubKnowledgeManager(
                str(vector_store_path),
                self.embeddings
            )
            
            return await super().initialize()
            
        except Exception as e:
            logger.error(f"Error initializing GitHub agent: {str(e)}")
            return False
    
    async def process_task(self, task: Task) -> TaskResult:
        """Process a task."""
        try:
            # Extract repository info from task
            repo_info = self._extract_repo_info(task)
            if not repo_info:
                return TaskResult(
                    success=False,
                    error="No repository information found in task"
                )
            
            # Configure analysis
            analysis_config = {
                "analyze_code": self.analyze_commits,
                "analyze_issues": self.analyze_issues,
                "analyze_commits": self.analyze_commits,
                "max_files": self.max_files,
                "excluded_files": self.excluded_files
            }
            
            # 1. Process repository data
            knowledge = await self.processor.analyze_repository(
                repo_info["owner"],
                repo_info["repo"],
                analysis_config
            )
            
            # 2. Apply reasoning
            # Generate hypotheses
            context_analysis = await self.reasoning.analyze_repository_context(
                knowledge.context
            )
            
            # Evaluate code
            code_evaluation = await self.reasoning.evaluate_code_quality(
                knowledge.key_files
            )
            
            # Analyze patterns
            dev_patterns = await self.reasoning.analyze_development_patterns(
                knowledge.significant_commits,
                knowledge.important_issues
            )
            
            # Synthesize knowledge
            synthesis = await self.reasoning.synthesize_knowledge(
                context_analysis,
                code_evaluation,
                dev_patterns
            )
            
            # 3. Store and validate knowledge
            storage_success = await self.knowledge_manager.store_repository_knowledge(
                knowledge,
                synthesis
            )
            
            if not storage_success:
                logger.warning("Failed to store repository knowledge")
            
            # Validate key insights
            validated_insights = []
            for insight in synthesis["insights"]:
                validation = await self.knowledge_manager.validate_knowledge({
                    "type": "insight",
                    "content": insight["content"],
                    "confidence": insight["confidence"]
                })
                
                if validation["valid"]:
                    validated_insights.append({
                        **insight,
                        "validation": validation
                    })
            
            # Create final result
            result = {
                "repository": knowledge.dict(),
                "analysis": {
                    "context": context_analysis,
                    "code_quality": code_evaluation,
                    "development": dev_patterns
                },
                "synthesis": {
                    **synthesis,
                    "validated_insights": validated_insights
                }
            }
            
            # Calculate confidence
            confidence = (
                code_evaluation["quality_score"] * 0.3 +
                dev_patterns["health_score"] * 0.3 +
                sum(i["confidence"] for i in validated_insights) / 
                (len(validated_insights) or 1) * 0.4
            )
            
            return TaskResult(
                success=True,
                result=result,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    def _extract_repo_info(self, task: Task) -> Optional[Dict[str, str]]:
        """Extract repository information from task."""
        try:
            # Try to extract from URL
            if "url" in task.input:
                url = task.input["url"]
                parts = url.strip("/").split("/")
                if "github.com" in parts:
                    idx = parts.index("github.com")
                    if len(parts) > idx + 2:
                        return {
                            "owner": parts[idx + 1],
                            "repo": parts[idx + 2]
                        }
            
            # Try to extract from owner/repo format
            if "repository" in task.input:
                repo = task.input["repository"]
                if "/" in repo:
                    owner, repo = repo.split("/")
                    return {"owner": owner, "repo": repo}
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting repo info: {str(e)}")
            return None
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.processor and self.processor.session:
            await self.processor.session.close()
        await super().cleanup()
