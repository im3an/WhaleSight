"""
Metrics display component for the Docker Dashboard.
Provides comprehensive visualization of container resource usage.
"""
import streamlit as st
import pandas as pd
import time
import datetime
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

def display_system_overview(system_stats: Dict[str, Any]):
    """
    Display Docker system-wide statistics.
    
    Args:
        system_stats: Dictionary containing system-wide Docker stats
    """
    if not system_stats:
        return
        
    st.subheader("Docker System Overview")
    
    # Create two rows of metrics to display system information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Containers", 
            f"{system_stats.get('containers_running', 0)} running",
            delta=f"{system_stats.get('containers_stopped', 0)} stopped"
        )
    
    with col2:
        st.metric(
            "Images", 
            system_stats.get('images', 0),
            delta=f"{system_stats.get('total_image_size', 0):.2f} GB"
        )
    
    with col3:
        st.metric(
            "Resources", 
            f"{system_stats.get('cpu_count', 0)} CPUs",
            delta=f"{system_stats.get('total_memory', 0):.1f} GB RAM"
        )
        
    # Version information as a caption
    st.caption(f"Docker {system_stats.get('docker_version', 'Unknown')} on {system_stats.get('operating_system', 'Unknown')} with kernel {system_stats.get('kernel_version', 'Unknown')}")

def display_container_status(containers: List[Dict[str, Any]]):
    """
    Display container status summary.
    
    Args:
        containers: List of container information dictionaries
    """
    if not containers:
        st.info("No containers found")
        return
        
    # Count container statuses
    running = sum(1 for c in containers if c['status'] == 'running')
    stopped = sum(1 for c in containers if c['status'] == 'exited')
    other = len(containers) - running - stopped
    
    # Count container health
    healthy = sum(1 for c in containers if c.get('health') == 'healthy')
    unhealthy = sum(1 for c in containers if c.get('health') == 'unhealthy')
    
    st.subheader("Container Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Running", 
            running,
            delta=f"{(running/len(containers)*100):.1f}%" if containers else None
        )
    
    with col2:
        st.metric(
            "Stopped", 
            stopped,
            delta=None
        )
    
    with col3:
        st.metric(
            "Health", 
            f"{healthy} healthy",
            delta=f"{unhealthy} unhealthy" if unhealthy > 0 else None,
            delta_color="inverse"
        )

def display_summary_metrics(stats_df: pd.DataFrame):
    """
    Display summary metrics for all containers.
    
    Args:
        stats_df: DataFrame containing container stats
    """
    if stats_df.empty:
        return
    
    st.subheader("Resource Utilization")
    
    # Calculate summary metrics
    total_cpu = stats_df['cpu_percent'].sum()
    total_mem_usage = stats_df['mem_usage'].sum()
    total_mem_limit = stats_df['mem_limit'].mean() * len(stats_df)  # Approximate total available
    
    if total_mem_limit > 0:
        total_mem_percent = (total_mem_usage / total_mem_limit) * 100
    else:
        total_mem_percent = 0
    
    # Calculate network and I/O totals
    total_network_rx = stats_df['network_rx'].sum()
    total_network_tx = stats_df['network_tx'].sum()
    total_block_read = stats_df['block_read'].sum()
    total_block_write = stats_df['block_write'].sum()
    
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
            "Containers", 
            len(stats_df),
            delta=None
        )
        
    # Second row for network and I/O metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Network I/O", 
            f"{format_bytes(total_network_rx + total_network_tx)}",
            delta=f"↓{format_bytes(total_network_rx)} ↑{format_bytes(total_network_tx)}"
        )
    
    with col2:
        st.metric(
            "Disk I/O", 
            f"{format_bytes(total_block_read + total_block_write)}",
            delta=f"R:{format_bytes(total_block_read)} W:{format_bytes(total_block_write)}"
        )
    
    with col3:
        total_pids = stats_df['pids'].sum() if 'pids' in stats_df.columns else 0
        st.metric(
            "Processes", 
            f"{int(total_pids)}",
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
    
    if not stats.get('running', False):
        st.info(f"Container '{stats.get('name', 'Unknown')}' is not running")
        return
    
    st.subheader(f"Container Metrics: {stats.get('name', 'Unknown')}")
    
    # Create three rows of metrics for comprehensive view
    
    # First row: CPU metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "CPU Usage", 
            f"{stats['cpu_percent']:.2f}%",
            delta=None
        )
    
    with col2:
        if 'cpu_throttled_periods' in stats and stats['cpu_throttled_periods'] > 0:
            throttle_info = f"{stats['cpu_throttled_periods']} periods"
        else:
            throttle_info = "No throttling"
            
        st.metric(
            "CPU Throttling", 
            throttle_info,
            delta=None
        )
    
    with col3:
        st.metric(
            "System CPU", 
            f"{stats.get('cpu_system_percent', 0):.2f}%",
            delta=None
        )
    
    # Second row: Memory metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Memory Usage", 
            f"{stats['mem_usage']:.2f} MB",
            delta=f"{stats['mem_percent']:.1f}% of limit"
        )
    
    with col2:
        mem_limit_gb = stats['mem_limit'] / 1024  # Convert to GB
        st.metric(
            "Memory Limit", 
            f"{mem_limit_gb:.2f} GB",
            delta=None
        )
    
    with col3:
        cache_mb = stats.get('mem_cache', 0)
        swap_mb = stats.get('mem_swap', 0)
        st.metric(
            "Cache/Swap", 
            f"{cache_mb:.2f} MB cache",
            delta=f"{swap_mb:.2f} MB swap" if swap_mb > 0 else None
        )
    
    # Third row: Network metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Network I/O", 
            f"↓{format_bytes(stats['network_rx'])} ↑{format_bytes(stats['network_tx'])}",
            delta=None
        )
    
    with col2:
        net_errors = stats.get('network_rx_errors', 0) + stats.get('network_tx_errors', 0)
        net_dropped = stats.get('network_rx_dropped', 0) + stats.get('network_tx_dropped', 0)
        
        st.metric(
            "Network Issues", 
            f"{net_errors} errors",
            delta=f"{net_dropped} dropped" if net_dropped > 0 else None,
            delta_color="inverse" if net_dropped > 0 else "normal"
        )
    
    with col3:
        st.metric(
            "Block I/O", 
            f"R: {format_bytes(stats['block_read'])}",
            delta=f"W: {format_bytes(stats['block_write'])}"
        )
    
    # Fourth row: Other important metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Processes", 
            stats.get('pids', 0),
            delta=None
        )
    
    with col2:
        oom_kills = stats.get('oom_kills', 0)
        st.metric(
            "OOM Kills", 
            oom_kills,
            delta="Warning: Memory issues" if oom_kills > 0 else None,
            delta_color="inverse" if oom_kills > 0 else "normal"
        )
        
    # Add timestamp of when these stats were collected
    st.caption(f"Last updated: {time.strftime('%H:%M:%S', time.localtime(stats['timestamp']))}")

def display_container_details(container: Dict[str, Any]):
    """
    Display operational details for a container.
    
    Args:
        container: Dictionary containing container information
    """
    if not container:
        return
        
    st.subheader("Container Configuration")
    
    # Display container details in an expandable section
    with st.expander("Container Details", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Basic Information**")
            st.markdown(f"**ID:** `{container.get('id', 'Unknown')}`")
            st.markdown(f"**Name:** `{container.get('name', 'Unknown')}`")
            st.markdown(f"**Image:** `{container.get('image', 'Unknown')}`")
            st.markdown(f"**Status:** `{container.get('status', 'Unknown')}`")
            st.markdown(f"**Health:** `{container.get('health', 'N/A')}`")
            st.markdown(f"**Created:** `{container.get('created', 'Unknown')}`")
        
        with col2:
            st.markdown("**Runtime Information**")
            st.markdown(f"**Uptime:** `{container.get('uptime_human', 'N/A')}`")
            st.markdown(f"**Restart Count:** `{container.get('restart_count', 0)}`")
            if container.get('exit_code') is not None:
                st.markdown(f"**Exit Code:** `{container.get('exit_code')}`")
            st.markdown(f"**Network Mode:** `{container.get('network_mode', 'N/A')}`")
    
    # Port mappings if available
    if container.get('ports'):
        with st.expander("Port Mappings", expanded=False):
            for port in container.get('ports', []):
                st.code(port)
    
    # Volume mappings if available
    if container.get('volumes'):
        with st.expander("Volume Mappings", expanded=False):
            for volume in container.get('volumes', []):
                st.code(volume)

def display_container_logs_and_events(logs: List[str], events: List[Dict[str, Any]]):
    """
    Display container logs and events.
    
    Args:
        logs: List of log lines
        events: List of event dictionaries
    """
    tab1, tab2 = st.tabs(["Logs", "Events"])
    
    with tab1:
        if logs:
            st.subheader("Container Logs")
            log_text = "\n".join(logs)
            st.text_area("Recent logs", log_text, height=300)
        else:
            st.info("No logs available")
    
    with tab2:
        if events:
            st.subheader("Container Events")
            for event in events:
                timestamp = datetime.datetime.fromtimestamp(event.get('time', 0))
                st.markdown(f"**{timestamp.strftime('%Y-%m-%d %H:%M:%S')}** - {event.get('action', 'Unknown action')}")
                if event.get('attributes'):
                    with st.expander("Details", expanded=False):
                        for key, value in event.get('attributes', {}).items():
                            st.markdown(f"**{key}:** {value}")
                st.divider()
        else:
            st.info("No events available")
