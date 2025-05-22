# #!/bin/sh



# # Путь к папке с GitHub репозиторием
# GITHUB_REPO_PATH=/Users/cinnabun/Projects/lms

# # Получаем информацию о текущей ветке
# branch_info=$(arc info)
# # echo "Current info: $branch_info"

# # Извлекаем название ветки из полученной информации
# current_branch=$(echo "$branch_info" | grep "branch:" | awk '{print $2}')

# # Выводим название ветки
# echo "Current branch: $current_branch"

# # Получаем сообщение коммита из текущего репозитория
# commit_message=$(arc log -n 1 --pretty="{title}")
# echo "Commit message: $commit_message"
# # Получаем список изменённых файлов в последнем коммите
# changed_files=$(arc diff --name-only HEAD~1 HEAD)
# echo "Commit files: $changed_files"

# # Переходим в репозиторий GitHub
# cd "$GITHUB_REPO_PATH" || { echo "Failed to change directory to $GITHUB_REPO_PATH"; exit 1; }

# # Проверяем, существует ли ветка с таким названием в GitHub репозитории
# if ! git rev-parse --verify "$current_branch" > /dev/null 2>&1; then
#   echo "Branch $current_branch does not exist in GitHub repository."
#   exit 1
# fi



# # Проверяем наличие файла блокировки
# if [ -f ".git/index.lock" ]; then
#   echo "File '.git/index.lock' exists. Please remove it and try again."
#   rm /Users/cinnabun/Projects/lms/.git/index.lock
# fi

# git checkout "$current_branch" || { echo "Failed to checkout branch $current_branch"; exit 1; }

# # Копируем изменённые файлы из исходного репозитория в GitHub репозиторий
# for file in $changed_files; do
#   # Разделяем путь файла по '/' и берём часть пути начиная с элемента после 'lms'
#   modified_file_path=$(echo "$file" | awk -F'/' '{for (i=1; i<=NF; i++) if ($i == "lms") {for (j=i+1; j<=NF; j++) printf "%s/", $(j); exit}}')
  
#   # Убираем лишний слеш в конце пути, если он есть
#   modified_file_path=$(echo "$modified_file_path" | sed 's/\/$//')
  
#   cp -r "/Users/cinnabun/arcadia/education/ysda/lms/$file" "./$modified_file_path"
#   if [ $? -ne 0 ]; then
#     echo "Failed to copy file: $modified_file_path"
#     echo "Failed to copy file: $file"
#     exit 1
#   fi
# done


# # Добавляем изменённые файлы в индекс GitHub репозитория
# git add .

# # Совершаем коммит с сообщением в GitHub репозитории
# git commit -m "$commit_message"


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

# Получаем список изменённых файлов в последнем коммите
changed_files=$(arc diff --name-only HEAD~1 HEAD)
echo "Commit files: $changed_files"

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
  if [ $? -ne 0 ]; then
    echo "Failed to remove the index.lock file."
    exit 1
  fi
fi

git checkout "$current_branch" || { echo "Failed to checkout branch $current_branch"; exit 1; }

# Копируем изменённые файлы из исходного репозитория в GitHub репозиторий
for file in $changed_files; do
  # Разделяем путь файла по '/' и берём часть пути начиная с элемента после 'lms'
  modified_file_path=$(echo "$file" | awk -F'/' '{for (i=1; i<=NF; i++) if ($i == "lms") {for (j=i+1; j<=NF; j++) printf "%s/", $(j); exit}}')
  
  # Убираем лишний слеш в конце пути, если он есть
  modified_file_path=$(echo "$modified_file_path" | sed 's/\/$//')
  
  cp -r "/Users/cinnabun/arcadia/education/ysda/lms/$modified_file_path" "./$modified_file_path"
  if [ $? -ne 0 ]; then
    echo "Failed to copy file: $modified_file_path"
    exit 1
  fi
done

# Добавляем изменённые файлы в индекс GitHub репозитория
git add .

# Совершаем коммит с сообщением в GitHub репозитории
git commit -m "$commit_message"
