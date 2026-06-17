@echo off
title Redrob AI Candidate Ranker
echo ===================================================
echo               Redrob AI Candidate Ranker
echo ===================================================
echo.
echo Step 1: Running candidate ranking pipeline...
python rank.py --candidates ./candidates.jsonl --out ./team.csv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ranking failed.
    goto end
)
echo.
echo Step 2: Validating generated submission file...
python validate_submission.py team.csv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Validation failed.
    goto end
)
echo.
echo Step 3: Launching web dashboard in your browser...
echo         URL: http://127.0.0.1:8765/
echo         Close this window or press Ctrl+C to stop the server.
echo.
echo ===================================================
echo Success! team.csv is ready and valid.
echo ===================================================
python serve_dashboard.py team.csv
:end
echo.
pause
