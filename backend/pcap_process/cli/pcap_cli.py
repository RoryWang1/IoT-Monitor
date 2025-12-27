"""
Unified PCAP Processing CLI

Single command-line interface for all PCAP processing operations.
Replaces multiple scattered scripts with a unified tool.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
import click

# Add project root to path for imports (only when running as script)
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    backend_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_path))

from database.connection import PostgreSQLDatabaseManager

from pcap_process.core.engine import PcapProcessingEngine
from pcap_process.core.config import ProcessingConfig

logger = logging.getLogger(__name__)


class PcapCLI:
    """
    Unified command-line interface for PCAP processing
    """
    
    def __init__(self):
        """Initialize CLI"""
        self.setup_logging()
        # UTC timezone for consistent time handling
        self.utc_timezone = timezone.utc
        logger.info("PCAP CLI initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('pcap_processing.log')
            ]
        )
    
    async def run(self):
        """Main CLI entry point"""
        print("IoT Device Monitor - PCAP Processing CLI")
        print("=" * 60)
        
        # Initialize database connection
        db_manager = PostgreSQLDatabaseManager()
        
        try:
            if not await db_manager.initialize():
                print("Failed to connect to database")
                return 1
            
            print("Database connection established")
            
            # Show main menu
            while True:
                choice = self.show_main_menu()
                
                if choice == '1':
                    await self.process_experiments(db_manager)
                elif choice == '2':
                    await self.process_single_experiment(db_manager)
                elif choice == '3':
                    await self.process_single_file(db_manager)
                elif choice == '4':
                    await self.show_statistics(db_manager)
                elif choice == '5':
                    await self.clear_data(db_manager)
                elif choice == '6':
                    await self.verify_schema(db_manager)
                elif choice == '7':
                    await self.analyze_experiment(db_manager)
                elif choice == '8':
                    await self.quality_check(db_manager)
                elif choice == '9':
                    await self._check_data_quality()
                elif choice == '10':
                    await self._test_pcap_processing_with_dedup()
                elif choice == '0':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"CLI error: {e}")
        finally:
            await db_manager.close()
        
        return 0
    
    def show_main_menu(self) -> str:
        """Show main menu and get user choice"""
        print("\nChoose an operation:")
        print("1. Process all experiments")
        print("2. Process single experiment")
        print("3. Process single PCAP file")
        print("4. Show statistics")
        print("5. Clear existing data")
        print("6. Verify database schema")
        print("7. Analyze experiment")
        print("8. Quality check")
        print("9. Check data quality")
        print("10. Test PCAP processing with deduplication")
        print("0. Exit")
        
        return input("\nEnter choice (0-10): ").strip()
    
    async def process_experiments(self, db_manager: PostgreSQLDatabaseManager):
        """Process all experiments"""
        print("\nProcessing all experiments...")
        
        # Get PCAP input path
        pcap_path = self.get_pcap_input_path()
        if not pcap_path:
            return
        
        config = ProcessingConfig()
        
        async with PcapProcessingEngine(db_manager, config) as engine:
            start_time = datetime.now(self.utc_timezone)
            
            result = await engine.process_all_experiments(pcap_path)
            
            end_time = datetime.now(self.utc_timezone)
            duration = (end_time - start_time).total_seconds()
            
            # Display results
            self.display_processing_results(result, duration)
    
    async def process_single_experiment(self, db_manager: PostgreSQLDatabaseManager):
        """Process a single experiment"""
        print("\nProcessing single experiment...")
        
        # Get PCAP input path and select experiment
        pcap_path = self.get_pcap_input_path()
        if not pcap_path:
            return
        
        experiments = self.find_experiments(pcap_path)
        if not experiments:
            print("No experiments found")
            return
        
        # Show experiment selection
        print("\nAvailable experiments:")
        for i, exp in enumerate(experiments, 1):
            print(f"  {i}. {exp.name}")
        
        try:
            choice = int(input(f"\nSelect experiment (1-{len(experiments)}): ")) - 1
            if choice < 0 or choice >= len(experiments):
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid input")
            return
        
        selected_exp = experiments[choice]
        config = ProcessingConfig()
        
        async with PcapProcessingEngine(db_manager, config) as engine:
            start_time = datetime.now(self.utc_timezone)
            
            result = await engine.process_experiment(selected_exp)
            
            end_time = datetime.now(self.utc_timezone)
            duration = (end_time - start_time).total_seconds()
            
            # Display results
            if result.get('success'):
                print(f"\nExperiment processed successfully!")
                print(f"   Experiment: {result['experiment_id']}")
                print(f"   Files processed: {result.get('files_processed', 0)}")
                print(f"   Packets processed: {result.get('packets_processed', 0)}")
                print(f"   Duration: {duration:.2f} seconds")
            else:
                print(f"\nProcessing failed: {result.get('error')}")
    
    async def process_single_file(self, db_manager: PostgreSQLDatabaseManager):
        """Process a single PCAP file"""
        print("\nProcessing single PCAP file...")
        
        # Get file path
        file_path = input("Enter PCAP file path: ").strip()
        if not file_path:
            print("No file path provided")
            return
        
        pcap_file = Path(file_path)
        if not pcap_file.exists():
            print(f"File not found: {pcap_file}")
            return
        
        # Get experiment ID and device MAC
        experiment_id = input("Enter experiment ID: ").strip() or "manual_processing"
        device_mac = input("Enter device MAC address (e.g., AA:BB:CC:DD:EE:FF): ").strip()
        
        if not device_mac:
            print("Device MAC address is required")
            return
        
        config = ProcessingConfig()
        
        async with PcapProcessingEngine(db_manager, config) as engine:
            start_time = datetime.now(self.utc_timezone)
            
            result = await engine.process_single_file(pcap_file, experiment_id, device_mac)
            
            end_time = datetime.now(self.utc_timezone)
            duration = (end_time - start_time).total_seconds()
            
            # Display results
            if result.get('success'):
                print(f"\nFile processed successfully!")
                print(f"   File: {pcap_file.name}")
                print(f"   Device: {device_mac}")
                print(f"   Packets processed: {result.get('packets_processed', 0)}")
                print(f"   Duration: {duration:.2f} seconds")
            else:
                print(f"\nProcessing failed: {result.get('error')}")
    
    async def show_statistics(self, db_manager: PostgreSQLDatabaseManager):
        """Show processing statistics"""
        print("\nDatabase Statistics:")
        print("=" * 40)
        
        try:
            config = ProcessingConfig()
            async with PcapProcessingEngine(db_manager, config) as engine:
                stats = await engine.storage.get_storage_stats()
                
                if 'error' in stats:
                    print(f"Error getting stats: {stats['error']}")
                    return
                
                print(f"Total packet flows: {stats.get('total_packet_flows', 0):,}")
                print(f"Unique devices: {stats.get('unique_devices', 0)}")
                print(f"Unique experiments: {stats.get('unique_experiments', 0)}")
                
                if stats.get('earliest_packet'):
                    print(f"Earliest packet: {stats['earliest_packet']}")
                if stats.get('latest_packet'):
                    print(f"Latest packet: {stats['latest_packet']}")
                
                print(f"Cached devices: {stats.get('cached_devices', 0)}")
        
        except Exception as e:
            print(f"Error getting statistics: {e}")
    
    async def clear_data(self, db_manager: PostgreSQLDatabaseManager):
        """Clear existing data"""
        print("\nThis will delete ALL packet flows and device data!")
        confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
        
        if confirm != 'yes':
            print("Operation cancelled")
            return
        
        try:
            print("Clearing packet flows...")
            await db_manager.execute_command("DELETE FROM packet_flows")
            
            print("Clearing devices...")
            await db_manager.execute_command("DELETE FROM devices WHERE experiment_id IS NOT NULL")
            
            print("Data cleared successfully")
        
        except Exception as e:
            print(f"Error clearing data: {e}")
    
    async def verify_schema(self, db_manager: PostgreSQLDatabaseManager):
        """Verify database schema"""
        print("\nVerifying database schema...")
        
        required_tables = ['devices', 'packet_flows']
        
        try:
            for table in required_tables:
                check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
                """
                
                result = await db_manager.execute_query(check_query, (table,))
                
                if result and result[0]['exists']:
                    print(f"Table '{table}' exists")
                else:
                    print(f"Table '{table}' missing")
        
        except Exception as e:
            print(f"Error verifying schema: {e}")
    
    def get_pcap_input_path(self) -> Path:
        """Get PCAP input directory path"""
        # Default to project structure
        project_root = Path(__file__).parent.parent.parent.parent
        default_path = project_root / "pcap_input"
        
        if default_path.exists():
            return default_path
        
        # Try relative to current directory
        custom_path = input(f"PCAP input directory (default: {default_path}): ").strip()
        
        if custom_path:
            path = Path(custom_path)
            if path.exists():
                return path
            else:
                print(f"Directory not found: {path}")
                return None
        
        return default_path if default_path.exists() else None
    
    def find_experiments(self, pcap_path: Path) -> list:
        """Find experiment directories"""
        return [d for d in pcap_path.iterdir() 
                if d.is_dir() and d.name.startswith('experiment_')]
    
    def display_processing_results(self, result: Dict[str, Any], duration: float):
        """Display processing results"""
        print("\nProcessing Results:")
        print("=" * 40)
        
        if result.get('success'):
            print(f"Total experiments: {result.get('total_experiments', 0)}")
            print(f"Successful: {result.get('successful', 0)}")
            print(f"Failed: {result.get('failed', 0)}")
            print(f"Duration: {duration:.2f} seconds")
            
            # Show individual experiment results
            if result.get('experiment_results'):
                print("\nExperiment Details:")
                for exp_result in result['experiment_results']:
                    if exp_result.get('success'):
                        print(f"   {exp_result['experiment_id']}: "
                              f"{exp_result.get('files_processed', 0)} files, "
                              f"{exp_result.get('packets_processed', 0)} packets")
                    else:
                        print(f"   {exp_result.get('experiment_id', 'Unknown')}: "
                              f"{exp_result.get('error', 'Unknown error')}")
        else:
            print(f"Processing failed: {result.get('error', 'Unknown error')}")
    
    async def analyze_experiment(self, db_manager: PostgreSQLDatabaseManager):
        """Analyze a single experiment"""
        print("\nAnalyzing experiment...")
        
        # Get experiment ID
        experiment_id = input("Enter experiment ID: ").strip()
        if not experiment_id:
            print("Experiment ID is required")
            return
        
        try:
            config = ProcessingConfig()
            async with PcapProcessingEngine(db_manager, config) as engine:
                result = await engine.analyze_experiment(experiment_id)
                
                if result.get('success'):
                    print(f"\nExperiment analysis completed successfully!")
                    print(f"   Experiment: {result['experiment_id']}")
                    print(f"   Analysis results: {result['analysis_results']}")
                else:
                    print(f"\nAnalysis failed: {result.get('error')}")
        
        except Exception as e:
            print(f"Error analyzing experiment: {e}")
            logger.error(f"Experiment analysis error: {e}")
    
    async def quality_check(self, db_manager: PostgreSQLDatabaseManager):
        """Check data quality and remove duplicates"""
        print("\nChecking data quality...")
        
        try:
            from ..storage.packet_storage import PacketStorage
            storage = PacketStorage(db_manager)
            
            # Check all experiments
            experiments_query = "SELECT experiment_id, experiment_name FROM experiments ORDER BY created_at DESC"
            experiments = await db_manager.execute_query(experiments_query)
            
            if not experiments:
                print("No experiments found in database")
                return
            
            print(f"\nFound {len(experiments)} experiments")
            
            # Get user input for experiment selection
            experiment_choices = ["all"] + [exp['experiment_id'] for exp in experiments[:10]]
            experiment_choice = input(f"Select experiment to analyze ({', '.join(experiment_choices)}): ").strip()
            
            if experiment_choice == "all":
                # Analyze all data
                quality_report = await storage.analyze_data_quality()
                print("\nOverall Data Quality Report:")
            else:
                # Analyze specific experiment
                quality_report = await storage.analyze_data_quality(experiment_choice)
                print(f"\nData Quality Report for Experiment: {experiment_choice}")
            
            if 'error' in quality_report:
                print(f"Error: {quality_report['error']}")
                return
            
            # Display basic statistics
            basic_stats = quality_report.get('basic_statistics', {})
            print("\nBasic Statistics:")
            print(f"  Total Records: {basic_stats.get('total_records', 0):,}")
            print(f"  Unique Flows: {basic_stats.get('unique_flows', 0):,}")
            print(f"  Unique Devices: {basic_stats.get('unique_devices', 0)}")
            print(f"  Unique Protocols: {basic_stats.get('unique_protocols', 0)}")
            print(f"  Average Packet Size: {basic_stats.get('avg_packet_size', 0):.1f} bytes")
            print(f"  Time Range: {basic_stats.get('earliest_timestamp')} to {basic_stats.get('latest_timestamp')}")
            
            # Display data quality summary
            quality_summary = quality_report.get('data_quality_summary', {})
            print("\nData Quality Summary:")
            print(f"  Unique Flow Ratio: {quality_summary.get('unique_flow_ratio', 0):.2%}")
            print(f"  Duplicate Flows: {quality_summary.get('duplicate_flows', 0)}")
            print(f"  Quality Status: {'Issues Found' if quality_summary.get('has_quality_issues') else 'Good'}")
            
            # Display potential duplicates
            duplicates = quality_report.get('potential_duplicates', [])
            if duplicates:
                print("\nPotential Duplicates Found:")
                for dup in duplicates[:3]:
                    print(f"  Flow Hash: {dup['flow_hash'][:16]}... (Records: {dup['record_count']}, Devices: {dup['device_count']})")
            
            # Display device perspective distribution
            device_stats = quality_report.get('device_perspectives', [])
            if device_stats:
                print("\nTop Devices by Flow Count:")
                for device in device_stats[:3]:
                    print(f"  Device: {device['device_id'][:8]}... (Total: {device['total_flows']}, In: {device['inbound_flows']}, Out: {device['outbound_flows']})")
            
            # Display protocol distribution
            protocols = quality_report.get('protocol_distribution', [])
            if protocols:
                print("\nTop Protocols:")
                for proto in protocols[:5]:
                    print(f"  {proto['protocol']}: {proto['flow_count']:,} flows ({proto['device_count']} devices)")
            
            print("\nData quality analysis completed")
            
        except Exception as e:
            print(f"Error during quality check: {e}")
            logger.error(f"Quality check error: {e}")

    async def _check_data_quality(self):
        """Check the data quality and the effect of deduplication"""
        click.echo("\nAnalyzing Data Quality...")
        
        try:
            from ..storage.packet_storage import PacketStorage
            storage = PacketStorage(self.db_manager)
            
            # Check the basic statistics
            stats_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT (device_id, packet_timestamp, src_ip, dst_ip, 
                               COALESCE(src_port, 0), COALESCE(dst_port, 0), 
                               protocol, flow_direction)) as unique_combinations,
                COUNT(DISTINCT device_id) as unique_devices,
                COUNT(DISTINCT experiment_id) as unique_experiments
            FROM packet_flows
            """
            stats = await self.db_manager.execute_query(stats_query)
            
            if stats:
                stat = stats[0]
                total = stat['total_records']
                unique = stat['unique_combinations']
                duplicate_rate = ((total - unique) / total * 100) if total > 0 else 0
                
                click.echo(f"Database Quality Report:")
                click.echo(f"  Total Records: {total:,}")
                click.echo(f"  Unique Combinations: {unique:,}")
                click.echo(f"  Duplicate Rate: {duplicate_rate:.2f}%")
                click.echo(f"  Unique Devices: {stat['unique_devices']}")
                click.echo(f"  Unique Experiments: {stat['unique_experiments']}")
                
                if duplicate_rate == 0:
                    click.echo("Perfect! No duplicate records found.")
                else:
                    click.echo(f"Found {total - unique:,} duplicate records ({duplicate_rate:.2f}%)")
            
            # Check the constraints status
            constraints_query = """
            SELECT constraint_name, constraint_type 
            FROM information_schema.table_constraints 
            WHERE table_name = 'packet_flows' AND constraint_type = 'UNIQUE'
            """
            constraints = await self.db_manager.execute_query(constraints_query)
            
            click.echo(f"\nDatabase Constraints:")
            for constraint in constraints:
                click.echo(f"  ✓ {constraint['constraint_name']}: {constraint['constraint_type']}")
            
        except Exception as e:
            click.echo(f"Data quality check failed: {e}")

    async def _test_pcap_processing_with_dedup(self):
        """Test the deduplication effect of new PCAP file processing"""
        click.echo("\nTesting PCAP Processing with Deduplication...")
        
        try:
            from ..storage.packet_storage import PacketStorage
            from ..parsers.packet_parser import PacketParser
            from pathlib import Path
            
            storage = PacketStorage(self.db_manager)
            parser = PacketParser()
            
            # Get the current record count
            before_query = "SELECT COUNT(*) as count FROM packet_flows"
            before_count = await self.db_manager.execute_query(before_query)
            initial_count = before_count[0]['count'] if before_count else 0
            
            click.echo(f"Initial packet_flows count: {initial_count:,}")
            
            # Simulate processing an existing PCAP file (should not increase records)
            pcap_files = []
            # Use relative path to find the project root directory
            project_root = Path(__file__).parent.parent.parent.parent
            pcap_dir = project_root / "pcap_input" / "experiment_1"
            if pcap_dir.exists():
                pcap_files = list(pcap_dir.glob("*.pcap"))[:3]  # Test the first 3 files
            
            if not pcap_files:
                click.echo("No PCAP files found for testing")
                return
            
            for pcap_file in pcap_files:
                # Extract MAC address from filename
                filename = pcap_file.name
                mac_parts = filename.split('_')[0]
                if len(mac_parts) == 17:  # Check MAC address length
                    device_mac = mac_parts
                    
                    click.echo(f"\nProcessing {filename}")
                    click.echo(f"   Device MAC: {device_mac}")
                    
                    try:
                        # Parse PCAP file
                        packet_flows = await parser.parse_pcap_file(pcap_file, device_mac)
                        click.echo(f"   Parsed {len(packet_flows)} flows")
                        
                        # Try storing (should be prevented by constraints)
                        result = await storage.store_packet_flows(
                            packet_flows, "experiment_1", device_mac
                        )
                        click.echo(f"   Storage result: {result.get('stored_count', 0)} new records")
                        
                    except Exception as e:
                        if "duplicate key value violates unique constraint" in str(e):
                            click.echo(f"   Duplicate prevention working: {e}")
                        else:
                            click.echo(f"   Unexpected error: {e}")
            
            # Check the final record count
            after_query = "SELECT COUNT(*) as count FROM packet_flows"
            after_count = await self.db_manager.execute_query(after_query)
            final_count = after_count[0]['count'] if after_count else 0
            
            click.echo(f"\nFinal packet_flows count: {final_count:,}")
            click.echo(f"New records added: {final_count - initial_count:,}")
            
            if final_count == initial_count:
                click.echo("Perfect! Deduplication is working correctly.")
            else:
                click.echo(f"{final_count - initial_count:,} new records were added.")
                
        except Exception as e:
            click.echo(f"PCAP processing test failed: {e}")


async def main():
    """CLI entry point"""
    cli = PcapCLI()
    return await cli.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 