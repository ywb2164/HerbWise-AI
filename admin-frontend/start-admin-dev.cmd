@echo off
cd /d "%~dp0"
"C:\Program Files\nodejs\node.exe" "node_modules\vite\bin\vite.js" --mode test --host 0.0.0.0 --port 9528
