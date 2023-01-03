#!/usr/bin/env LC_ALL=he-IL.UTF-8 PYTHONIOENCODING=UTF-8 python3
# -*- coding: utf-8 -*-

# <xbar.title>GitLab Pipelines Status Indicator</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Yaniv Mordekhay</xbar.author>
# <xbar.author.github>yanivmo</xbar.author.github>
# <xbar.desc>Displays the status of GitLab pipelines for the specified branches. The tracked branches should be listed in the configuration file.</xbar.desc>
# <xbar.image></xbar.image>
# <xbar.dependencies>python3</xbar.dependencies>
# <xbar.var>string(VAR_GITLAB_TOKEN=""): GitLab personal API token.</xbar.var>
# <xbar.var>string(VAR_CONFIG_PATHNAME="~/.gitlab-status-indicator.json"): Location of the configuration file. File format: {[ProjectFullName]: BranchNamesList}</xbar.var>

# The config file is a JSON file containing an object whose attributes are project names and their
# values are lists of branch names. For example:
# {
#     "google/search": ["master", "develop"]
# }

import os
import json
import socket
from datetime import datetime
from urllib import request
from urllib.error import URLError
from urllib.parse import urlencode, quote

GITLAB_TOKEN = os.environ.get("VAR_GITLAB_TOKEN")
CONFIG_PATHNAME = os.environ.get("VAR_CONFIG_PATHNAME")

PIPELINE_STATUSES = {
    "created": "",
    "waiting_for_resource": "",
    "preparing": "",
    "pending": "",
    "running": "",
    "success": "✅",
    "failed": "❌",
    "canceled": "✖️",
    "skipped": "➖",
    "manual": "",
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

    def get_branch_latest_finished_pipeline(self, project_id, branch_name):
        uri = f"projects/{project_id}/pipelines"
        query = {
            "ref": branch_name,
            "scope": "finished",
            "per_page": 1,
        }
        pipelines = self.get_resource(uri, query)
        return pipelines[0] if len(pipelines) > 0 else None

    def get_branches(self, project_id):
        uri = f"projects/{project_id}/repository/branches"
        query = {}
        branches = self.get_resource(uri, query)
        return [b for b in branches if b["merged"] is False]


def normalize_time(time_str):
    return (
        datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        .replace(microsecond=0)
        .strftime("%c")
    )


def process_pipeline(pipeline):
    status = PIPELINE_STATUSES.get(pipeline["status"], "?")
    ref = pipeline["ref"]
    web_url = pipeline["web_url"]
    created_at = normalize_time(pipeline["created_at"])

    print(f"{status} {ref} | href={web_url}")
    print(f"--⏱ {created_at} | href={web_url}")


def process_project_branches(project_branches):
    gitlab = GitLab(GITLAB_TOKEN)

    for project_name, branches in project_branches.items():
        print(project_name)

        for branch_name in branches:
            try:
                pipeline = gitlab.get_branch_latest_finished_pipeline(
                    quote(project_name, safe=""), branch_name
                )
            except URLError as e:
                if (
                    isinstance(e.reason, socket.gaierror)
                    and e.reason.errno == socket.EAI_NONAME
                ):
                    print("💔 No connection | color=red")
                    break
                raise e
            process_pipeline(pipeline)

        print("---")


def gitlab_logo():
    return "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"


def main():
    if GITLAB_TOKEN is None:
        raise Exception("GitLab personal API token is not configured.")

    if CONFIG_PATHNAME is None:
        raise Exception("ERROR: Configuration file location is not configured.")

    config_pathname = os.path.expanduser(CONFIG_PATHNAME)
    with open(config_pathname) as f:
        project_branches = json.load(f)

    print(f"| image={gitlab_logo()}")
    print("---")
    process_project_branches(project_branches)


if __name__ == "__main__":
    main()
