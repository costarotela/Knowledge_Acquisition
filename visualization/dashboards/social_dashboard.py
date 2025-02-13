"""
Social media dashboard for visualizing social network analysis.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from core_system.monitoring.monitor import MonitoringSystem
from agents.specialized.social_media_agent import SocialMediaAgent

def render_platform_metrics(monitoring: MonitoringSystem):
    """Render social media platform metrics."""
    st.header("Platform Metrics")
    
    # Create metrics grid
    col1, col2, col3 = st.columns(3)
    
    platforms = ["twitter", "reddit", "linkedin"]
    
    for i, platform in enumerate(platforms):
        with [col1, col2, col3][i]:
            posts = monitoring.get_metric_value(
                "posts_processed",
                {"platform": platform}
            )
            profiles = monitoring.get_metric_value(
                "profiles_analyzed",
                {"platform": platform}
            )
            
            st.metric(
                f"{platform.title()}",
                f"{posts} posts, {profiles} profiles",
                delta=f"+{posts + profiles}" if posts + profiles > 0 else None
            )

def render_engagement_analysis(posts: pd.DataFrame):
    """Render engagement analysis visualization."""
    st.header("Engagement Analysis")
    
    # Calculate engagement metrics
    engagement = posts.groupby("platform").agg({
        "likes": "sum",
        "shares": "sum",
        "comments": "sum",
        "engagement_score": "mean"
    }).fillna(0)
    
    # Create radar chart
    categories = ["Likes", "Shares", "Comments", "Engagement"]
    
    fig = go.Figure()
    
    for platform in engagement.index:
        fig.add_trace(go.Scatterpolar(
            r=[
                engagement.loc[platform, "likes"],
                engagement.loc[platform, "shares"],
                engagement.loc[platform, "comments"],
                engagement.loc[platform, "engagement_score"] * 100
            ],
            theta=categories,
            fill="toself",
            name=platform.title()
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max([
                    engagement["likes"].max(),
                    engagement["shares"].max(),
                    engagement["comments"].max(),
                    engagement["engagement_score"].max() * 100
                ])]
            )
        ),
        showlegend=True,
        title="Platform Engagement Metrics"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_temporal_activity(posts: pd.DataFrame):
    """Render temporal activity visualization."""
    st.header("Temporal Activity")
    
    # Group by time
    hourly_activity = posts.groupby([
        posts["timestamp"].dt.hour,
        "platform"
    ]).size().unstack(fill_value=0)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=hourly_activity.values.T,
        x=hourly_activity.index,
        y=hourly_activity.columns,
        colorscale="Viridis"
    ))
    
    fig.update_layout(
        title="Activity Heatmap by Hour",
        xaxis_title="Hour of Day",
        yaxis_title="Platform",
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_content_analysis(posts: pd.DataFrame):
    """Render content analysis visualization."""
    st.header("Content Analysis")
    
    # Combine all content
    text = " ".join(posts["content"].fillna(""))
    
    # Generate word cloud
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="white"
    ).generate(text)
    
    # Display word cloud
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    
    st.pyplot(fig)
    
    # Hashtag analysis
    if "hashtags" in posts.columns:
        hashtags = []
        for tags in posts["hashtags"]:
            if isinstance(tags, list):
                hashtags.extend(tags)
        
        hashtag_counts = pd.Series(hashtags).value_counts()
        
        fig = px.bar(
            x=hashtag_counts.index[:20],
            y=hashtag_counts.values[:20],
            title="Top 20 Hashtags",
            labels={
                "x": "Hashtag",
                "y": "Frequency"
            }
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_influence_network(profiles: pd.DataFrame):
    """Render influence network visualization."""
    st.header("Influence Network")
    
    # Create network
    G = nx.Graph()
    
    # Add nodes
    for _, profile in profiles.iterrows():
        G.add_node(
            profile["username"],
            platform=profile["platform"],
            followers=profile.get("followers", 0),
            influence=profile.get("influence_score", 0)
        )
    
    # Add edges based on mentions
    for _, post in posts.iterrows():
        if isinstance(post.get("mentions"), list):
            for mention in post["mentions"]:
                if mention in profiles["username"].values:
                    G.add_edge(post["author"], mention)
    
    # Calculate node positions
    pos = nx.spring_layout(G)
    
    # Create network visualization
    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines"
    )
    
    # Add edges
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace["x"] += tuple([x0, x1, None])
        edge_trace["y"] += tuple([y0, y1, None])
    
    # Create node trace
    node_trace = go.Scatter(
        x=[],
        y=[],
        text=[],
        mode="markers",
        hoverinfo="text",
        marker=dict(
            showscale=True,
            colorscale="YlOrRd",
            size=[],
            color=[],
            colorbar=dict(
                thickness=15,
                title="Influence Score",
                xanchor="left",
                titleside="right"
            )
        )
    )
    
    # Add nodes
    for node in G.nodes():
        x, y = pos[node]
        node_trace["x"] += tuple([x])
        node_trace["y"] += tuple([y])
        node_trace["marker"]["size"] += tuple([
            20 + G.nodes[node]["followers"] / 100
        ])
        node_trace["marker"]["color"] += tuple([
            G.nodes[node]["influence"]
        ])
        node_trace["text"] += tuple([
            f"{node} ({G.nodes[node]['platform']})<br>"
            f"Followers: {G.nodes[node]['followers']}<br>"
            f"Influence: {G.nodes[node]['influence']:.2f}"
        ])
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Social Influence Network",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_profile_analysis(profiles: pd.DataFrame):
    """Render profile analysis visualization."""
    st.header("Profile Analysis")
    
    # Platform distribution
    platform_dist = profiles["platform"].value_counts()
    
    fig = px.pie(
        values=platform_dist.values,
        names=platform_dist.index,
        title="Profiles by Platform"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Influence distribution
    if "influence_score" in profiles.columns:
        fig = px.histogram(
            profiles,
            x="influence_score",
            color="platform",
            title="Influence Score Distribution",
            nbins=20
        )
        
        st.plotly_chart(fig, use_container_width=True)

def main():
    """Main dashboard."""
    st.set_page_config(
        page_title="Social Media Dashboard",
        page_icon="🌐",
        layout="wide"
    )
    
    st.title("Social Media Analysis")
    
    # Load data
    monitoring = MonitoringSystem()
    posts = pd.read_csv("data/social/posts.csv")
    profiles = pd.read_csv("data/social/profiles.csv")
    
    # Convert date columns
    posts["timestamp"] = pd.to_datetime(posts["timestamp"])
    
    # Render components
    render_platform_metrics(monitoring)
    
    # Time range filter
    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(
            posts["timestamp"].min(),
            posts["timestamp"].max()
        )
    )
    
    platform_filter = st.sidebar.multiselect(
        "Platforms",
        options=posts["platform"].unique(),
        default=posts["platform"].unique()
    )
    
    # Filter data
    filtered_posts = posts[
        (posts["timestamp"].dt.date >= date_range[0]) &
        (posts["timestamp"].dt.date <= date_range[1]) &
        (posts["platform"].isin(platform_filter))
    ]
    
    filtered_profiles = profiles[
        profiles["platform"].isin(platform_filter)
    ]
    
    # Render visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        render_engagement_analysis(filtered_posts)
        render_content_analysis(filtered_posts)
    
    with col2:
        render_temporal_activity(filtered_posts)
        render_profile_analysis(filtered_profiles)
    
    render_influence_network(filtered_profiles)

if __name__ == "__main__":
    main()
