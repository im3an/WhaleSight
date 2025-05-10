"""
Enhanced container list component for the Docker Dashboard.
Displays comprehensive container information including status, health, and configuration.
"""
import streamlit as st
import pandas as pd

def display_container_list(containers_df: pd.DataFrame):
    """
    Display a list of containers with enhanced info and selection options.
    
    Args:
        containers_df: DataFrame containing container information
    """
    if containers_df.empty:
        st.warning("No containers found")
        return None
    
    # Container status summary
    running_count = len(containers_df[containers_df['status'] == 'running'])
    stopped_count = len(containers_df[containers_df['status'] == 'exited'])
    other_count = len(containers_df) - running_count - stopped_count
    
    # Display container counts by status
    st.subheader("Container Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Running", running_count, delta=None)
    with col2:
        st.metric("Stopped", stopped_count, delta=None)
    with col3:
        st.metric("Other", other_count, delta=None)
    
    # Add filter options
    st.subheader("Container List")
    
    # Create filter tabs
    tab1, tab2, tab3 = st.tabs(["All Containers", "Running Only", "Stopped Only"])
    
    with tab1:
        filtered_containers = containers_df
        display_filtered_containers(filtered_containers, "all")
    
    with tab2:
        running_containers = containers_df[containers_df['status'] == 'running']
        display_filtered_containers(running_containers, "running")
    
    with tab3:
        stopped_containers = containers_df[containers_df['status'] == 'exited']
        display_filtered_containers(stopped_containers, "stopped")
    
    # Return the selected container ID from the active tab
    selected_container_id = st.session_state.get('selected_container_id', None)
    return selected_container_id

def display_filtered_containers(filtered_df: pd.DataFrame, status_type: str):
    """Display containers of a specific status type with filtering options."""
    # Add a search box for filtering containers
    search_term = st.text_input(f"Filter {status_type} containers", "", key=f"search_{status_type}")
    
    # Filter containers based on search term
    if search_term:
        search_results = filtered_df[
            filtered_df['name'].str.contains(search_term, case=False) | 
            filtered_df['image'].str.contains(search_term, case=False)
        ]
    else:
        search_results = filtered_df
    
    if search_results.empty:
        st.info(f"No {status_type} containers match the filter: '{search_term}'")
        return None
    
    # Create a selection widget
    container_options = {row['name']: row['id'] for _, row in search_results.iterrows()}
    
    if container_options:
        selected_container = st.selectbox(
            "Select a container for detailed view:",
            options=list(container_options.keys()),
            key=f"select_{status_type}"
        )
        
        selected_id = container_options[selected_container]
        # Store the selected ID in session state
        st.session_state.selected_container_id = selected_id
        
        # Display the selected container's detailed info
        selected_container_df = search_results[search_results['id'] == selected_id]
        if not selected_container_df.empty:
            display_container_details(selected_container_df.iloc[0])
    
    return None

def display_container_details(container_data):
    """Display detailed information about the selected container."""
    # Container identity
    st.markdown(f"### {container_data['name']}")
    
    # Create tabs for different types of container info
    tabs = st.tabs(["Overview", "Configuration", "Volumes & Networks"])
    
    # Overview tab
    with tabs[0]:
        col1, col2 = st.columns(2)
        
        with col1:
            # Status indicator with color
            status_color = {
                'running': '🟢',
                'exited': '🔴',
                'paused': '🟠',
                'created': '🔵'
            }.get(container_data['status'], '⚪')
            
            st.markdown(f"**Status:** {status_color} {container_data['status']}")
            
            # Health status if available
            if container_data['health'] != 'N/A':
                health_color = {
                    'healthy': '✅',
                    'unhealthy': '❌',
                    'starting': '⏳'
                }.get(container_data['health'], '❓')
                st.markdown(f"**Health:** {health_color} {container_data['health']}")
            
            # Uptime for running containers
            if container_data['status'] == 'running' and container_data['uptime_human'] != 'N/A':
                st.markdown(f"**Uptime:** {container_data['uptime_human']}")
            
            # Exit code for stopped containers
            if container_data['status'] == 'exited' and container_data['exit_code'] is not None:
                exit_status = "Success" if container_data['exit_code'] == 0 else f"Error ({container_data['exit_code']})"
                st.markdown(f"**Exit Code:** {exit_status}")
            
            st.markdown(f"**Restart Count:** {container_data['restart_count']}")
        
        with col2:
            st.markdown(f"**Image:** {container_data['image']}")
            st.markdown(f"**ID:** {container_data['id']}")
            st.markdown(f"**Created:** {container_data['created'][:19].replace('T', ' ')}")
    
    # Configuration tab
    with tabs[1]:
        st.markdown("#### Port Mappings")
        if container_data['ports'] and len(container_data['ports']) > 0:
            for port in container_data['ports']:
                st.code(port)
        else:
            st.text("No port mappings")
        
        st.markdown("#### Network Mode")
        st.code(container_data['network_mode'])
    
    # Volumes tab
    with tabs[2]:
        st.markdown("#### Volumes")
        if container_data['volumes'] and len(container_data['volumes']) > 0:
            for volume in container_data['volumes']:
                st.code(volume)
        else:
            st.text("No volumes mounted")