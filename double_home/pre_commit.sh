#!/bin/sh



# Путь к папке с GitHub репозиторием
GITHUB_REPO_PATH=/Users/cinnabun/Projects/lms

# Получаем информацию о текущей ветке
branch_info=$(arc info)

# Извлекаем название ветки из полученной информации
current_branch=$(echo "$branch_info" | grep "branch:" | awk '{print $2}')

# Выводим название ветки
echo "Current branch: $current_branch"

# Получаем сообщение коммита из текущего репозитория
commit_message=$(arc log -n 1 --pretty="{title}")
echo "Commit message: $commit_message"

# Переходим в репозиторий GitHub
cd "$GITHUB_REPO_PATH" || { echo "Failed to change directory to $GITHUB_REPO_PATH"; exit 1; }

# Проверяем, существует ли ветка с таким названием в GitHub репозитории
if ! git rev-parse --verify "$current_branch" > /dev/null 2>&1; then
  echo "Branch $current_branch does not exist in GitHub repository."
  exit 1
fi

# Проверяем наличие файла блокировки
if [ -f ".git/index.lock" ]; then
  echo "File '.git/index.lock' exists. Please remove it and try again."
  rm /Users/cinnabun/Projects/lms/.git/index.lock
  exit 1
fi

git checkout "$current_branch" || { echo "Failed to checkout branch $current_branch"; exit 1; }

# Копируем изменённые файлы из исходного репозитория в GitHub репозиторий
# Предполагаем, что исходные файлы находятся в директории /path/to/source/repo
cp -r /Users/cinnabun/arcadia/education/ysda/lms/* .

# Добавляем изменённые файлы в индекс GitHub репозитория
git add .

# Совершаем коммит с сообщением в GitHub репозитории
git commit -m "$commit_message"
