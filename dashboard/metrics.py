"""
Metrics display component for the Docker Dashboard.
"""
import streamlit as st
import pandas as pd
import time
from typing import Dict, List, Any

def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"

def display_summary_metrics(stats_df: pd.DataFrame):
    """
    Display summary metrics for all containers.
    
    Args:
        stats_df: DataFrame containing container stats
    """
    if stats_df.empty:
        return
    
    st.subheader("System Overview")
    
    # Calculate summary metrics
    total_cpu = stats_df['cpu_percent'].sum()
    total_mem_usage = stats_df['mem_usage'].sum()
    total_mem_limit = stats_df['mem_limit'].mean() * len(stats_df)  # Approximate total available
    
    if total_mem_limit > 0:
        total_mem_percent = (total_mem_usage / total_mem_limit) * 100
    else:
        total_mem_percent = 0
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total CPU Usage", 
            f"{total_cpu:.2f}%",
            delta=None
        )
    
    with col2:
        st.metric(
            "Memory Usage", 
            f"{total_mem_usage:.2f} MB",
            delta=f"{total_mem_percent:.1f}% of limit"
        )
    
    with col3:
        st.metric(
            "Active Containers", 
            len(stats_df),
            delta=None
        )

def display_container_metrics(stats: Dict[str, Any], history: List[Dict[str, Any]]):
    """
    Display detailed metrics for a specific container.
    
    Args:
        stats: Dictionary containing the latest container stats
        history: List of historical stats dictionaries for the container
    """
    if not stats:
        st.warning("No stats available for this container")
        return
    
    st.subheader(f"Container Metrics: {stats.get('name', 'Unknown')}")
    
    # Create two rows of metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "CPU Usage", 
            f"{stats['cpu_percent']:.2f}%",
            delta=None
        )
    
    with col2:
        st.metric(
            "Memory Usage", 
            f"{stats['mem_usage']:.2f} MB",
            delta=f"{stats['mem_percent']:.1f}% of limit"
        )
    
    with col3:
        mem_limit_gb = stats['mem_limit'] / 1024  # Convert to GB
        st.metric(
            "Memory Limit", 
            f"{mem_limit_gb:.2f} GB",
            delta=None
        )
    
    # Second row for network and block I/O
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Network In", 
            format_bytes(stats['network_rx']),
            delta=None
        )
    
    with col2:
        st.metric(
            "Network Out", 
            format_bytes(stats['network_tx']),
            delta=None
        )
    
    with col3:
        st.metric(
            "Block I/O", 
            f"R: {format_bytes(stats['block_read'])} / W: {format_bytes(stats['block_write'])}",
            delta=None
        )
        
    # Add timestamp of when these stats were collected
    st.caption(f"Last updated: {time.strftime('%H:%M:%S', time.localtime(stats['timestamp']))}")