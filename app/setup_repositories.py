# Copyright © 2022 Cerc

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http:#www.gnu.org/licenses/>.

# env vars:
# CERC_REPO_BASE_DIR defaults to ~/cerc

import os
import sys
import argparse
from decouple import config
import git
from tqdm import tqdm
import click

class GitProgress(git.RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = tqdm(unit = 'B', ascii = True, unit_scale = True)

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()

def is_git_repo(path):
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False

# TODO: find a place for this in the context of click
#parser = argparse.ArgumentParser(
#    epilog="Config provided either in .env or settings.ini or env vars: CERC_REPO_BASE_DIR (defaults to ~/cerc)"
#   )

@click.command()
@click.option('--check-only', is_flag=True, default=False)
@click.option('--pull', is_flag=True, default=False)
@click.option('--branches-file', help="checkout branches specified in this file")
@click.pass_context
def command(ctx, check_only, pull, branches_file):
    '''git clone the set of repositories required to build the complete system from source'''

    quiet = ctx.obj.quiet
    verbose = ctx.obj.verbose
    dry_run = ctx.obj.dry_run

    branches = []

    if branches_file:
        if verbose:
            print(f"loading branches from: {branches_file}")
        with open(branches_file) as branches_file_open:
            branches = branches_file_open.read().splitlines()
        if verbose:
            print(f"Branches are: {branches}")

    dev_root_path = os.path.expanduser(config("DEV_ROOT", default="~/cerc"))

    if not quiet:
        print(f'Dev Root is: {dev_root_path}')

    if not os.path.isdir(dev_root_path):
        if not quiet:
            print(f'Dev root directory doesn\'t exist, creating')
        os.makedirs(dev_root_path)

    with open("repository-list.txt") as repository_list_file:
        repos = repository_list_file.read().splitlines()

    if verbose:
        print (f'Repos: {repos}')

    def process_repo(repo):
        full_github_repo_path = f'git@github.com:{repo}'
        repoName = repo.split("/")[-1]
        full_filesystem_repo_path = os.path.join(dev_root_path, repoName)
        is_present = os.path.isdir(full_filesystem_repo_path)
        if not quiet:
            present_text = f'already exists active branch: {git.Repo(full_filesystem_repo_path).active_branch}' if is_present else 'Needs to be fetched'
            print(f'Checking: {full_filesystem_repo_path}: {present_text}')
        # Quick check that it's actually a repo
        if is_present:
            if not is_git_repo(full_filesystem_repo_path):
                print(f'Error: {full_filesystem_repo_path} does not contain a valid git repository')
                sys.exit(1)
            else:
                if pull:
                    if verbose:
                        print(f'Running git pull for {full_filesystem_repo_path}')
                    if not check_only:
                        git_repo = git.Repo(full_filesystem_repo_path)
                        origin = git_repo.remotes.origin
                        origin.pull(progress = None if quiet else GitProgress())
                    else:
                        print("(git pull skipped)")
        if not is_present:
            # Clone
            if verbose:
                print(f'Running git clone for {full_github_repo_path} into {full_filesystem_repo_path}')
            if not dry_run:
                git.Repo.clone_from(full_github_repo_path, full_filesystem_repo_path, 
                progress = None if quiet else GitProgress())
            else:
                print("(git clone skipped)")
        # Checkout the requested branch, if one was specified
        if branches:
            # Find the current repo in the branches list
            for repo_branch in branches:
                repo_branch_tuple = repo_branch.split(" ")
                if repo_branch_tuple[0] == repo:
                    # checkout specified branch
                    branch_to_checkout = repo_branch_tuple[1]
                    if verbose:
                        print(f"checking out branch {branch_to_checkout} in repo {repo}")
                        git_repo = git.Repo(full_filesystem_repo_path)
                        git_repo.git.checkout(branch_to_checkout)
                    


    for repo in repos:
        process_repo(repo)
