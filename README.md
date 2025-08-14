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
required API keys like `QUANDL_API_KEY`.

When deploying to Streamlit Cloud, open the app's **⚙️ Settings → Secrets** and
paste the contents of your local `secrets.toml`.

The data pipeline reads the connection string using
`st.secrets["DATABASE_URL"]`. If it is not provided a SQLite database named
`app.db` will be created inside the pipeline's data directory.

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


