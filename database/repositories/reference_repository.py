"""
Reference Data Repository
Handle device name and vendor mapping operations
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ReferenceRepository:
    """Repository for reference data operations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def _format_mac_address(self, mac_address: str) -> str:
        """
        Format MAC address, support multiple input formats
        - Automatically add colon (if missing)
        - Convert to standard uppercase format
        - Support various separators (:, -, no separator)
        """
        if not mac_address:
            raise ValueError("MAC address cannot be empty")
        
        # Remove all non-hexadecimal characters and convert to uppercase
        clean_mac = ''.join(c.upper() for c in mac_address if c.upper() in '0123456789ABCDEF')
        
        if len(clean_mac) != 12:
            raise ValueError(f"Invalid MAC address format: {mac_address}")
        
        # Format as standard colon-separated format
        formatted = ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
        return formatted
    
    def _format_oui_pattern(self, oui_pattern: str) -> str:
        """
        Format OUI pattern, support multiple input formats
        - Automatically add colon (if missing)
        - Convert to standard uppercase format
        """
        if not oui_pattern:
            raise ValueError("OUI pattern cannot be empty")
        
        # Remove all non-hexadecimal characters and convert to uppercase
        clean_oui = ''.join(c.upper() for c in oui_pattern if c.upper() in '0123456789ABCDEF')
        
        if len(clean_oui) != 6:
            raise ValueError(f"Invalid OUI pattern format: {oui_pattern}. Expected 6 hex characters.")
        
        # Format as standard colon-separated format
        formatted = ':'.join(clean_oui[i:i+2] for i in range(0, 6, 2))
        return formatted
    

    
    async def get_known_device(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get specific known device by MAC address"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT mac_address, device_name, device_type, vendor, notes, COALESCE(is_protected, FALSE) as is_protected FROM known_devices WHERE mac_address = $1",
                (mac_address,)
            )
            
            if result:
                device = result[0]
                return {
                    "mac_address": device.get("mac_address"),
                    "device_name": device.get("device_name"),
                    "device_type": device.get("device_type"),
                    "vendor": device.get("vendor"),
                    "notes": device.get("notes"),
                    "is_protected": device.get("is_protected", False)
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get known device {mac_address}: {e}")
            return None
    
    async def add_known_device(self, mac_address: str, device_name: str, device_type: str = "unknown", 
                              vendor: str = "Unknown", notes: Optional[str] = None) -> bool:
        """Add a new known device to the database"""
        try:
            # Format MAC address
            mac_formatted = self._format_mac_address(mac_address)
            
            # Use INSERT ... ON CONFLICT to ensure new record is set to non-protected state
            query = """
                INSERT INTO known_devices (mac_address, device_name, device_type, vendor, notes, is_protected)
                VALUES ($1, $2, $3, $4, $5, FALSE)
                ON CONFLICT (mac_address) 
                DO UPDATE SET 
                    device_name = EXCLUDED.device_name,
                    device_type = EXCLUDED.device_type,
                    vendor = EXCLUDED.vendor,
                    notes = EXCLUDED.notes,
                    is_protected = CASE 
                        WHEN known_devices.is_protected = TRUE THEN known_devices.is_protected
                        ELSE FALSE
                    END
            """
            
            await self.db_manager.execute_command(
                query,
                (mac_formatted, device_name, device_type, vendor, notes)
            )
            
            logger.info(f"Added/updated known device: {mac_formatted} -> {device_name} (non-protected)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add known device {mac_address}: {e}")
            return False
    
    async def update_known_device(self, mac_address: str, **kwargs) -> bool:
        """Update an existing known device"""
        try:
            # Build dynamic update query
            update_fields = []
            params = []
            param_index = 1
            
            for field, value in kwargs.items():
                if field in ['device_name', 'device_type', 'vendor', 'notes'] and value is not None:
                    update_fields.append(f"{field} = ${param_index + 1}")
                    params.append(value)
                    param_index += 1
            
            if not update_fields:
                return False
            
            # Add mac_address as the WHERE parameter
            params.insert(0, mac_address)
            
            query = f"""
                UPDATE known_devices 
                SET {', '.join(update_fields)}
                WHERE mac_address = $1
            """
            
            rows_affected = await self.db_manager.execute_command(query, tuple(params))
            
            # Check if any rows were affected (handle both string and int responses)
            success = False
            if rows_affected:
                if isinstance(rows_affected, str):
                    success = "UPDATE 1" in rows_affected
                elif isinstance(rows_affected, int):
                    success = rows_affected > 0
                else:
                    try:
                        success = int(rows_affected) > 0
                    except (ValueError, TypeError):
                        success = False
            
            if success:
                logger.info(f"Updated known device: {mac_address}")
                return True
            else:
                logger.warning(f"No known device found to update: {mac_address}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update known device {mac_address}: {e}")
            return False
    
    async def delete_known_device(self, mac_address: str) -> bool:
        """Delete a known device (handles protected devices by removing protection first)"""
        try:
            # First check if the device exists
            device_info = await self.db_manager.execute_query(
                "SELECT mac_address, COALESCE(is_protected, FALSE) as is_protected FROM known_devices WHERE mac_address = $1",
                (mac_address,)
            )
            
            if not device_info:
                logger.warning(f"No known device found to delete: {mac_address}")
                return False
            
            is_protected = device_info[0].get('is_protected', False)
            if is_protected:
                logger.info(f"Removing protection from device before deletion: {mac_address}")
                # Remove protection first
                await self.db_manager.execute_command(
                    "UPDATE known_devices SET is_protected = FALSE WHERE mac_address = $1",
                    (mac_address,)
                )
            
            # Now delete the device
            rows_affected = await self.db_manager.execute_command(
                "DELETE FROM known_devices WHERE mac_address = $1",
                (mac_address,)
            )
            
            # Check if any rows were affected (handle both string and int responses)
            success = False
            if rows_affected:
                if isinstance(rows_affected, str):
                    # PostgreSQL returns "DELETE 1" for successful deletion
                    success = "DELETE 1" in rows_affected
                elif isinstance(rows_affected, int):
                    success = rows_affected > 0
                else:
                    # Try to convert to int if possible
                    try:
                        success = int(rows_affected) > 0
                    except (ValueError, TypeError):
                        success = False
            
            if success:
                logger.info(f"Successfully deleted known device: {mac_address}")
                return True
            else:
                logger.warning(f"Failed to delete known device: {mac_address}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete known device {mac_address}: {e}")
            return False
    
    async def get_vendor_by_oui(self, oui_pattern: str) -> Optional[Dict[str, Any]]:
        """Get vendor information by OUI pattern"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT oui_pattern, vendor_name, device_category FROM vendor_patterns WHERE oui_pattern = $1",
                (oui_pattern,)
            )
            
            if result:
                vendor = result[0]
                return {
                    "oui_pattern": vendor.get("oui_pattern"),
                    "vendor_name": vendor.get("vendor_name"),
                    "device_category": vendor.get("device_category")
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vendor by OUI {oui_pattern}: {e}")
            return None
    
    async def add_vendor_pattern(self, oui_pattern: str, vendor_name: str, device_category: str = "unknown") -> bool:
        """Add a new vendor pattern to the database"""
        try:
            # Format OUI pattern (ensure colon format)
            oui_formatted = self._format_oui_pattern(oui_pattern)
            
            # Use INSERT ... ON CONFLICT to ensure new record is set to non-protected state
            query = """
                INSERT INTO vendor_patterns (oui_pattern, vendor_name, device_category, is_protected)
                VALUES ($1, $2, $3, FALSE)
                ON CONFLICT (oui_pattern) 
                DO UPDATE SET 
                    vendor_name = EXCLUDED.vendor_name,
                    device_category = EXCLUDED.device_category,
                    is_protected = CASE 
                        WHEN vendor_patterns.is_protected = TRUE THEN vendor_patterns.is_protected
                        ELSE FALSE
                    END
            """
            
            await self.db_manager.execute_command(
                query,
                (oui_formatted, vendor_name, device_category)
            )
            
            logger.info(f"Added/updated vendor pattern: {oui_formatted} -> {vendor_name} (non-protected)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vendor pattern {oui_pattern}: {e}")
            return False
    
    async def update_vendor_pattern(self, oui_pattern: str, vendor_name: str, 
                                   device_category: str = "unknown") -> bool:
        """Update an existing vendor pattern"""
        try:
            rows_affected = await self.db_manager.execute_command(
                """
                UPDATE vendor_patterns 
                SET vendor_name = $2, device_category = $3
                WHERE oui_pattern = $1
                """,
                (oui_pattern, vendor_name, device_category)
            )
            
            # Check if any rows were affected (handle both string and int responses)
            success = False
            if rows_affected:
                if isinstance(rows_affected, str):
                    # PostgreSQL returns "UPDATE 1" for successful update
                    success = "UPDATE 1" in rows_affected
                elif isinstance(rows_affected, int):
                    success = rows_affected > 0
                else:
                    # Try to convert to int if possible
                    try:
                        success = int(rows_affected) > 0
                    except (ValueError, TypeError):
                        success = False
            
            if success:
                logger.info(f"Updated vendor pattern: {oui_pattern} -> {vendor_name}")
                return True
            else:
                logger.warning(f"No vendor pattern found to update: {oui_pattern}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update vendor pattern {oui_pattern}: {e}")
            return False
    
    async def delete_vendor_pattern(self, oui_pattern: str) -> bool:
        """Delete a vendor pattern (only if not protected)"""
        try:
            # First check if the pattern exists and is not protected
            pattern_info = await self.db_manager.execute_query(
                "SELECT is_protected FROM vendor_patterns WHERE oui_pattern = $1",
                (oui_pattern,)
            )
            
            if not pattern_info:
                logger.warning(f"No vendor pattern found to delete: {oui_pattern}")
                return False
            
            is_protected = pattern_info[0].get('is_protected', True)
            if is_protected:
                logger.warning(f"Cannot delete protected vendor pattern: {oui_pattern}")
                return False
            
            # Delete the pattern
            rows_affected = await self.db_manager.execute_command(
                "DELETE FROM vendor_patterns WHERE oui_pattern = $1 AND is_protected = FALSE",
                (oui_pattern,)
            )
            
            # Check if any rows were affected (handle both string and int responses)
            success = False
            if rows_affected:
                if isinstance(rows_affected, str):
                    # PostgreSQL returns "DELETE 1" for successful deletion
                    success = "DELETE 1" in rows_affected
                elif isinstance(rows_affected, int):
                    success = rows_affected > 0
                else:
                    # Try to convert to int if possible
                    try:
                        success = int(rows_affected) > 0
                    except (ValueError, TypeError):
                        success = False
            
            if success:
                logger.info(f"Deleted vendor pattern: {oui_pattern}")
                return True
            else:
                logger.warning(f"Failed to delete vendor pattern (may be protected): {oui_pattern}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete vendor pattern {oui_pattern}: {e}")
            return False
    
    async def search_vendors(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for vendors by OUI pattern (MAC prefix) with fuzzy matching
        Supports search without colons and case-insensitive matching
        """
        try:
            # Clean and format search term for MAC address pattern matching
            clean_search = ''.join(c.upper() for c in search_term if c.upper() in '0123456789ABCDEF')
            
            # Create multiple search patterns for flexibility
            patterns = []
            params = []
            param_count = 1
            
            # 1. Direct MAC prefix match (cleaned input)
            if clean_search:
                # For partial MAC addresses, pad with wildcards
                if len(clean_search) >= 2:
                    # Format as XX:XX:XX pattern
                    formatted_prefix = ':'.join(clean_search[i:i+2] for i in range(0, min(len(clean_search), 6), 2))
                    if len(clean_search) < 6:
                        formatted_prefix += '%'
                    patterns.append(f"oui_pattern ILIKE ${param_count}")
                    params.append(f"{formatted_prefix}%")
                    param_count += 1
            
            # 2. Vendor name match (fallback for text searches)
            if search_term and not clean_search:
                patterns.append(f"vendor_name ILIKE ${param_count}")
                params.append(f"%{search_term}%")
                param_count += 1
            
            # 3. Raw text match in OUI pattern (for cases like "ac15a2")
            if clean_search:
                patterns.append(f"REPLACE(oui_pattern, ':', '') ILIKE ${param_count}")
                params.append(f"%{clean_search}%")
                param_count += 1
            
            if not patterns:
                return []
            
            where_clause = " OR ".join(patterns)
            params.append(limit)
            
            query = f"""
                SELECT oui_pattern, vendor_name, device_category
                FROM vendor_patterns
                WHERE {where_clause}
                ORDER BY 
                    CASE 
                        WHEN oui_pattern ILIKE $1 THEN 1 
                        ELSE 2 
                    END,
                    vendor_name
                LIMIT ${len(params)}
            """
            
            results = await self.db_manager.execute_query(query, tuple(params))
            
            return [
                {
                    "oui_pattern": r.get("oui_pattern"),
                    "vendor_name": r.get("vendor_name"),
                    "device_category": r.get("device_category")
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search vendors: {e}")
            return []

    async def search_known_devices(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for known devices by MAC address or device name with fuzzy matching
        Supports search without colons and case-insensitive matching
        """
        try:
            # Clean and format search term for MAC address matching
            clean_search = ''.join(c.upper() for c in search_term if c.upper() in '0123456789ABCDEF')
            
            patterns = []
            params = []
            param_count = 1
            
            # 1. MAC address pattern matching
            if clean_search:
                # Format as XX:XX:XX:XX:XX:XX pattern for complete MAC
                if len(clean_search) >= 2:
                    formatted_mac = ':'.join(clean_search[i:i+2] for i in range(0, min(len(clean_search), 12), 2))
                    if len(clean_search) < 12:
                        formatted_mac += '%'
                    patterns.append(f"mac_address ILIKE ${param_count}")
                    params.append(f"{formatted_mac}%")
                    param_count += 1
                
                # Raw MAC search without colons
                patterns.append(f"REPLACE(mac_address, ':', '') ILIKE ${param_count}")
                params.append(f"%{clean_search}%")
                param_count += 1
            
            # 2. Device name search (always included for text searches)
            if search_term:
                patterns.append(f"device_name ILIKE ${param_count}")
                params.append(f"%{search_term}%")
                param_count += 1
                
                # Vendor search
                patterns.append(f"vendor ILIKE ${param_count}")
                params.append(f"%{search_term}%")
                param_count += 1
            
            if not patterns:
                return []
            
            where_clause = " OR ".join(patterns)
            params.append(limit)
            
            # Create prioritized ORDER BY clause
            order_clauses = []
            if clean_search and len(params) >= 2:
                # MAC address exact match gets highest priority
                order_clauses.append(f"CASE WHEN mac_address ILIKE ${1} THEN 1 ELSE 4 END")
            if search_term:
                # Device name starts with search term gets second priority
                order_clauses.append(f"CASE WHEN device_name ILIKE '{search_term}%' THEN 2 ELSE 4 END")
                # Device name contains search term gets third priority  
                order_clauses.append(f"CASE WHEN device_name ILIKE '%{search_term}%' THEN 3 ELSE 4 END")
            
            order_by = ", ".join(order_clauses) if order_clauses else "device_name"
            
            query = f"""
                SELECT mac_address, device_name, device_type, vendor, notes
                FROM known_devices
                WHERE {where_clause}
                ORDER BY {order_by}, device_name
                LIMIT ${len(params)}
            """
            
            results = await self.db_manager.execute_query(query, tuple(params))
            
            return [
                {
                    "mac_address": r.get("mac_address"),
                    "device_name": r.get("device_name"),
                    "device_type": r.get("device_type"),
                    "vendor": r.get("vendor"),
                    "notes": r.get("notes")
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search known devices: {e}")
            return []
    
    async def get_reference_stats(self) -> Dict[str, Any]:
        """Get reference data statistics"""
        try:
            known_devices_count = await self.db_manager.execute_scalar(
                "SELECT COUNT(*) FROM known_devices"
            )
            
            vendor_patterns_count = await self.db_manager.execute_scalar(
                "SELECT COUNT(*) FROM vendor_patterns"
            )
            
            # Get recent known devices (by device name since we don't have created_at)
            recent_known_devices = await self.db_manager.execute_query(
                "SELECT device_name, mac_address FROM known_devices ORDER BY device_name LIMIT 5"
            )
            
            # Get top vendors
            top_vendors = await self.db_manager.execute_query(
                """
                SELECT vendor_name, COUNT(*) as pattern_count
                FROM vendor_patterns
                GROUP BY vendor_name
                ORDER BY pattern_count DESC
                LIMIT 5
                """
            )
            
            return {
                "known_devices_count": known_devices_count,
                "vendor_patterns_count": vendor_patterns_count,
                "recent_known_devices": [
                    {"device_name": d.get("device_name"), "mac_address": d.get("mac_address")}
                    for d in recent_known_devices
                ],
                "top_vendors": [
                    {"vendor_name": v.get("vendor_name"), "pattern_count": v.get("pattern_count")}
                    for v in top_vendors
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get reference stats: {e}")
            return {
                "known_devices_count": 0,
                "vendor_patterns_count": 0,
                "recent_known_devices": [],
                "top_vendors": []
            }
    
    def _get_unknown_device_info(self, mac_address: str) -> Dict[str, Any]:
        """Return unknown device information"""
        return {
            "mac_address": mac_address,
            "resolved_name": "Unknown",
            "resolved_vendor": "Unknown",
            "resolved_type": "unknown",
            "source": "none"
        } 