# Database Connection Fix Plan

## Issue
- Database connection timeout to host 34.39.5.6:5432 in GitHub Actions CI/CD
- Error: pg8000.exceptions.InterfaceError - Can't create connection (timeout 60s)

## Root Cause Analysis
- Host 34.39.5.6 is likely a GCP Cloud SQL public IP that may have changed or is unreachable
- Direct pg8000 connection used instead of Cloud SQL connector
- No fallback or retry mechanism for connection failures

## Steps to Fix

### 1. Diagnose Cloud SQL Instance
- [ ] Check if Cloud SQL instance is running
- [ ] Verify current public IP address
- [ ] Confirm firewall rules allow connections from 0.0.0.0/0 or GitHub Actions IPs
- [ ] Update DATABASE_URL secret if IP has changed

### 2. Update Connection Code to Use Cloud SQL Connector
- [x] Modify `data_pipeline/db_connection.py` to use `google.cloud.sql.connector`
- [x] Parse DATABASE_URL to extract instance connection name
- [x] Implement connector-based engine creation
- [x] Add fallback to direct connection if connector fails

### 3. Add Error Handling and Logging
- [x] Improve connection error messages
- [x] Add retry logic for transient failures
- [x] Log connection attempts and failures

### 4. Update Test Files
- [x] Remove hardcoded IPs from test files
- [x] Use environment variables or mock connections for tests

### 5. Test and Validate
- [ ] Test connection from local environment
- [ ] Run CI/CD pipeline to verify fix
- [ ] Monitor for connection stability

## Files to Modify
- `data_pipeline/db_connection.py` - Main connection logic
- `data_pipeline/update_financial_data.py` - Remove unused imports, improve error handling
- `test_db_connection.py` - Remove hardcoded IP
- `test_ip_port_connection.py` - Remove hardcoded IP
- `requirements.txt` - Ensure google-cloud-sql-connector is included

## Dependencies
- google-cloud-sql-connector (already imported but not used)
- Updated DATABASE_URL format for Cloud SQL instance
