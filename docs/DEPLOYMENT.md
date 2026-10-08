# Deployment handoff

The app is deployed at [https://mahima-ecommerce-analytics.streamlit.app/](https://mahima-ecommerce-analytics.streamlit.app/). The source is published in `mahima68/ecommerce-profitability-demand-forecasting`, branch `main`, entry point `app.py`. The hosted runtime is Python 3.12.15. All seven pages were checked, including a live price scenario and calculated local analyst answer. No API credentials are configured on the host.

The host flagged PyArrow 25.0.1 for a known stability issue and replaced it with 24.0.0. Requirements now pin 24.0.0 explicitly; all 53 local tests pass with this version.

## Streamlit Community Cloud

1. Create or choose your own GitHub repository and push this project's source package.
2. Include `app.py`, `src/`, `requirements.txt`, `.streamlit/config.toml`, `assumptions.json`, `data/processed/transactions.parquet`, and the reports/docs used by the app. The processed transaction file is approximately 25 MB, below GitHub's 100 MB individual-file limit.
3. Sign in to Streamlit Community Cloud with access to that repository. Create an app from branch `main`, entry point `app.py`, using Python 3.12.
4. Launch without AI credentials first. Verify all seven pages and a price scenario.
5. Use the free local analyst without credentials. Test a profitability question, an unavailable month, and an unsupported question.
6. The optional OpenAI adapter is outside the free scope. Enabling it requires paid API credits and explicit server configuration `ENABLE_LIVE_AI=true`, plus private key/model settings. Live requests remain unverified.

The app reads prebuilt Parquet/CSV data; a cloud app does not need to download and process the million-row XLSX at startup. It also does not require a running PostgreSQL service. PostgreSQL is an independently deployable analytics backend.

## Docker

For a local container on a machine with Docker installed:

```sh
docker build -t retail-decisions .
docker run --rm -p 127.0.0.1:8501:8501 retail-decisions
```

For dashboard-only Compose, run `docker compose up --build`. For dashboard plus PostgreSQL, set a nonempty `POSTGRES_PASSWORD` securely and run `docker compose -f compose.yaml -f compose.postgres.yaml up --build`. PostgreSQL keeps its required password and a loopback port binding. Stop the existing local Postgres.app server first if it already uses port 5432.

The `.dockerignore` excludes secrets, raw source data, SQLite, exception exports, and Power BI files from the container build. The Dockerfile includes a health check. It was not built in this environment because Docker is unavailable. Verify the image before deploying it on a remote service. Bindings in the Compose file default to loopback for local use.

## What requires the owner

Choose the GitHub repository/account and hosting account, complete any sign-in or service terms, and configure API credentials securely if enabling live AI. No secrets need to be shared in chat. A reviewable local app, source package, and screenshots are already available.

## Official references

- Streamlit deployment: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- Streamlit secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling
