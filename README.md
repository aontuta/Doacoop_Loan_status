# Doacoop Loan Status Updater

This project updates loan status data from Oracle DB to Google Sheets using GitHub Actions.

## Setup

- Add GitHub secrets: GCP_CREDENTIALS, ORACLE_USER, ORACLE_PASS, ORACLE_DSN
- Schedule or trigger the workflow manually

## Files

- `update_to_sheet.py`: Script to fetch Oracle data and update Google Sheet
- `.github/workflows/update-loanstatus.yml`: GitHub Actions workflow
