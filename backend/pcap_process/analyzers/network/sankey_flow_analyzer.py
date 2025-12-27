#!/usr/bin/env python3

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)

class SankeyFlowAnalyzer:
    """Sankey flow analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.min_flow_threshold = 4096  # Increase minimum flow threshold (bytes) - reduce small flow noise
        self.max_links = 80   # Reduce maximum links - improve performance
        self.max_nodes = 40   # Reduce maximum nodes - improve performance

    def _adaptive_dbscan_parameters(self, data_points):
        """
        Adaptive DBSCAN parameter selection based on K-distance graph
        """
        if len(data_points) < 4:
            return 0.9, 4  # Fall back to default values
        
        # Calculate K-distance graph
        k = min(4, len(data_points) - 1)  # Adaptive K value
        nbrs = NearestNeighbors(n_neighbors=k).fit(data_points)
        distances, _ = nbrs.kneighbors(data_points)
        
        # Get k-distance (distance of k-th neighbor)
        k_distances = distances[:, k-1]
        k_distances_sorted = np.sort(k_distances)[::-1]  # Sort in descending order
        
        # Use least squares polynomial curve fitting method to determine Eps parameter
        try:
            x = np.arange(len(k_distances_sorted))
            # 15-degree polynomial fitting
            poly_coeffs = np.polyfit(x, k_distances_sorted, min(15, len(x)-1))
            fitted_curve = np.polyval(poly_coeffs, x)
            
            # Find knee point (knee point)
            # Calculate the second derivative of the curve to find the knee point
            second_derivative = np.diff(fitted_curve, 2)
            if len(second_derivative) > 0:
                knee_index = np.argmax(np.abs(second_derivative))
                eps = k_distances_sorted[min(knee_index, len(k_distances_sorted)-1)]
            else:
                eps = np.median(k_distances_sorted)
                
        except Exception as e:
            logger.warning(f"Polynomial fitting failed, using median method: {e}")
            eps = np.median(k_distances_sorted)
        
        # Use mathematical expectation method to generate MinPts parameter
        neighborhood_counts = []
        for point in data_points:
            # Calculate the number of neighbors within eps distance
            distances_from_point = np.linalg.norm(data_points - point, axis=1)
            neighbors_count = np.sum(distances_from_point <= eps)
            neighborhood_counts.append(neighbors_count)
        
        # Calculate MinPts based on mathematical expectation, add noise to reduce threshold
        if neighborhood_counts:
            min_pts = max(4, int(np.mean(neighborhood_counts) * 0.8))
        else:
            min_pts = 4
        
        logger.info(f"Adaptive DBSCAN parameters: eps={eps:.3f}, min_pts={min_pts} (based on {len(data_points)} data points)")
        return eps, min_pts

    def _standardize_device_classification(self, ip: str, device_type: Optional[str] = None, 
                                         is_local_device: bool = False) -> str:
        """
        Unified device classification logic - ensure the same classification for the same IP in any context
        """
        # Priority 1: If it is a registered device, use the device type
        if device_type and device_type.lower() not in ['unknown', 'null', '', 'none']:
            return device_type.title()
        
        # Priority 2: If it is a registered device but the type is unknown, mark it as IoT Device
        if is_local_device and device_type and device_type.lower() == 'unknown':
            return 'IoT Device'
        
        # Priority 3: Classify based on IP address pattern
        if ip.startswith('192.168.'):
            return 'Local Device'
        elif ip.startswith('10.'):
            return 'Internal Device'  
        elif ip.startswith('172.'):
            return 'Private Device'
        elif ip in ['8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1']:
            return 'DNS Server'
        elif ip.startswith('169.254.'):
            return 'Link-Local Device'
        else:
            return 'Internet Server'

    async def analyze_device_to_location_flow(self, experiment_id: str, time_window: str = "24h", 
                                            group_by: str = "device_type") -> Dict[str, Any]:
        """
        Analyze the flow distribution from devices to locations
        Only count external traffic to avoid duplicate with device-to-device
        Use adaptive DBSCAN clustering
        Use device resolution service to get the correct device information
        """
        try:
            from backend.services.ip_geolocation_service import IPGeolocationService
            from database.services.device_resolution_service import ConfigurableDeviceResolutionService
            
            geolocation_service = IPGeolocationService(self.db_manager)
            resolution_service = ConfigurableDeviceResolutionService(self.db_manager)
            
            start_time, end_time = await self._get_time_bounds(experiment_id, time_window)
            
            if group_by not in ['device_type', 'manufacturer', 'device_name']:
                group_by = 'device_type'

            # Unified query: get all external traffic data and MAC addresses
            query = f"""
            WITH external_flows AS (
                SELECT 
                    pf.device_id,
                    d.mac_address,
                    pf.dst_ip,
                    SUM(pf.packet_size) as total_bytes,
                    COUNT(*) as total_packets,
                    COUNT(DISTINCT pf.device_id) as device_count
                FROM packet_flows pf
                LEFT JOIN devices d ON pf.device_id = d.device_id
                WHERE pf.experiment_id = $1
                AND pf.packet_timestamp >= $2 
                AND pf.packet_timestamp <= $3
                AND pf.dst_ip IS NOT NULL 
                AND pf.dst_ip != '0.0.0.0'::inet
                -- Optimized external filtering: use network operators instead of string matching
                AND NOT (pf.dst_ip <<= '192.168.0.0/16'::inet
                        OR pf.dst_ip <<= '10.0.0.0/8'::inet
                        OR pf.dst_ip <<= '172.16.0.0/12'::inet
                        OR pf.dst_ip <<= '169.254.0.0/16'::inet
                        -- Filter multicast and broadcast addresses
                        OR pf.dst_ip <<= '224.0.0.0/4'::inet     -- Multicast address range
                        OR pf.dst_ip = '255.255.255.255'::inet   -- Broadcast address
                        OR pf.dst_ip <<= '239.0.0.0/8'::inet)    -- Management multicast address
                GROUP BY pf.device_id, d.mac_address, pf.dst_ip
                HAVING SUM(pf.packet_size) >= $4
                ORDER BY total_bytes DESC
                LIMIT {self.max_links}
            )
            SELECT * FROM external_flows
            """
            
            result = await self.db_manager.execute_query(query, 
                (experiment_id, start_time, end_time, self.min_flow_threshold))
            
            if not result:
                return self._empty_sankey_response("device-to-location")

            # Get all MAC addresses and perform bulk device resolution
            mac_addresses = list(set(row['mac_address'] for row in result if row['mac_address']))
            device_resolutions = await resolution_service.bulk_resolve_devices(mac_addresses)
            
            # Create a mapping from MAC addresses to device information
            mac_to_info = {}
            for mac, resolution in device_resolutions.items():
                # Extract the corresponding classification information based on group_by parameter
                if group_by == 'device_name':
                    category = resolution.get('resolvedName', f"Device_{mac.replace(':', '').upper()[-6:]}")
                elif group_by == 'manufacturer':
                    category = resolution.get('resolvedVendor', 'Unknown')
                elif group_by == 'device_type':
                    category = resolution.get('resolvedType', 'IoT Device')
                else:
                    category = 'Unknown'
                
                mac_to_info[mac] = category
            
            # Reorganize the data, using the parsed device information as classification
            processed_result = []
            for row in result:
                mac_address = row['mac_address']
                if mac_address and mac_address in mac_to_info:
                    device_category = mac_to_info[mac_address]
                else:
                    # If the MAC address is empty or cannot be parsed, use the default value
                    if group_by == 'device_name':
                        device_category = f"Device_{mac_address.replace(':', '').upper()[-6:] if mac_address else 'Unknown'}"
                    elif group_by == 'manufacturer':
                        device_category = 'Unknown'
                    else:  # device_type
                        device_category = 'IoT Device'
                
                processed_result.append({
                    'device_category': device_category,
                    'dst_ip': row['dst_ip'],
                    'total_bytes': row['total_bytes'],
                    'total_packets': row['total_packets'],
                    'device_count': row['device_count']
                })
            
            result = processed_result
            
            # Get location information
            unique_ips = list(set(row['dst_ip'] for row in result))
            
            # Limit the number of location queries
            if len(unique_ips) > 50:
                logger.info(f"Large number of IPs ({len(unique_ips)}), using optimized processing")
                # Sort by traffic, only process the top 50 most important IPs
                ip_traffic = {}
                for row in result:
                    ip = row['dst_ip']
                    ip_traffic[ip] = ip_traffic.get(ip, 0) + row['total_bytes']
                
                # Select the top 50 IPs with the highest traffic for location queries
                top_ips = sorted(ip_traffic.items(), key=lambda x: x[1], reverse=True)[:50]
                unique_ips = [ip for ip, _ in top_ips]
                
                # Filter result to only keep top IPs
                result = [row for row in result if row['dst_ip'] in unique_ips]
            
            locations = await geolocation_service.bulk_get_locations(unique_ips)
            
            # Build nodes and links
            nodes = []
            links = []
            source_stats = {}
            target_stats = {}
            
            # Process data and create links
            for row in result:
                source_key = row['device_category']
                dst_ip = row['dst_ip']
                location = locations.get(dst_ip)
                
                if location:
                    country = location.get('country', 'Unknown')
                    country_code = location.get('countryCode', 'UN')
                    target_key = f"{country} ({country_code})"
                else:
                    target_key = "Unknown Location"
                
                # Count source nodes
                if source_key not in source_stats:
                    source_stats[source_key] = {'total_bytes': 0, 'destination_count': 0}
                source_stats[source_key]['total_bytes'] += row['total_bytes']
                source_stats[source_key]['destination_count'] += 1
                
                # Count target nodes
                if target_key not in target_stats:
                    target_stats[target_key] = {'total_bytes': 0, 'ip_count': 0}
                target_stats[target_key]['total_bytes'] += row['total_bytes']
                target_stats[target_key]['ip_count'] += 1
                
                # Create links
                links.append({
                    'source': f"source_{source_key}",
                    'target': f"target_{target_key}",
                    'value': row['total_bytes'],
                    'packets': row['total_packets'],
                    'color': self._get_link_color(row['total_bytes'])
                })
            
            # Create nodes
            for source_key, stats in source_stats.items():
                nodes.append({
                    'id': f"source_{source_key}",
                    'name': source_key,
                    'category': 'source',
                    'type': group_by,
                    'value': stats['total_bytes'],
                    'destination_count': stats['destination_count'],
                    'color': self._get_source_color(source_key)
                })
            
            for target_key, stats in target_stats.items():
                nodes.append({
                    'id': f"target_{target_key}",
                    'name': target_key,
                    'category': 'target',
                    'type': 'location',
                    'value': stats['total_bytes'],
                    'ip_count': stats['ip_count'],
                    'color': self._get_target_color(target_key)
                })
            
            # Calculate external flow bytes and get total experiment bytes for comparison
            external_flow_bytes = sum(link['value'] for link in links)
            
            # Get total experiment bytes for data consistency
            total_experiment_bytes = await self._get_total_experiment_bytes(experiment_id, start_time, end_time)
            
            return {
                'flow_type': 'device-to-location',
                'experiment_id': experiment_id,
                'time_window': time_window,
                'group_by': group_by,
                'nodes': nodes,
                'links': links,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_links': len(links),
                    'external_flow_bytes': external_flow_bytes,  # 明确标识这是外部流量
                    'total_bytes': external_flow_bytes,  # 当前流程的字节数
                    'total_traffic': external_flow_bytes,  # 保持向后兼容
                    'total_experiment_bytes': total_experiment_bytes,  # 实验总字节数，确保数据一致性
                    'data_scope': 'External traffic only (to internet destinations)',
                    'location_coverage': len([ip for ip in unique_ips if ip in locations]) / len(unique_ips) * 100 if unique_ips else 0,
                    'analyzed_ips': len(unique_ips),
                    'located_ips': len(locations)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing device-to-location flow: {e}")
            return self._empty_sankey_response("device-to-location")

    async def analyze_device_to_device_flow(self, experiment_id: str, time_window: str = "24h") -> Dict[str, Any]:
        """
        Analyze device-to-device flow
        Only count internal traffic to avoid duplicate with device-to-location
        """
        try:
            start_time, end_time = await self._get_time_bounds(experiment_id, time_window)
            
            # Ensure device classification consistency, only count internal traffic
            query = """
            WITH device_mapping AS (
                -- Create a unified mapping table from IP to device type
                SELECT DISTINCT
                    ip_address,
                    CASE 
                        WHEN device_type IS NOT NULL AND device_type != 'unknown' 
                        THEN device_type
                        WHEN device_id IS NOT NULL 
                        THEN 'IoT Device'
                        ELSE NULL
                    END as unified_device_type
                FROM devices 
                WHERE experiment_id = $1
            ),
            internal_flows AS (
                SELECT 
                    -- Unified source device classification
                    COALESCE(
                        src_map.unified_device_type,
                        CASE 
                            WHEN HOST(pf.src_ip) LIKE '192.168.%' THEN 'Local Device'
                            WHEN HOST(pf.src_ip) LIKE '10.%' THEN 'Internal Device'
                            WHEN HOST(pf.src_ip) LIKE '172.%' THEN 'Private Device'
                            ELSE 'External Device'
                        END
                    ) as source_type,
                    
                    -- Unified target device classification
                    COALESCE(
                        dst_map.unified_device_type,
                        CASE 
                            WHEN HOST(pf.dst_ip) LIKE '192.168.%' THEN 'Local Device'
                            WHEN HOST(pf.dst_ip) LIKE '10.%' THEN 'Internal Device'
                            WHEN HOST(pf.dst_ip) LIKE '172.%' THEN 'Private Device'
                            WHEN HOST(pf.dst_ip) LIKE '8.8.%' OR HOST(pf.dst_ip) LIKE '1.1.%' THEN 'DNS Server'
                            WHEN HOST(pf.dst_ip) LIKE '169.254.%' THEN 'Link-Local Device'
                            ELSE 'Internet Server'
                        END
                    ) as target_type,
                    
                    SUM(pf.packet_size) as total_bytes,
                    COUNT(*) as total_packets,
                    COUNT(DISTINCT pf.src_ip) as unique_src_ips,
                    COUNT(DISTINCT pf.dst_ip) as unique_dst_ips
                FROM packet_flows pf
                LEFT JOIN device_mapping src_map ON HOST(pf.src_ip) = HOST(src_map.ip_address)
                LEFT JOIN device_mapping dst_map ON HOST(pf.dst_ip) = HOST(dst_map.ip_address)
                WHERE pf.experiment_id = $1
                AND pf.packet_timestamp >= $2 
                AND pf.packet_timestamp <= $3
                AND pf.src_ip != pf.dst_ip
                -- Only count internal traffic to avoid duplicate with device-to-location
                AND (HOST(pf.dst_ip) LIKE '192.168.%' 
                     OR HOST(pf.dst_ip) LIKE '10.%' 
                     OR HOST(pf.dst_ip) LIKE '172.%'
                     OR HOST(pf.dst_ip) LIKE '169.254.%')
                GROUP BY source_type, target_type
                HAVING SUM(pf.packet_size) >= $4
                ORDER BY total_bytes DESC
                LIMIT $5
            )
            SELECT * FROM internal_flows
            """
            
            result = await self.db_manager.execute_query(query, 
                (experiment_id, start_time, end_time, self.min_flow_threshold, self.max_links))
            
            if not result:
                return self._empty_sankey_response("device-to-device")
            
            # Build nodes and links
            nodes = []
            links = []
            source_stats = {}
            target_stats = {}
            
            for row in result:
                source_key = row['source_type']
                target_key = row['target_type']
                
                # If source and target are the same, skip
                if source_key == target_key:
                    continue
                
                # Count source nodes
                if source_key not in source_stats:
                    source_stats[source_key] = {
                        'total_bytes': 0, 
                        'target_count': 0,
                        'unique_src_ips': 0
                    }
                source_stats[source_key]['total_bytes'] += row['total_bytes']
                source_stats[source_key]['target_count'] += 1
                source_stats[source_key]['unique_src_ips'] += row['unique_src_ips']
                
                # Count target nodes
                if target_key not in target_stats:
                    target_stats[target_key] = {
                        'total_bytes': 0, 
                        'source_count': 0,
                        'unique_dst_ips': 0
                    }
                target_stats[target_key]['total_bytes'] += row['total_bytes']
                target_stats[target_key]['source_count'] += 1
                target_stats[target_key]['unique_dst_ips'] += row['unique_dst_ips']
                
                # Create links
                links.append({
                    'source': f"source_{source_key}",
                    'target': f"target_{target_key}",
                    'value': row['total_bytes'],
                    'packets': row['total_packets'],
                    'src_ips': row['unique_src_ips'],
                    'dst_ips': row['unique_dst_ips'],
                    'color': self._get_link_color(row['total_bytes'])
                })
            
            # Create nodes
            for source_key, stats in source_stats.items():
                nodes.append({
                    'id': f"source_{source_key}",
                    'name': source_key,
                    'category': 'source',
                    'type': 'device',
                    'value': stats['total_bytes'],
                    'target_count': stats['target_count'],
                    'unique_ips': stats['unique_src_ips'],
                    'color': self._get_device_color(source_key)
                })
            
            for target_key, stats in target_stats.items():
                nodes.append({
                    'id': f"target_{target_key}",
                    'name': target_key,
                    'category': 'target',
                    'type': 'device',
                    'value': stats['total_bytes'],
                    'source_count': stats['source_count'],
                    'unique_ips': stats['unique_dst_ips'],
                    'color': self._get_device_color(target_key)
                })
            
            # Calculate internal flow bytes and get total experiment bytes for comparison
            internal_flow_bytes = sum(link['value'] for link in links)
            
            # Get total experiment bytes for data consistency
            total_experiment_bytes = await self._get_total_experiment_bytes(experiment_id, start_time, end_time)
            
            return {
                'flow_type': 'device-to-device',
                'experiment_id': experiment_id,
                'time_window': time_window,
                'nodes': nodes,
                'links': links,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_links': len(links),
                    'internal_flow_bytes': internal_flow_bytes,  # 明确标识这是内部流量
                    'total_bytes': internal_flow_bytes,  # 当前流程的字节数
                    'total_traffic': internal_flow_bytes,  # 保持向后兼容
                    'total_experiment_bytes': total_experiment_bytes,  # 实验总字节数，确保数据一致性
                    'data_scope': 'Internal network traffic only (to avoid duplicate with device-to-location)'
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing device-to-device flow: {e}")
            return self._empty_sankey_response("device-to-device")

    async def analyze_protocol_to_service_flow(self, experiment_id: str, time_window: str = "24h") -> Dict[str, Any]:
        """
        Analyze protocol-to-service flow
        """
        try:
            start_time, end_time = await self._get_time_bounds(experiment_id, time_window)
            
            query = """
            WITH protocol_flows AS (
                SELECT 
                    CASE 
                        WHEN pf.app_protocol IS NOT NULL AND pf.app_protocol != '' 
                        THEN pf.app_protocol
                        WHEN pf.protocol IS NOT NULL AND pf.protocol != '' 
                        THEN pf.protocol
                        ELSE 'Unknown'
                    END as protocol,
                    CASE 
                        -- Local network priority
                        WHEN HOST(pf.dst_ip) LIKE '192.168.%' OR HOST(pf.dst_ip) LIKE '10.%' OR HOST(pf.dst_ip) LIKE '172.%' 
                        THEN 'Local Network'
                        -- Web services (HTTP/HTTPS related)
                        WHEN pf.dst_port IN (80, 443, 8080, 8443, 8000, 9000, 3000) 
                            OR pf.app_protocol IN ('HTTP', 'HTTPS')
                        THEN 'Web Services'
                        -- DNS services
                        WHEN pf.dst_port IN (53, 853, 5353) 
                            OR pf.app_protocol IN ('DNS', 'mDNS')
                        THEN 'DNS Services'
                        -- Email services
                        WHEN pf.dst_port IN (25, 587, 993, 995, 110, 143, 465) 
                            OR pf.app_protocol IN ('SMTP', 'IMAP', 'POP3')
                        THEN 'Email Services'
                        -- Remote access services
                        WHEN pf.dst_port IN (22, 23, 3389, 5900, 5901) 
                            OR pf.app_protocol IN ('SSH', 'Telnet', 'RDP', 'VNC')
                        THEN 'Remote Access'
                        -- Streaming services
                        WHEN pf.dst_port IN (1935, 554, 8554, 1755) 
                            OR pf.app_protocol IN ('RTMP', 'RTSP', 'HLS')
                        THEN 'Media Streaming'
                        -- File transfer services
                        WHEN pf.dst_port IN (21, 20, 69, 873, 989, 990) 
                            OR pf.app_protocol IN ('FTP', 'TFTP', 'SFTP', 'FTPS', 'rsync')
                        THEN 'File Transfer'
                        -- IoT/Smart home protocols
                        WHEN pf.dst_port IN (1883, 8883, 5683, 5684, 61616) 
                            OR pf.app_protocol IN ('MQTT', 'CoAP', 'AMQP')
                        THEN 'IoT Services'
                        -- Network time services    
                        WHEN pf.dst_port IN (123, 37) 
                            OR pf.app_protocol = 'NTP'
                        THEN 'Time Services'
                        -- DHCP services
                        WHEN pf.dst_port IN (67, 68) 
                            OR pf.app_protocol = 'DHCP'
                        THEN 'Network Config'
                        -- Cloud services (based on common cloud service ports)
                        WHEN pf.dst_port IN (6443, 2379, 2380, 10250) 
                        THEN 'Cloud Services'
                        -- Database services
                        WHEN pf.dst_port IN (3306, 5432, 1433, 1521, 27017, 6379) 
                        THEN 'Database Services'
                        -- Other services
                        ELSE 'Other Services'
                    END as service_type,
                    SUM(pf.packet_size) as total_bytes,
                    COUNT(*) as total_packets,
                    COUNT(DISTINCT pf.dst_ip) as unique_destinations
                FROM packet_flows pf
                WHERE pf.experiment_id = $1
                AND pf.packet_timestamp >= $2 
                AND pf.packet_timestamp <= $3
                GROUP BY 
                    CASE 
                        WHEN pf.app_protocol IS NOT NULL AND pf.app_protocol != '' 
                        THEN pf.app_protocol
                        WHEN pf.protocol IS NOT NULL AND pf.protocol != '' 
                        THEN pf.protocol
                        ELSE 'Unknown'
                    END,
                    CASE 
                        -- Local network priority
                        WHEN HOST(pf.dst_ip) LIKE '192.168.%' OR HOST(pf.dst_ip) LIKE '10.%' OR HOST(pf.dst_ip) LIKE '172.%' 
                        THEN 'Local Network'
                        -- Web services (HTTP/HTTPS related)
                        WHEN pf.dst_port IN (80, 443, 8080, 8443, 8000, 9000, 3000) 
                            OR pf.app_protocol IN ('HTTP', 'HTTPS')
                        THEN 'Web Services'
                        -- DNS services
                        WHEN pf.dst_port IN (53, 853, 5353) 
                            OR pf.app_protocol IN ('DNS', 'mDNS')
                        THEN 'DNS Services'
                        -- Email services
                        WHEN pf.dst_port IN (25, 587, 993, 995, 110, 143, 465) 
                            OR pf.app_protocol IN ('SMTP', 'IMAP', 'POP3')
                        THEN 'Email Services'
                        -- Remote access services
                        WHEN pf.dst_port IN (22, 23, 3389, 5900, 5901) 
                            OR pf.app_protocol IN ('SSH', 'Telnet', 'RDP', 'VNC')
                        THEN 'Remote Access'
                        -- Media streaming services
                        WHEN pf.dst_port IN (1935, 554, 8554, 1755) 
                            OR pf.app_protocol IN ('RTMP', 'RTSP', 'HLS')
                        THEN 'Media Streaming'
                        -- File transfer services
                        WHEN pf.dst_port IN (21, 20, 69, 873, 989, 990) 
                            OR pf.app_protocol IN ('FTP', 'TFTP', 'SFTP', 'FTPS', 'rsync')
                        THEN 'File Transfer'
                        -- IoT/smart home protocols
                        WHEN pf.dst_port IN (1883, 8883, 5683, 5684, 61616) 
                            OR pf.app_protocol IN ('MQTT', 'CoAP', 'AMQP')
                        THEN 'IoT Services'
                        -- Network time services
                        WHEN pf.dst_port IN (123, 37) 
                            OR pf.app_protocol = 'NTP'
                        THEN 'Time Services'
                        -- DHCP services
                        WHEN pf.dst_port IN (67, 68) 
                            OR pf.app_protocol = 'DHCP'
                        THEN 'Network Config'
                        -- Cloud services (based on common cloud service ports)
                        WHEN pf.dst_port IN (6443, 2379, 2380, 10250) 
                        THEN 'Cloud Services'
                        -- Database services
                        WHEN pf.dst_port IN (3306, 5432, 1433, 1521, 27017, 6379) 
                        THEN 'Database Services'
                        -- Other services
                        ELSE 'Other Services'
                    END
                HAVING SUM(pf.packet_size) >= $4
                ORDER BY total_bytes DESC
                LIMIT $5
            )
            SELECT * FROM protocol_flows
            """
            
            result = await self.db_manager.execute_query(query, 
                (experiment_id, start_time, end_time, self.min_flow_threshold, self.max_links))
            
            if not result:
                return self._empty_sankey_response("protocol-to-service")
            
            # Build nodes and links
            nodes = []
            links = []
            protocol_stats = {}
            service_stats = {}
            
            for row in result:
                protocol = row['protocol']
                service_type = row['service_type']
                
                # Count protocol nodes
                if protocol not in protocol_stats:
                    protocol_stats[protocol] = {
                        'total_bytes': 0,
                        'service_count': 0
                    }
                protocol_stats[protocol]['total_bytes'] += row['total_bytes']
                protocol_stats[protocol]['service_count'] += 1
                
                # Count service nodes
                if service_type not in service_stats:
                    service_stats[service_type] = {
                        'total_bytes': 0,
                        'protocol_count': 0
                    }
                service_stats[service_type]['total_bytes'] += row['total_bytes']
                service_stats[service_type]['protocol_count'] += 1
                
                # Create links
                links.append({
                    'source': f"protocol_{protocol}",
                    'target': f"service_{service_type}",
                    'value': row['total_bytes'],
                    'packets': row['total_packets'],
                    'destinations': row['unique_destinations'],
                    'color': self._get_link_color(row['total_bytes'])
                })
            
            # Create protocol nodes
            for protocol, stats in protocol_stats.items():
                nodes.append({
                    'id': f"protocol_{protocol}",
                    'name': protocol,
                    'category': 'source',
                    'type': 'protocol',
                    'value': stats['total_bytes'],
                    'service_count': stats['service_count'],
                    'color': self._get_protocol_color(protocol)
                })
            
            # Create service nodes
            for service_type, stats in service_stats.items():
                nodes.append({
                    'id': f"service_{service_type}",
                    'name': service_type,
                    'category': 'target',
                    'type': 'service',
                    'value': stats['total_bytes'],
                    'protocol_count': stats['protocol_count'],
                    'color': self._get_service_color(service_type)
                })
            
            # Calculate protocol flow bytes (this should match total experiment bytes)
            protocol_flow_bytes = sum(link['value'] for link in links)
            
            # Get total experiment bytes for data consistency verification
            total_experiment_bytes = await self._get_total_experiment_bytes(experiment_id, start_time, end_time)
            
            return {
                'flow_type': 'protocol-to-service',
                'experiment_id': experiment_id,
                'time_window': time_window,
                'nodes': nodes,
                'links': links,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_links': len(links),
                    'protocol_flow_bytes': protocol_flow_bytes,  # 明确标识这是协议流量
                    'total_bytes': protocol_flow_bytes,  # 当前流程的字节数
                    'total_traffic': protocol_flow_bytes,  # 保持向后兼容
                    'total_experiment_bytes': total_experiment_bytes,  # 实验总字节数，确保数据一致性
                    'data_scope': 'All network traffic by protocol and service',
                    'data_consistency_check': abs(protocol_flow_bytes - total_experiment_bytes) < (total_experiment_bytes * 0.05) if total_experiment_bytes > 0 else True
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing protocol-to-service flow: {e}")
            return self._empty_sankey_response("protocol-to-service")

    async def _get_time_bounds(self, experiment_id: str, time_window: str) -> Tuple[datetime, datetime]:
        """Get time bounds - use experiment timezone for unified time handling"""
        try:
            if time_window == "auto":
                # Auto mode: get actual time range of experiment data
                query = """
                SELECT MIN(packet_timestamp) as min_time, MAX(packet_timestamp) as max_time
                FROM packet_flows 
                WHERE experiment_id = $1
                """
                result = await self.db_manager.execute_query(query, (experiment_id,))
                
                if result and result[0]['min_time'] and result[0]['max_time']:
                    start_time = result[0]['min_time']
                    end_time = result[0]['max_time']
                    logger.info(f"Time window auto: {start_time} to {end_time}")
                    return start_time, end_time
                else:
                    # If no data, use 24-hour window of current time in experiment timezone
                    try:
                        # Import the correct timezone manager
                        try:
                            from database.services.timezone_manager import timezone_manager
                            logger.info("Using database.services.timezone_manager for time bounds")
                        except ImportError:
                            from backend.api.common.timezone_manager import timezone_manager
                            logger.warning("Falling back to backend.api.common.timezone_manager for time bounds")
                        
                        experiment_tz = timezone_manager.get_experiment_timezone(experiment_id)  # Remove await
                        logger.info(f"Using experiment timezone {experiment_tz} for time bounds calculation")
                        
                        # Get current time in experiment timezone
                        from datetime import datetime, timezone as dt_timezone
                        utc_now = datetime.now(dt_timezone.utc)
                        end_time = timezone_manager.convert_to_experiment_timezone(utc_now, experiment_id)
                        start_time = end_time - timedelta(hours=24)
                        return start_time, end_time
                    except Exception as tz_error:
                        logger.warning(f"Failed to get experiment timezone, using UTC: {tz_error}")
                        end_time = datetime.now()
                        start_time = end_time - timedelta(hours=24)
                        return start_time, end_time
            else:
                # Relative time window: use current time in experiment timezone as end time
                try:
                    # Import the correct timezone manager
                    try:
                        from database.services.timezone_manager import timezone_manager
                        logger.info("Using database.services.timezone_manager for time bounds")
                    except ImportError:
                        from backend.api.common.timezone_manager import timezone_manager
                        logger.warning("Falling back to backend.api.common.timezone_manager for time bounds")
                    
                    experiment_tz = timezone_manager.get_experiment_timezone(experiment_id)  # Remove await
                    logger.info(f"Using experiment timezone {experiment_tz} for time bounds calculation")
                    
                    # Get current time in experiment timezone
                    from datetime import datetime, timezone as dt_timezone
                    utc_now = datetime.now(dt_timezone.utc)
                    end_time = timezone_manager.convert_to_experiment_timezone(utc_now, experiment_id)
                except Exception as tz_error:
                    logger.warning(f"Failed to get experiment timezone, using UTC: {tz_error}")
                    end_time = datetime.now()
                
                if time_window == "1h":
                    start_time = end_time - timedelta(hours=1)
                elif time_window == "2h":
                    start_time = end_time - timedelta(hours=2)
                elif time_window == "6h":
                    start_time = end_time - timedelta(hours=6)
                elif time_window == "12h":
                    start_time = end_time - timedelta(hours=12)
                elif time_window == "24h":
                    start_time = end_time - timedelta(hours=24)
                elif time_window == "48h":
                    start_time = end_time - timedelta(hours=48)
                else:
                    # Default 24 hours
                    start_time = end_time - timedelta(hours=24)
                
                logger.info(f"Time window {time_window} (experiment timezone): {start_time} to {end_time}")
                return start_time, end_time
                
        except Exception as e:
            logger.error(f"Error getting time bounds: {e}")
            # Return default 24-hour window when error occurs
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            return start_time, end_time

    async def _get_total_experiment_bytes(self, experiment_id: str, start_time, end_time) -> int:
        """
        获取实验的总字节数，与其他API保持一致的计算方式
        这确保了数据一致性检查的准确性
        """
        try:
            query = """
            SELECT COALESCE(SUM(packet_size), 0) as total_bytes
            FROM packet_flows 
            WHERE experiment_id = $1
            AND packet_timestamp >= $2 
            AND packet_timestamp <= $3
            """
            
            result = await self.db_manager.execute_query(query, (experiment_id, start_time, end_time))
            
            if result and len(result) > 0:
                return int(result[0]['total_bytes'] or 0)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error getting total experiment bytes: {e}")
            return 0

    def _empty_sankey_response(self, flow_type: str) -> Dict[str, Any]:
        """Return empty Sankey diagram response"""
        return {
            'flow_type': flow_type,
            'experiment_id': '',
            'time_window': '',
            'nodes': [],
            'links': [],
            'metadata': {
                'total_nodes': 0,
                'total_links': 0,
                'total_bytes': 0,  # 当前流程的字节数
                'total_traffic': 0,  # 保持向后兼容
                'total_experiment_bytes': 0,  # 实验总字节数
                'data_scope': 'No data available'
            }
        }

    def _get_source_color(self, source_key: str) -> str:
        """Get source node color"""
        color_map = {
            'IoT Device': '#3498DB',      # Blue
            'Local Device': '#2ECC71',    # Green  
            'Internal Device': '#9B59B6', # Purple
            'Private Device': '#E67E22',  # Orange
            'External Device': '#E74C3C', # Red
            'Unknown Device': '#95A5A6',  # Gray
            'Unknown Manufacturer': '#BDC3C7'
        }
        return color_map.get(source_key, '#34495E')

    def _get_target_color(self, target_key: str) -> str:
        """Get target node color"""
        if 'United States' in target_key:
            return '#3498DB'
        elif 'China' in target_key:
            return '#E74C3C'
        elif 'United Kingdom' in target_key or 'Ireland' in target_key:
            return '#2ECC71'
        elif 'Germany' in target_key:
            return '#F39C12'
        elif 'Unknown' in target_key:
            return '#95A5A6'
        else:
            return '#9B59B6'

    def _get_device_color(self, device_key: str) -> str:
        """Get device node color"""
        color_map = {
            'IoT Device': '#3498DB',
            'Local Device': '#2ECC71',
            'Internal Device': '#9B59B6',
            'Private Device': '#E67E22',
            'External Device': '#E74C3C',
            'DNS Server': '#F39C12',
            'Link-Local Device': '#1ABC9C',
            'Internet Server': '#34495E'
        }
        return color_map.get(device_key, '#95A5A6')

    def _get_protocol_color(self, protocol: str) -> str:
        """Get protocol node color"""
        color_map = {
            'HTTP': '#3498DB',
            'HTTPS': '#2ECC71',
            'DNS': '#9B59B6',
            'DHCP': '#E67E22',
            'TCP': '#E74C3C',
            'UDP': '#F39C12',
            'ICMP': '#1ABC9C'
        }
        return color_map.get(protocol, '#95A5A6')

    def _get_service_color(self, service_type: str) -> str:
        """Get service node color"""
        color_map = {
            'Web Services': '#3498DB',
            'Local Network': '#2ECC71',
            'DNS Services': '#9B59B6',
            'Email Services': '#E67E22',
            'Remote Access': '#E74C3C',
            'Media Streaming': '#F39C12',
            'File Transfer': '#1ABC9C',
            'IoT Services': '#8E44AD',
            'Time Services': '#D35400',
            'Network Config': '#16A085',
            'Cloud Services': '#2980B9',
            'Database Services': '#8B4513'
        }
        return color_map.get(service_type, '#95A5A6')

    def _get_link_color(self, traffic_bytes: int) -> str:
        """Get link color based on traffic size"""
        if traffic_bytes > 50000000:    # >50MB
            return '#E74C3C'  # Red - high traffic
        elif traffic_bytes > 10000000:  # >10MB
            return '#F39C12'  # Orange - medium-high traffic
        elif traffic_bytes > 1000000:   # >1MB
            return '#F1C40F'  # Yellow - medium traffic
        else:
            return '#3498DB'  # Blue - low traffic

