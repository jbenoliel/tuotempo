@echo off
echo Revirtiendo base de datos a Segurcaixa...
powershell -Command "(Get-Content .env) -replace 'MYSQLDATABASE=tuotempo', 'MYSQLDATABASE=Segurcaixa' | Set-Content .env"
echo Base de datos revertida a Segurcaixa
pause
