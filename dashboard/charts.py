"""
Charts component for the Docker Dashboard.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import time

def create_resource_usage_charts(history: List[Dict[str, Any]]):
    """
    Create CPU and memory usage charts for a specific container.
    
    Args:
        history: List of historical stats dictionaries for the container
    """
    if not history:
        st.info("Waiting for data to display charts...")
        return
    
    # Convert history to DataFrame
    df = pd.DataFrame(history)
    
    # Convert timestamp to datetime for better x-axis
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Create CPU usage chart
    cpu_fig = px.line(
        df, 
        x='datetime', 
        y='cpu_percent',
        title='CPU Usage Over Time',
        labels={'cpu_percent': 'CPU Usage (%)', 'datetime': 'Time'}
    )
    cpu_fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified"
    )
    cpu_fig.update_yaxes(range=[0, max(100, df['cpu_percent'].max() * 1.1)])
    st.plotly_chart(cpu_fig, use_container_width=True)
    
    # Create memory usage chart
    mem_fig = px.line(
        df, 
        x='datetime', 
        y=['mem_usage', 'mem_limit'],
        title='Memory Usage Over Time',
        labels={'value': 'Memory (MB)', 'datetime': 'Time', 'variable': 'Metric'},
        color_discrete_map={'mem_usage': 'blue', 'mem_limit': 'red'}
    )
    mem_fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    st.plotly_chart(mem_fig, use_container_width=True)

def create_system_overview_chart(stats_df: pd.DataFrame):
    """
    Create a bar chart showing resource usage across all containers.
    
    Args:
        stats_df: DataFrame containing all container stats
    """
    if stats_df.empty:
        return
    
    # Create CPU usage comparison chart
    cpu_fig = px.bar(
        stats_df,
        x='name',
        y='cpu_percent',
        title='CPU Usage by Container',
        labels={'cpu_percent': 'CPU Usage (%)', 'name': 'Container'},
        color='cpu_percent',
        color_continuous_scale='Viridis'
    )
    cpu_fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=100),
        coloraxis_colorbar=dict(title='CPU %')
    )
    cpu_fig.update_xaxes(tickangle=45)
    st.plotly_chart(cpu_fig, use_container_width=True)
    
    # Create memory usage comparison chart
    mem_fig = px.bar(
        stats_df,
        x='name',
        y='mem_percent',
        title='Memory Usage by Container (% of Limit)',
        labels={'mem_percent': 'Memory Usage (%)', 'name': 'Container'},
        color='mem_percent',
        color_continuous_scale='Viridis'
    )
    mem_fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=100),
        coloraxis_colorbar=dict(title='Memory %')
    )
    mem_fig.update_xaxes(tickangle=45)
    st.plotly_chart(mem_fig, use_container_width=True)