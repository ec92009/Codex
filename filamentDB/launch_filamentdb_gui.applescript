set projectDir to "/Users/ecohen/Codex/filamentDB"
set uvPath to "/opt/homebrew/bin/uv"
set logFile to POSIX path of ((path to temporary items folder as text) & "filamentdb_gui.log")

do shell script "cd " & quoted form of projectDir & " && nohup " & quoted form of uvPath & " run python filament_db_gui.py >> " & quoted form of logFile & " 2>&1 &"
