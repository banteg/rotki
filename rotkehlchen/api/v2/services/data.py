"""Data service for import/export and database management"""
import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rotkehlchen.api.v2.services.database import DatabaseService


class DataService:
    """Service for handling data import/export and database operations"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    def import_rotki_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Import data from rotki JSON format"""
        imported = {
            'trades': 0,
            'balances': 0,
            'transactions': 0,
            'tags': 0,
        }
        
        # Import trades
        if 'trades' in data:
            for trade in data['trades']:
                # TODO: Process and insert trade
                imported['trades'] += 1
        
        # Import manual balances
        if 'balances' in data:
            for balance in data['balances']:
                # TODO: Process and insert balance
                imported['balances'] += 1
        
        # Import transactions
        if 'transactions' in data:
            for tx in data['transactions']:
                # TODO: Process and insert transaction
                imported['transactions'] += 1
        
        # Import tags
        if 'tags' in data:
            for tag in data['tags']:
                with self.db.conn.write_ctx() as cursor:
                    cursor.execute(
                        '''INSERT OR IGNORE INTO tags 
                           (name, description, background_color, foreground_color)
                           VALUES (?, ?, ?, ?)''',
                        (
                            tag['name'],
                            tag.get('description'),
                            tag.get('background_color'),
                            tag.get('foreground_color'),
                        ),
                    )
                imported['tags'] += 1
        
        return imported
    
    def import_cointracking_csv(self, csv_content: str) -> dict[str, Any]:
        """Import data from CoinTracking CSV format"""
        imported = {'trades': 0, 'errors': []}
        
        reader = csv.DictReader(csv_content.splitlines())
        for row in reader:
            try:
                # Parse CoinTracking format
                # TODO: Convert CoinTracking format to rotki format
                imported['trades'] += 1
            except Exception as e:
                imported['errors'].append(f"Row {reader.line_num}: {str(e)}")
        
        return imported
    
    def import_cryptocom_csv(self, csv_content: str) -> dict[str, Any]:
        """Import data from Crypto.com CSV format"""
        imported = {'transactions': 0, 'errors': []}
        
        reader = csv.DictReader(csv_content.splitlines())
        for row in reader:
            try:
                # Parse Crypto.com format
                # TODO: Convert Crypto.com format to rotki format
                imported['transactions'] += 1
            except Exception as e:
                imported['errors'].append(f"Row {reader.line_num}: {str(e)}")
        
        return imported
    
    def export_user_data(self, directory_path: str | None = None) -> str:
        """Export all user data to JSON file"""
        if directory_path is None:
            directory_path = os.path.expanduser("~/rotki_exports")
        
        # Create export directory
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rotki_export_{timestamp}.json"
        filepath = os.path.join(directory_path, filename)
        
        # Collect all data
        export_data = {
            'version': 2,
            'timestamp': timestamp,
            'trades': self._export_trades(),
            'balances': self._export_balances(),
            'transactions': self._export_transactions(),
            'tags': self._export_tags(),
            'accounts': self._export_accounts(),
            'settings': self._export_settings(),
        }
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath
    
    def _export_trades(self) -> list[dict[str, Any]]:
        """Export trades data"""
        trades = []
        # TODO: Query and format trades
        return trades
    
    def _export_balances(self) -> list[dict[str, Any]]:
        """Export manual balances"""
        balances = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                '''SELECT asset, label, amount, location, category
                   FROM manually_tracked_balances''',
            )
            for row in cursor:
                balances.append({
                    'asset': row[0],
                    'label': row[1],
                    'amount': row[2],
                    'location': row[3],
                    'category': row[4],
                })
        return balances
    
    def _export_transactions(self) -> list[dict[str, Any]]:
        """Export transactions"""
        transactions = []
        # TODO: Query and format transactions
        return transactions
    
    def _export_tags(self) -> list[dict[str, Any]]:
        """Export tags"""
        tags = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                '''SELECT name, description, background_color, foreground_color
                   FROM tags''',
            )
            for row in cursor:
                tags.append({
                    'name': row[0],
                    'description': row[1],
                    'background_color': row[2],
                    'foreground_color': row[3],
                })
        return tags
    
    def _export_accounts(self) -> list[dict[str, Any]]:
        """Export blockchain accounts"""
        accounts = []
        # TODO: Query and format accounts
        return accounts
    
    def _export_settings(self) -> dict[str, Any]:
        """Export user settings"""
        return self.db.get_settings().__dict__
    
    def get_database_info(self) -> dict[str, Any]:
        """Get database information"""
        with self.db.conn.read_ctx() as cursor:
            # Get database size
            cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            size = cursor.fetchone()[0]
            
            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
        
        return {
            'size': size,
            'size_mb': round(size / (1024 * 1024), 2),
            'tables': len(tables),
            'table_counts': counts,
            'version': self.db.get_version(),
        }
    
    def list_backups(self) -> list[dict[str, Any]]:
        """List available database backups"""
        backup_dir = os.path.expanduser("~/.rotki/backups")
        backups = []
        
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith('.db'):
                    filepath = os.path.join(backup_dir, file)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': file,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def create_backup(self) -> str:
        """Create a database backup"""
        backup_dir = os.path.expanduser("~/.rotki/backups")
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"rotki_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_file)
        
        # TODO: Get actual database path
        # For now, this is a placeholder
        db_path = os.path.expanduser("~/.rotki/rotkehlchen.db")
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        else:
            raise FileNotFoundError("Database file not found")
        
        return backup_path
    
    def restore_backup(self, backup_file: str) -> None:
        """Restore from a database backup"""
        backup_dir = os.path.expanduser("~/.rotki/backups")
        backup_path = os.path.join(backup_dir, backup_file)
        
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file {backup_file} not found")
        
        # TODO: Get actual database path and implement safe restore
        # This should:
        # 1. Verify backup integrity
        # 2. Create backup of current DB
        # 3. Replace current DB with backup
        # 4. Restart services
        
        raise NotImplementedError("Database restore not yet implemented")