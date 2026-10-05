@echo off
cd /d C:\Projet_Tiers_Payant
call venv\Scripts\activate.bat
python manage.py backup_db --keep 30
exit