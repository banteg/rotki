"""Data handler using the new ORM system"""

import base64
import hashlib
import logging
import shutil
import zlib
from collections.abc import Sequence
from pathlib import Path

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import USERDB_NAME, USERSDIR_NAME
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.db.orm.database import RotkehlchenDatabase, create_database
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BUFFERSIZE = 64 * 1024


class DataHandler:
    """Manages user data and database lifecycle using the ORM system"""

    def __init__(
            self,
            data_directory: Path,
            msg_aggregator: MessagesAggregator,
            sql_vm_instructions_cb: int,
    ):
        self.logged_in = False
        self.data_directory = data_directory
        self.username = 'no_user'
        self.msg_aggregator = msg_aggregator
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        self.db: RotkehlchenDatabase | None = None

    def logout(self) -> None:
        """Log out the current user and close database connections"""
        if self.logged_in:
            self.username = 'no_user'
            self.user_data_dir: Path | None = None
            
            if self.db is not None:
                # TODO: Update owned assets in global DB before logout
                with self.db.session_manager.user_db_session() as session:
                    owned_assets = self.db.repos.owned_assets.get_all_owned_assets()
                    # TODO: Update global DB with owned assets
                
                self.db.close()
                self.db = None
            
            self.logged_in = False

    def unlock(
            self,
            username: str,
            password: str,
            create_new: bool,
            resume_from_backup: bool,
            initial_settings: ModifiableDBSettings | None = None,
    ) -> Path:
        """Unlocks a user, either logging them in or creating a new user

        May raise:
        - SystemPermissionError if there are permission errors when accessing the DB
        or a directory in the user's filesystem
        - AuthenticationError if the given user does not exist, or if
        sqlcipher version problems are detected
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - DBSchemaError if database schema is malformed
        """
        user_data_dir = self.data_directory / USERSDIR_NAME / username
        
        if create_new:
            try:
                if (user_data_dir / USERDB_NAME).exists():
                    raise AuthenticationError(
                        f'User {username} already exists. User data dir: {user_data_dir}',
                    )

                user_data_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise SystemPermissionError(
                    f'Failed to create directory for user: {e!s}',
                ) from e

        else:
            try:
                if not user_data_dir.exists():
                    raise AuthenticationError(f'User {username} does not exist')

                if not (user_data_dir / USERDB_NAME).exists():
                    raise PermissionError

            except PermissionError as e:
                # This is bad. User directory exists but database is missing.
                # Or either DB or user directory can't be accessed due to permissions
                # Make a backup of the directory that user should probably remove
                # on their own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    self.data_directory / USERSDIR_NAME / f'{username}_broken_{ts_now()}',
                )
                raise SystemPermissionError(
                    f'User {username} exists but DB is missing. '
                    f'The user directory has been backed up. '
                    f'To take manual action and fix the directory please inspect '
                    f'{user_data_dir} to see what remains and decide on how to proceed.',
                ) from e

        # Initialize the ORM database
        self.db = create_database(
            user_data_dir=user_data_dir,
            password=password,
            echo_sql=False,
        )
        
        # Set initial settings if creating new user
        if create_new and initial_settings is not None:
            with self.db.repos.unit_of_work():
                for key, value in initial_settings.serialize_for_db().items():
                    self.db.repos.settings.set_setting(key, value)

        self.logged_in = True
        self.username = username
        self.user_data_dir = user_data_dir
        
        return user_data_dir

    def export_user_data(self, dirpath: Path | None) -> Path:
        """Export user data to a zip file

        May raise:
        - PermissionError if the temp backup file/directory can not be created
        """
        if not self.logged_in:
            raise RuntimeError('Cannot export user data when not logged in')

        if dirpath is None:
            dirpath = self.user_data_dir

        is_temporary_directory = False
        if dirpath.is_file():
            output_filename = dirpath
            dirpath = output_filename.parent
        else:
            is_temporary_directory = True
            output_filename = dirpath / f'{self.username}_{timestamp_to_date(ts_now(), formatstr="%d_%m_%Y_%H_%M_%S")}.zip'  # noqa: E501

        if not is_temporary_directory:
            temp_dbpath = dirpath / 'temp.db'
        else:
            dirpath = dirpath / f'{self.username}_{timestamp_to_date(ts_now(), formatstr="%d_%m_%Y_%H_%M_%S")}'  # noqa: E501
            dirpath.mkdir(parents=True, exist_ok=True)
            temp_dbpath = dirpath / USERDB_NAME
        
        # Backup database
        self.db.backup(temp_dbpath)
        
        # Compress the directory
        shutil.make_archive(str(output_filename).replace('.zip', ''), 'zip', dirpath)
        
        if is_temporary_directory:
            shutil.rmtree(dirpath, ignore_errors=True)
        else:
            temp_dbpath.unlink(missing_ok=True)

        return output_filename

    def import_user_data(
            self,
            user_data: dict[str, Any],
            password: str,
    ) -> None:
        """Import user data from a dictionary

        May raise:
        - UnknownAsset if an asset in the data can't be identified
        - BadFunctionInput if the data does not contain required keys
        """
        if not self.logged_in:
            raise RuntimeError('Cannot import user data when not logged in')

        # TODO: Implement user data import using ORM repositories
        # TODO: This would involve parsing the data and using appropriate repositories
        # TODO: to insert the data into the database
        raise NotImplementedError("User data import needs to be implemented with ORM")

    def compress_and_encrypt_db(self, password: str) -> tuple[bytes, str]:
        """Compress and encrypt the database

        Returns a tuple of (encrypted_data, sha256_checksum)
        """
        if not self.logged_in:
            raise RuntimeError('Cannot compress and encrypt DB when not logged in')

        # Create temporary backup
        temp_backup = self.user_data_dir / 'temp_backup.db'
        self.db.backup(temp_backup)
        
        try:
            # Read and compress the backup
            with open(temp_backup, 'rb') as f:
                data = f.read()
            
            compressed_data = zlib.compress(data, level=9)
            encrypted_data = encrypt(compressed_data, password.encode())
            
            # Calculate checksum
            checksum = base64.b64encode(
                hashlib.sha256(encrypted_data).digest(),
            ).decode('ascii')
            
            return encrypted_data, checksum
            
        finally:
            # Clean up temp backup
            temp_backup.unlink(missing_ok=True)

    def decompress_and_decrypt_db(self, password: str, encrypted_data: bytes) -> None:
        """Decrypt and decompress an encrypted database backup

        May raise:
        - AuthenticationError if the password is wrong
        """
        if self.logged_in:
            raise RuntimeError('Cannot decompress and decrypt DB when already logged in')

        try:
            decrypted_data = decrypt(encrypted_data, password.encode())
            decompressed_data = zlib.decompress(decrypted_data)
        except Exception as e:
            raise AuthenticationError('Failed to decrypt database') from e

        # Write to temporary file and restore
        temp_db = self.user_data_dir / 'temp_restore.db'
        try:
            with open(temp_db, 'wb') as f:
                f.write(decompressed_data)
            
            # Close current DB if any
            if self.db:
                self.db.close()
            
            # Move temp to actual location
            db_path = self.user_data_dir / USERDB_NAME
            shutil.move(str(temp_db), str(db_path))
            
            # Reopen database
            self.db = create_database(
                user_data_dir=self.user_data_dir,
                password=password,
                echo_sql=False,
            )
            
        finally:
            temp_db.unlink(missing_ok=True)