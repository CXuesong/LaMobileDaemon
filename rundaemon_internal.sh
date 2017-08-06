# The script is invoked by rundaemon.sh

cd LaMobileDaemon
while true; do
	echo $(date) Push a page! ;
	python3 LaMobileDaemon.py;
	sleep 40h;
done;
