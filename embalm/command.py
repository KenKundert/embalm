# Commands

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
from .collection import Collection
from .preferences import (
    DEFAULT_COMMAND,
    DUPLICITY_LOG_FILE,
    KNOWN_SETTINGS,
    RESTORE_DIR,
)
from .utilities import two_columns, render_command
from inform import (
    Color, Error,
    cull, display, full_stop, indent, narrate, output, render, warn,
)
from docopt import docopt
from shlib import mkdir, mv, rm, to_path, Run, set_prefs
set_prefs(use_inform=True, log_cmd=True)
from textwrap import dedent, fill
import arrow
import os
import re
import sys


# Utilities {{{1
# title() {{{2
def title(text):
    return full_stop(text.capitalize())

# duplicity_options() {{{2
def duplicity_options(settings, options):
    args = []
    gpg_binary = settings.value('gpg_binary')
    if gpg_binary:
        args.extend(['--gpg-binary', str(to_path(gpg_binary))])
    if DUPLICITY_LOG_FILE:
        args.extend(f'--log-file {DUPLICITY_LOG_FILE}'.split())
        rm(DUPLICITY_LOG_FILE)
    if settings.ssh_backend_method == 'option':
        args.extend('--ssh-backend pexpect'.split())
    args.append('-v9' if 'verbose' in options else '-v8')
    args.append('--dry-run' if 'trial-run' in options else '')
    return cull(args)

# archive_dir_command() {{{2
def archive_dir_command(settings):
    return f'--archive-dir {settings.archive_dir} --name {settings.config_name}'.split()

# sftp_command() {{{2
def sftp_command(settings):
    command = ['sftp']
        # don't add -v option, it hopelessly confuses pexpect
    ssh_identity = settings.value('ssh_identity')
    if ssh_identity:
        command.extend(['-i', str(to_path(ssh_identity))])
    if settings.bw_limit:
        command.extend(['-l', str(settings.bw_limit)])
    return ['--sftp-command', ' '.join(command)]

# render() {{{2
def render_path(path):
    return str(to_path(path))

# excludes() {{{2
def excludes(settings):
    excludes = []
    for each in settings.values('excludes'):
        excludes.extend(['--exclude', render_path(each)])
    return excludes

# destination() {{{2
def destination(settings):
    if settings.ssh_backend_method == 'option':
        protocol = 'sftp'
    elif settings.ssh_backend_method == 'protocol':
        protocol = 'pexpect+sftp'
    else:
        raise NotImplementedError
    dest_server = settings.value('dest_server')
    dest_dir = settings.value('dest_dir')
    return f'{protocol}://{dest_server}/{dest_dir}'

# publish_passcode() {{{2
def publish_passcode(settings):
    passcode = settings.gpg_passphrase
    if not passcode and settings.avendesora_account:
        narrate('running avendesora to access passphrase.')
        try:
            from avendesora import PasswordGenerator, PasswordError
            pw = PasswordGenerator()
            account = pw.get_account(settings.value('avendesora_account'))
            passcode = str(account.get_value('passcode'))
        except PasswordError as err:
            settings.fail(err)
        except ImportError:
            settings.fail(
                'Avendesora is not available',
                'you must specify gpg_passphrase in settings.',
                sep = ', '
            )
    else:
        settings.fail('you must specify gpg_passphrase in settings.')

    narrate('gpg passphrase is set.')
    return dict(PASSPHRASE = passcode)

# run_duplicity() {{{2
def run_duplicity(cmd, settings, narrating):
    os.environ.update(publish_passcode(settings))
    for ssh_var in 'SSH_AGENT_PID SSH_AUTH_SOCK'.split():
        if ssh_var not in os.environ:
            warn(
                'environment variable not found, is ssh-agent running?',
                culprit=ssh_var
            )
    narrate('running:\n{}'.format(indent(render_command(cmd))))
    modes = 'soeW' if narrating else 'sOEW'
    Run(cmd, modes=modes, env=os.environ)

# Command base class {{{1
class Command(object):
    @classmethod
    def commands(cls):
        for cmd in cls.__subclasses__():
            if hasattr(cmd, 'NAMES'):
                yield cmd
            for sub in cmd.commands():
                if hasattr(sub, 'NAMES'):
                    yield sub

    @classmethod
    def commands_sorted(cls):
        for cmd in sorted(cls.commands(), key=lambda c: c.get_name()):
            yield cmd

    @classmethod
    def find(cls, name):
        if not name:
            name = DEFAULT_COMMAND
        for command in cls.commands():
            if name in command.NAMES:
                return command, command.NAMES[0]
        raise Error('unknown command.', culprit=name)

    @classmethod
    def execute(cls, name, args, settings, options):
        narrate('{}:'.format(name))
        cls.run(name, args if args else [], settings, options)

    @classmethod
    def summarize(cls, width=16):
        summaries = []
        for cmd in Command.commands_sorted():
            summaries.append(two_columns(', '.join(cmd.NAMES), cmd.DESCRIPTION))
        return '\n'.join(summaries)

    @classmethod
    def get_name(cls):
        return cls.NAMES[0]

    @classmethod
    def help(cls):
        text = dedent("""
            {title}

            {usage}
        """).strip()
        return text.format(
            title=title(cls.DESCRIPTION), usage=cls.USAGE,
        )


# Backup command group {{{1
class Backup(Command):
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        kind = 'full' if command in 'full f'.split() else 'incr'

        # check the dependencies are available
        for each in settings.values('must_exist'):
            path = to_path(each)
            if not path.exists():
                raise Error(
                    'does not exist, perform setup and restart.',
                    culprit=each
                )

        # run prerequisites
        for each in settings.values('run_before_backup'):
            narrate('running:', each)
            Run(each, 'SoeW')
        rm('duplicity.log')

        # run duplicity
        cmd = (
            f'duplicity {kind}'.split()
            + duplicity_options(settings, options)
            + archive_dir_command(settings)
            + sftp_command(settings)
            + excludes(settings)
            + [render_path(settings.src_dir), destination(settings)]
        )
        run_duplicity(cmd, settings, 'narrate' in options)

        # update the date files
        now = arrow.now()
        if kind == 'full':
            settings.full_date_file.write_text(str(now))
        settings.incr_date_file.write_text(str(now))

        # run any scripts specified to be run after a backup
        for each in settings.values('run_after_backup'):
            narrate('running:', each)
            Run(each, 'SoeW')

# Full backup command {{{2
class FullBackup(Backup):
    NAMES = 'full f'.split()
    DESCRIPTION = 'run a full backup'
    USAGE = dedent("""
        Usage:
            embalm full
            embalm f

        Once configured, you would perform your first backup as a full backup:

            ./embalm full

        After that, you should normally prefer incremental backups, though you
        should run a full backup every few months.
    """).strip()
    REQUIRES_EXCLUSIVITY = True


# Incremental backup command {{{2
class IncrementalBackup(Backup):
    NAMES = 'incremental incr inc i'.split()
    DESCRIPTION = 'run an incremental backup'
    USAGE = dedent("""
        Usage:
            embalm incremental
            embalm incr
            embalm inc
            embalm i
            embalm

        After you have run a full backup, you may run incremental backups, which
        are considerably faster and consume much less space:

            ./embalm incremental

        or simply:

            ./embalm

        However, it is important to run a full backup every few months.
    """).strip()
    REQUIRES_EXCLUSIVITY = True


# Configs command {{{1
class Configs(Command):
    NAMES = 'config', 'c'
    DESCRIPTION = 'list available backup configurations'
    USAGE = dedent("""
        Usage:
            embalm configs
            embalm c
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        configurations = Collection(settings.configuration_files)
        if configurations:
            output('Available Configurations:', *configurations, sep='\n    ')
        else:
            output('No configurations available.')


# Due command {{{1
class Due(Command):
    NAMES = 'due', 'd'
    DESCRIPTION = 'days since last backup'
    USAGE = dedent("""
        Used with status bar programs, such as i3status, to make user aware that
        backups are due.

        Usage:
            embalm due [options]

        Options:
            -d <num>, --inc-days <num>   emit message if this many days have passed
                                         since incremental backup
            -D <num>, --full-days <num>  emit message if this many days have passed
                                         since full backup
            -m <msg>, --message <msg>    the message to emit

        If you specify either --inc-days or --full-days or both, the message is printed 
        if the corresponding backup is overdue, otherwise nothing is printed. If both 
        durations are specified and both are violated, then two messages are printed.

        If you specify the message, the following replacements are available:
            days: the number of days since the backup
            elapsed: the time that has elapsed since the backup
            kind: the type of backup, either 'incremental' or 'full'.

        Otherwise, the time that has elapsed since each backup is printed.

        Examples:
            > embalm due
            A incremental backup was performed 19 hours ago.
            A full backup was performed 21 days ago.

            > embalm due -d0.5 -m "It has been {days:.1f} days since the last {kind} backup."
            It has been 0.8 days since the last incremental backup.

            > embalm due -D90 -m "It has been {elapsed} since the last {kind} backup."
            It has been 4 months since the last full backup.
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        def gen_message(kind, date):
            if cmdline['--message']:
                since_last_backup = arrow.now() - date
                days = since_last_backup.total_seconds()/86400
                elapsed = date.humanize(only_distance=True)
                return cmdline['--message'].format(
                    days=days, kind=kind, elapsed=elapsed
                )
            else:
                return f'{kind} backup was performed {date.humanize()}.'

        # Get date of last incremental backup and warn user if it is overdue
        incr_date_file = settings.incr_date_file
        try:
            incr_backup_date = arrow.get(incr_date_file.read_text())
        except FileNotFoundError:
            incr_backup_date = arrow.get('19560105', 'YYYYMMDD')
        except arrow.parser.ParserError:
            fatal('date not given in iso format.', culprit=inc_date_file)
        if cmdline.get('--inc-days'):
            since_last_backup = arrow.now() - incr_backup_date
            days = since_last_backup.total_seconds()/86400
            if days > float(cmdline['--inc-days']):
                output(gen_message('incremental', incr_backup_date))

        # Get date of last full backup and warn user if it is overdue
        full_date_file = settings.full_date_file
        try:
            full_backup_date = arrow.get(full_date_file.read_text())
        except FileNotFoundError:
            full_backup_date = arrow.get('19560105', 'YYYYMMDD')
        except arrow.parser.ParserError:
            fatal('date not given in iso format.', culprit=full_date_file)
        if cmdline.get('--full-days'):
            since_last_backup = arrow.now() - full_backup_date
            days = since_last_backup.total_seconds()/86400
            if days > float(cmdline['--full-days']):
                output(gen_message('full', full_backup_date))

        # Don't print a message if limits were imposed and backups are not overdye
        if cmdline.get('--inc-days') or cmdline.get('--full-days'):
            return

        # Otherwise, simply report age of backups
        output(gen_message('full', full_backup_date))
        output(gen_message('incremental', incr_backup_date))


# Help {{{1
class Help(Command):
    NAMES = 'help', 'h'
    DESCRIPTION = 'give information about commands or other topics'
    USAGE = dedent("""
        Usage:
            embalm help [<topic>]
            embalm h    [<topic>]
    """).strip()
    REQUIRES_EXCLUSIVITY = False
    EMBALM_DESCRIPTION = dedent("""
        Embalm is a simple command line utility to orchestrate backups. It is
        built on Duplicity, which is a powerful and flexible utility for
        managing encrypted backups, however it has a rather heavy user
        interface. With Embalm, you specify all the details about your backups
        once in advance, and then use a very simple command line interface for
        your day-to-day activities.  The details are contained in
        ~/.config/embalm.  That directory will contains a file (settings) that
        contains shared settings, and then another file for each backup
        configuration you have.

        Each backup configuration has a working directory.  Those directories
        hold the logfiles and the Duplicity archive directory. The archive
        directory contains Duplicity housekeeping files for the backup. You can
        place as many of the embalm executables as you wish in that directory
        and they can be configured to share the archive directory.
    """)

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        from .help import HelpMessage
        HelpMessage.show(cmdline['<topic>'], cls.EMBALM_DESCRIPTION)


# Info command {{{1
class Info(Command):
    NAMES = 'info',
    DESCRIPTION = 'print information about a backup'
    USAGE = dedent("""
        Usage:
            embalm info
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        display(f'              config: {settings.config_name}')
        display(f'              source: {settings.src_dir}')
        display(f'         destination: {settings.dest_server}:{settings.dest_dir}')
        display(f'  settings directory: {settings.config_dir}')
        display(f'   working directory: {settings.working_dir}')
        display(f'   archive directory: {settings.archive_dir}')
        display(f'   restore directory: {settings.restore_dir}')
        display(f'              logile: {settings.logfile}')


# Manifest command {{{1
class Manifest(Command):
    NAMES = 'manifest', 'm'
    DESCRIPTION = 'output the files that can be restored'
    USAGE = dedent("""
        Usage:
            embalm [options] manifest
            embalm [options] m

        Options:
            -d <date>, --date <date>   date of the desired version of paths

        Once a backup has been performed, you can list the files available in 
        your archive using:

            embalm manifest

        You can list the files that existed on a particular date using:

            embalm manifest --date 2015-04-01

        Or, you can list the files that existed 3.5 days ago using:

            embalm manifest --date 3D12h

        The interval string passed as the date is constructed using an integer 
        followed by one of the following characters s (seconds), m (minutes), 
        h (hours), D (days), W (weeks), M (months), or Y (years). You can 
        combine several to get more resolution.
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        date = ['--time', cmdline['--date']] if cmdline['--date'] else []

        # run duplicity
        rm('duplicity.log')
        cmd = (
            f'duplicity list-current-files'.split()
            + duplicity_options(settings, options)
            + archive_dir_command(settings)
            + sftp_command(settings)
            + date
            + [destination(settings)]
        )
        run_duplicity(cmd, settings, True)


# Restore command {{{1
class Restore(Command):
    NAMES = 'restore', 'r'
    DESCRIPTION = 'recover file or files from backups'
    USAGE = dedent("""
        Usage:
            embalm [options] restore <path>...
            embalm [options] r       <path>...

        Options:
            -d <date>, --date <date>   date of the desired version of paths

        You restore a file or directory using:

            embalm restore src/verif/av/manpages/settings.py

        Use manifest to determine what path you should specify to identify the
        desired file or directory (they will paths relative to the source
        directory).

        You can restore the version of a file or directory that existed on a
        particular date using:

            embalm --date 2015-04-01 restore src/verif/av/manpages/settings.py

        Or, you can restore the version that existed 6 months ago using:

            embalm --date 6M restore src/verif/av/manpages/settings.py

        Your restored files will be found in the working directory in
        {RESTORE_DIR}.
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        paths = cmdline['<path>']
        date = ['--time', cmdline['--date']] if cmdline['--date'] else []

        # run duplicity
        rm('duplicity.log')
        mkdir(settings.restore_dir)
        for path in paths:
            desired = to_path(settings.starting_dir, path).relative_to(settings.src_dir)
            narrate('restoring:', path)
            dest = to_path(settings.restore_dir, desired.name)

            cmd = (
                f'duplicity restore --file-to-restore {desired}'.split()
                + duplicity_options(settings, options)
                + archive_dir_command(settings)
                + sftp_command(settings)
                + date
                + [destination(settings), dest]
            )
            run_duplicity(cmd, settings, 'narrate' in options)
            output(f"restored as: {dest}", culprit=path)


# Settings command {{{1
class Settings(Command):
    NAMES = 'settings', 's'
    DESCRIPTION = 'list settings of chosen configuration'
    USAGE = dedent("""
        Usage:
            embalm settings
            embalm s
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        highlight = Color('yellow')
        normal = Color('cyan')

        for k, v in settings:
            key = f'{k:>22s}'
            key = normal(key) if k in KNOWN_SETTINGS else highlight(key)
            output(f'{key}: {render(v, level=6)}')


# Version {{{1
class Version(Command):
    NAMES = 'version',
    DESCRIPTION = 'display embalm version'
    USAGE = dedent("""
        Usage:
            embalm version
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        # get the Python version
        python = 'Python %s.%s.%s' % (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # output the Avendesora version along with the Python version
        from .__init__ import __version__, __released__
        output('embalm version: %s (%s) [%s].' % (
            __version__, __released__, python
        ))
