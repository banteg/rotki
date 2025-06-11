"""Premium sync manager using ORM"""

import logging
import shutil
import tempfile
from enum import Enum
from typing import Any, Literal, NamedTuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.constants.misc import USERSDIR_NAME
from rotkehlchen.data_handler_orm import DataHandler
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.api import PremiumAuthenticationError, RotkehlchenPermissionError
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    Premium,
    PremiumCredentials,
    RemoteMetadata,
    premium_create_and_verify,
)
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CanSync(Enum):
    YES = 0
    NO = 1
    ASK_USER = 2


class SyncCheckResult(NamedTuple):
    # The result of the sync check
    can_sync: CanSync
    # If result is ASK_USER, what should the message be?
    message: str
    payload: dict[str, Any] | None


class PremiumSyncManager(LockableQueryMixIn):
    """Premium sync manager using ORM for database operations"""

    def __init__(self, migration_manager: DataMigrationManager, data: DataHandler) -> None:
        super().__init__()
        # Initialize this with the value saved in the DB using ORM
        # These 2 vars contain the timestamp of our side. When did this DB try to upload
        self.last_data_upload_ts = self._get_last_upload_timestamp_orm(data)
        self.last_upload_attempt_ts = self.last_data_upload_ts
        # This contains the last known successful DB upload timestamp in the remote.
        self.last_remote_data_upload_ts = 0  # gets populated only after the first API call
        self.data = data
        self.migration_manager = migration_manager
        self.premium: Premium | None = None

    def _get_last_upload_timestamp_orm(self, data: DataHandler) -> Timestamp:
        """Get last data upload timestamp using ORM"""
        if not data.db:
            return Timestamp(0)
            
        cache_value = data.db.repos.cache.get_cache_value(DBCacheStatic.LAST_DATA_UPLOAD_TS.value)
        if cache_value:
            return Timestamp(int(cache_value))
        return Timestamp(0)

    def _query_last_data_metadata(self) -> RemoteMetadata:
        """Query remote metadata and keep up to date the last remote data upload ts"""
        assert self.premium is not None, 'caller should make sure premium exists'
        metadata = self.premium.query_last_data_metadata()
        self.last_remote_data_upload_ts = metadata.upload_ts
        return metadata

    def _can_sync_data_from_server(self, new_account: bool) -> SyncCheckResult:
        """
        Checks if the remote data can be pulled from the server.

        Returns a SyncCheckResult denoting whether we can pull for sure,
        whether we can't pull or whether the user should be asked. If the user
        should be asked a message is also returned
        """
        log.debug('can sync data from server -- start')
        if self.premium is None:
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        try:
            metadata = self._query_last_data_metadata()
        except (RemoteError, PremiumAuthenticationError) as e:
            log.debug('can sync data from server failed', error=str(e))
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        if new_account:
            return SyncCheckResult(can_sync=CanSync.YES, message='', payload=None)

        # Check settings using ORM
        premium_should_sync = self.data.db.repos.settings.get_setting('premium_should_sync')
        if not premium_should_sync:
            # If it's not a new account and the db setting for premium syncing is off stop
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        our_last_write_ts = self.data.db.repos.settings.get_setting('last_write_ts')
        our_last_write_ts = Timestamp(int(our_last_write_ts)) if our_last_write_ts else Timestamp(0)

        local_more_recent = our_last_write_ts >= metadata.last_modify_ts
        if local_more_recent:
            log.debug('sync from server stopped -- local is newer')
            return SyncCheckResult(can_sync=CanSync.NO, message='', payload=None)

        return SyncCheckResult(
            can_sync=CanSync.ASK_USER,
            message='Detected remote database more recent than local. '
                    'Do you want to replace local with remote?',
            payload={
                'local_last_modified': our_last_write_ts,
                'remote_last_modified': metadata.last_modify_ts,
            },
        )

    def _can_sync_data_to_server(self) -> bool:
        """Checks if the local data can be pushed to the server.

        Should be called only when we know premium is active
        """
        log.debug('can sync data to server -- start')
        if self.premium is None:
            log.debug('can sync data to server -- no premium')
            return False

        # Check settings using ORM
        premium_should_sync = self.data.db.repos.settings.get_setting('premium_should_sync')
        if not premium_should_sync:
            log.debug('can sync data to server -- premium_should_sync is False')
            return False

        our_last_write_ts = self.data.db.repos.settings.get_setting('last_write_ts')
        our_last_write_ts = Timestamp(int(our_last_write_ts)) if our_last_write_ts else Timestamp(0)

        if self.last_remote_data_upload_ts == 0:
            try:
                metadata = self._query_last_data_metadata()
            except RemoteError as e:
                log.debug('can sync data to server failed', error=str(e))
                return False

            remote_ts = metadata.upload_ts
        else:
            remote_ts = self.last_remote_data_upload_ts

        if our_last_write_ts <= remote_ts:
            log.debug(
                'can sync data to server -- remote is newer or same',
                local_last_write=our_last_write_ts,
                remote_last_write=remote_ts,
            )
            return False

        return True

    def maybe_upload_data_to_server(self) -> bool:
        """Upload data to server if conditions are met using ORM"""
        if self.premium is None:
            return False

        assert self.premium is not None, 'caller should make sure premium exists'
        if self._can_sync_data_to_server() is False:
            return False

        with self.update_task_lock:
            # Write the upload ts in the cache using ORM
            with self.data.db.repos.unit_of_work():
                self.last_upload_attempt_ts = ts_now()
                self.data.db.repos.cache.update_cache(
                    key=DBCacheStatic.LAST_DATA_UPLOAD_TS.value,
                    value=str(self.last_upload_attempt_ts),
                )

            log.debug('maybe upload to server -- start')
            error = self._upload_data_to_server()
            log.debug('maybe upload to server -- done', error=error)

            if error:
                # Do not update the last upload ts, but update the attempt ts
                log.error(error)
                self.data.db.msg_aggregator.add_error(error)
                return False

            # Update the last upload ts using ORM
            self.last_data_upload_ts = self.last_upload_attempt_ts
            with self.data.db.repos.unit_of_work():
                self.data.db.repos.cache.update_cache(
                    key=DBCacheStatic.LAST_DATA_UPLOAD_TS.value,
                    value=str(self.last_data_upload_ts),
                )

        return True

    def _upload_data_to_server(self) -> str | None:
        """Upload data to server

        Returns an error message if something went wrong
        """
        assert self.premium is not None, 'caller should make sure premium exists'
        # Make a backup of the database using ORM
        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.data.db.backup(f.name)
            
            # Compress and encrypt the database
            with open(f.name, 'rb') as backup_file:
                data = backup_file.read()
            
            try:
                result = self.premium.upload_data(
                    data_blob=data,
                    timestamp=self.last_upload_attempt_ts,
                    compression_type='zlib',
                )
            except RemoteError as e:
                return str(e)
            finally:
                # Clean up temp file
                shutil.rmtree(f.name, ignore_errors=True)

        if result:
            return None

        return 'Could not upload data to remote server'

    def _sync_data_from_server_and_replace_local(self) -> str | None:
        """Sync data from server and replace local using ORM"""
        assert self.premium is not None, 'caller should make sure premium exists'
        try:
            result = self.premium.download_data()
        except RemoteError as e:
            return f'Could not download data: {e!s}'
        except UnableToDecryptRemoteData:
            return 'The remote database is encrypted with a different password than the one you provided'  # noqa: E501

        # Dekrypt and decompress result and save to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(result)
            
            # Logout to close the current DB
            self.data.logout()
            
            # Move the temporary file to replace the user DB
            user_db_path = self.data.user_data_dir / 'rotkehlchen.db'
            shutil.move(f.name, user_db_path)
            
            # Re-login with the new database
            try:
                self.data.unlock(
                    username=self.data.username,
                    password=self.data.password,
                    create_new=False,
                    resume_from_backup=False,
                )
            except Exception as e:
                return f'Could not unlock database after sync: {e!s}'

        # Update last write timestamp using ORM
        with self.data.db.repos.unit_of_work():
            self.data.db.repos.settings.set_setting('last_write_ts', str(ts_now()))

        return None

    def try_premium_at_start(
            self,
            given_premium_credentials: PremiumCredentials | None,
            username: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            sync_database: bool,
    ) -> Premium | None:
        """Try to setup premium at start using ORM"""
        if given_premium_credentials is not None:
            credentials = given_premium_credentials
        else:
            # Get credentials from database using ORM
            credentials_data = self.data.db.repos.settings.get_setting('premium_credentials')
            if not credentials_data:
                return None
            
            # TODO: Deserialize credentials from stored format
            # TODO: This needs proper implementation
            credentials = None

        if credentials is None:
            return None

        try:
            self.premium = premium_create_and_verify(credentials)
        except PremiumAuthenticationError as e:
            if create_new is False:
                # If we are unlocking an existing account and the api key
                # is now not valid, just keep going without premium
                log.error(
                    'Could not authenticate with the rotkehlchen server with '
                    'the API keys found in the Database. Continuing without premium',
                    error=str(e),
                )
                return None

            # Else this is a new account and the credentials were given by the user
            raise

        if self.premium is None:
            return None

        if sync_database is False:
            return self.premium

        # Sync data from server if approved
        result = self._can_sync_data_from_server(create_new)
        if result.can_sync == CanSync.YES:
            self._sync_data_from_server_and_replace_local()
        elif result.can_sync == CanSync.ASK_USER and sync_approval == 'yes':
            if create_new:
                self.msg_aggregator.add_error(
                    'Skipping remote database sync on new account creation',
                )
            else:
                self._sync_data_from_server_and_replace_local()

        return self.premium

    @protect_with_lock()
    def check_if_should_sync(self, force_upload: bool = False) -> bool:
        """Checks if we should sync using ORM

        Returns true if we should sync
        """
        if self.premium is None:
            return False

        # Check timing constraints using ORM
        our_last_write_ts = self.data.db.repos.settings.get_setting('last_write_ts')
        our_last_write_ts = Timestamp(int(our_last_write_ts)) if our_last_write_ts else Timestamp(0)

        if our_last_write_ts <= self.last_data_upload_ts and force_upload is False:
            log.debug('check_if_should_sync -- last write ts <= last upload ts')
            return False

        now = ts_now()
        seconds_since_last_upload = now - self.last_upload_attempt_ts
        if seconds_since_last_upload < 60 and not force_upload:
            log.debug('check_if_should_sync -- too soon since last upload attempt')
            return False

        return True

    def sync_data(self, action: Literal['upload', 'download']) -> tuple[bool, str]:
        """Manually sync data with premium using ORM"""
        if self.premium is None:
            return False, 'No premium credentials found'

        if action == 'upload':
            if self._can_sync_data_to_server():
                error = self._upload_data_to_server()
                if error:
                    return False, error
                return True, 'Successfully uploaded data to server'
            return False, 'Cannot sync data to server at this time'
        else:  # download
            result = self._can_sync_data_from_server(new_account=False)
            if result.can_sync == CanSync.YES:
                error = self._sync_data_from_server_and_replace_local()
                if error:
                    return False, error
                return True, 'Successfully downloaded data from server'
            elif result.can_sync == CanSync.ASK_USER:
                return False, result.message
            return False, 'Cannot sync data from server at this time'