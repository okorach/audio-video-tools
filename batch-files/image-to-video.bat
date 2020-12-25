image-to-video -g 5 --framesize 3840x2160 --effect panorama --panorama_effect 0.1,0.9,0.6,0.4 --duration 20 -i %1
image-to-video -g 5 --framesize 3840x2160 --effect zoom --zoom_effect 100,120 -i %1
pause