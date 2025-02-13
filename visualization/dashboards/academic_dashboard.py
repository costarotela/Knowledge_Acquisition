"""
Academic research dashboard for visualizing paper analysis.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import pandas as pd
from datetime import datetime, timedelta

from core_system.monitoring.monitor import MonitoringSystem
from agents.specialized.academic_agent import AcademicAgent

def render_paper_metrics(monitoring: MonitoringSystem):
    """Render paper processing metrics."""
    st.header("Paper Processing Metrics")
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        papers_processed = monitoring.get_metric_value(
            "papers_processed",
            {"source": "arxiv"}
        )
        st.metric(
            "Papers Processed (arXiv)",
            papers_processed,
            delta="+1" if papers_processed > 0 else None
        )
    
    with col2:
        papers_scholar = monitoring.get_metric_value(
            "papers_processed",
            {"source": "scholar"}
        )
        st.metric(
            "Papers Processed (Scholar)",
            papers_scholar,
            delta="+1" if papers_scholar > 0 else None
        )
    
    with col3:
        citations = monitoring.get_metric_value("citations_extracted")
        st.metric(
            "Citations Extracted",
            citations,
            delta=f"+{citations}" if citations > 0 else None
        )

def render_citation_network(papers: pd.DataFrame):
    """Render citation network visualization."""
    st.header("Citation Network")
    
    # Create network
    G = nx.DiGraph()
    
    # Add nodes and edges
    for _, paper in papers.iterrows():
        G.add_node(
            paper["title"],
            citations=paper["citations"],
            year=paper["published"].year
        )
        
        # Add citation edges
        if isinstance(paper.get("references"), list):
            for ref in paper["references"]:
                if ref in papers["title"].values:
                    G.add_edge(paper["title"], ref)
    
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
            colorscale="YlGnBu",
            size=[],
            color=[],
            colorbar=dict(
                thickness=15,
                title="Citations",
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
            20 + G.nodes[node]["citations"] * 2
        ])
        node_trace["marker"]["color"] += tuple([
            G.nodes[node]["citations"]
        ])
        node_trace["text"] += tuple([
            f"{node}<br>"
            f"Citations: {G.nodes[node]['citations']}<br>"
            f"Year: {G.nodes[node]['year']}"
        ])
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Paper Citation Network",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_topic_analysis(papers: pd.DataFrame):
    """Render topic analysis visualization."""
    st.header("Topic Analysis")
    
    # Extract topics/keywords
    topics = []
    for _, paper in papers.iterrows():
        if isinstance(paper.get("keywords"), list):
            topics.extend(paper["keywords"])
    
    # Count topic frequency
    topic_counts = pd.Series(topics).value_counts()
    
    # Create treemap
    fig = px.treemap(
        names=topic_counts.index,
        parents=["Topics"] * len(topic_counts),
        values=topic_counts.values,
        title="Research Topics Distribution"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_temporal_analysis(papers: pd.DataFrame):
    """Render temporal analysis visualization."""
    st.header("Temporal Analysis")
    
    # Group by year
    yearly_papers = papers.groupby(
        papers["published"].dt.year
    ).size()
    
    # Create line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=yearly_papers.index,
        y=yearly_papers.values,
        mode="lines+markers",
        name="Papers Published"
    ))
    
    # Add citation trends if available
    if "citations" in papers.columns:
        yearly_citations = papers.groupby(
            papers["published"].dt.year
        )["citations"].mean()
        
        fig.add_trace(go.Scatter(
            x=yearly_citations.index,
            y=yearly_citations.values,
            mode="lines+markers",
            name="Average Citations",
            yaxis="y2"
        ))
        
        fig.update_layout(
            yaxis2=dict(
                title="Average Citations",
                overlaying="y",
                side="right"
            )
        )
    
    fig.update_layout(
        title="Publication and Citation Trends",
        xaxis_title="Year",
        yaxis_title="Number of Papers",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_venue_analysis(papers: pd.DataFrame):
    """Render publication venue analysis."""
    st.header("Publication Venues")
    
    if "venue" in papers.columns:
        # Count papers by venue
        venue_counts = papers["venue"].value_counts()
        
        # Create bar chart
        fig = px.bar(
            x=venue_counts.index,
            y=venue_counts.values,
            title="Papers by Publication Venue",
            labels={
                "x": "Venue",
                "y": "Number of Papers"
            }
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_author_analysis(papers: pd.DataFrame):
    """Render author analysis visualization."""
    st.header("Author Analysis")
    
    # Extract all authors
    authors = []
    for _, paper in papers.iterrows():
        if isinstance(paper.get("authors"), list):
            authors.extend(paper["authors"])
    
    # Count author frequency
    author_counts = pd.Series(authors).value_counts()
    
    # Create horizontal bar chart
    fig = px.bar(
        x=author_counts.values[:20],
        y=author_counts.index[:20],
        orientation="h",
        title="Top 20 Contributing Authors",
        labels={
            "x": "Number of Papers",
            "y": "Author"
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main dashboard."""
    st.set_page_config(
        page_title="Academic Research Dashboard",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("Academic Research Analysis")
    
    # Load data
    monitoring = MonitoringSystem()
    papers = pd.read_csv("data/processed/papers.csv")
    
    # Convert date columns
    papers["published"] = pd.to_datetime(papers["published"])
    
    # Render components
    render_paper_metrics(monitoring)
    
    # Time range filter
    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(
            papers["published"].min(),
            papers["published"].max()
        )
    )
    
    # Filter data
    filtered_papers = papers[
        (papers["published"].dt.date >= date_range[0]) &
        (papers["published"].dt.date <= date_range[1])
    ]
    
    # Render visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        render_citation_network(filtered_papers)
        render_temporal_analysis(filtered_papers)
    
    with col2:
        render_topic_analysis(filtered_papers)
        render_venue_analysis(filtered_papers)
    
    render_author_analysis(filtered_papers)

if __name__ == "__main__":
    main()
