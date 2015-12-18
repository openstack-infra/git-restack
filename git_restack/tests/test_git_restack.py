# -*- coding: utf-8 -*-

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

from git_restack import tests


class GitRestackTestCase(tests.BaseGitRestackTestCase):
    """Class for config tests."""

    def test_git_restack(self):
        self._run_git('local', 'clone', self._dir('upstream'))
        self._simple_change('local', 'b1 text', 'b1')
        self._simple_change('local', 'b2 text', 'b2')
        self._simple_change('local', 'b3 text', 'b3')

        commits = self._git_log('local')
        self.assertEqual(commits[0][1], 'b3')
        self.assertEqual(commits[1][1], 'b2')
        self.assertEqual(commits[2][1], 'b1')
        self.assertEqual(commits[3][1], 'second commit')
        self.assertEqual(commits[4][1], 'initial commit')
        out = self._run_git_restack()
        lines = out.split('\n')
        self.assertEqual(lines[0], 'pick %s %s' %
                         (commits[2][0], commits[2][1]))
        self.assertEqual(lines[1], 'pick %s %s' %
                         (commits[1][0], commits[1][1]))
        self.assertEqual(lines[2], 'pick %s %s' %
                         (commits[0][0], commits[0][1]))
        self.assertEqual(lines[3], '')

    def test_git_restack_gitreview(self):
        self._run_git('local', 'clone', self._dir('upstream'))
        self._run_git('local', 'checkout', 'branch2')
        self._simple_change('local', 'b1 text', 'b1')
        self._simple_change('local', 'b2 text', 'b2')
        self._simple_change('local', 'b3 text', 'b3')

        commits = self._git_log('local')
        self.assertEqual(commits[0][1], 'b3')
        self.assertEqual(commits[1][1], 'b2')
        self.assertEqual(commits[2][1], 'b1')
        self.assertEqual(commits[3][1], 'branch2 commit')
        self.assertEqual(commits[4][1], 'second commit')
        self.assertEqual(commits[5][1], 'initial commit')
        out = self._run_git_restack()
        lines = out.split('\n')
        self.assertEqual(lines[0], 'pick %s %s' %
                         (commits[2][0], commits[2][1]))
        self.assertEqual(lines[1], 'pick %s %s' %
                         (commits[1][0], commits[1][1]))
        self.assertEqual(lines[2], 'pick %s %s' %
                         (commits[0][0], commits[0][1]))
        self.assertEqual(lines[3], '')

    def test_git_restack_arg(self):
        self._run_git('local', 'clone', self._dir('upstream'))
        self._run_git('local', 'checkout', 'branch1')
        self._simple_change('local', 'b1 text', 'b1')
        self._simple_change('local', 'b2 text', 'b2')
        self._simple_change('local', 'b3 text', 'b3')

        commits = self._git_log('local')
        self.assertEqual(commits[0][1], 'b3')
        self.assertEqual(commits[1][1], 'b2')
        self.assertEqual(commits[2][1], 'b1')
        self.assertEqual(commits[3][1], 'branch1 commit')
        self.assertEqual(commits[4][1], 'second commit')
        self.assertEqual(commits[5][1], 'initial commit')
        out = self._run_git_restack('branch1')
        lines = out.split('\n')
        self.assertEqual(lines[0], 'pick %s %s' %
                         (commits[2][0], commits[2][1]))
        self.assertEqual(lines[1], 'pick %s %s' %
                         (commits[1][0], commits[1][1]))
        self.assertEqual(lines[2], 'pick %s %s' %
                         (commits[0][0], commits[0][1]))
        self.assertEqual(lines[3], '')
