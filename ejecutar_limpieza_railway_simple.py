#!/usr/bin/env python3
import subprocess

consultas = [
    "SELECT COUNT(*) as total_registros FROM call_schedule;",
    "DELETE cs1 FROM call_schedule cs1 INNER JOIN call_schedule cs2 WHERE cs1.id < cs2.id AND cs1.lead_id = cs2.lead_id AND cs1.status = 'cancelled' AND cs2.status = 'cancelled' AND DATE(cs1.created_at) = DATE(cs2.created_at);",
    "SELECT COUNT(*) as total_registros_despues FROM call_schedule;"
]

print("LIMPIEZA RAILWAY MYSQL")
for consulta in consultas:
    cmd = ['railway', 'run', '--service', 'MySQL', 'mysql', '-e', consulta]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print("Error:", result.stderr.strip())