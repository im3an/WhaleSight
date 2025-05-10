"""
Docker Container Resource Usage Dashboard
A Streamlit app for monitoring Docker container resource usage.
"""
import streamlit as st
import time
import pandas as pd
from docker_stats import DockerStats
from dashboard import container_list, metrics, charts

# Initialize session state for storing container history
if 'container_histories' not in st.session_state:
    st.session_state.container_histories = {}  # Dict to store history by container ID

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Initialize Docker stats collector
@st.cache_resource
def get_docker_stats():
    return DockerStats()

docker_stats = get_docker_stats()

# Page config
st.set_page_config(
    page_title="Docker Container Dashboard",
    page_icon="🐳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dashboard title
st.title("🐳 Docker Container Resource Dashboard")

# Check Docker connection
if not docker_stats.test_docker_connection():
    st.error("❌ Cannot connect to Docker. Make sure Docker is running.")
    st.stop()

# Sidebar controls
st.sidebar.header("Dashboard Controls")

# Refresh interval selector
refresh_interval = st.sidebar.slider(
    "Refresh Interval (seconds)",
    min_value=2,
    max_value=60,
    value=5
)

# Refresh button
refresh = st.sidebar.button("Refresh Now")

# Max history data points to keep
history_limit = st.sidebar.slider(
    "History Data Points",
    min_value=10,
    max_value=500,
    value=100
)

# Auto-refresh logic
if (time.time() - st.session_state.last_refresh) > refresh_interval or refresh:
    with st.spinner("Fetching container stats..."):
        # Get all container stats
        all_stats_df = docker_stats.get_all_container_stats()
        
        # Update container histories
        for _, row in all_stats_df.iterrows():
            container_id = row['id']
            container_stats = row.to_dict()
            
            # Initialize history for new containers
            if container_id not in st.session_state.container_histories:
                st.session_state.container_histories[container_id] = []
                
            # Add current stats to history
            st.session_state.container_histories[container_id].append(container_stats)
            
            # Limit history size
            if len(st.session_state.container_histories[container_id]) > history_limit:
                st.session_state.container_histories[container_id] = st.session_state.container_histories[container_id][-history_limit:]
        
        st.session_state.last_refresh = time.time()
    
    # Get container list for selection
    containers_df = pd.DataFrame(docker_stats.get_containers())
else:
    # Use cached container list if not refreshing
    containers_df = pd.DataFrame(docker_stats.get_containers())
    all_stats_df = docker_stats.get_all_container_stats()

# Display system overview metrics
if 'all_stats_df' in locals() and not all_stats_df.empty:
    metrics.display_summary_metrics(all_stats_df)
    
    # Display system-wide charts
    st.subheader("System Resource Usage")
    charts.create_system_overview_chart(all_stats_df)

# Container selection and detailed view
if not containers_df.empty:
    st.markdown("---")
    selected_container_id = container_list.display_container_list(containers_df)
    
    if selected_container_id:
        st.markdown("---")
        
        # Display detailed metrics for selected container
        if selected_container_id in st.session_state.container_histories:
            container_history = st.session_state.container_histories[selected_container_id]
            latest_stats = container_history[-1] if container_history else {}
            
            metrics.display_container_metrics(latest_stats, container_history)
            charts.create_resource_usage_charts(container_history)
        else:
            st.info(f"Waiting for stats data for container {selected_container_id}...")
else:
    st.warning("No running containers found")

# Display last refresh time
st.sidebar.caption(f"Last refreshed: {time.strftime('%H:%M:%S')}")
st.sidebar.caption(f"Next auto-refresh in: {refresh_interval - int(time.time() - st.session_state.last_refresh)} seconds")

# About section in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.info(
    """
    **Docker Container Resource Dashboard**
    
    Monitor resource usage of your Docker containers in real-time.
    
    GitHub: [Your Repository URL]
    """
)