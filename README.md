## 📢 Project Release History

| Version | Description | Status | Link |
|---|---|---|---|
| **v1.0-beta** | Phase 1 Pre-Release — Data Pipeline & Screener | 🚧 Pre-Release | [View Release](https://github.com/DataByRajesh/EquityAlphaEngine/releases/tag/v1.0-beta) |

---

> 📝 **Note:**
> This is a **pre-release** version. The project is under active development.
> Phase 2 (Macro Data Integration) is planned in upcoming releases.

### Secrets configuration

Streamlit's secrets mechanism is used for values such as database connection
strings and API keys. Start by copying the example secrets file:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and fill in your own values. At a minimum set
`DATABASE_URL` (e.g. `postgresql://user:password@host:5432/database`) and any
required API keys like `QUANDL_API_KEY`. These values can also be supplied via
environment variables when Streamlit's secrets are not available.

When deploying to Streamlit Cloud, open the app's **⚙️ Settings → Secrets** and
paste the contents of your local `secrets.toml`.

The data pipeline first checks the `DATABASE_URL` environment variable and then
`st.secrets["DATABASE_URL"]`. If neither is provided a SQLite database named
`app.db` will be created inside the pipeline's data directory.

### Required Environment Variables

Create a `.env` file or export the following variables before running the
pipeline:

```env
QUANDL_API_KEY=your_quandl_api_key
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
DATABASE_URL=postgresql://user:password@host:5432/database
```

- `QUANDL_API_KEY` – required for retrieving macro indicators and UK market
  data. If this variable is missing, macro and UK data retrieval will fail.
- `GMAIL_CREDENTIALS_FILE` – path to your Gmail OAuth credentials file.
- `GMAIL_TOKEN_FILE` – location to store the Gmail OAuth token.
- `DATABASE_URL` – connection string for the database.

Additional optional variables include `MAX_THREADS`, `CACHE_BACKEND`,
`CACHE_REDIS_URL`, `CACHE_S3_BUCKET`, and `CACHE_S3_PREFIX`.

### Running the Streamlit Screener

An interactive stock screener is available via Streamlit. Run it from the
project root with:

```bash
streamlit run streamlit_app.py
```

On Streamlit Community Cloud, set the app's entry point to `streamlit_app.py`
to launch the screener without extra path configuration.

### Fetching UK Market Data

Run the data pipeline script to download FTSE 100 data. The command below
fetches the last decade of data by default; adjust `--years` as needed:

```bash
python data_pipeline/UK_data.py --years 10
```


### Concurrency configuration

The pipeline executes many network-bound requests in parallel. The default
thread count now scales with available CPU cores (roughly five threads per
core) for better performance on larger machines. You can override this by
setting the `MAX_THREADS` environment variable:

```bash
MAX_THREADS=20 python data_pipeline/UK_data.py --years 10
```


### Optional cache backends

The pipeline defaults to a local filesystem cache. To use Redis or Amazon S3
as the cache backend, install the corresponding optional packages:

```bash
pip install redis   # required for CACHE_BACKEND=redis
pip install boto3   # required for CACHE_BACKEND=s3
```

These dependencies are not installed by default, so ensure they are available
before selecting the related backend.

