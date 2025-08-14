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
`stocks_data.db` will be created inside the pipeline's data directory.


