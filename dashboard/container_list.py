"""
Container list component for the Docker Dashboard.
"""
import streamlit as st
import pandas as pd

def display_container_list(containers_df: pd.DataFrame):
    """
    Display a list of containers with basic info and selection options.
    
    Args:
        containers_df: DataFrame containing container information
    """
    if containers_df.empty:
        st.warning("No running containers found")
        return None
    
    st.subheader("Running Containers")
    
    # Add a search box for filtering containers
    search_term = st.text_input("Filter containers", "")
    
    # Filter containers based on search term
    if search_term:
        filtered_df = containers_df[
            containers_df['name'].str.contains(search_term, case=False) | 
            containers_df['image'].str.contains(search_term, case=False)
        ]
    else:
        filtered_df = containers_df
        
    if filtered_df.empty:
        st.info(f"No containers match the filter: '{search_term}'")
        return None
    
    # Create a selection widget
    container_options = {row['name']: row['id'] for _, row in filtered_df.iterrows()}
    selected_container = st.selectbox(
        "Select a container for detailed view:",
        options=list(container_options.keys()),
        index=0
    )
    
    selected_id = container_options[selected_container]
    
    # Display the selected container's basic info
    selected_container_df = filtered_df[filtered_df['id'] == selected_id]
    if not selected_container_df.empty:
        container_data = selected_container_df.iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Selected Container", container_data['name'])
            st.text(f"Image: {container_data['image']}")
        with col2:
            st.text(f"Status: {container_data['status']}")
            st.text(f"ID: {container_data['id']}")
    
    return selected_id