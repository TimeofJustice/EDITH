now=$(date +"%Y-%m-%d_%H-%M-%S")

# shellcheck disable=SC2164
cd /home/ftpuser/ftp/files/EDITH
screen -S Discord -L -Logfile data/logs/"${now}".log python3 main.py
