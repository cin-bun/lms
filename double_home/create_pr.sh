#!/bin/bash

source_branch=$1
target_branch=$2
title=$3
body=$4
github_repo_url=$5

# Создаём пул реквест в GitHub
gh pr create \
  --title "$title" \
  --body "$body" \
  --base "$target_branch" \
  --head "$source_branch" \
  --repo "$github_repo_url"
