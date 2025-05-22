#!/bin/sh

GITHUB_REPO_PATH=/Users/cinnabun/Projects/lms

# Получаем информацию о текущей ветке
branch_info=$(arc info)

# Извлекаем название ветки из полученной информации
current_branch=$(echo "$branch_info" | grep "branch:" | awk '{print $2}')

# Выводим название ветки
echo "Current branch: $current_branch"

# Переходим в репозиторий GitHub
cd "$GITHUB_REPO_PATH" || { echo "Failed to change directory to $GITHUB_REPO_PATH"; exit 1; }

# Проверяем, существует ли ветка с таким названием в GitHub репозитории
if ! git rev-parse --verify "$current_branch" > /dev/null 2>&1; then
  echo "Branch $current_branch does not exist in GitHub repository."
  exit 1
fi

# Проверяем, существует ли ветка на удалённом сервере GitHub, и создаём её, если нет
if ! git ls-remote --heads origin | grep -q "$current_branch"; then
  git push origin "$current_branch":refs/heads/"$current_branch"
fi

# Пуш в GitHub
git push origin "$current_branch"
