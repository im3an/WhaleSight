"""
Docker stats collector module that interfaces with the Docker API
to collect container resource usage metrics.

This enhanced module collects comprehensive container metrics including:
- Container status and health
- Detailed CPU, memory, network, and storage metrics
- Container configuration and operational data
"""
import docker
import time
import pandas as pd
import datetime
from typing import Dict, List, Any, Tuple, Optional

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
        """Get list of running containers with enhanced info."""
        if not self.is_connected:
            return []
        
        containers = []
        try:
            # Get all containers, not just running ones
            for container in self.client.containers.list(all=True):
                # Calculate uptime for running containers
                uptime = None
                restart_count = 0
                health_status = "N/A"
                exit_code = None
                
                if container.status == "running":
                    start_time = container.attrs.get('State', {}).get('StartedAt')
                    if start_time:
                        start_time = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        uptime = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds()

                # Get restart count
                restart_count = container.attrs.get('RestartCount', 0)
                
                # Get health status if available
                health = container.attrs.get('State', {}).get('Health', {})
                if health:
                    health_status = health.get('Status', 'N/A')
                
                # Get exit code for stopped containers
                if container.status == "exited":
                    exit_code = container.attrs.get('State', {}).get('ExitCode')
                
                # Get container info including environment variables and ports
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                port_mappings = []
                for container_port, host_ports in ports.items() if ports else {}:
                    if host_ports:
                        for port_mapping in host_ports:
                            port_mappings.append(f"{port_mapping['HostIp']}:{port_mapping['HostPort']}->{container_port}")
                
                # Get volume information
                volumes = container.attrs.get('Mounts', [])
                volume_info = []
                for volume in volumes:
                    volume_info.append(f"{volume.get('Source')} -> {volume.get('Destination')}")
                
                containers.append({
                    'id': container.id[:12],  # Short ID
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'status': container.status,
                    'health': health_status,
                    'uptime': uptime,
                    'uptime_human': self._format_uptime(uptime) if uptime else 'N/A',
                    'created': container.attrs['Created'],
                    'restart_count': restart_count,
                    'exit_code': exit_code,
                    'network_mode': container.attrs.get('HostConfig', {}).get('NetworkMode', 'N/A'),
                    'ports': port_mappings,
                    'volumes': volume_info
                })
        except Exception as e:
            print(f"Error getting container list: {e}")
        
        return containers
        
    def _format_uptime(self, seconds: float) -> str:
        """Format seconds into a human-readable uptime string."""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get detailed stats for a specific container with enhanced metrics."""
        if not self.is_connected:
            return {}
        
        try:
            container = self.client.containers.get(container_id)
            
            # Skip if container is not running
            if container.status != "running":
                return {
                    'id': container_id,
                    'name': container.name,
                    'status': container.status,
                    'running': False,
                    'timestamp': time.time()
                }
            
            stats = container.stats(stream=False)  # Get a single stats snapshot
            
            # Check if we have valid stats data
            if not stats or 'cpu_stats' not in stats or 'precpu_stats' not in stats:
                return {
                    'id': container_id,
                    'name': container.name,
                    'status': 'unknown',
                    'running': False,
                    'timestamp': time.time()
                }
            
            # Process CPU stats - add safety checks
            cpu_delta = 0
            system_delta = 0
            
            if 'cpu_usage' in stats['cpu_stats'] and 'cpu_usage' in stats['precpu_stats'] and \
               'total_usage' in stats['cpu_stats']['cpu_usage'] and 'total_usage' in stats['precpu_stats']['cpu_usage']:
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            
            if 'system_cpu_usage' in stats['cpu_stats'] and 'system_cpu_usage' in stats['precpu_stats']:
                system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            
            online_cpus = stats['cpu_stats'].get('online_cpus', 
                          len(stats['cpu_stats'].get('cpu_usage', {}).get('percpu_usage', [1])))
            
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
            
            # CPU throttling stats
            cpu_throttled_periods = 0
            cpu_throttled_time = 0
            if 'throttling_data' in stats.get('cpu_stats', {}):
                cpu_throttled_periods = stats['cpu_stats']['throttling_data'].get('throttled_periods', 0)
                cpu_throttled_time = stats['cpu_stats']['throttling_data'].get('throttled_time', 0)
            
            # Process memory stats - add safety checks
            mem_stats = stats.get('memory_stats', {})
            mem_usage = mem_stats.get('usage', 0)
            mem_limit = mem_stats.get('limit', 1)  # Prevent division by zero
            mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0
            
            # Get cache memory if available
            mem_cache = mem_stats.get('stats', {}).get('cache', 0)
            
            # Get swap memory if available
            mem_swap = mem_stats.get('stats', {}).get('swap', 0)
            
            # Memory failures (OOM)
            oom_kills = mem_stats.get('stats', {}).get('oom_kills', 0)
            
            # Process network stats if available
            network_rx = 0
            network_tx = 0
            network_rx_dropped = 0
            network_tx_dropped = 0
            network_rx_errors = 0
            network_tx_errors = 0
            
            if 'networks' in stats:
                for interface, data in stats['networks'].items():
                    network_rx += data.get('rx_bytes', 0)
                    network_tx += data.get('tx_bytes', 0)
                    network_rx_dropped += data.get('rx_dropped', 0)
                    network_tx_dropped += data.get('tx_dropped', 0)
                    network_rx_errors += data.get('rx_errors', 0)
                    network_tx_errors += data.get('tx_errors', 0)
            
            # Process block I/O stats if available
            block_read = 0
            block_write = 0
            io_time = 0
            io_wait_time = 0
            
            blkio_stats = stats.get('blkio_stats', {})
            
            # Read/write bytes
            if 'io_service_bytes_recursive' in blkio_stats and blkio_stats['io_service_bytes_recursive'] is not None:
                for entry in blkio_stats['io_service_bytes_recursive']:
                    if entry.get('op') == 'Read':
                        block_read += entry.get('value', 0)
                    elif entry.get('op') == 'Write':
                        block_write += entry.get('value', 0)
            
            # Service time
            if 'io_service_time_recursive' in blkio_stats and blkio_stats['io_service_time_recursive'] is not None:
                for entry in blkio_stats['io_service_time_recursive']:
                    io_time += entry.get('value', 0)
            
            # Wait time
            if 'io_wait_time_recursive' in blkio_stats and blkio_stats['io_wait_time_recursive'] is not None:
                for entry in blkio_stats['io_wait_time_recursive']:
                    io_wait_time += entry.get('value', 0)
            
            # Get PIDs
            pids = stats.get('pids_stats', {}).get('current', 0)
            
            return {
                'id': container_id,
                'name': container.name,
                'status': container.status,
                'running': True,
                
                # CPU metrics
                'cpu_percent': round(cpu_percent, 2),
                'cpu_throttled_periods': cpu_throttled_periods,
                'cpu_throttled_time': cpu_throttled_time,
                'cpu_system_percent': round((system_delta / online_cpus) * 100.0, 2) if system_delta > 0 and online_cpus > 0 else 0,
                
                # Memory metrics
                'mem_usage': round(mem_usage / (1024 * 1024), 2),  # MB
                'mem_limit': round(mem_limit / (1024 * 1024), 2),  # MB
                'mem_percent': round(mem_percent, 2),
                'mem_cache': round(mem_cache / (1024 * 1024), 2) if mem_cache else 0,  # MB
                'mem_swap': round(mem_swap / (1024 * 1024), 2) if mem_swap else 0,  # MB
                'oom_kills': oom_kills,
                
                # Network metrics
                'network_rx': network_rx,
                'network_tx': network_tx,
                'network_rx_dropped': network_rx_dropped,
                'network_tx_dropped': network_tx_dropped,
                'network_rx_errors': network_rx_errors,
                'network_tx_errors': network_tx_errors,
                
                # Block I/O metrics
                'block_read': block_read,
                'block_write': block_write,
                'io_time': io_time,
                'io_wait_time': io_wait_time,
                
                # Process metrics
                'pids': pids,
                
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"Error getting stats for container {container_id}: {e}")
            return {
                'id': container_id,
                'name': container_id[:12],  # Use ID as name if we can't get the actual name
                'status': 'error',
                'running': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_all_container_stats(self) -> pd.DataFrame:
        """Get stats for all running containers and return as DataFrame."""
        if not self.is_connected:
            return pd.DataFrame()
        
        all_stats = []
        containers = self.get_containers()
        
        for container in containers:
            # Only get stats for running containers
            if container['status'] == 'running':
                stats = self.get_container_stats(container['id'])
                if stats:
                    all_stats.append(stats)
        
        if not all_stats:
            return pd.DataFrame()
        
        return pd.DataFrame(all_stats)
    
    def get_container_logs(self, container_id: str, lines: int = 50) -> List[str]:
        """Get the most recent logs from a container."""
        if not self.is_connected:
            return []
        
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8').splitlines()
            return logs
        except Exception as e:
            print(f"Error getting logs for container {container_id}: {e}")
            return []
    
    def get_container_events(self, container_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events for a specific container."""
        if not self.is_connected:
            return []
        
        try:
            # Get system events filtered by this container
            events = []
            for event in self.client.events(decode=True, filters={'container': container_id}):
                events.append({
                    'time': event['time'],
                    'type': event['Type'],
                    'action': event['Action'],
                    'id': event['Actor']['ID'][:12],
                    'attributes': event['Actor'].get('Attributes', {})
                })
                if len(events) >= limit:
                    break
            return events
        except Exception as e:
            print(f"Error getting events for container {container_id}: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall Docker system stats."""
        if not self.is_connected:
            return {}
        
        try:
            # Get Docker info
            info = self.client.info()
            
            # Get system disk usage
            usage = self.client.df()
            
            # Calculate total image and container sizes
            total_image_size = sum(image['Size'] for image in usage.get('Images', []))
            total_container_size = sum(container['SizeRw'] for container in usage.get('Containers', []) if 'SizeRw' in container)
            
            return {
                'containers_running': info.get('ContainersRunning', 0),
                'containers_paused': info.get('ContainersPaused', 0),
                'containers_stopped': info.get('ContainersStopped', 0),
                'images': info.get('Images', 0),
                'docker_version': info.get('ServerVersion', 'Unknown'),
                'total_memory': info.get('MemTotal', 0) / (1024 * 1024 * 1024),  # GB
                'cpu_count': info.get('NCPU', 0),
                'kernel_version': info.get('KernelVersion', 'Unknown'),
                'operating_system': info.get('OperatingSystem', 'Unknown'),
                'total_image_size': total_image_size / (1024 * 1024 * 1024),  # GB
                'total_container_size': total_container_size / (1024 * 1024 * 1024),  # GB
            }
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return {}
    
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
