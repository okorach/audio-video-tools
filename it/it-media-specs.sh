for f in *.mp4 *.jpg
do
	media-specs -i $f
	code=$?
	if [ $code -ne 0 ]; then
		2>&1 echo "media-specs -i $f FAILED"
		exit $code
	fi
done
echo "media-specs SUCCESS"
exit 0
