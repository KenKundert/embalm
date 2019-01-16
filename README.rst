embalm -- Encrypted Backups to a Remote Server
==============================================

:Author: Ken Kundert
:Version: 0.2.0
:Released: 2018-09-14

*This program is no longer being supported. It has been replaced by `Emborg 
<https://github.com/KenKundert/emborg>`_, which is a front-end for Borg rather 
than Duplicity.*

Embalm is a simple command line utility to orchestrate backups. It is built on 
Duplicity, which is a powerful and flexible utility for managing encrypted 
backups, however it has a rather heavy user interface. With Embalm, you specify 
all the details about your backups once in advance, and then use a very simple 
command line interface for your day-to-day activities.  The details are 
contained in ~/.config/embalm.  That directory will contains a file (settings) 
that contains shared settings, and then another file for each backup 
configuration you have.

You will need to dedicate a working directory to your backups.  This directory 
will hold the logfiles and the Duplicity archive directory. The archive 
directory contains Duplicity housekeeping files for the backup. You can place as 
many of the embalm executables as you wish in that directory and they can be 
configured to share the archive directory.

Commands
========

Config
------

List the available backup configurations.  Each configuration will have 
a different source directory (the directory to back up). It can also have 
different settings.

To run a command on a specific configuration, add --config=<cfg> or -c cfg 
before the command. For example::

    embalm -c home full


Due
---

When run with no options it indicates when full and incremental backups were 
last run.  For example::

    > embalm due
    incremental backup was performed 19 hours ago.
    full backup was performed 21 days ago.

You can also specify options that result in an output message if a time limit 
has been exceeded. This allow you to use this with status bar programs such as 
i3status to generate reminders.


Full
----

Run a full backup.  For example::

   embalm full

You first backup must be a full backup, however you should occasionally run full 
backups.  Perhaps once a quarter or twice a year.


Incremental
-----------

Run an incremental backup.  For example::

   embalm incremental

or::

   embalm

Incremental backups should be run on a routine basis, perhaps once a day.  
Incremental backups are preferred over full backups because they are much faster 
and consume much less space. However, the longer you go without a full backup 
the longer your restore will take and due to some issues in Duplicity if you go 
too long you will lose the ability to do restores.


Info
----

This command prints out the locations of important files and directories.


Manifest
--------

Once a backup has been performed, you can list the files available in your 
backup using::

   embalm manifest

You can list the files that existed on a particular date using::

   embalm --date 2015-04-01 manifest

Or, you can list the files that existed 3.5 days ago using::

   embalm --date 3D12h manifest

The interval string passed as the date is constructed using an integer followed 
by one of the following characters s (seconds), m (minutes), h (hours), 
D (days), W (weeks), M (months), or Y (years). You can combine several to get 
more resolution.


Restore
-------

You restore a file or directory using::

   embalm restore ~/bin

Use manifest to determine what path you should specify to identify the desired 
file or directory.

You can restore the version of a file that existed on a particular date using::

   embalm --date 2015-04-01 restore bin

Or, you can restore the version that existed 6 months ago using::

   embalm --date 6M restore bin

The file will be restored into your working directory.


Settings
--------

This command displays all the settings that affect a backup configuration.


Help
----

Information about a variety of topics is provided with the help command.

Use::

   embalm help

for a list of topics, and::

   embalm help <topic>

for information about a specific topic.


Trouble
-------

If Duplicity is refusing to work for you, run using the verbose flags::

   embalm -v -n backup full

Then carefully read the error messages. They should lead you to the problem.


Configuration
=============

Shared Settings
---------------

Shared settings go in ~/.config/embalm/settings. This is a Python file that 
contains values needed by Embalm. It might look like the following::

    default_configuration = 'home'        # default backup configuration
    configuration_files = 'home websites' # available backup configurations
    avendesora_account = 'duplicity'      # Avendesora account name (holds passphrase for encryption key)
    gpg_passphrase = None                 # GPG passphrase to use (if specified, Avendesora is not used)
    ssh_identity = "~/.ssh/backups"       # SSH private key file
    dest_server = "backups"               # SSH name for remote host (may include username, ex. user@server)
    notify = "me@mydomain.com"            # email address to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                          # notification program
    ssh_backend_method = 'protocol'       # use 'option' for Duplicity version 0.6.25 and lower
                                          # use 'protocol' for Duplicity version 0.7.05 and above
    bw_limit = 2000                       # bandwidth limit in kbps
    gpg_binary = 'gpg2'                   # which gpg to use


Configuration Settings
----------------------

Each backup configuration must have a settings file in ~/.config/embalm. The 
name of the file is the name of the backup configuration.  It might look like 
the following::

    dest_dir = '/mnt/backups/{host_name}/{config_name}'
                            # remote directory for backup sets
    src_dir = '~'           # absolute path to directory to be backed up
    excludes = '''
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
    '''.split()
                            # list of glob strings of files or directories to skip

    # commands to be run before and after backups (run from working directory)
    run_before_backup = [
        './clean-home >& clean-home.log',
            # remove the detritus before backing up
    ]
    run_after_backup = [
        './rebuild-manpages > /dev/null',
            # rebuild my man pages, they were deleted in clean
    ]

    # if set, this file or these files must exist or backups will quit with an error
    must_exist = '~/doc/thesis'

String values may incorporate other string valued settings. Use braces to 
interpolate another setting. In addition, you may interpolate the configuration 
name ('config_name'), the host name ('host_name'), the user name ('user_name') 
or Embalm's program name ('prog_name'). An example of this is shown in 
*dest_dir* above.


Precautions
===========

You should assure you have a backup copy of the GPG passphrase in a safe place.  
This is very important. If the only copy of the GPG passphrase is on the disk 
being backed up, then if that disk were to fail you would not be able to access 
your backups.

If you keep the GPG passphrase in the embalm file, you should set its 
permissions so that it is not readable by others::

   chmod 700 embalm

Better yet is to simply not store the passphrase in the embalm script. This can 
be arranged if you are using `Abraxas <https://github.com/KenKundert/abraxas>`_, 
which is a flexible password management system. The interface to Abraxas is 
already built in to embalm, but its use is optional (it need not be installed).

It is also best, if it can be arranged, to keep your backups at a remote site so 
that your backups do not get destroyed in the same disaster, such as a fire or 
flood, that claims your original files. If you do not have, or do not wish to 
use, your own server, Duplicity offers a number of backends that allow you to 
place your backups in the cloud (Rackspace, Dropbox, Amazon, Google, etc.).  
Remember, your data is fully encrypted, so they cannot pry.


Duplicity
---------
Between Duplicity version 0.6.25 and 0.7.05 the way you specify the SSH backend 
changes. Duplicity provides several different implementations of the SSH 
backend. The default is paramiko, however it does not support bandwidth 
limiting. So instead, embalm uses the pexpect version. In version 0.6.25 the 
backend was specified with '--ssh-backend pexpect'. In version 0.7.05 it is now 
specified by adding it to the protocol specification for the remote destination, 
so 'sftp://...' changes to 'pexpect+sftp://...'.

To address this, embalm provides the SSH_BACKEND_METHOD which should be set to 
'option' for Duplicity version 0.6.25 and lower, and should be set to 'protocol' 
for version 0.7.05 and above.
