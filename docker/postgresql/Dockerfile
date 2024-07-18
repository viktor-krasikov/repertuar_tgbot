FROM postgres:14.5-alpine

# Создаем пользователя Postgres
ENV POSTGRES_USER=viktorkrasikov
ENV POSTGRES_PASSWORD=123456

# Копирование скрипта для инициализации базы данных
COPY init.sql /docker-entrypoint-initdb.d/

# Expose port 5432
EXPOSE 5432

# Запуск Postgresql
CMD ["postgres"]