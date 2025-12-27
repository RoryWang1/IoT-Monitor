#!/usr/bin/env python3
"""
Quick Reference Data Setup Script
Simple script for quickly exporting and importing reference data
"""

import asyncio
import sys
from pathlib import Path
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command):
    """Run shell command and return result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def print_banner(text):
    """Print formatted banner"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def export_reference_data():
    """Export reference data"""
    print_banner("EXPORTING REFERENCE DATA")
    
    export_script = project_root / "utils" / "export_reference_data.py"
    command = f"cd {project_root} && python {export_script}"
    
    print("🚀 Starting export...")
    success, stdout, stderr = run_command(command)
    
    if success:
        print("Export completed successfully!")
        
        # Show file list
        export_dir = project_root / "reference_backup" / "export_data"
        if export_dir.exists():
            print(f"\nFiles exported to: {export_dir}")
            files = list(export_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            print(f"Total files: {len(files)}")
            print(f"Total size: {total_size / (1024*1024):.1f} MB")
    else:
        print("Export failed!")
        if stderr:
            print(f"Error: {stderr}")
    
    return success

def import_reference_data(clear_existing=True):
    """Import reference data"""
    print_banner("IMPORTING REFERENCE DATA")
    
    import_script = project_root / "utils" / "import_reference_data.py"
    command = f"cd {project_root} && python {import_script}"
    
    if not clear_existing:
        command += " --no-clear"
    
    print("Starting import...")
    success, stdout, stderr = run_command(command)
    
    if success:
        print("Import completed successfully!")
    else:
        print("Import failed!")
        if stderr:
            print(f"Error: {stderr}")
    
    return success

def check_system_status():
    """Check if database system is running"""
    print_banner("CHECKING SYSTEM STATUS")
    
    # Check database connection
    test_command = f"cd {project_root} && psql -h localhost -p 5433 -U iot_user -d iot_monitor -c 'SELECT 1;' > /dev/null 2>&1"
    success, _, _ = run_command(test_command)
    
    if success:
        print("Database is running and accessible")
        return True
    else:
        print("Database is not running or not accessible")
        print("Try running: ./utils/start_system.sh")
        return False

def show_usage():
    """Show usage information"""
    print("""
Quick Reference Data Setup Tool

Available commands:
  export    - Export current reference data to JSON files
  import    - Import reference data from JSON files (clears existing)
  check     - Check system status
  help      - Show this help message

Examples:
  python utils/quick_reference_setup.py export
  python utils/quick_reference_setup.py import
  python utils/quick_reference_setup.py check

For more advanced options, use the individual scripts:
  - utils/export_reference_data.py
  - utils/import_reference_data.py
""")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "export":
        if not check_system_status():
            sys.exit(1)
        
        success = export_reference_data()
        sys.exit(0 if success else 1)
        
    elif command == "import":
        if not check_system_status():
            sys.exit(1)
            
        success = import_reference_data()
        sys.exit(0 if success else 1)
        
    elif command == "check":
        success = check_system_status()
        sys.exit(0 if success else 1)
        
    elif command in ["help", "-h", "--help"]:
        show_usage()
        
    else:
        print(f"Unknown command: {command}")
        show_usage()
        sys.exit(1)

if __name__ == "__main__":
    main() 