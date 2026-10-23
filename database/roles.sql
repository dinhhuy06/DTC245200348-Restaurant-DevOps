-- Idempotent setup for new AND existing database volumes.
-- Passwords come from the container environment.
\getenv app_password APP_DB_PASSWORD
\getenv monitor_password POSTGRES_EXPORTER_PASSWORD
BEGIN;
SELECT 'CREATE ROLE restaurant_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'restaurant_app')
\gexec
SELECT format('ALTER ROLE restaurant_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L', :'app_password')
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO restaurant_app', current_database())
\gexec
GRANT USAGE ON SCHEMA public TO restaurant_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dishes, restaurant_tables, orders, order_items TO restaurant_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO restaurant_app;
SELECT 'CREATE ROLE restaurant_monitor LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'restaurant_monitor')
\gexec
SELECT format('ALTER ROLE restaurant_monitor WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %L', :'monitor_password')
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO restaurant_monitor', current_database())
\gexec
GRANT pg_monitor TO restaurant_monitor;
COMMIT;
