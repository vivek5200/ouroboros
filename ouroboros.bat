@echo off
REM Ouroboros CLI Launcher for Windows
REM Quick shortcut to run the Ouroboros CLI

REM Activate virtual environment if it exists
IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the CLI with all arguments passed through
python ouroboros_cli.py %*
