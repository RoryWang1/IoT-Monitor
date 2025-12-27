#!/usr/bin/env python3
"""
Reference Data Import Script
Import reference data from JSON files to database for migration
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

class ReferenceDataImporter:
    """Import reference data from JSON files"""
    
    def __init__(self, import_dir: str = None):
        self.db_manager = PostgreSQLDatabaseManager()
        if import_dir:
            self.import_dir = Path(import_dir)
        else:
            self.import_dir = project_root / "reference_backup" / "export_data"
        
    async def initialize(self):
        """Initialize database connection"""
        await self.db_manager.initialize()
        
    async def cleanup(self):
        """Cleanup database connection"""
        await self.db_manager.close()
        
    def check_import_files(self) -> bool:
        """Check if import files exist"""
        if not self.import_dir.exists():
            print(f"Import directory not found: {self.import_dir}")
            return False
            
        required_files = [
            "vendor_patterns.json",
            "known_devices.json", 
            "ip_geolocation_ref_index.json"
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.import_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"Missing required files: {missing_files}")
            return False
            
        print(f"All required files found in {self.import_dir}")
        return True
        
    async def clear_existing_data(self):
        """Clear existing reference data (with confirmation)"""
        print("\nClearing existing reference data...")
        
        # Get current counts
        vendor_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM vendor_patterns"
        )
        device_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM known_devices"
        )
        ip_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM ip_geolocation_ref"
        )
        
        if vendor_count > 0 or device_count > 0 or ip_count > 0:
            print(f"Current data:")
            print(f"   - Vendor patterns: {vendor_count:,}")
            print(f"   - Known devices: {device_count:,}")
            print(f"   - IP geolocation: {ip_count:,}")
            
            response = input("\nDo you want to clear existing data? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("Import cancelled by user")
                return False
        
        # Disable protection and clear data
        print("Clearing existing data...")
        
        # Clear with CASCADE to handle foreign keys
        await self.db_manager.execute_command(
            "UPDATE vendor_patterns SET is_protected = FALSE"
        )
        await self.db_manager.execute_command(
            "UPDATE known_devices SET is_protected = FALSE"  
        )
        await self.db_manager.execute_command(
            "UPDATE ip_geolocation_ref SET is_protected = FALSE"
        )
        
        await self.db_manager.execute_command("DELETE FROM vendor_patterns")
        await self.db_manager.execute_command("DELETE FROM known_devices")
        await self.db_manager.execute_command("DELETE FROM ip_geolocation_ref")
        
        # Reset sequences
        await self.db_manager.execute_command(
            "SELECT setval('ip_geolocation_ref_id_seq', 1, false)"
        )
        
        print("Existing data cleared")
        return True
        
    async def import_vendor_patterns(self):
        """Import vendor_patterns data"""
        print("\nImporting vendor_patterns...")
        
        file_path = self.import_dir / "vendor_patterns.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        data = file_data["data"]
        
        # Prepare batch insert
        query = """
        INSERT INTO vendor_patterns (oui_pattern, vendor_name, device_category, is_protected, created_at)
        VALUES ($1, $2, $3, $4, $5)
        """
        
        batch_data = []
        for record in data:
            created_at = None
            if record.get("created_at"):
                created_at = datetime.fromisoformat(record["created_at"])
            
            batch_data.append((
                record["oui_pattern"],
                record["vendor_name"],
                record["device_category"],
                record.get("is_protected", True),
                created_at
            ))
        
        # Execute batch insert using bulk_insert
        columns = ['oui_pattern', 'vendor_name', 'device_category', 'is_protected', 'created_at']
        await self.db_manager.bulk_insert('vendor_patterns', columns, batch_data)
        
        print(f"Imported {len(batch_data)} vendor patterns")
        return len(batch_data)
        
    async def import_known_devices(self):
        """Import known_devices data"""
        print("\nImporting known_devices...")
        
        file_path = self.import_dir / "known_devices.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        data = file_data["data"]
        
        # Prepare batch insert
        query = """
        INSERT INTO known_devices (mac_address, device_name, device_type, vendor, notes, is_protected, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        batch_data = []
        for record in data:
            created_at = None
            if record.get("created_at"):
                created_at = datetime.fromisoformat(record["created_at"])
            
            batch_data.append((
                record["mac_address"],
                record["device_name"],
                record["device_type"],
                record["vendor"],
                record.get("notes"),
                record.get("is_protected", True),
                created_at
            ))
        
        # Execute batch insert using bulk_insert
        columns = ['mac_address', 'device_name', 'device_type', 'vendor', 'notes', 'is_protected', 'created_at']
        await self.db_manager.bulk_insert('known_devices', columns, batch_data)
        
        print(f"Imported {len(batch_data)} known devices")
        return len(batch_data)
        
    async def import_ip_geolocation_ref(self):
        """Import ip_geolocation_ref data from chunks"""
        print("\nImporting ip_geolocation_ref...")
        
        # Read index file
        index_path = self.import_dir / "ip_geolocation_ref_index.json"
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        total_chunks = index_data["total_chunks"]
        files = index_data["files"]
        
        print(f"Processing {total_chunks} chunk files...")
        
        total_imported = 0
        
        # Prepare insert query
        query = """
        INSERT INTO ip_geolocation_ref (id, start_ip, end_ip, country_code, country_name, asn, asn_name, is_protected, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        for i, filename in enumerate(files, 1):
            file_path = self.import_dir / filename
            
            if not file_path.exists():
                print(f"Warning: File not found: {filename}")
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            data = chunk_data["data"]
            
            # Prepare batch data
            batch_data = []
            for record in data:
                created_at = None
                if record.get("created_at"):
                    created_at = datetime.fromisoformat(record["created_at"])
                
                batch_data.append((
                    record["id"],
                    record["start_ip"],
                    record["end_ip"],
                    record["country_code"], 
                    record["country_name"],
                    record.get("asn"),
                    record.get("asn_name"),
                    record.get("is_protected", True),
                    created_at
                ))
            
            # Execute batch insert using bulk_insert
            columns = ['id', 'start_ip', 'end_ip', 'country_code', 'country_name', 'asn', 'asn_name', 'is_protected', 'created_at']
            await self.db_manager.bulk_insert('ip_geolocation_ref', columns, batch_data)
            
            total_imported += len(batch_data)
            print(f"Imported chunk {i}/{total_chunks}: {len(batch_data)} records")
        
        # Update sequence to correct value
        max_id = await self.db_manager.execute_scalar(
            "SELECT MAX(id) FROM ip_geolocation_ref"
        )
        if max_id:
            await self.db_manager.execute_command(
                f"SELECT setval('ip_geolocation_ref_id_seq', {max_id}, true)"
            )
        
        print(f"Imported {total_imported:,} IP geolocation records")
        return total_imported
        
    async def verify_import(self):
        """Verify imported data"""
        print("\nVerifying imported data...")
        
        # Get counts
        vendor_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM vendor_patterns"
        )
        device_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM known_devices"
        )
        ip_count = await self.db_manager.execute_scalar(
            "SELECT COUNT(*) FROM ip_geolocation_ref"
        )
        
        print(f"Imported data verification:")
        print(f"   - Vendor patterns: {vendor_count:,}")
        print(f"   - Known devices: {device_count:,}")
        print(f"   - IP geolocation: {ip_count:,}")
        print(f"   - Total: {vendor_count + device_count + ip_count:,}")
        
        # Check for any obvious issues
        issues = []
        
        if vendor_count == 0:
            issues.append("No vendor patterns imported")
        if device_count == 0:
            issues.append("No known devices imported")
        if ip_count == 0:
            issues.append("No IP geolocation data imported")
            
        if issues:
            print(f"Issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("All data imported successfully!")
        
        return len(issues) == 0
        
    async def import_all(self, clear_existing: bool = True):
        """Import all reference data"""
        print("Starting reference data import...")
        print(f"Import directory: {self.import_dir}")
        
        # Check files
        if not self.check_import_files():
            return False
        
        # Clear existing data if requested
        if clear_existing:
            if not await self.clear_existing_data():
                return False
        
        try:
            # Import each table
            vendor_count = await self.import_vendor_patterns()
            device_count = await self.import_known_devices()
            ip_count = await self.import_ip_geolocation_ref()
            
            # Verify import
            success = await self.verify_import()
            
            if success:
                print(f"\nImport completed successfully!")
                print(f"Total records imported: {vendor_count + device_count + ip_count:,}")
            else:
                print(f"\nImport completed with issues")
                
            return success
            
        except Exception as e:
            print(f"\nImport failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import reference data from JSON files")
    parser.add_argument("--import-dir", help="Directory containing JSON files to import")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    args = parser.parse_args()
    
    importer = ReferenceDataImporter(args.import_dir)
    
    try:
        await importer.initialize()
        success = await importer.import_all(clear_existing=not args.no_clear)
        sys.exit(0 if success else 1)
    finally:
        await importer.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 