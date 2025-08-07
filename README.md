## 📢 Project Release History

| Version | Description | Status | Link |
|---|---|---|---|
| **v1.0-beta** | Phase 1 Pre-Release — Data Pipeline & Screener | 🚧 Pre-Release | [View Release](https://github.com/DataByRajesh/EquityAlphaEngine/releases/tag/v1.0-beta) |

---

> 📝 **Note:**
> This is a **pre-release** version. The project is under active development.
> Phase 2 (Macro Data Integration) is planned in upcoming releases.

## Configuration

Caching now uses a cloud object store rather than local files. Set the
environment variable `CACHE_BUCKET` to the name of an Amazon S3 bucket to
enable the cache. If the bucket is unset or unreachable, the application will
continue without caching.


