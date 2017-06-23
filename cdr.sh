while true
do
	echo "accepting connections on port 6666"
	nc -l -p 6666 127.0.0.1
done
