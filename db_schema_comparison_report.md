# Database Schema Comparison Report: SQL vs SQLModel

## Executive Summary

This report compares the raw SQL schema definitions in `db/schema.py` with the SQLModel implementations in `db/models/`. Several critical issues have been identified that need to be addressed to ensure data integrity and proper cascading behavior.

## Critical Issues Found

### 1. Missing CASCADE Rules

#### History Events - Asset Relationship
- **SQL Schema**: `FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE`
- **SQLModel**: Only has `ForeignKey('assets.identifier', onupdate='CASCADE')` 
- **Missing**: `ondelete` behavior not specified

#### EVM Events Info
- **SQL Schema**: `FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE`
- **SQLModel**: Missing both `onupdate='CASCADE'` and `ondelete='CASCADE'`

#### ETH Staking Events Info
- **SQL Schema**: `FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE`
- **SQLModel**: Missing both `onupdate='CASCADE'` and `ondelete='CASCADE'`

#### History Events Mappings
- **SQL Schema**: `FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE`
- **SQLModel**: Only has `ondelete='CASCADE'`, missing `onupdate='CASCADE'`

#### EVM Transaction Authorizations
- **SQL Schema**: `FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE`
- **SQLModel**: Has correct `ondelete='CASCADE'`

#### Optimism Transactions  
- **SQL Schema**: `FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE`
- **SQLModel**: Only has `ondelete='CASCADE'`, missing `onupdate='CASCADE'`

#### ZkSync Lite Transactions
- **SQL Schema**: `FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE`
- **SQLModel**: Missing `onupdate='CASCADE'`

#### ZkSync Lite Swaps
- **SQL Schema**: Multiple foreign keys with `ON UPDATE CASCADE`
- **SQLModel**: Missing `onupdate='CASCADE'` on asset foreign keys

### 2. Missing UNIQUE Constraints

#### Location Table
- **SQL Schema**: `seq INTEGER UNIQUE`
- **SQLModel**: `seq` column exists but no unique constraint specified

#### Balance Category Table
- **SQL Schema**: `seq INTEGER UNIQUE`
- **SQLModel**: `seq` column exists but no unique constraint specified

#### ZkSync Lite TX Type Table
- **SQL Schema**: `seq INTEGER UNIQUE`
- **SQLModel**: `seq` column exists but no unique constraint specified

#### Skipped External Events Table
- **SQL Schema**: `UNIQUE(data, location)`
- **SQLModel**: Missing UniqueConstraint

### 3. Missing or Incorrect Primary Keys

#### EVM Internal Transactions
- **SQL Schema**: Composite primary key on `(parent_tx, trace_id, from_address, to_address, value, gas, gas_used)`
- **SQLModel**: Has all columns marked as primary key correctly

#### MultiSettings Table
- **SQL Schema**: No primary key, only `UNIQUE(name, value)` constraint
- **SQLModel**: Made both columns primary keys to satisfy SQLAlchemy requirements (this is documented as intentional)

### 4. Missing CHECK Constraints

#### EVM TX Receipts
- **SQL Schema**: `status INTEGER NOT NULL CHECK (status IN (0, 1))`
- **SQLModel**: Has CheckConstraint but defined at table level, not column level

### 5. Virtual/Generated Columns

#### NFTs Table
- **SQL Schema**: `blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL`
- **SQLModel**: Correctly implemented using `Computed("'ETH'", persisted=False)`

### 6. Missing Tables in SQLModel

The following tables from the SQL schema appear to be missing SQLModel implementations:
- No missing tables were identified, but some relationships may not be properly configured

### 7. Type Mismatches

#### Timestamps
- Some models use `TimestampType` custom type while others use plain `INTEGER`
- Need to verify consistency across all timestamp columns

#### Text vs VARCHAR
- SQL schema uses `VARCHAR[24]`, `VARCHAR[30]`, `VARCHAR[42]` in various places
- SQLModel sometimes uses `TEXT` instead of specific VARCHAR lengths

### 8. Missing Relationship Back References

Several models are missing `back_populates` on their relationships:

#### Asset Model
- Missing `history_events` relationship back reference
- Missing `zksynclite_transactions` relationship back reference

#### Location Model  
- Missing relationship back references for various foreign key references

### 9. Missing Indexes

The SQL schema defines several performance indexes that should be verified in SQLModel:
- `idx_history_events_entry_type`
- `idx_history_events_timestamp`
- `idx_history_events_location`
- `idx_history_events_location_label`
- `idx_history_events_asset`
- `idx_history_events_type`
- `idx_history_events_subtype`
- `idx_history_events_ignored`

## Recommendations

1. **Immediate Actions**:
   - Add missing `onupdate='CASCADE'` and `ondelete='CASCADE'` to all foreign keys that require them
   - Add missing UNIQUE constraints to enum tables
   - Fix the composite primary key for EVM internal transactions
   - Add the virtual column definition for NFTs.blockchain

2. **Testing Required**:
   - Verify cascade behavior works correctly after adding missing rules
   - Test that unique constraints are enforced
   - Ensure indexes are created properly

3. **Code Review**:
   - Review all ForeignKey definitions to ensure they match the SQL schema
   - Verify that all CHECK constraints are properly defined
   - Ensure consistent use of custom types like TimestampType

## Files to Modify

1. `/workspace/rotkehlchen/db/models/user/history.py`
   - Add `onupdate='CASCADE'` to EvmEventInfo foreign key
   - Add `onupdate='CASCADE'` to EthStakingEventInfo foreign key  
   - Add `onupdate='CASCADE'` to HistoryEventMapping foreign key
   - Add UniqueConstraint('data', 'location') to SkippedExternalEvent

2. `/workspace/rotkehlchen/db/models/user/evm.py`
   - Add `onupdate='CASCADE'` to OptimismTransaction foreign key

3. `/workspace/rotkehlchen/db/models/user/enums.py`
   - Add unique=True to Location.seq column
   - Add unique=True to BalanceCategory.seq column
   - Add unique=True to ZkSyncLiteTxType.seq column

4. `/workspace/rotkehlchen/db/models/user/models.py`
   - Add missing back_populates relationships for Asset model

5. `/workspace/rotkehlchen/db/models/user/staking.py`
   - Foreign keys already have correct CASCADE rules

6. `/workspace/rotkehlchen/db/models/user/zksynclite.py`
   - Foreign keys already have correct CASCADE rules

## Next Steps

1. Create unit tests to verify schema compatibility
2. Run migration tests to ensure no data loss
3. Performance test with indexes to verify query performance
4. Document any intentional deviations from the SQL schema