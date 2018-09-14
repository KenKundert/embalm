# Avendesora Password Generator Settings
#
# Copyright (C) 2016 Kenneth S. Kundert

# License {{{1
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/.

# Imports {{{1
from appdirs import user_config_dir, user_data_dir

# Preferences {{{1
PROGRAM_NAME = 'embalm'
DEFAULT_COMMAND = 'incremental'
ENCODING = 'utf-8'
INDENT = '    '

CONFIG_DIR = user_config_dir(PROGRAM_NAME)
DATA_DIR = user_data_dir(PROGRAM_NAME)
ARCHIVE_DIR = 'archives'
RESTORE_DIR = 'restored'

SETTINGS_FILE = 'settings'
EMBALM_LOG_FILE = '{prog_name}.log'
DUPLICITY_LOG_FILE = 'duplicity.log'
LOCK_FILE = 'lock'
INCR_DATE_FILE = 'lastbackup_incr'
FULL_DATE_FILE = 'lastbackup_full'

CONFIGS_SETTING = 'configuration_files'
DEFAULT_CONFIG_SETTING = 'default_configuration'
INCLUDE_SETTING = 'include'
WORKING_DIR_SETTING = 'working_dir'
DEFAULT_WORKING_DIR = '{}/{{config_name}}'.format(DATA_DIR)

KNOWN_SETTINGS = '''
    avendesora_account
    bw_limit
    config_name
    configuration_files
    default_configuration
    dest_dir
    dest_server
    excludes
    gpg_binary
    gpg_passphrase
    must_exist
    notifier
    notify
    run_after_backup
    run_before_backup
    src_dir
    ssh_backend_method
    ssh_identity
    working_dir
'''.split()
    # Any setting found in the users settings files that is not found in
    # KNOWN_SETTINGS is highlighted as a unknown setting by the settings
    # command.
