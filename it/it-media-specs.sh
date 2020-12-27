for f in *.mp4 *.mkv *.avi *.mov *.jpg *.gif *.png *.mp3 *.m4a *.wav *.ogg
do
    cmd="media-specs -i $f"
	$cmd
    code=$?
    if [ $code -ne 0 ]; then
        1>&2 echo "========================================"
        1>&2 echo "FAILED: $cmd"
        1>&2 echo "========================================"
        exit $code
    fi
done
echo "----------------------------------------"
echo "SUCCESS $(basename $0)"
echo "----------------------------------------"
exit 0
