"""
Social media agent for knowledge extraction from social platforms.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import tweepy
import praw
import linkedin_api
from pydantic import BaseModel

from ..base import BaseAgent
from core_system.pipeline.schemas import ProcessingStage, DataType
from core_system.monitoring.monitor import MonitoringSystem

class SocialPost(BaseModel):
    """Social media post model."""
    platform: str
    post_id: str
    author: str
    content: str
    timestamp: datetime
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    hashtags: List[str] = []
    mentions: List[str] = []
    urls: List[str] = []
    media: List[Dict[str, Any]] = []
    engagement_score: Optional[float] = None

class SocialProfile(BaseModel):
    """Social media profile model."""
    platform: str
    profile_id: str
    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    joined_date: Optional[datetime] = None
    verified: bool = False
    influence_score: Optional[float] = None

class SocialMediaAgent(BaseAgent):
    """Agent for processing social media content."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize social media agent."""
        super().__init__(config)
        
        # Initialize clients
        self.twitter_client = None
        self.reddit_client = None
        self.linkedin_client = None
        
        # Initialize metrics
        self.monitoring.register_metric(
            name="posts_processed",
            metric_type="counter",
            description="Number of social media posts processed",
            labels=["platform"]
        )
        
        self.monitoring.register_metric(
            name="profiles_analyzed",
            metric_type="counter",
            description="Number of social media profiles analyzed",
            labels=["platform"]
        )
    
    async def initialize(self):
        """Initialize agent resources."""
        await super().initialize()
        
        # Initialize Twitter client
        if self.config.get("twitter"):
            auth = tweepy.OAuthHandler(
                self.config["twitter"]["consumer_key"],
                self.config["twitter"]["consumer_secret"]
            )
            auth.set_access_token(
                self.config["twitter"]["access_token"],
                self.config["twitter"]["access_token_secret"]
            )
            self.twitter_client = tweepy.API(auth)
        
        # Initialize Reddit client
        if self.config.get("reddit"):
            self.reddit_client = praw.Reddit(
                client_id=self.config["reddit"]["client_id"],
                client_secret=self.config["reddit"]["client_secret"],
                user_agent=self.config["reddit"]["user_agent"]
            )
        
        # Initialize LinkedIn client
        if self.config.get("linkedin"):
            self.linkedin_client = linkedin_api.Linkedin(
                self.config["linkedin"]["username"],
                self.config["linkedin"]["password"]
            )
    
    async def cleanup(self):
        """Cleanup agent resources."""
        await super().cleanup()
        # Cleanup specific resources
    
    async def _process_extraction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process extraction task."""
        try:
            platform = task.get("platform", "").lower()
            
            if platform == "twitter":
                return await self._process_twitter(task)
            elif platform == "reddit":
                return await self._process_reddit(task)
            elif platform == "linkedin":
                return await self._process_linkedin(task)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
        except Exception as e:
            self.logger.error("Extraction error", error=str(e))
            raise
    
    async def _process_twitter(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process Twitter content."""
        if not self.twitter_client:
            raise ValueError("Twitter client not initialized")
        
        content_type = task.get("type")
        
        if content_type == "post":
            # Get tweet
            tweet_id = task["post_id"]
            tweet = self.twitter_client.get_status(
                tweet_id,
                tweet_mode="extended"
            )
            
            # Create post model
            post = SocialPost(
                platform="twitter",
                post_id=str(tweet.id),
                author=tweet.user.screen_name,
                content=tweet.full_text,
                timestamp=tweet.created_at,
                likes=tweet.favorite_count,
                shares=tweet.retweet_count,
                hashtags=[h["text"] for h in tweet.entities.get("hashtags", [])],
                mentions=[m["screen_name"] for m in tweet.entities.get("user_mentions", [])],
                urls=[u["expanded_url"] for u in tweet.entities.get("urls", [])],
                media=[m for m in tweet.entities.get("media", [])]
            )
            
            # Calculate engagement score
            post.engagement_score = (
                (post.likes or 0) * 1 +
                (post.shares or 0) * 2 +
                len(post.comments or []) * 1.5
            ) / 100
            
            # Update metrics
            self.monitoring.record_metric(
                "posts_processed",
                1,
                {"platform": "twitter"}
            )
            
            return {"post": post.dict()}
            
        elif content_type == "profile":
            # Get user profile
            username = task["username"]
            user = self.twitter_client.get_user(username)
            
            # Create profile model
            profile = SocialProfile(
                platform="twitter",
                profile_id=str(user.id),
                username=user.screen_name,
                name=user.name,
                bio=user.description,
                followers=user.followers_count,
                following=user.friends_count,
                posts_count=user.statuses_count,
                joined_date=user.created_at,
                verified=user.verified
            )
            
            # Calculate influence score
            profile.influence_score = (
                (profile.followers or 0) * 2 +
                (profile.posts_count or 0) * 0.5
            ) / 1000
            
            # Update metrics
            self.monitoring.record_metric(
                "profiles_analyzed",
                1,
                {"platform": "twitter"}
            )
            
            return {"profile": profile.dict()}
        
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    
    async def _process_reddit(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process Reddit content."""
        if not self.reddit_client:
            raise ValueError("Reddit client not initialized")
        
        content_type = task.get("type")
        
        if content_type == "post":
            # Get submission
            post_id = task["post_id"]
            submission = self.reddit_client.submission(id=post_id)
            
            # Create post model
            post = SocialPost(
                platform="reddit",
                post_id=submission.id,
                author=submission.author.name if submission.author else "[deleted]",
                content=submission.selftext,
                timestamp=datetime.fromtimestamp(submission.created_utc),
                likes=submission.score,
                comments=len(submission.comments),
                urls=[submission.url] if submission.url else []
            )
            
            # Calculate engagement score
            post.engagement_score = (
                (post.likes or 0) * 1 +
                len(post.comments or []) * 2
            ) / 100
            
            # Update metrics
            self.monitoring.record_metric(
                "posts_processed",
                1,
                {"platform": "reddit"}
            )
            
            return {"post": post.dict()}
            
        elif content_type == "profile":
            # Get user profile
            username = task["username"]
            redditor = self.reddit_client.redditor(username)
            
            # Create profile model
            profile = SocialProfile(
                platform="reddit",
                profile_id=username,
                username=username,
                karma=redditor.link_karma + redditor.comment_karma,
                joined_date=datetime.fromtimestamp(redditor.created_utc)
            )
            
            # Update metrics
            self.monitoring.record_metric(
                "profiles_analyzed",
                1,
                {"platform": "reddit"}
            )
            
            return {"profile": profile.dict()}
        
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    
    async def _process_linkedin(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn content."""
        if not self.linkedin_client:
            raise ValueError("LinkedIn client not initialized")
        
        content_type = task.get("type")
        
        if content_type == "post":
            # Get post
            post_id = task["post_id"]
            post_data = self.linkedin_client.get_post(post_id)
            
            # Create post model
            post = SocialPost(
                platform="linkedin",
                post_id=post_id,
                author=post_data["author"],
                content=post_data["content"],
                timestamp=datetime.fromtimestamp(post_data["time"]),
                likes=post_data.get("likes_count"),
                comments=post_data.get("comments_count"),
                shares=post_data.get("shares_count")
            )
            
            # Update metrics
            self.monitoring.record_metric(
                "posts_processed",
                1,
                {"platform": "linkedin"}
            )
            
            return {"post": post.dict()}
            
        elif content_type == "profile":
            # Get profile
            profile_id = task["profile_id"]
            profile_data = self.linkedin_client.get_profile(profile_id)
            
            # Create profile model
            profile = SocialProfile(
                platform="linkedin",
                profile_id=profile_id,
                name=profile_data.get("name"),
                headline=profile_data.get("headline"),
                connections=profile_data.get("connections"),
                company=profile_data.get("company"),
                position=profile_data.get("position")
            )
            
            # Update metrics
            self.monitoring.record_metric(
                "profiles_analyzed",
                1,
                {"platform": "linkedin"}
            )
            
            return {"profile": profile.dict()}
        
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    
    async def _process_validation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process validation task."""
        content = task["content"]
        content_type = task.get("type")
        
        if content_type == "post":
            post = SocialPost(**content["post"])
            # Validate post data
            if not post.content:
                raise ValueError("Empty post content")
            
            return {
                "valid": True,
                "post": post.dict()
            }
            
        elif content_type == "profile":
            profile = SocialProfile(**content["profile"])
            # Validate profile data
            if not profile.username:
                raise ValueError("Empty username")
            
            return {
                "valid": True,
                "profile": profile.dict()
            }
        
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    
    async def _process_storage(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process storage task."""
        content = task["content"]
        content_type = task.get("type")
        
        # Store in appropriate format/location
        if content_type == "post":
            filename = f"data/social/posts/{content['post']['platform']}_{content['post']['post_id']}.json"
        else:
            filename = f"data/social/profiles/{content['profile']['platform']}_{content['profile']['profile_id']}.json"
        
        # TODO: Implement proper storage
        with open(filename, "w") as f:
            json.dump(content, f)
        
        return {
            "stored": True,
            "location": filename
        }
