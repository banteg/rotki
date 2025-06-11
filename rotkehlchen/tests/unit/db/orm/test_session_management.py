"""Test session management and transaction handling"""

import pytest
from sqlalchemy.exc import IntegrityError

from rotkehlchen.db.orm.models import DBSettings, Tag
from rotkehlchen.db.orm.repositories import SettingsRepository, TagRepository


class TestSessionManagement:
    """Test database session management"""
    
    def test_session_context_manager(self, session_manager):
        """Test session context manager behavior"""
        # Test successful transaction
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            settings_repo.set_setting("test_key", "test_value")
        
        # Verify data persisted
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            value = settings_repo.get_setting("test_key")
            assert value == "test_value"
    
    def test_session_rollback_on_error(self, session_manager):
        """Test session rollback on error"""
        # Try to add duplicate tag (should fail)
        try:
            with session_manager.user_db_session() as session:
                tag_repo = TagRepository(session)
                tag_repo.add_tag("dup_tag", "First", "000000", "FFFFFF")
                tag_repo.add_tag("dup_tag", "Second", "FFFFFF", "000000")  # Duplicate
        except IntegrityError:
            pass  # Expected
        
        # Verify nothing was committed
        with session_manager.user_db_session() as session:
            tag_repo = TagRepository(session)
            tag = tag_repo.get_tag("dup_tag")
            assert tag is None
    
    def test_manual_commit_control(self, session_manager):
        """Test manual commit control"""
        # Add data without auto-commit
        with session_manager.user_db_session(commit=False) as session:
            settings_repo = SettingsRepository(session)
            settings_repo.set_setting("manual_test", "value")
            # Manually commit
            session.commit()
        
        # Verify data persisted
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            value = settings_repo.get_setting("manual_test")
            assert value == "value"
    
    def test_nested_transactions_with_savepoints(self, session_manager):
        """Test nested transactions using savepoints"""
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            
            # Add first setting
            settings_repo.set_setting("outer", "value1")
            
            # Create savepoint
            savepoint = session.begin_nested()
            
            try:
                # Add second setting
                settings_repo.set_setting("inner", "value2")
                
                # Force an error
                raise ValueError("Test error")
            except ValueError:
                # Rollback to savepoint
                savepoint.rollback()
            
            # Add third setting
            settings_repo.set_setting("after_rollback", "value3")
        
        # Verify results
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            
            # First and third should exist
            assert settings_repo.get_setting("outer") == "value1"
            assert settings_repo.get_setting("after_rollback") == "value3"
            
            # Second should not exist (rolled back)
            assert settings_repo.get_setting("inner") is None
    
    def test_multiple_database_sessions(self, session_manager):
        """Test working with multiple databases"""
        # Add to user database
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            settings_repo.set_setting("user_setting", "user_value")
        
        # Add to transient database
        with session_manager.transient_db_session() as session:
            # Create settings table in transient DB
            from rotkehlchen.db.orm.models import DBSettings
            DBSettings.__table__.create(session.bind, checkfirst=True)
            
            settings_repo = SettingsRepository(session)
            settings_repo.set_setting("transient_setting", "transient_value")
        
        # Verify isolation
        with session_manager.user_db_session() as session:
            settings_repo = SettingsRepository(session)
            assert settings_repo.get_setting("user_setting") == "user_value"
            assert settings_repo.get_setting("transient_setting") is None
        
        with session_manager.transient_db_session() as session:
            settings_repo = SettingsRepository(session)
            assert settings_repo.get_setting("transient_setting") == "transient_value"
            assert settings_repo.get_setting("user_setting") is None


class TestUnitOfWork:
    """Test unit of work pattern"""
    
    def test_unit_of_work_commit(self, test_repos):
        """Test unit of work successful commit"""
        from rotkehlchen.db.orm.repositories import UnitOfWork
        
        with UnitOfWork(test_repos.session) as uow:
            # Make multiple changes
            test_repos.settings.set_setting("uow_test1", "value1")
            test_repos.settings.set_setting("uow_test2", "value2")
            test_repos.tags.add_tag("uow_tag", "UOW Tag", "000000", "FFFFFF")
            
            # All changes committed on exit
        
        # Verify all changes persisted
        assert test_repos.settings.get_setting("uow_test1") == "value1"
        assert test_repos.settings.get_setting("uow_test2") == "value2"
        assert test_repos.tags.get_tag("uow_tag") is not None
    
    def test_unit_of_work_rollback(self, test_repos):
        """Test unit of work rollback on error"""
        from rotkehlchen.db.orm.repositories import UnitOfWork
        
        try:
            with UnitOfWork(test_repos.session) as uow:
                # Make changes
                test_repos.settings.set_setting("rollback_test", "value")
                test_repos.tags.add_tag("rollback_tag", "Tag", "000000", "FFFFFF")
                
                # Force an error
                raise RuntimeError("Test error")
        except RuntimeError:
            pass  # Expected
        
        # Verify nothing was committed
        assert test_repos.settings.get_setting("rollback_test") is None
        assert test_repos.tags.get_tag("rollback_tag") is None
    
    def test_unit_of_work_nested(self, test_repos):
        """Test nested unit of work with savepoints"""
        from rotkehlchen.db.orm.repositories import UnitOfWork
        
        with UnitOfWork(test_repos.session) as outer_uow:
            test_repos.settings.set_setting("outer_setting", "outer_value")
            
            try:
                with UnitOfWork(test_repos.session) as inner_uow:
                    test_repos.settings.set_setting("inner_setting", "inner_value")
                    raise RuntimeError("Inner error")
            except RuntimeError:
                pass  # Inner UOW rolled back
            
            test_repos.settings.set_setting("after_inner", "after_value")
        
        # Verify outer and after committed, inner rolled back
        assert test_repos.settings.get_setting("outer_setting") == "outer_value"
        assert test_repos.settings.get_setting("after_inner") == "after_value"
        assert test_repos.settings.get_setting("inner_setting") is None