#!/bin/bash

branch_name=$1
github_repo_path=/Users/cinnabun/Projects/lms

# Создание ветки в монорепозитории
arc checkout -b $branch_name
arc push $branch_name


# Переходим в репозиторий GitHub
cd "$github_repo_path"

# Создание ветки в GitHub
git checkout -b "$branch_name"
git push origin "$branch_name"

