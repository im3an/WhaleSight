"""
Docker stats collector module that interfaces with the Docker API
to collect container resource usage metrics.
"""
import docker
import time
import pandas as pd
from typing import Dict, List, Any

class DockerStats:
    """Class to collect and process Docker container statistics."""
    
    def __init__(self):
        """Initialize Docker client connection."""
        try:
            self.client = docker.from_env()
            self.is_connected = True
        except Exception as e:
            print(f"Error connecting to Docker: {e}")
            self.is_connected = False
    
    def get_containers(self) -> List[Dict[str, Any]]:
        """Get list of running containers with basic info."""
        if not self.is_connected:
            return []
        
        containers = []
        try:
            for container in self.client.containers.list():
                containers.append({
                    'id': container.id[:12],  # Short ID
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'status': container.status,
                    'created': container.attrs['Created']
                })
        except Exception as e:
            print(f"Error getting container list: {e}")
        
        return containers
    
    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get detailed stats for a specific container."""
        if not self.is_connected:
            return {}
        
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)  # Get a single stats snapshot
            
            # Process CPU stats
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            online_cpus = stats['cpu_stats'].get('online_cpus', len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1])))
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
            
            # Process memory stats
            mem_usage = stats['memory_stats']['usage']
            mem_limit = stats['memory_stats']['limit']
            mem_percent = (mem_usage / mem_limit) * 100.0
            
            # Process network stats if available
            network_rx = 0
            network_tx = 0
            if 'networks' in stats:
                for interface, data in stats['networks'].items():
                    network_rx += data['rx_bytes']
                    network_tx += data['tx_bytes']
            
            # Process block I/O stats if available
            block_read = 0
            block_write = 0
            if 'blkio_stats' in stats and 'io_service_bytes_recursive' in stats['blkio_stats']:
                for entry in stats['blkio_stats']['io_service_bytes_recursive']:
                    if entry['op'] == 'Read':
                        block_read += entry['value']
                    elif entry['op'] == 'Write':
                        block_write += entry['value']
            
            return {
                'id': container_id,
                'name': container.name,
                'cpu_percent': round(cpu_percent, 2),
                'mem_usage': round(mem_usage / (1024 * 1024), 2),  # MB
                'mem_limit': round(mem_limit / (1024 * 1024), 2),  # MB
                'mem_percent': round(mem_percent, 2),
                'network_rx': network_rx,
                'network_tx': network_tx,
                'block_read': block_read,
                'block_write': block_write,
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"Error getting stats for container {container_id}: {e}")
            return {}
    
    def get_all_container_stats(self) -> pd.DataFrame:
        """Get stats for all running containers and return as DataFrame."""
        if not self.is_connected:
            return pd.DataFrame()
        
        all_stats = []
        containers = self.get_containers()
        
        for container in containers:
            stats = self.get_container_stats(container['id'])
            if stats:
                all_stats.append(stats)
        
        if not all_stats:
            return pd.DataFrame()
        
        return pd.DataFrame(all_stats)
    
    def test_docker_connection(self) -> bool:
        """Test if Docker connection is working."""
        if not self.is_connected:
            return False
        
        try:
            self.client.ping()
            return True
        except:
            return False

# For testing the module directly
if __name__ == "__main__":
    docker_stats = DockerStats()
    if docker_stats.test_docker_connection():
        print("Connected to Docker successfully")
        containers = docker_stats.get_containers()
        print(f"Found {len(containers)} containers")
        
        stats_df = docker_stats.get_all_container_stats()
        print(stats_df)
    else:
        print("Failed to connect to Docker")