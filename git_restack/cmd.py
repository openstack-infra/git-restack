#!/usr/bin/env python
from __future__ import print_function

COPYRIGHT = """\
Copyright (C) 2011-2012 OpenStack LLC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.

See the License for the specific language governing permissions and
limitations under the License."""

import argparse
import datetime
import os
import shlex
import subprocess
import sys

import pkg_resources

if sys.version < '3':
    import ConfigParser
    import urllib
    import urlparse
    urlencode = urllib.urlencode
    urljoin = urlparse.urljoin
    urlparse = urlparse.urlparse
    do_input = raw_input
else:
    import configparser as ConfigParser

    import urllib.parse
    import urllib.request
    urlencode = urllib.parse.urlencode
    urljoin = urllib.parse.urljoin
    urlparse = urllib.parse.urlparse
    do_input = input

VERBOSE = False
UPDATE = False
LOCAL_MODE = 'GITREVIEW_LOCAL_MODE' in os.environ
CONFIGDIR = os.path.expanduser("~/.config/git-review")
GLOBAL_CONFIG = "/etc/git-review/git-review.conf"
USER_CONFIG = os.path.join(CONFIGDIR, "git-review.conf")
DEFAULTS = dict(branch='master')


class GitRestackException(Exception):
    pass


class CommandFailed(GitRestackException):

    def __init__(self, *args):
        Exception.__init__(self, *args)
        (self.rc, self.output, self.argv, self.envp) = args
        self.quickmsg = dict([
            ("argv", " ".join(self.argv)),
            ("rc", self.rc),
            ("output", self.output)])

    def __str__(self):
        return self.__doc__ + """
The following command failed with exit code %(rc)d
    "%(argv)s"
-----------------------
%(output)s
-----------------------""" % self.quickmsg


class GitDirectoriesException(CommandFailed):
    "Cannot determine where .git directory is."
    EXIT_CODE = 70


class GitMergeBaseException(CommandFailed):
    "Cannot determine merge base."
    EXIT_CODE = 71


class GitConfigException(CommandFailed):
    """Git config value retrieval failed."""
    EXIT_CODE = 128


def run_command_foreground(*argv, **kwargs):
    if VERBOSE:
        print(datetime.datetime.now(), "Running:", " ".join(argv))
    if len(argv) == 1:
        # for python2 compatibility with shlex
        if sys.version_info < (3,) and isinstance(argv[0], unicode):
            argv = shlex.split(argv[0].encode('utf-8'))
        else:
            argv = shlex.split(str(argv[0]))
    subprocess.call(argv)


def run_command_status(*argv, **kwargs):
    if VERBOSE:
        print(datetime.datetime.now(), "Running:", " ".join(argv))
    if len(argv) == 1:
        # for python2 compatibility with shlex
        if sys.version_info < (3,) and isinstance(argv[0], unicode):
            argv = shlex.split(argv[0].encode('utf-8'))
        else:
            argv = shlex.split(str(argv[0]))
    stdin = kwargs.pop('stdin', None)
    newenv = os.environ.copy()
    newenv['LANG'] = 'C'
    newenv['LANGUAGE'] = 'C'
    newenv.update(kwargs)
    p = subprocess.Popen(argv,
                         stdin=subprocess.PIPE if stdin else None,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         env=newenv)
    (out, nothing) = p.communicate(stdin)
    out = out.decode('utf-8', 'replace')
    return (p.returncode, out.strip())


def run_command(*argv, **kwargs):
    (rc, output) = run_command_status(*argv, **kwargs)
    return output


def run_command_exc(klazz, *argv, **env):
    """Run command *argv, on failure raise klazz

    klazz should be derived from CommandFailed
    """
    (rc, output) = run_command_status(*argv, **env)
    if rc != 0:
        raise klazz(rc, output, argv, env)
    return output


def get_version():
    requirement = pkg_resources.Requirement.parse('git-restack')
    provider = pkg_resources.get_provider(requirement)
    return provider.version


def git_directories():
    """Determine (absolute git work directory path, .git subdirectory path)."""
    cmd = ("git", "rev-parse", "--show-toplevel", "--git-dir")
    out = run_command_exc(GitDirectoriesException, *cmd)
    try:
        return out.splitlines()
    except ValueError:
        raise GitDirectoriesException(0, out, cmd, {})


def git_config_get_value(section, option, default=None, as_bool=False):
    """Get config value for section/option."""
    cmd = ["git", "config", "--get", "%s.%s" % (section, option)]
    if as_bool:
        cmd.insert(2, "--bool")
    if LOCAL_MODE:
        __, git_dir = git_directories()
        cmd[2:2] = ['-f', os.path.join(git_dir, 'config')]
    try:
        return run_command_exc(GitConfigException, *cmd).strip()
    except GitConfigException as exc:
        if exc.rc == 1:
            return default
        raise


class Config(object):
    """Expose as dictionary configuration options."""

    def __init__(self, config_file=None):
        self.config = DEFAULTS.copy()
        filenames = [] if LOCAL_MODE else [GLOBAL_CONFIG, USER_CONFIG]
        if config_file:
            filenames.append(config_file)
        for filename in filenames:
            if os.path.exists(filename):
                if filename != config_file:
                    msg = ("Using global/system git-review config files (%s) "
                           "is deprecated")
                    print(msg % filename)
                self.config.update(load_config_file(filename))

    def __getitem__(self, key):
        value = git_config_get_value('gitreview', key)
        if value is None:
            value = self.config[key]
        return value


def load_config_file(config_file):
    """Load configuration options from a file."""
    configParser = ConfigParser.ConfigParser()
    configParser.read(config_file)
    options = {
        'scheme': 'scheme',
        'hostname': 'host',
        'port': 'port',
        'project': 'project',
        'branch': 'defaultbranch',
        'remote': 'defaultremote',
        'rebase': 'defaultrebase',
        'track': 'track',
        'usepushurl': 'usepushurl',
    }
    config = {}
    for config_key, option_name in options.items():
        if configParser.has_option('gerrit', option_name):
            config[config_key] = configParser.get('gerrit', option_name)
    return config


def main():
    usage = "git restack [BRANCH]"

    parser = argparse.ArgumentParser(usage=usage, description=COPYRIGHT)

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                        help="Output more information about what's going on")
    parser.add_argument("--license", dest="license", action="store_true",
                        help="Print the license and exit")
    parser.add_argument("--version", action="version",
                        version='%s version %s' %
                        (os.path.split(sys.argv[0])[-1], get_version()))
    parser.add_argument("branch", nargs="?")

    parser.set_defaults(verbose=False)

    try:
        (top_dir, git_dir) = git_directories()
    except GitDirectoriesException as no_git_dir:
        pass
    else:
        no_git_dir = False
        config = Config(os.path.join(top_dir, ".gitreview"))
    options = parser.parse_args()
    if no_git_dir:
        raise no_git_dir

    if options.license:
        print(COPYRIGHT)
        sys.exit(0)

    global VERBOSE
    VERBOSE = options.verbose

    if options.branch is None:
        branch = config['branch']
    else:
        branch = options.branch

    if branch is None:
        branch = 'master'

    status = 0

    cmd = "git merge-base HEAD origin/%s" % branch
    base = run_command_exc(GitMergeBaseException, cmd)

    run_command_foreground("git rebase -i %s" % base, stdin=sys.stdin)

    sys.exit(status)


if __name__ == "__main__":
    main()
