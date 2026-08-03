@echo off
REM Windows cmd wrapper for the stack CLI. Delegates to the bash script.
REM Usage: stack status   /   stack hermes "task"  /  etc.
@bash "%~dp0stack" %*
