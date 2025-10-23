# coding-challenges
All Prosigliere coding challenges housed here

## Containerized demo (Airflow + Postgres)

This repo includes a `docker-compose.yml` which will start:
- 3 Postgres containers (db1, db2, dw)
- 1 Airflow container (webserver + scheduler)

To run locally:

```powershell
docker compose build
docker compose up -d
```

Visit http://localhost:8080/login/ (username: admin / password: admin) after the webserver is up.

Notes:
- The Airflow image includes the `solution/` code mounted into the DAGs folder so the `demo_etl_to_postgres` DAG will be available.
- This environment is for local demo only.
