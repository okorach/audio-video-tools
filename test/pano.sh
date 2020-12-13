ffmpeg -i in.jpg -y -vf "scale=6000:-1" out.jpg

# Horizontal OK
ffmpeg -framerate 50 -loop 1 -i in.jpg -y -filter_complex "[0:v]scale=6000:-1,crop=iw:2160:0:(in_h-out_h)/2,crop=3840:2160:'min((iw/17)*t,iw-out_w)':0" -t 8 pan_horiz.mp4

# Diag OK
ffmpeg -framerate 50 -loop 1 -i in.jpg -y -filter_complex "[0:v]scale=6000:-1,crop=3840:2160:'min(iw*t/17,iw-ow'):'min(ih-oh,ih*t/17)'" -t 8 -s 3840x2160 pan_diag.mp4

# Vertical OK
ffmpeg -framerate 50 -loop 1 -i in.jpg -y -filter_complex "[0:v]scale=5000:-1,crop=3840:2160:(in_w-out_w)/2:'min(in_h-out_h,(ih/17)*t)'" -t 8 -s 3840x2160 pan_vert.mp4

#ffmpeg -loop 1 -i in.jpg -y -vf "crop=1500:ih-400:7:'min(400,(ih/20)*t)'" -t 10 pan_zoom.mp4
#ffmpeg -loop 1 -i in.jpg  -vf "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d=125" -t 5 zoomout1.mp4
#ffmpeg -loop 1 -i in.jpg -vf "crop=iw:ih-400" -vf "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d=125" -t 5 zoomout.mp4

# Zoom in OK
ffmpeg -framerate 50 -i in.jpg -filter_complex "[0:v]scale=6000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125,trim=duration=10[v]" -map "[v]" -s 3840x2160 -y zoomin.mp4

ffmpeg -i zoomin.mp4 -vf reverse -y zoomout_rev.mp4
ffmpeg -i pan_diag.mp4 -vf reverse -y pan_diag_rev.mp4
ffmpeg -i pan_horiz.mp4 -vf reverse -y pan_horiz_rev.mp4
ffmpeg -i pan_vert.mp4 -vf reverse -y pan_vert_rev.mp4

# zoom out
ffmpeg -framerate 50 -i in.jpg -filter_complex "[0:v]scale=6000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125,trim=duration=10[v]" -map "[v]" -s 3840x2160 -y zoomout.mp4

#ffmpeg -framerate 50 -loop 1 -i in.jpg -filter_complex "[0:v]scale=8000x4000,zoompan=d=300:z='if(gte(zoom,2)+eq(ld(1),1)*gt(zoom,1),zoom-0.04*st(1,1),zoom+0.04+0*st(1,0))':s=1920x1080" -y -s 1920x1280 zoomout.mp4