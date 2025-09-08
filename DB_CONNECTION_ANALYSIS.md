# Database Connection and Session Flow Analysis

## Critical Issues Identified

### 1. **CRITICAL: Missing `db.py` File in Streamlit App**

**File:** `streamlit_app.py`
**Line:** 8
```python
from db import get_db  # ❌ This file doesn't exist!
```

**Impact:** Streamlit app will crash on startup with ImportError.

**Fix Required:**
```python
# Replace with:
from data_pipeline.db_connection import get_db
```

### 2. **CRITICAL: DBHelper Missing Engine Property**

**File:** `data_pipeline/db_utils.py`
**Lines:** 89-90, 108, 125, 140, 165, 175, 185
```python
class DBHelper:
    def __init__(self, db_url: Optional[str] = None):
        self.database_url = db_url or self.get_secret_lazy()("DATABASE_URL")
        self.session = SessionLocal()  # ✅ Creates session
        # ❌ MISSING: self.engine = create_engine(self.database_url)
        # ❌ MISSING: self.inspector = inspect(self.engine)
```

**Impact:** All references to `self.engine` and `self.inspector` will fail with AttributeError.

**References that will fail:**
- Line 108: `autoload_with=self.engine`
- Line 125: `MetaData().create_all(self.engine, tables=[table])`
- Line 140: `autoload_with=self.engine`
- Line 165: `Table(table_name, MetaData(), autoload_with=self.engine)`
- Line 175: `with self.engine.begin() as conn:`
- Line 185: `with self.engine.begin() as conn:`

### 3. **CRITICAL: Incorrect Database Helper Instantiation**

**File:** `data_pipeline/market_data.py`
**Line:** 398
```python
Dbhelper = get_db()(get_secret_lazy()("DATABASE_URL"))  # ❌ WRONG!
```

**Problem Analysis:**
- `get_db()` returns a generator that yields SQLAlchemy sessions
- `get_secret_lazy()` returns a function, not a string
- This line attempts to call a generator as a function

**Correct Implementation:**
```python
from data_pipeline.db_utils import DBHelper
from data_pipeline.utils import get_secret
db_helper = DBHelper(get_secret("DATABASE_URL"))
```

### 4. **CRITICAL: Inconsistent Session Management Patterns**

#### Pattern 1: FastAPI Endpoints (web/api.py)
```python
def get_db():
    return DBHelper(get_secret("DATABASE_URL"))  # ✅ Returns DBHelper instance

@app.get("/endpoint")
def endpoint():
    db = get_db()  # ✅ Gets DBHelper
    # ... use db.engine ...
    db.close()     # ✅ Calls DBHelper.close()
```

#### Pattern 2: DB Connection Module (data_pipeline/db_connection.py)
```python
def get_db():
    """Provide a database session."""
    db = SessionLocal()  # ✅ Returns SQLAlchemy Session
    try:
        yield db
    finally:
        db.close()
```

#### Pattern 3: Streamlit App (streamlit_app.py)
```python
session = next(get_db())  # ❌ Expects generator, but imports wrong get_db
```

**Problem:** Three different `get_db()` functions with incompatible return types!

## Session Flow Analysis

### 1. **DBHelper Class Session Management**

**Current Implementation:**
```python
class DBHelper:
    def __init__(self, db_url: Optional[str] = None):
        self.session = SessionLocal()  # Creates session in constructor
        
    def create_table(self, ...):
        with self.session.begin():  # Uses instance session
            # ... operations ...
        except Exception as e:
            self.session.rollback()
        finally:
            self.session.close()  # Closes session after each operation
            
    def close(self):
        self.session.close()  # Also closes in destructor
```

**Issues:**
1. **Double session closure**: Session closed in both operation methods AND close()
2. **Session reuse after closure**: Once closed in create_table(), subsequent operations will fail
3. **Missing engine**: Operations reference self.engine which doesn't exist

### 2. **API Endpoint Session Management**

**Current Pattern:**
```python
@app.get("/endpoint")
def endpoint():
    db = get_db()           # Creates new DBHelper instance
    query = f"SELECT ..."   # ❌ SQL injection vulnerability
    df = pd.read_sql(query, db.engine)  # ❌ db.engine doesn't exist
    db.close()              # Calls DBHelper.close()
    return df.to_dict(orient="records")
```

**Issues:**
1. **Missing engine property**: `db.engine` will raise AttributeError
2. **No error handling**: If query fails, db.close() never called
3. **SQL injection**: Direct string interpolation

### 3. **Global Engine vs Instance Engines**

**Inconsistent Usage:**
```python
# Global engine (db_connection.py)
engine = initialize_engine()

# Used in some places:
with engine.connect() as connection:  # ✅ Uses global engine

# But DBHelper tries to create its own:
class DBHelper:
    def __init__(self, db_url):
        # ❌ Should use global engine or create self.engine
        self.session = SessionLocal()  # Uses global engine's session factory
```

## Recommended Fixes

### 1. **Fix DBHelper Class**

```python
class DBHelper:
    def __init__(self, db_url: Optional[str] = None):
        if db_url:
            # Create dedicated engine for this instance
            self.engine = create_engine(db_url, pool_pre_ping=True)
            self.session_factory = sessionmaker(bind=self.engine)
        else:
            # Use global engine
            from data_pipeline.db_connection import engine, SessionLocal
            self.engine = engine
            self.session_factory = SessionLocal
        
        self.inspector = inspect(self.engine)
        self._session = None
    
    @property
    def session(self):
        if self._session is None:
            self._session = self.session_factory()
        return self._session
    
    def close(self):
        if self._session:
            self._session.close()
            self._session = None
        # Don't dispose engine if using global one
        if hasattr(self, '_own_engine'):
            self.engine.dispose()
```

### 2. **Fix API Endpoints**

```python
from contextlib import contextmanager

@contextmanager
def get_db_context():
    db = DBHelper()
    try:
        yield db
    finally:
        db.close()

@app.get("/endpoint")
def endpoint(min_mktcap: int = 0, top_n: int = 10):
    with get_db_context() as db:
        query = text("""
            SELECT * FROM financial_tbl 
            WHERE marketCap >= :min_mktcap 
            ORDER BY factor_composite ASC 
            LIMIT :top_n
        """)
        df = pd.read_sql(query, db.engine, params={
            'min_mktcap': min_mktcap, 
            'top_n': top_n
        })
        return df.to_dict(orient="records")
```

### 3. **Fix Streamlit App**

```python
# Replace the import
from data_pipeline.db_connection import get_db

# Fix session usage
def get_db_session():
    return next(get_db())

# Use context manager
from contextlib import contextmanager

@contextmanager
def streamlit_db_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()

# In main app:
with streamlit_db_session() as session:
    # Use session for any direct DB operations
    # But primarily use API calls
    pass
```

### 4. **Fix Market Data Pipeline**

```python
# In market_data.py, replace:
# Dbhelper = get_db()(get_secret_lazy()("DATABASE_URL"))

# With:
from data_pipeline.db_utils import DBHelper
db_helper = DBHelper()  # Uses global engine
try:
    db_helper.create_table(financial_tbl, financial_df, primary_keys=["Date", "Ticker"])
    db_helper.insert_dataframe(financial_tbl, financial_df, unique_cols=["Date", "Ticker"])
    
    if macro_df is not None:
        macro_tbl = "macro_data_tbl"
        db_helper.create_table(macro_tbl, macro_df, primary_keys=["Date"])
        db_helper.insert_dataframe(macro_tbl, macro_df, unique_cols=["Date"])
finally:
    db_helper.close()
```

## Summary of Critical Issues

1. **Missing `db.py`**: Streamlit app will crash
2. **Missing `self.engine`**: DBHelper operations will fail
3. **Incorrect instantiation**: Market data pipeline will crash
4. **Inconsistent patterns**: Three different `get_db()` functions
5. **Session lifecycle issues**: Double closure, reuse after close
6. **Security vulnerabilities**: SQL injection in all API endpoints
7. **Resource leaks**: No proper cleanup on exceptions

## Priority Order for Fixes

1. **IMMEDIATE**: Fix missing `self.engine` in DBHelper
2. **IMMEDIATE**: Fix streamlit import error
3. **IMMEDIATE**: Fix market_data.py instantiation
4. **HIGH**: Implement proper session lifecycle management
5. **HIGH**: Fix SQL injection vulnerabilities
6. **MEDIUM**: Standardize database connection patterns
7. **MEDIUM**: Add proper error handling and resource cleanup

These fixes are critical for the application to function at all. The current state would result in multiple runtime crashes.
