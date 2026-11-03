# Freelancing and MatchMaking 
# Freelancer Project Matching & Management: SQL Dashboard (Streamlit)

Runs every SQL statement from the DBMS mini project report (DDL, DML, Queries 1-24, the
section 13 extras, DCL, TCL) against a live database and shows the SQL, the result, the row
count and the run time.

## 1. Install (once)

1. Install Python 3.9+ from https://www.python.org/downloads/ (tick "Add Python to PATH" on Windows).
2. Put `app.py` and `requirements.txt` in one folder, open a terminal in it, then:

   Windows:
       python -m venv venv
       venv\Scripts\activate
       pip install -r requirements.txt

   macOS / Linux:
       python3 -m venv venv
       source venv/bin/activate
       pip install -r requirements.txt

## 2. Run

    streamlit run app.py

The browser opens at http://localhost:8501.

## 3. First use

* Default engine is **SQLite (demo)**: no database install needed. Click
  **Initialize / Reset sample database** in the sidebar once. That creates all 8 tables and the
  sample data copied from the report.
* To use **MySQL** (the engine in your report):
  1. Make sure MySQL 8.x is running (MySQL Workbench, or `mysql -u root -p` works).
  2. Sidebar: choose **MySQL**, enter host (localhost), port (3306), user, password, database (FreelancerDB).
  3. Click **Initialize / Reset sample database**. It runs CREATE DATABASE, all CREATE TABLE and
     INSERT statements.
  4. GRANT / REVOKE (section 11.3) needs an account that has CREATE USER and GRANT OPTION (e.g. root).
  Optional: set MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE as environment
  variables to pre-fill the sidebar.

## 4. Using the dashboard

| Sidebar section | What it shows |
|---|---|
| Dashboard overview | KPIs and charts, each produced by SQL |
| Schema & data | ER diagram, table browser, DESCRIBE, CREATE TABLE code |
| DML (8.4) | UPDATE / DELETE with before / during / after view. Rolled back by default; toggle to COMMIT |
| DQL 1-10 | SELECT, WHERE, ORDER BY, DISTINCT, aggregates, GROUP BY, HAVING |
| Joins & subqueries 11-17 | INNER, LEFT, SELF join, nested / single-row / multi-row / correlated |
| Views, indexes, DCL 18-20 | CREATE VIEW, CREATE INDEX, EXPLAIN, GRANT / REVOKE / SHOW GRANTS (MySQL) |
| Transactions 21-24 | COMMIT, ROLLBACK, SAVEPOINT, transactional INSERT, plus what a second session sees |
| Additional (13) | Reports, ALTER, DROP VIEW, DESCRIBE, skill-based matching (pick any project) |
| Testing & verification | Row counts, aggregate checks, run-all-queries smoke test, TC01-TC07 |
| SQL playground | Run your own read-only query |

SELECT queries run automatically. Anything that changes data has a **Run** button.

## 5. Good to know

* Q21, Q23, Q24 really COMMIT. Use **Initialize / Reset** to restore the original data and re-run them.
* The report's average payment (47,875) is calculated after the section 8.4 DELETE. In the Testing
  section that check turns green once you run D3 with COMMIT enabled.
* SQLite demo mode translates MySQL-only syntax (START TRANSACTION, EXPLAIN, DESCRIBE, CHECK OPTION).
  GRANT / REVOKE cannot run on SQLite because it has no users.

## 6. Troubleshooting

* `streamlit: command not found`: activate the venv, or use `python -m streamlit run app.py`.
* `Can't connect to MySQL server`: start the MySQL service and recheck host / port / password.
* `Access denied`: wrong user or password in the sidebar.
* `ModuleNotFoundError: mysql`: run `pip install -r requirements.txt` inside the activated venv.
