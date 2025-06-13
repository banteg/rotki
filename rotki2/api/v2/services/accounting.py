"""Accounting service for managing accounting rules and configurations"""
from typing import Any

from rotki2.api.v2.services.database import DatabaseService


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
        query = """SELECT identifier, event_type, event_subtype, counterparty,
                         taxable, count_entire_amount_spend, count_cost_basis_pnl,
                         method, accounting_treatment
                  FROM accounting_rules
                  WHERE 1=1"""
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
                """INSERT INTO accounting_rules
                   (event_type, event_subtype, counterparty, taxable,
                    count_entire_amount_spend, count_cost_basis_pnl,
                    method, accounting_treatment)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
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
                """UPDATE accounting_rules
                   SET event_type = ?, event_subtype = ?, counterparty = ?,
                       taxable = ?, count_entire_amount_spend = ?,
                       count_cost_basis_pnl = ?, method = ?,
                       accounting_treatment = ?
                   WHERE identifier = ?""",
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
                """SELECT property_name, setting_name, value
                   FROM accounting_rules_links
                   ORDER BY property_name, setting_name""",
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
                """INSERT OR REPLACE INTO accounting_rules_links
                   (property_name, setting_name, value)
                   VALUES (?, ?, ?)""",
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
                """DELETE FROM accounting_rules_links
                   WHERE property_name = ? AND setting_name = ?""",
                (property_name, setting_name),
            )
            return cursor.rowcount > 0

    def query_accounting_rules(
        self,
        event_types: list[str] | None = None,
        event_subtypes: list[str] | None = None,
        counterparties: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query accounting rules with filters - v1 compatibility"""
        query = """SELECT identifier, event_type, event_subtype, counterparty,
                         taxable, count_entire_amount_spend, count_cost_basis_pnl,
                         method, accounting_treatment
                  FROM accounting_rules
                  WHERE 1=1"""
        params = []

        if event_types:
            placeholders = ','.join(['?'] * len(event_types))
            query += f' AND event_type IN ({placeholders})'
            params.extend(event_types)

        if event_subtypes:
            placeholders = ','.join(['?'] * len(event_subtypes))
            query += f' AND event_subtype IN ({placeholders})'
            params.extend(event_subtypes)

        if counterparties:
            placeholders = ','.join(['?'] * len(counterparties))
            query += f' AND counterparty IN ({placeholders})'
            params.extend(counterparties)

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

    def add_accounting_rule(
        self,
        event_type: str,
        event_subtype: str | None,
        counterparty: str | None,
        taxable: bool,
        count_entire_amount_spend: bool = False,
        count_cost_basis_pnl: bool = True,
        accounting_treatment: str | None = None,
    ) -> int:
        """Add a new accounting rule - v1 compatibility"""
        return self.create_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype or '',
            counterparty=counterparty,
            taxable=taxable,
            count_entire_amount_spend=count_entire_amount_spend,
            count_cost_basis_pnl=count_cost_basis_pnl,
            method='fifo',  # Default method
            accounting_treatment=accounting_treatment,
        )

    def edit_accounting_rule(
        self,
        identifier: int,
        event_type: str,
        event_subtype: str | None,
        counterparty: str | None,
        taxable: bool,
        count_entire_amount_spend: bool = False,
        count_cost_basis_pnl: bool = True,
        accounting_treatment: str | None = None,
    ) -> bool:
        """Edit an existing accounting rule - v1 compatibility"""
        return self.update_accounting_rule(
            rule_id=identifier,
            event_type=event_type,
            event_subtype=event_subtype or '',
            counterparty=counterparty,
            taxable=taxable,
            count_entire_amount_spend=count_entire_amount_spend,
            count_cost_basis_pnl=count_cost_basis_pnl,
            method='fifo',  # Default method
            accounting_treatment=accounting_treatment,
        )

    def get_accounting_rule_info(self) -> dict[str, Any]:
        """Get information about linkable accounting rule properties"""
        return {
            'event_types': [
                'trade', 'fee', 'deposit', 'withdrawal',
                'income', 'loss', 'staking', 'transfer',
            ],
            'event_subtypes': [
                'buy', 'sell', 'fee', 'reward', 'spend',
                'receive', 'return_wrapped', 'liquidate',
                'generate_debt', 'payback_debt',
            ],
            'counterparties': [
                'uniswap', 'compound', 'aave', 'maker',
                'curve', 'convex', 'yearn', 'liquity',
                'balancer', 'sushiswap', '1inch',
            ],
            'linkable_properties': [
                {
                    'name': 'include_gas_costs',
                    'description': 'Include gas costs in the accounting',
                },
                {
                    'name': 'include_crypto2crypto',
                    'description': 'Include crypto to crypto trades',
                },
            ],
        }

    def import_accounting_rules(self, filepath: str) -> dict[str, Any]:
        """Import accounting rules from a file"""
        import json
        from pathlib import Path

        path = Path(filepath)
        if not path.exists():
            raise ValueError(f'File {filepath} does not exist')

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        imported_count = 0
        failed_count = 0

        rules = data.get('rules', [])

        for rule in rules:
            try:
                self.add_accounting_rule(
                    event_type=rule['event_type'],
                    event_subtype=rule.get('event_subtype'),
                    counterparty=rule.get('counterparty'),
                    taxable=rule['taxable'],
                    count_entire_amount_spend=rule.get('count_entire_amount_spend', False),
                    count_cost_basis_pnl=rule.get('count_cost_basis_pnl', True),
                    accounting_treatment=rule.get('accounting_treatment'),
                )
                imported_count += 1
            except Exception:
                failed_count += 1

        return {
            'imported': imported_count,
            'failed': failed_count,
            'total': len(rules),
        }

    def export_accounting_rules(
        self,
        directory_path: str | None = None,
    ) -> str:
        """Export accounting rules to a file"""
        import json
        from pathlib import Path

        rules = self.query_accounting_rules()

        export_data = {
            'version': 1,
            'rules': rules,
        }

        if directory_path:
            path = Path(directory_path) / 'accounting_rules_export.json'
        else:
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            path = temp_dir / 'accounting_rules_export.json'

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)

        return str(path)

    def get_accounting_rule_conflicts(self) -> list[dict[str, Any]]:
        """Get conflicts between accounting rules"""
        conflicts = []

        with self.db.conn.read_ctx() as cursor:
            # Find rules with same event_type, event_subtype, and counterparty
            result = cursor.execute(
                """SELECT r1.identifier, r1.event_type, r1.event_subtype, 
                          r1.counterparty, r1.method as rule,
                          r2.identifier, r2.method as rule
                   FROM accounting_rules r1
                   JOIN accounting_rules r2 
                   ON r1.event_type = r2.event_type
                   AND (r1.event_subtype = r2.event_subtype OR 
                        (r1.event_subtype IS NULL AND r2.event_subtype IS NULL))
                   AND (r1.counterparty = r2.counterparty OR 
                        (r1.counterparty IS NULL AND r2.counterparty IS NULL))
                   WHERE r1.identifier < r2.identifier""",
            ).fetchall()

            for row in result:
                conflicts.append({
                    'rule1': {
                        'identifier': row[0],
                        'event_type': row[1],
                        'event_subtype': row[2],
                        'counterparty': row[3],
                        'rule': row[4],
                    },
                    'rule2': {
                        'identifier': row[5],
                        'rule': row[6],
                    },
                })

        return conflicts

    def resolve_accounting_rule_conflicts(
        self,
        conflicts: list[dict[str, Any]],
        resolution: str = 'keep_both',
    ) -> int:
        """Resolve accounting rule conflicts"""
        resolved_count = 0

        if resolution == 'keep_both':
            # Nothing to do, keep both rules
            return 0

        with self.db.conn.write_ctx() as cursor:
            for conflict in conflicts:
                if resolution == 'keep_local':
                    # Delete rule2 (the newer/remote rule)
                    cursor.execute(
                        'DELETE FROM accounting_rules WHERE identifier = ?',
                        (conflict['rule2']['identifier'],),
                    )
                    resolved_count += 1
                elif resolution == 'keep_remote':
                    # Delete rule1 (the older/local rule)
                    cursor.execute(
                        'DELETE FROM accounting_rules WHERE identifier = ?',
                        (conflict['rule1']['identifier'],),
                    )
                    resolved_count += 1

        return resolved_count
