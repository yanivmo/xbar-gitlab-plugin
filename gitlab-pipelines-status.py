#!/usr/bin/env LC_ALL=he-IL.UTF-8 PYTHONIOENCODING=UTF-8 python3
# -*- coding: utf-8 -*-

# <xbar.title>GitLab Pipelines Status Indicator</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Yaniv Mordekhay</xbar.author>
# <xbar.author.github>yanivmo</xbar.author.github>
# <xbar.desc>Displays the status of GitLab pipelines for the specified branches. The tracked branches should be listed in the configuration file.</xbar.desc>
# <xbar.image>https://i.imgur.com/TghSti5.png</xbar.image>
# <xbar.dependencies>python3</xbar.dependencies>
# <xbar.abouturl>https://github.com/yanivmo/xbar-gitlab-plugin</xbar.abouturl>
# <xbar.var>string(VAR_GITLAB_TOKEN=""): GitLab personal API token.</xbar.var>
# <xbar.var>string(VAR_SPECIFIC_CONFIG_PATHNAME="~/xbar/.gitlab-specific-status-indicator.json"): Location of the configuration file. File format: {[ProjectFullName]: BranchNamesList}</xbar.var>
# <xbar.var>string(VAR_AUTO_CONFIG_PATHNAME="~/xbar/.gitlab-auto-status-indicator.json"): Location of the projects to follow configuration file. File format: {projects: [ProjectFullName1, ProjectFullName2]}</xbar.var>

# The config file is a JSON file containing an object whose attributes are project names and their
# values are lists of branch names. For example:
# {
#     "google/search": ["master", "develop"]
# }

import os
import json
import socket
from datetime import datetime, timezone
from urllib import request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote

GITLAB_TOKEN = os.environ.get("VAR_GITLAB_TOKEN")
SPECIFIC_CONFIG_PATHNAME = os.environ.get("VAR_SPECIFIC_CONFIG_PATHNAME")
AUTO_CONFIG_PATHNAME = os.environ.get("VAR_AUTO_CONFIG_PATHNAME")

PIPELINE_STATUSES = {
    "created": "",
    "waiting_for_resource": "⏳",
    "preparing": "▶️",
    "pending": "⏳",
    "running": "▶️",
    "success": "✅",
    "failed": "❌",
    "canceled": "✖️",
    "skipped": "➖",
    "manual": "💤",
    "scheduled": "",
}


def http_get_json(url, headers):
    headers["Accept"] = "application/json"
    req = request.Request(url, headers=headers)
    response = request.urlopen(req)
    text = response.read().decode("utf-8")
    return json.loads(text)


class GitLab:
    API_BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, api_token):
        self._api_token = api_token

    def get_resource(self, uri, query: dict = None):
        if query is None:
            query = {}
        url = f"{GitLab.API_BASE_URL}/{uri}?{urlencode(query)}"

        headers = {"PRIVATE-TOKEN": self._api_token}

        return http_get_json(url, headers)

    def get_branch_merge_request(self, project_id, branch_name: str):
        uri = f"projects/{project_id}/merge_requests"
        query = {"source_branch": branch_name}
        return self.get_resource(uri, query)

    def get_all_my_merge_requests(self, project_id, username: str):
        uri = f"projects/{project_id}/merge_requests"
        query = {"state": "opened", "assignee_username": username}
        return self.get_resource(uri, query)

    def get_my_username(self):
        uri = 'user'
        user = self.get_resource(uri)
        return user['username']

    def get_ref_latest_pipelines(self, project_id, ref: str, count=3):
        uri = f"projects/{project_id}/pipelines"
        query = {
            "ref": ref,
            "per_page": count,
        }
        return self.get_resource(uri, query)

    def get_merge_request_latest_pipelines(self, project_id, mr_id: str, count=3):
        mr_ref = f"refs/merge-requests/{mr_id}/head"
        pipelines = self.get_ref_latest_pipelines(project_id, mr_ref, count)

        mr_train_ref = f"refs/merge-requests/{mr_id}/train"
        train_pipelines = self.get_ref_latest_pipelines(project_id, mr_train_ref, count)

        return sorted(
            pipelines + train_pipelines, key=lambda p: p["created_at"], reverse=True
        )

    def get_branch_latest_pipelines(self, project_id, branch_name: str, count=3):
        if branch_name.startswith("!"):
            return self.get_merge_request_latest_pipelines(
                project_id, branch_name[1:], count
            )
        else:
            return self.get_ref_latest_pipelines(project_id, branch_name, count)

    def get_pipeline(self, project_id, pipeline_id: str):
        uri = f"projects/{project_id}/pipelines/{pipeline_id}"
        return self.get_resource(uri)

    def get_branches(self, project_id):
        uri = f"projects/{project_id}/repository/branches"
        query = {}
        branches = self.get_resource(uri, query)
        return [b for b in branches if b["merged"] is False]


def normalize_time(time_str):
    return (
        datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        .replace(microsecond=0, tzinfo=timezone.utc)
        .astimezone()
        .strftime("%c")
    )


def process_branch_pipelines(pipelines):
    for p in pipelines:
        status = PIPELINE_STATUSES.get(p["status"], "?")
        pipeline_id = p["id"]
        url = p["web_url"]
        created_at = normalize_time(p["created_at"])

        train_icon = ""
        if p["ref"].endswith("train"):
            train_icon = "🚂🚃🚃"
        print(
            f"--{status} #{pipeline_id}    ⏰ {created_at}  {train_icon}| href={url} font=Monaco"
        )


def generate_branch_list(plugin_config):
    gitlab = GitLab(GITLAB_TOKEN)
    username = gitlab.get_my_username()

    branches = {}

    for project in plugin_config['projects']:
        branches[project] = []
        quoted_project = quote(project, safe="")
        my_mrs = gitlab.get_all_my_merge_requests(quoted_project, username)
        for mr in my_mrs:
            branches[project].append(mr["source_branch"])

    return branches

def process_all_merge_requests(plugin_config):
    print('Merge Requests')
    print("---")
    gitlab = GitLab(GITLAB_TOKEN)
    username = gitlab.get_my_username()

    for project in plugin_config['projects']:
        quoted_project = quote(project, safe="")
        print(project, username)
        my_mrs = gitlab.get_all_my_merge_requests(quoted_project, username)
    for mr in my_mrs:
        mr_id = mr["iid"]
        mr_url = mr["web_url"]
        print(f"└┈Ⓜ️{mr_id}| href={mr_url} font=Monaco")

def process_project_branches(project_branches):
    gitlab = GitLab(GITLAB_TOKEN)

    for project_name, branches in project_branches.items():

        if len(branches):
            print(project_name)

        quoted_project = quote(project_name, safe="")

        for branch_name in branches:
            try:
                pipelines = gitlab.get_branch_latest_pipelines(
                    quoted_project, branch_name
                )
                branch_status = "🤷"
                if pipelines:
                    branch_status = PIPELINE_STATUSES.get(pipelines[0]["status"], "?")
                print(f"{branch_status} {branch_name}")

            except HTTPError as e:
                if e.code == 404:
                    print(f"💔Not found: {branch_name} | color=red")
                    continue
                raise e
            except URLError as e:
                if (
                        isinstance(e.reason, socket.gaierror)
                        and e.reason.errno == socket.EAI_NONAME
                ):
                    print("💔 No connection | color=red")
                    break
                raise e

            process_branch_pipelines(pipelines)

            merge_requests = gitlab.get_branch_merge_request(
                quoted_project, branch_name
            )
            for mr in merge_requests:
                mr_id = mr["iid"]
                mr_title = mr["title"]
                pipelines = gitlab.get_merge_request_latest_pipelines(
                    quoted_project, mr_id
                )

                if pipelines:
                    pipeline_status = PIPELINE_STATUSES.get(pipelines[0]["status"], "?")
                    print(f"└┈Ⓜ️{pipeline_status} !{mr_id}: {mr_title}")
                    process_branch_pipelines(pipelines)

        print("---")


def gitlab_logo_dark():
    return "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"


def main():
    if GITLAB_TOKEN is None:
        raise Exception("GitLab personal API token is not configured.")

    print(f"| templateImage={gitlab_logo_dark()}")
    print("---")

    if SPECIFIC_CONFIG_PATHNAME is None and AUTO_CONFIG_PATHNAME is None:
        raise Exception("Configuration file location is not configured.")

    if ((SPECIFIC_CONFIG_PATHNAME and os.path.exists(os.path.expanduser(SPECIFIC_CONFIG_PATHNAME))) and
            AUTO_CONFIG_PATHNAME and os.path.exists(os.path.expanduser(AUTO_CONFIG_PATHNAME))):
        raise Exception("Choose only one configuration file type: auto/specific")

    if SPECIFIC_CONFIG_PATHNAME and os.path.exists(os.path.expanduser(SPECIFIC_CONFIG_PATHNAME)):
        config_pathname = os.path.expanduser(SPECIFIC_CONFIG_PATHNAME)
        with open(config_pathname) as f:
            project_branches = json.load(f)
        process_project_branches(project_branches)

    elif AUTO_CONFIG_PATHNAME and os.path.exists(os.path.expanduser(AUTO_CONFIG_PATHNAME)):
        config_pathname = os.path.expanduser(AUTO_CONFIG_PATHNAME)
        with open(config_pathname) as f:
            plugin_config = json.load(f)
        project_branches = generate_branch_list(plugin_config)
        process_project_branches(project_branches)
        # process_all_merge_requests(plugin_config)

if __name__ == "__main__":
    main()
