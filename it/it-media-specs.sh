for f in *.mp4 *.mkv *.avi *.mov *.jpg *.gif *.png *.mp3 *.m4a *.wav *.ogg
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
