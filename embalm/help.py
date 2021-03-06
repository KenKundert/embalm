# Help
# Output a help topic.

# License {{{1
# Copyright (C) 2017 Kenneth S. Kundert
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.


# Imports {{{1
from .command import Command
from .utilities import pager, two_columns
from inform import error, output
from textwrap import dedent

# HelpMessage base class {{{1
class HelpMessage(object):
    # get_name() {{{2
    @classmethod
    def get_name(cls):
        try:
            return cls.name.lower()
        except AttributeError:
            # consider converting lower to upper case transitions in __name__ to
            # dashes.
            return cls.__name__.lower()

    # topics {{{2
    @classmethod
    def topics(cls):
        for sub in cls.__subclasses__():
            yield sub

    # show {{{2
    @classmethod
    def show(cls, name=None, desc=None):
        if name:
            command, _ = Command.find(name)
            if command:
                return pager(command.help())
            for topic in cls.topics():
                if name == topic.get_name():
                    return pager(topic.help())
            error('topic not found.', culprit=name)
        else:
            cls.help(desc)

    # summarize {{{2
    @classmethod
    def summarize(cls, width=16):
        summaries = []
        for topic in sorted(cls.topics(), key=lambda topic: topic.get_name()):
            summaries.append(two_columns(topic.get_name(), topic.DESCRIPTION))
        return '\n'.join(summaries)

    # help {{{2
    @classmethod
    def help(cls, desc):
        if desc:
            output(desc.strip() + '\n')

        output('Available commands:')
        output(Command.summarize())

        output('\nAvailable topics:')
        output(cls.summarize())


# Overview class {{{1
class Overview(HelpMessage):
    DESCRIPTION = "overview of embalm"

    @staticmethod
    def help():
        text = dedent("""
            Embalm is a simple command line utility to orchestrate backups. It
            is built on Duplicity, which is a powerful and flexible utility for
            managing encrypted backups, however it has a rather heavy user
            interface. With embalm, you specify all the details about your
            backups once in advance, and then use a very simple command line
            interface for your day-to-day activities.

            Embalm requires generic configuration information be specified in
            ~/.config/embalm/settings. In this same directory you may have files
            that may have specific backup configurations. This files should be
            listed in configuration_files in the primary settings file. To use a
            configuration, specify its name with the --config command line option.

            Each backup configuration must have a persistent working directory
            (specified with working_dir setting). After reading the appropriate
            configuration, Embalm will change to the working directory before
            running.  This directory will contain the Duplicity backup sets as
            well as the Duplicity and Embalm log files. It might also contain
            executables that are associated with the configuration, such as a
            configuration to strip unwanted files before the backup is
            performed.
        """).strip()
        return text


# Precautions class {{{1
class Precautions(HelpMessage):
    DESCRIPTION = "what everybody should know before using embalm"

    @staticmethod
    def help():
        text = dedent("""
            You should assure you have a backup copy of the GPG passphrase in a
            safe place.  This is very important. If the only copy of the GPG
            passphrase is on the disk being backed up and that disk were to fail
            you would not be able to access your backups.

            If you keep the GPG passphrase in a settings file, you should set
            its permissions so that it is not readable by others:

                chmod 700 ~/.config/embalm/settings

            Better yet is to simply not store the passphrase.  This can be
            arranged if you are using Avendesora
            (https://github.com/KenKundert/avendesora), which is a flexible
            password management system. The interface to Avendesora is already
            built in to embalm, but its use is optional (it need not be
            installed).

            It is also best, if it can be arranged, to keep your backups at a
            remote site so that your backups do not get destroyed in the same
            disaster, such as a fire or flood, that claims your original files.
            If you do not have, or do not wish to use, your own server,
            Duplicity offers a number of backends that allow you to place your
            backups in the cloud (Rackspace, Dropbox, Amazon, Google, etc.).
            Remember, your data is fully encrypted, so they cannot pry.
        """).strip()
        return text


