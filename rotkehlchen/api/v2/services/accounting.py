"""Accounting service for managing accounting rules and configurations"""
from typing import Any

from rotkehlchen.api.v2.services.database import DatabaseService


class AccountingService:
    """Service for handling accounting rules and tax configurations"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    def get_accounting_rules(
        self,
        event_type: str | None = None,
        event_subtype: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get accounting rules with optional filtering"""
        query = '''SELECT identifier, event_type, event_subtype, counterparty,
                         taxable, count_entire_amount_spend, count_cost_basis_pnl,
                         method, accounting_treatment
                  FROM accounting_rules
                  WHERE 1=1'''
        params = []
        
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        if event_subtype:
            query += ' AND event_subtype = ?'
            params.append(event_subtype)
        
        query += ' ORDER BY identifier'
        
        rules = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query, params)
            for row in cursor:
                rules.append({
                    'identifier': row[0],
                    'event_type': row[1],
                    'event_subtype': row[2],
                    'counterparty': row[3],
                    'taxable': bool(row[4]),
                    'count_entire_amount_spend': bool(row[5]),
                    'count_cost_basis_pnl': bool(row[6]),
                    'method': row[7],
                    'accounting_treatment': row[8],
                })
        
        return rules
    
    def create_accounting_rule(
        self,
        event_type: str,
        event_subtype: str,
        counterparty: str | None = None,
        taxable: bool = True,
        count_entire_amount_spend: bool = True,
        count_cost_basis_pnl: bool = True,
        method: str = 'fifo',
        accounting_treatment: str | None = None,
    ) -> int:
        """Create a new accounting rule"""
        # Validate method
        valid_methods = ['fifo', 'lifo', 'hifo', 'lofo']
        if method not in valid_methods:
            raise ValueError(f'Invalid method. Must be one of: {valid_methods}')
        
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                '''INSERT INTO accounting_rules
                   (event_type, event_subtype, counterparty, taxable,
                    count_entire_amount_spend, count_cost_basis_pnl,
                    method, accounting_treatment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    event_type,
                    event_subtype,
                    counterparty,
                    int(taxable),
                    int(count_entire_amount_spend),
                    int(count_cost_basis_pnl),
                    method,
                    accounting_treatment,
                ),
            )
            return cursor.lastrowid
    
    def update_accounting_rule(
        self,
        rule_id: int,
        event_type: str,
        event_subtype: str,
        counterparty: str | None = None,
        taxable: bool = True,
        count_entire_amount_spend: bool = True,
        count_cost_basis_pnl: bool = True,
        method: str = 'fifo',
        accounting_treatment: str | None = None,
    ) -> bool:
        """Update an existing accounting rule"""
        # Validate method
        valid_methods = ['fifo', 'lifo', 'hifo', 'lofo']
        if method not in valid_methods:
            raise ValueError(f'Invalid method. Must be one of: {valid_methods}')
        
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                '''UPDATE accounting_rules
                   SET event_type = ?, event_subtype = ?, counterparty = ?,
                       taxable = ?, count_entire_amount_spend = ?,
                       count_cost_basis_pnl = ?, method = ?,
                       accounting_treatment = ?
                   WHERE identifier = ?''',
                (
                    event_type,
                    event_subtype,
                    counterparty,
                    int(taxable),
                    int(count_entire_amount_spend),
                    int(count_cost_basis_pnl),
                    method,
                    accounting_treatment,
                    rule_id,
                ),
            )
            return cursor.rowcount > 0
    
    def delete_accounting_rule(self, rule_id: int) -> bool:
        """Delete an accounting rule"""
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                'DELETE FROM accounting_rules WHERE identifier = ?',
                (rule_id,),
            )
            return cursor.rowcount > 0
    
    def get_linked_rules(self) -> list[dict[str, Any]]:
        """Get all linked accounting settings"""
        rules = []
        
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                '''SELECT property_name, setting_name, value
                   FROM accounting_rules_links
                   ORDER BY property_name, setting_name''',
            )
            
            for row in cursor:
                rules.append({
                    'property_name': row[0],
                    'setting_name': row[1],
                    'value': row[2],
                })
        
        return rules
    
    def create_linked_rule(
        self,
        property_name: str,
        setting_name: str,
        value: Any,
    ) -> None:
        """Create a new linked accounting setting"""
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                '''INSERT OR REPLACE INTO accounting_rules_links
                   (property_name, setting_name, value)
                   VALUES (?, ?, ?)''',
                (property_name, setting_name, str(value)),
            )
    
    def delete_linked_rule(
        self,
        property_name: str,
        setting_name: str,
    ) -> bool:
        """Delete a linked accounting setting"""
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                '''DELETE FROM accounting_rules_links
                   WHERE property_name = ? AND setting_name = ?''',
                (property_name, setting_name),
            )
            return cursor.rowcount > 0