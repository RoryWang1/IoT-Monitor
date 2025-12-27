#!/usr/bin/env python3
"""
Reference Data Export Script
Export reference data from database to JSON files for migration
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import asyncpg
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import PostgreSQLDatabaseManager

class ReferenceDataExporter:
    """Export reference data to JSON files"""
    
    def __init__(self):
        self.db_manager = PostgreSQLDatabaseManager()
        self.output_dir = project_root / "reference_backup" / "export_data"
        self.max_file_size_mb = 20  # GitHub file size limit
        
    async def initialize(self):
        """Initialize database connection"""
        await self.db_manager.initialize()
        
    async def cleanup(self):
        """Cleanup database connection"""
        await self.db_manager.close()
        
    def ensure_output_dir(self):
        """Ensure output directory exists"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def export_vendor_patterns(self):
        """Export vendor_patterns table"""
        print("📦 Exporting vendor_patterns...")
        
        query = """
        SELECT oui_pattern, vendor_name, device_category, 
               is_protected, created_at
        FROM vendor_patterns 
        ORDER BY oui_pattern
        """
        
        results = await self.db_manager.execute_query(query)
        
        data = []
        for row in results:
            data.append({
                "oui_pattern": row["oui_pattern"],
                "vendor_name": row["vendor_name"], 
                "device_category": row["device_category"],
                "is_protected": row["is_protected"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        # Save as single file (small dataset)
        output_file = self.output_dir / "vendor_patterns.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "table_name": "vendor_patterns",
                "export_date": datetime.now().isoformat(),
                "total_records": len(data),
                "data": data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(data)} vendor patterns to {output_file}")
        return len(data)
        
    async def export_known_devices(self):
        """Export known_devices table"""
        print("📦 Exporting known_devices...")
        
        query = """
        SELECT mac_address, device_name, device_type, vendor, 
               notes, is_protected, created_at
        FROM known_devices 
        ORDER BY mac_address
        """
        
        results = await self.db_manager.execute_query(query)
        
        data = []
        for row in results:
            data.append({
                "mac_address": row["mac_address"],
                "device_name": row["device_name"],
                "device_type": row["device_type"],
                "vendor": row["vendor"],
                "notes": row["notes"],
                "is_protected": row["is_protected"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        # Save as single file (small dataset)
        output_file = self.output_dir / "known_devices.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "table_name": "known_devices",
                "export_date": datetime.now().isoformat(),
                "total_records": len(data),
                "data": data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(data)} known devices to {output_file}")
        return len(data)
        
    async def export_ip_geolocation_ref(self):
        """Export ip_geolocation_ref table in chunks"""
        print("📦 Exporting ip_geolocation_ref...")
        
        # Get total count
        total_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM ip_geolocation_ref"
        )
        
        chunk_size = 50000  # Records per file
        total_files = (total_count + chunk_size - 1) // chunk_size
        
        print(f"📊 Total records: {total_count:,}")
        print(f"📄 Will create {total_files} files")
        
        exported_count = 0
        
        for chunk_num in range(total_files):
            offset = chunk_num * chunk_size
            
            query = """
            SELECT id, start_ip, end_ip, country_code, country_name,
                   asn, asn_name, is_protected, created_at
            FROM ip_geolocation_ref 
            ORDER BY id
            LIMIT $1 OFFSET $2
            """
            
            results = await self.db_manager.execute_query(query, (chunk_size, offset))
            
            data = []
            for row in results:
                data.append({
                    "id": row["id"],
                    "start_ip": str(row["start_ip"]),
                    "end_ip": str(row["end_ip"]),
                    "country_code": row["country_code"],
                    "country_name": row["country_name"],
                    "asn": row["asn"],
                    "asn_name": row["asn_name"],
                    "is_protected": row["is_protected"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            
            # Save chunk file
            output_file = self.output_dir / f"ip_geolocation_ref_part_{chunk_num + 1:03d}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "table_name": "ip_geolocation_ref",
                    "export_date": datetime.now().isoformat(),
                    "chunk_info": {
                        "chunk_number": chunk_num + 1,
                        "total_chunks": total_files,
                        "chunk_size": chunk_size,
                        "offset": offset
                    },
                    "total_records_in_chunk": len(data),
                    "data": data
                }, f, indent=2, ensure_ascii=False)
            
            exported_count += len(data)
            print(f"Exported chunk {chunk_num + 1}/{total_files}: {len(data)} records to {output_file}")
        
        # Create index file
        index_file = self.output_dir / "ip_geolocation_ref_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "table_name": "ip_geolocation_ref",
                "export_date": datetime.now().isoformat(),
                "total_records": total_count,
                "total_chunks": total_files,
                "chunk_size": chunk_size,
                "files": [f"ip_geolocation_ref_part_{i+1:03d}.json" for i in range(total_files)]
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Created index file: {index_file}")
        return exported_count
        
    async def export_all(self):
        """Export all reference data"""
        print("🚀 Starting reference data export...")
        print(f"📁 Output directory: {self.output_dir}")
        
        self.ensure_output_dir()
        
        # Export each table
        vendor_count = await self.export_vendor_patterns()
        device_count = await self.export_known_devices() 
        ip_count = await self.export_ip_geolocation_ref()
        
        # Create summary
        summary = {
            "export_date": datetime.now().isoformat(),
            "tables_exported": {
                "vendor_patterns": vendor_count,
                "known_devices": device_count,
                "ip_geolocation_ref": ip_count
            },
            "total_records": vendor_count + device_count + ip_count
        }
        
        summary_file = self.output_dir / "export_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nExport completed!")
        print(f"Summary:")
        print(f"   - Vendor patterns: {vendor_count:,}")
        print(f"   - Known devices: {device_count:,}")
        print(f"   - IP geolocation: {ip_count:,}")
        print(f"   - Total: {summary['total_records']:,}")
        print(f"Files saved to: {self.output_dir}")

async def main():
    """Main function"""
    exporter = ReferenceDataExporter()
    
    try:
        await exporter.initialize()
        await exporter.export_all()
    finally:
        await exporter.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 