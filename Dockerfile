# Используем образ MySQL
FROM mysql:8

# Устанавливаем переменные окружения для инициализации БД
ENV MYSQL_ROOT_PASSWORD=my_mysql_password
ENV MYSQL_USER=viktorkrasikov
ENV MYSQL_PASSWORD=my_mysql_password
ENV MYSQL_DATABASE=viktorkrasikov$repertuar

# Копируем SQL скрипт для создания БД и таблиц
COPY docker_mysql_init.sql /docker-entrypoint-initdb.d/

# Пробрасываем порт MySQL наружу
EXPOSE 3306