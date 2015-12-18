# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import fixtures
import testtools

from git_restack.tests import utils


class BaseGitRestackTestCase(testtools.TestCase):
    """Base class for the git-restack tests."""

    def setUp(self):
        """Configure testing environment.

        Prepare directory for the testing and clone test Git repository.
        Require Gerrit war file in the .gerrit directory to run Gerrit local.
        """
        super(BaseGitRestackTestCase, self).setUp()
        self.useFixture(fixtures.Timeout(2 * 60, True))

        self.root_dir = self.useFixture(fixtures.TempDir()).path
        self.upstream_dir = os.path.join(self.root_dir, "upstream")
        self.local_dir = os.path.join(self.root_dir, "local")

        os.makedirs(self._dir('upstream'))
        self._run_git('upstream', 'init')
        self._simple_change('upstream', 'initial text', 'initial commit')
        self._simple_change('upstream', 'second text', 'second commit')
        self._run_git('upstream', 'checkout', '-b', 'branch1')
        self._simple_change('upstream', 'branch1 text', 'branch1 commit')
        self._run_git('upstream', 'checkout', 'master')
        self._run_git('upstream', 'checkout', '-b', 'branch2')

        gitreview = '[gerrit]\ndefaultbranch=branch2\n'
        self._simple_change('upstream', gitreview, 'branch2 commit',
                            file_=self._dir('upstream', '.gitreview'))
        self._run_git('upstream', 'checkout', 'master')

    def _dir(self, base, *args):
        """Creates directory name from base name and other parameters."""
        return os.path.join(getattr(self, base + '_dir'), *args)

    def _run_git(self, dirname, command, *args):
        """Run git command using test git directory."""
        if command == 'clone':
            return utils.run_git(command, args[0], self._dir(dirname))
        return utils.run_git('--git-dir=' + self._dir(dirname, '.git'),
                             '--work-tree=' + self._dir(dirname),
                             command, *args)

    def _run_git_restack(self, *args, **kwargs):
        """Run git-restack utility from source."""
        git_restack = utils.run_cmd('which', 'git-restack')
        kwargs.setdefault('chdir', self.local_dir)
        return utils.run_cmd(git_restack, *args, **kwargs)

    def _simple_change(self, dirname, change_text, commit_message,
                       file_=None):
        """Helper method to create small changes and commit them."""
        if file_ is None:
            file_ = self._dir(dirname, 'test_file.txt')
        utils.write_to_file(file_, change_text.encode())
        self._run_git(dirname, 'add', file_)
        self._run_git(dirname, 'commit', '-m', commit_message)

    def _git_log(self, dirname):
        out = self._run_git(dirname, 'log', '--oneline')
        commits = []
        for line in out.split('\n'):
            commits.append(line.split(' ', 1))
        return commits
