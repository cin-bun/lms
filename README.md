# YSDA lms

## Настройка переменных окружения

**TODO:** Определить способ генерации файла `.env` (https://docs.yandex-team.ru/yatool/commands/vault). 

Можно скопировать переменные окружения из [этой ссылки](https://paste.yandex-team.ru/a35ee897-3a57-4e07-8ea8-a884f0fd29ef) и положить файл рядом с сервисом `lms/settings/.env`.

## Запуск сервиса

Запуск в DEV режиме:

### Подготовка окружения

```bash
brew install libpng libjpeg libpqxx libmagic swig curl

# Install libraries that depend on openssl
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/opt/homebrew/opt/openssl@3/include/lib -L/opt/homebrew/opt/curl/lib" CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include -I/opt/homebrew/opt/curl/include" pip install --compile --no-cache-dir pycurl
env LDFLAGS="-L$(brew --prefix openssl)/lib" \
CFLAGS="-I$(brew --prefix openssl)/include" \
SWIG_FEATURES="-cpperraswarn -includeall -I$(brew --prefix openssl)/include" \
pip install M2Crypto==0.38.0

# for fish shell
env PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L"(brew --prefix openssl)"/lib -L/usr/local/opt/curl/lib" CPPFLAGS="-I"(brew --prefix openssl)"/include -I/usr/local/opt/curl/include" pip install --compile --no-cache-dir pycurl
env LDFLAGS="-L"(brew --prefix openssl)"/lib" CFLAGS="-I"(brew --prefix openssl)"/include" SWIG_FEATURES="-cpperraswarn -includeall -I"(brew --prefix openssl)"/include" pip install m2crypto

# postgres
brew install postgresql@14
brew services start postgresql@14

# redis
brew install redis
brew services start redis

# Install pyenv
brew install pyenv

# Установака зависимотей
pipenv install --dev
```

### DB для запуска

**TODO:** Подумать над общей тестовой базой данных.

```bash
psql postgres

# Создаем базу данных и пользователя.
CREATE DATABASE cscdb;
CREATE USER csc WITH password 'FooBar';
ALTER USER csc with CREATEDB;
GRANT ALL privileges ON DATABASE cscdb TO csc;
```

### Запуск сервиса

```bash
pyenv shell
sudo python manage.py runserver 127.0.0.1:80 --settings=lk_yandexdataschool_ru.settings.local
```

---

## Ручной деплой сервиса
[YSDA YD](https://yd.yandex-team.ru/projects/ysda/deploy)

Для запуска рекомендуется использовать [Colima](https://github.com/abiosoft/colima).

### Запуск на MacOS

```bash
colima start --arch aarch64 --vm-type=vz --vz-rosetta --cpu 6 --memory 8
```

### Сборка сервиса

Сначала необходимо собрать сервис [lms-frontend](https://a.yandex-team.ru/arcadia/education/ysda/site-frontend):

```bash
# education/ysda/site-frontend
docker build -t lms-webpack-bundles .
```

После успешной сборки [lms-frontend](https://a.yandex-team.ru/arcadia/education/ysda/site-frontend), можно приступать к сборке [lms](https://a.yandex-team.ru/arcadia/education/ysda/lms):

```bash
# Создаем хеш для Docker-образа.
export APP_VERSION=${VERSION:-$(arc rev-parse HEAD | cut -c 1-16)-$(arc diff --stat | md5)}

# education/ysda/lms
docker build -t registry.yandex.net/ysda/app:$APP_VERSION .

# Пушим собранный образ в Яндекс Docker Registry.
docker push registry.yandex.net/ysda/app:$APP_VERSION

# Выводим хеш образа в консоль.
echo ysda/app:$APP_VERSION
```

После этого образ можно разместить в стейдж в YD и запустить.
