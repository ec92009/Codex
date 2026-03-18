set projectDir to "/Users/ecohen/Codex/imageTo3MF"
set uvBinary to "/opt/homebrew/bin/uv"
set logFile to POSIX path of ((path to temporary items folder as text) & "imageTo3MF_gui.log")

do shell script "cd " & quoted form of projectDir & " && nohup " & quoted form of uvBinary & " run --project " & quoted form of projectDir & " python " & quoted form of (projectDir & "/image_grade_to_3mf_gui.py") & " >>" & quoted form of logFile & " 2>&1 &"
