FROM postgres:12

# install postgis
RUN apt-get update && apt-get install -y \
    postgis \
    postgresql-12-postgis-3 \
    postgresql-12-postgis-3-scripts

EXPOSE 5432

CMD [ "postgres" ]
