#!/usr/bin/env python3
"""
Migration Management Utility for Smart Parking Management System
Provides easy commands for managing database migrations
"""

import asyncio
import sys
import argparse
import subprocess
import os
from pathlib import Path
from datetime import datetime

# Add the parent directory to sys.path to import our app
sys.path.append(str(Path(__file__).resolve().parents[1]))

class MigrationManager:
    """Migration management utility"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).resolve().parents[1]
        self.alembic_ini = self.backend_dir / "alembic.ini"
        
        if not self.alembic_ini.exists():
            raise FileNotFoundError("alembic.ini not found. Please run from backend directory.")
    
    def run_command(self, command: list, capture_output=False):
        """Run a command and return the result"""
        try:
            if capture_output:
                result = subprocess.run(command, cwd=self.backend_dir, capture_output=True, text=True)
                return result.returncode == 0, result.stdout, result.stderr
            else:
                result = subprocess.run(command, cwd=self.backend_dir)
                return result.returncode == 0
        except Exception as e:
            print(f"Error running command: {e}")
            return False
    
    def check_alembic(self):
        """Check if Alembic is available"""
        success, stdout, stderr = self.run_command(["alembic", "--version"], capture_output=True)
        if success:
            print(f"✅ Alembic available: {stdout.strip()}")
            return True
        else:
            print("❌ Alembic not found. Please install it: pip install alembic")
            return False
    
    def current_revision(self):
        """Show current migration revision"""
        print("🔍 Current migration revision:")
        success, stdout, stderr = self.run_command(["alembic", "current"], capture_output=True)
        if success:
            if stdout.strip():
                print(f"Current: {stdout.strip()}")
            else:
                print("No migrations applied yet")
        else:
            print(f"Error: {stderr}")
        return success
    
    def migration_history(self):
        """Show migration history"""
        print("📜 Migration history:")
        success = self.run_command(["alembic", "history", "--verbose"])
        return success
    
    def create_migration(self, message: str, autogenerate: bool = True):
        """Create a new migration"""
        print(f"🆕 Creating migration: {message}")
        
        # Generate timestamp-based revision ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        command = ["alembic", "revision"]
        if autogenerate:
            command.append("--autogenerate")
        command.extend(["-m", message])
        
        success = self.run_command(command)
        if success:
            print("✅ Migration created successfully")
        else:
            print("❌ Failed to create migration")
        return success
    
    def upgrade(self, revision: str = "head"):
        """Upgrade to a specific revision"""
        print(f"⬆️  Upgrading to: {revision}")
        success = self.run_command(["alembic", "upgrade", revision])
        if success:
            print("✅ Upgrade completed successfully")
        else:
            print("❌ Upgrade failed")
        return success
    
    def downgrade(self, revision: str = "-1"):
        """Downgrade to a specific revision"""
        print(f"⬇️  Downgrading to: {revision}")
        
        # Confirm downgrade
        confirm = input("Are you sure you want to downgrade? This may result in data loss. (y/N): ")
        if confirm.lower() != 'y':
            print("Downgrade cancelled")
            return False
        
        success = self.run_command(["alembic", "downgrade", revision])
        if success:
            print("✅ Downgrade completed successfully")
        else:
            print("❌ Downgrade failed")
        return success
    
    def show_migration(self, revision: str):
        """Show details of a specific migration"""
        print(f"🔍 Migration details: {revision}")
        success = self.run_command(["alembic", "show", revision])
        return success
    
    def stamp(self, revision: str):
        """Mark a revision as current without running migrations"""
        print(f"🏷️  Stamping revision: {revision}")
        
        # Confirm stamp
        confirm = input("Are you sure you want to stamp this revision? (y/N): ")
        if confirm.lower() != 'y':
            print("Stamp cancelled")
            return False
        
        success = self.run_command(["alembic", "stamp", revision])
        if success:
            print("✅ Revision stamped successfully")
        else:
            print("❌ Stamp failed")
        return success
    
    def check_migration_conflicts(self):
        """Check for migration conflicts"""
        print("🔍 Checking for migration conflicts...")
        
        # Get current revision
        success, current_stdout, _ = self.run_command(["alembic", "current"], capture_output=True)
        if not success:
            print("❌ Could not determine current revision")
            return False
        
        # Get available revisions
        success, history_stdout, _ = self.run_command(["alembic", "history"], capture_output=True)
        if not success:
            print("❌ Could not get migration history")
            return False
        
        # Check for branches
        if "branch" in history_stdout.lower():
            print("⚠️  Migration branches detected. You may need to merge migrations.")
            return False
        
        print("✅ No migration conflicts detected")
        return True
    
    def validate_migrations(self):
        """Validate migration consistency"""
        print("🔍 Validating migrations...")
        
        # Try a dry run to head
        success, stdout, stderr = self.run_command(["alembic", "upgrade", "head", "--sql"], capture_output=True)
        if success:
            print("✅ Migrations are valid")
            return True
        else:
            print(f"❌ Migration validation failed: {stderr}")
            return False
    
    def reset_database(self):
        """Reset database to clean state"""
        print("🔄 Resetting database...")
        
        # Confirm reset
        confirm = input("This will destroy all data. Are you absolutely sure? (y/N): ")
        if confirm.lower() != 'y':
            print("Reset cancelled")
            return False
        
        # Downgrade to base
        success = self.downgrade("base")
        if not success:
            return False
        
        # Upgrade to head
        success = self.upgrade("head")
        return success
    
    def auto_generate_migration(self, message: str):
        """Auto-generate migration based on model changes"""
        print(f"🤖 Auto-generating migration: {message}")
        
        success = self.run_command(["alembic", "revision", "--autogenerate", "-m", message])
        if success:
            print("✅ Auto-generated migration created")
            print("⚠️  Please review the generated migration before applying it")
        else:
            print("❌ Auto-generation failed")
        return success
    
    def merge_migrations(self, revisions: list, message: str):
        """Merge multiple migration heads"""
        print(f"🔀 Merging migrations: {', '.join(revisions)}")
        
        command = ["alembic", "merge"] + revisions + ["-m", message]
        success = self.run_command(command)
        if success:
            print("✅ Migrations merged successfully")
        else:
            print("❌ Merge failed")
        return success
    
    def backup_database(self):
        """Create database backup before migrations"""
        print("💾 Creating database backup...")
        
        # This would implement database backup logic
        # For now, just show the command that should be run
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/parking_db")
        
        if "postgresql" in db_url:
            print("To backup PostgreSQL database, run:")
            print(f"pg_dump {db_url} > backup_$(date +%Y%m%d_%H%M%S).sql")
        
        return True
    
    def interactive_mode(self):
        """Interactive migration management"""
        print("🎮 Interactive Migration Manager")
        print("=" * 40)
        
        while True:
            print("\nAvailable commands:")
            print("1. Show current revision")
            print("2. Show migration history")
            print("3. Create new migration")
            print("4. Upgrade migrations")
            print("5. Downgrade migrations")
            print("6. Validate migrations")
            print("7. Check conflicts")
            print("8. Reset database")
            print("9. Auto-generate migration")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-9): ").strip()
            
            if choice == "0":
                print("Goodbye! 👋")
                break
            elif choice == "1":
                self.current_revision()
            elif choice == "2":
                self.migration_history()
            elif choice == "3":
                message = input("Enter migration message: ").strip()
                if message:
                    self.create_migration(message)
            elif choice == "4":
                revision = input("Enter revision (default: head): ").strip() or "head"
                self.upgrade(revision)
            elif choice == "5":
                revision = input("Enter revision (default: -1): ").strip() or "-1"
                self.downgrade(revision)
            elif choice == "6":
                self.validate_migrations()
            elif choice == "7":
                self.check_migration_conflicts()
            elif choice == "8":
                self.reset_database()
            elif choice == "9":
                message = input("Enter migration message: ").strip()
                if message:
                    self.auto_generate_migration(message)
            else:
                print("Invalid choice. Please try again.")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Migration Management Utility')
    parser.add_argument('command', nargs='?', choices=[
        'current', 'history', 'create', 'upgrade', 'downgrade', 
        'show', 'stamp', 'check', 'validate', 'reset', 'auto', 
        'merge', 'backup', 'interactive'
    ], help='Migration command to run')
    
    parser.add_argument('--message', '-m', help='Migration message')
    parser.add_argument('--revision', '-r', help='Revision identifier')
    parser.add_argument('--revisions', nargs='+', help='Multiple revisions for merge')
    parser.add_argument('--autogenerate', action='store_true', help='Auto-generate migration')
    
    args = parser.parse_args()
    
    # Create migration manager
    try:
        manager = MigrationManager()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Check Alembic availability
    if not manager.check_alembic():
        sys.exit(1)
    
    # Handle commands
    if not args.command:
        manager.interactive_mode()
        return
    
    success = True
    
    if args.command == 'current':
        success = manager.current_revision()
    elif args.command == 'history':
        success = manager.migration_history()
    elif args.command == 'create':
        if not args.message:
            print("❌ Migration message required. Use --message or -m")
            sys.exit(1)
        success = manager.create_migration(args.message, args.autogenerate)
    elif args.command == 'upgrade':
        revision = args.revision or "head"
        success = manager.upgrade(revision)
    elif args.command == 'downgrade':
        revision = args.revision or "-1"
        success = manager.downgrade(revision)
    elif args.command == 'show':
        if not args.revision:
            print("❌ Revision required. Use --revision or -r")
            sys.exit(1)
        success = manager.show_migration(args.revision)
    elif args.command == 'stamp':
        if not args.revision:
            print("❌ Revision required. Use --revision or -r")
            sys.exit(1)
        success = manager.stamp(args.revision)
    elif args.command == 'check':
        success = manager.check_migration_conflicts()
    elif args.command == 'validate':
        success = manager.validate_migrations()
    elif args.command == 'reset':
        success = manager.reset_database()
    elif args.command == 'auto':
        if not args.message:
            print("❌ Migration message required. Use --message or -m")
            sys.exit(1)
        success = manager.auto_generate_migration(args.message)
    elif args.command == 'merge':
        if not args.revisions or not args.message:
            print("❌ Multiple revisions and message required. Use --revisions and --message")
            sys.exit(1)
        success = manager.merge_migrations(args.revisions, args.message)
    elif args.command == 'backup':
        success = manager.backup_database()
    elif args.command == 'interactive':
        manager.interactive_mode()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
