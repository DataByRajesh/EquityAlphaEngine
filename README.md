## 📢 Project Release History

| Version | Description | Status | Link |
|---|---|---|---|
| **v1.0-beta** | Phase 1 Pre-Release — Data Pipeline & Screener | 🚧 Pre-Release | [View Release](https://github.com/DataByRajesh/EquityAlphaEngine/releases/tag/v1.0-beta) |

---

> 📝 **Note:**
> This is a **pre-release** version. The project is under active development.
> Phase 2 (Macro Data Integration) is planned in upcoming releases.

### Installing dependencies

For a lightweight setup that only runs the Streamlit screener locally, install
the packages in `requirements.txt`:

```bash
pip install -r requirements.txt
```

To run the full data pipeline or deploy in a cloud environment, use the
broader dependency set in `requirements-pipeline.txt`:

```bash
pip install -r requirements-pipeline.txt
```

### Database configuration

The data pipeline now relies on SQLAlchemy for database access.  Set the
`DATABASE_URL` environment variable to point to your database before running the
pipeline.  Any SQLAlchemy-compatible connection string is supported, for
example:

```bash
export DATABASE_URL="sqlite:///path/to/stocks_data.db"
```

If `DATABASE_URL` is not provided a SQLite database named `stocks_data.db` will
be created inside the pipeline's data directory.


