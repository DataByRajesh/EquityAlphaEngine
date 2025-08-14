"""Minimal Quandl API usage example."""
import os
import quandl


def main() -> None:
    api_key = os.environ.get("QUANDL_API_KEY")
    if not api_key:
        raise RuntimeError("Set the QUANDL_API_KEY environment variable")
    quandl.ApiConfig.api_key = api_key
    data = quandl.get("FRED/CPILFESL")  # US CPI (free dataset)
    print(data.tail())


if __name__ == "__main__":
    main()
