import quandl
quandl.ApiConfig.api_key = "pXBknNEt9LEV6DRBnfhs"
data = quandl.get("FRED/CPILFESL")  # US CPI (free dataset)
print(data.tail())