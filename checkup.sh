#!/bin/bash
DEFAULTPWD=/home/pi/project/
SQLLITE=/home/pi/project/Batz/db.sqlite3
REQUE=/home/pi/project/requirements.txt

cd $DEFAULTPWD || exit
if [ -d .git ]; then
  echo .git;
else
  git init
  git remote add origin https://github.com/Brisseta/SmartHome.git
  git pull origin forlinux
fi
if [[ -f "$SQLLITE" ]]; then
    echo "db.sqlite3 file exists" > /home/pi/project/shell_out/temp.txt
  else
    if [[ "$(pwd)" == *"$DEFAULTPWD"* ]]; then
      cd $DEFAULTPWD/Batz/ || exit
      wget https://github.com/Brisseta/SmartHome/blob/master/db.sqlite3
      cd ..
      echo "get db.sqlite3 file from repository" >> /home/pi/project/shell_out/temp.txt
    fi
fi
if [[ -f "$REQUE" ]]; then
    echo "requirements.txt file exists" >> /home/pi/project/shell_out/temp.txt
    else
      cd $DEFAULTPWD || exit
      wget https://github.com/Brisseta/SmartHome/blob/master/requirements.txt
      echo "get requirements.txt file from repository" >> /home/pi/project/shell_out/temp.txt
fi
cd $DEFAULTPWD/Batz || exit
source /home/pi/project/venv/bin/activate
pip install -r "/home/pi/project/requirements.txt" -v --exists-action s
echo "pip install success" >> /home/pi/project/shell_out/temp.txt
screens=(/var/run/screen/S-*/*)
if (( ${#screens[@]} == 0 )); then
    echo "no screen session found in /var/run/screen" >> /home/pi/project/shell_out/temp.txt
    screen -dmS Batz python $DEFAULTPWD/Batz/Batz_API/Main.py
    echo "liste des process en shell background" >> /home/pi/project/shell_out/temp.txt
    else
        echo "des process sont en cours - suppression des process" >> /home/pi/project/shell_out/temp.txt
        echo "$(screen -ls)" >> /home/pi/project/shell_out/temp.txt
        killall screen
        screen -dmS Batz python $DEFAULTPWD/Batz/Batz_API/Main.py
        echo "lancement du process Batz" >> /home/pi/project/shell_out/temp.txt
        echo "$(screen -ls)" >> /home/pi/project/shell_out/temp.txt
fi



