import logging
import quandl

logger = logging.getLogger(__name__)
quandl.ApiConfig.api_key = "pXBknNEt9LEV6DRBnfhs"
data = quandl.get("FRED/CPILFESL")  # US CPI (free dataset)
logger.info("\n%s", data.tail())
