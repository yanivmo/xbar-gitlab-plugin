# GitLab Pipelines Status Indicator

![plugin screenshot](https://i.imgur.com/TghSti5.pngg)

This is a plugin for [Xbar](https://xbarapp.com/) displaying GitLab pipelines status.

## Features

- Monitors multiple projects and branches simultaneously.
- The user controls which projects and branches to monitor.
- Displays the status of the latest three pipelines for each branch and merge request.
- Automatically discovers the merge requests of the configured branches.
- Supports merge trains 🚂🚃🚃
- Clicking a pipeline takes to the pipeline web page.

## Manual installation

1. Copy `gitlab-pipelines-status.py` and `gitlab-pipelines-status.5m.py.vars.json` into xbar plugins directory; e.g., on Mac it is `/Users/yaniv/Library/Application Support/xbar/plugins`.
2. Configure the projects and the branches in `config.json`.
3. In `gitlab-pipelines-status.5m.py.vars.json` set the location of `config.json` and the API key.

