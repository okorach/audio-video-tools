#!python3
#
# media-tools
# Copyright (C) 2019-2021 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

"""
This script renames files with format YYYY-MM-DD_HHMMSS_<root>
"""

import sys
import os
import argparse
from typing import Optional
import concurrent.futures
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import utilities.file as fil
from datetime import datetime

SEQ = "#SEQ#"
SIZE = "#SIZE#"
DEVICE = "#DEVICE#"
TIMESTAMP = "#TIMESTAMP#"
FPS = "#FPS#"
BITRATE = "#BITRATE#"

DEFAULT_FORMAT = f"{util.FILE_DATE_FMT} - #SEQ3# - {SIZE} - {DEVICE}"
DEFAULT_VIDEO_FORMAT = f"{util.FILE_DATE_FMT} - {SEQ} - {SIZE} - {FPS}fps - {BITRATE}MBps"
DEFAULT_PHOTO_FORMAT = f"{util.FILE_DATE_FMT} - {SEQ} - {SIZE} - {DEVICE}"


def get_device(exif_data: dict[str, str]) -> str:
    device = ""
    if "EXIF:Make" in exif_data:
        device = exif_data["EXIF:Make"]
        if "EXIF:Model" in exif_data:
            device += " " + exif_data["EXIF:Model"]
    elif "QuickTime:Author" in exif_data:
        device = exif_data["QuickTime:Author"]
    elif "QuickTime:CompressorName" in exif_data:
        device = exif_data["QuickTime:CompressorName"]
    return device


def get_size(exif_data: dict[str, str]) -> str:
    size = ""
    if "File:ImageWidth" in exif_data and "File:ImageHeight" in exif_data:
        size = f'{exif_data["File:ImageWidth"]}x{exif_data["File:ImageHeight"]}'
    elif "EXIF:ExifImageWidth" in exif_data and "EXIF:ExifImageHeight" in exif_data:
        size = f'{exif_data["EXIF:ExifImageWidth"]}x{exif_data["EXIF:ExifImageHeight"]}'
    elif "QuickTime:SourceImageWidth" in exif_data and "QuickTime:SourceImageHeight" in exif_data:
        size = f'{exif_data["QuickTime:SourceImageWidth"]}x{exif_data["QuickTime:SourceImageHeight"]}'
    elif "QuickTime:ImageWidth" in exif_data and "QuickTime:ImageHeight" in exif_data:
        size = f'{exif_data["QuickTime:ImageWidth"]}x{exif_data["QuickTime:ImageHeight"]}'
    elif "Composite:ImageSize" in exif_data:
        size = exif_data["Composite:ImageSize"].replace(" ", "x")
    return size


def get_bitrate(exif_data: dict[str, str]) -> int:
    bitrate = None
    if "Composite:AvgBitrate" in exif_data:
        bitrate = round(int(exif_data["Composite:AvgBitrate"]) / 1024 / 1024)
    return bitrate


def get_codec(exif_data: dict[str, str]) -> str:
    codec = ""
    if "QuickTime:CompressorID" in exif_data:
        codec = exif_data["QuickTime:CompressorID"]

    if codec == "avc1":
        codec = "h264"
    elif codec == "hev1":
        codec = "h265"

    return codec


def get_fps(exif_data: dict[str, str]) -> int:
    fps = None
    if "QuickTime:VideoFrameRate" in exif_data:
        fps = round(float(exif_data["QuickTime:VideoFrameRate"]))
    return fps


def get_formats(nb_photos, nb_videos, **kwargs):
    prefix = kwargs.get("prefix", None)
    pformat = vformat = SEQ
    if nb_videos > 0:
        if kwargs.get("video_format", None) in (None, ""):
            if prefix is None:
                print("Error: One of --prefix or --video_format option is required")
                sys.exit(1)
            vformat = f"{kwargs.get('prefix')} - {DEFAULT_VIDEO_FORMAT}"
        else:
            vformat = kwargs["video_format"]
    if nb_photos > 0:
        if kwargs.get("photo_format", None) in (None, ""):
            if prefix is None:
                print("Error: One of --prefix or --photo_format option is required")
                sys.exit(1)
            pformat = f"{kwargs.get('prefix')} - {DEFAULT_PHOTO_FORMAT}"
        else:
            pformat = kwargs["photo_format"]
    return (pformat, vformat)


def get_file_data(filename: str) -> Optional[dict[str, str]]:
    if fil.extension(filename).lower() not in (
        "jpg",
        "mp4",
        "jpeg",
        "gif",
        "png",
        "mp2",
        "mpeg",
        "mpeg4",
        "mpeg2",
        "vob",
        "mov",
    ):
        return None

    log.logger.info("Reading data for %s", filename)
    with ExifToolHelper() as et:
        for data in et.get_metadata(filename):
            log.logger.debug("MetaData = %s", util.json_fmt(data))
            #            for data in et.get_tags(file, tags=["DateTimeOriginal", "Make", "Model", "FileModifyDate"]):
            #                log.logger.debug("Data = %s", util.json_fmt(data))
            creation_date = util.get_creation_date(data)
            device = get_device(data)
            bitrate = get_bitrate(data)
            fps = get_fps(data)
            size = get_size(data)
    return {
        "creation_date": creation_date,
        "device": device,
        "file": filename,
        "bitrate": bitrate,
        "size": size,
        "fps": fps,
    }


def get_files_data(files: list[str], sortby: str) -> dict[str : dict[str:str]]:
    seq = 1
    filelist = {}
    nb_files = len(files)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="GetMetadata") as executor:
        futures = [executor.submit(get_file_data, file) for file in files]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result(timeout=10)  # Retrieve result or raise an exception
                log.logger.debug("Result: %s", str(result))
            except TimeoutError:
                log.logger.error(
                    "Finding sync timed out after 60 seconds for %s, sync killed.",
                    str(future),
                )
            except Exception as e:
                log.logger.error("Task raised an exception: %s", str(e))
            if not result:
                continue
            if sortby == "name":
                filelist[result["filename"]] = result
            elif sortby == "device":
                if result["device"] is not None:
                    filelist[f"{result['device']} {seq:06}"] = result
            else:
                if result["creation_date"] is not None:
                    filelist[f"{result['creation_date'].strftime(util.FILE_DATE_FMT)} {seq:06}"] = result
            seq += 1
            log.logger.debug("Extracted %d/%d files = %d%%", seq, nb_files, (100 * seq) // nb_files)
    return filelist


def get_fmt(filename: str, photo_format: str, video_format: str, other_format: str) -> str:
    fmt = other_format
    if fil.is_image_file(filename):
        fmt = photo_format
    elif fil.is_video_file(filename):
        fmt = video_format
    if TIMESTAMP not in fmt and SEQ[:3] not in fmt:
        fmt = f"{SEQ} - {fmt}"
    return fmt


def rename(filename: str, new_filename: str) -> tuple[int, int, int]:
    log.logger.info("Renaming %s into %s", filename, new_filename)
    photo = video = other = 0
    success = True
    try:
        file_type = fil.get_type(filename)
        if filename != new_filename:
            os.rename(filename, new_filename)
    except os.error:
        success = False
        ext = fil.extension(new_filename)
        base = fil.strip_extension(filename)
        for v in range(2, 10):
            try:
                if filename != f"{base} {v}.{ext}":
                    os.rename(filename, f"{base} {v}.{ext}")
                success = True
                break
            except os.error:
                continue
    if success:
        if file_type == fil.FileType.IMAGE_FILE:
            photo = 1
        elif file_type == fil.FileType.VIDEO_FILE:
            video = 1
        else:
            other = 1
            log.logger.warning("%s is not a media file", filename)
    else:
        log.logger.warning("Unable to rename")
    return (photo, video, other)


def main() -> None:
    util.init("renamer")
    parser = argparse.ArgumentParser(description="Stacks images vertically or horizontally")
    parser.add_argument("-f", "--files", nargs="+", help="List of files to rename", required=True)
    parser.add_argument("--prefix", help="Prefix for files", required=False)
    parser.add_argument("--video_format", help="Format for the renamed video files", required=False)
    parser.add_argument("--format", help="Format for files", required=False, default=DEFAULT_FORMAT)
    parser.add_argument("--photo_format", help="Format for the renamed photo files", required=False)
    parser.add_argument(
        "--seqstart",
        help="Sequence number start for the renamed files",
        required=False,
        default=1,
    )
    parser.add_argument("-r", "--root", help="Root name", required=False)
    parser.add_argument(
        "--sortby",
        help="How to sort sequence numbers",
        required=False,
        default="timestamp",
    )
    parser.add_argument("-g", "--debug", required=False, type=int, help="Debug level")
    kwargs = util.parse_media_args(parser)

    file_list = fil.file_list(*kwargs["files"], file_type=None, recurse=False)
    nb_photo_files = sum(1 for f in file_list if fil.extension(f).lower() in ("jpg", "jpeg", "gif", "png"))
    nb_video_files = sum(1 for f in file_list if fil.extension(f).lower() in ("mp4", "mpeg4", "mpeg2", "mp2", "mpeg", "vob", "mov"))
    nb_other_files = len(file_list) - nb_photo_files - nb_video_files

    photo_seq = video_seq = other_seq = int(kwargs.get("seqstart", 1))
    (photo_format, video_format) = get_formats(nb_photo_files, nb_video_files, **kwargs)

    files_data = get_files_data(fil.file_list(*kwargs["files"], file_type=None, recurse=False), kwargs["sortby"])

    log.logger.info("%d image files and %d video files to process", nb_photo_files, nb_video_files)
    for key in sorted(files_data.keys()):
        filename = files_data[key]["file"]
        ext = fil.extension(filename).lower()
        device = files_data[key]["device"]
        creation_date = files_data[key]["creation_date"]
        dirname = fil.dirname(filename)
        fmt = get_fmt(filename, photo_format, video_format, kwargs["format"])
        file_fmt = fmt.replace(DEVICE, device)
        file_fmt = file_fmt.replace(TIMESTAMP, util.FILE_DATE_FMT)
        file_fmt = file_fmt.replace(BITRATE, str(files_data[key]["bitrate"]))
        file_fmt = file_fmt.replace(FPS, str(files_data[key]["fps"]))
        file_fmt = file_fmt.replace(SIZE, files_data[key]["size"])

        if fil.is_image_file(filename):
            seq = photo_seq
            nb_files = nb_photo_files
        elif fil.is_video_file(filename):
            seq = video_seq
            nb_files = nb_video_files
        else:
            seq = other_seq
            nb_files = nb_other_files
            log.logger.warning("%s is not a media file", filename)
        file_fmt = file_fmt.replace("#SEQ1#", f"{seq:01}")
        if nb_files < 100:
            file_fmt = file_fmt.replace(SEQ, f"{seq:02}")
        elif nb_files < 1000:
            file_fmt = file_fmt.replace(SEQ, f"{seq:03}")
        elif nb_files < 10000:
            file_fmt = file_fmt.replace(SEQ, f"{seq:04}")
        else:
            file_fmt = file_fmt.replace(SEQ, f"{seq:05}")
        file_fmt = file_fmt.replace("#SEQ2#", f"{seq:02}")
        file_fmt = file_fmt.replace("#SEQ3#", f"{seq:03}")
        file_fmt = file_fmt.replace("#SEQ4#", f"{seq:04}")
        file_fmt = file_fmt.replace("#SEQ5#", f"{seq:05}")
        new_filename = dirname + os.sep + creation_date.strftime(file_fmt) + "." + ext
        if new_filename == filename:
            log.logger.info("File %s does need to be renamed, skipped...", filename)
            continue

        (p, v, o) = rename(filename, new_filename)
        photo_seq += p
        video_seq += v
        other_seq += o


if __name__ == "__main__":
    main()

"""
"Composite:AdvancedSceneMode": "DC-FZ82 3 7",
"Composite:Aperture": 7.1,
"Composite:BlueBalance": 1.83203125,
"Composite:CircleOfConfusion": "0.00511899255158468",
"Composite:FOV": 6.93646437681511,
"Composite:FocalLength35efl": 297,
"Composite:GPSLatitude": 36.5898759173417,
"Composite:GPSLongitude": -6.19841110604444,
"Composite:GPSPosition": "36.5898759173417 -6.19841110604444",
"Composite:HyperfocalDistance": 70.4462999062984,
"Composite:ImageSize": "3403 2271",
"Composite:LightValue": 15.6214223338967,
"Composite:Megapixels": 7.728213,
"Composite:RedBalance": 1.6865234375,
"Composite:ScaleFactor35efl": 5.8695652173913,
"Composite:ShutterSpeed": 0.00125,
"Composite:SubSecCreateDate": "2023:08:08 13:37:52.060",
"Composite:SubSecDateTimeOriginal": "2023:08:08 13:37:52.060",
"Composite:SubSecModifyDate": "2023:08:09 19:33:37.060",
"EXIF:Artist": "Picasa",
"EXIF:ColorSpace": 1,
"EXIF:ComponentsConfiguration": "1 2 3 0",
"EXIF:CompressedBitsPerPixel": 4,
"EXIF:Compression": 6,
"EXIF:Contrast": 0,
"EXIF:CreateDate": "2023:08:08 13:37:52",
"EXIF:CustomRendered": 0,
"EXIF:DateTimeOriginal": "2023:08:08 13:37:52",
"EXIF:DigitalZoomRatio": 0,
"EXIF:ExifImageHeight": 2271,
"EXIF:ExifImageWidth": 3403,
"EXIF:ExifVersion": "0230",
"EXIF:ExposureCompensation": 0,
"EXIF:ExposureMode": 0,
"EXIF:ExposureProgram": 8,
"EXIF:ExposureTime": 0.00125,
"EXIF:FNumber": 7.1,
"EXIF:FileSource": 3,
"EXIF:Flash": 16,
"EXIF:FlashpixVersion": "0100",
"EXIF:FocalLength": 50.6,
"EXIF:FocalLengthIn35mmFormat": 297,
"EXIF:GPSLatitude": 36.5898759173417,
"EXIF:GPSLatitudeRef": "N",
"EXIF:GPSLongitude": 6.19841110604444,
"EXIF:GPSLongitudeRef": "W",
"EXIF:GPSVersionID": "2 3 0 0",
"EXIF:GainControl": 0,
"EXIF:ISO": 80,
"EXIF:ImageUniqueID": "4942bbb22fd922ec2ed7ee0319f1fa83",
"EXIF:InteropIndex": "R98",
"EXIF:InteropVersion": "0100",
"EXIF:LightSource": 0,
"EXIF:Make": "Panasonic",
"EXIF:MaxApertureValue": 5.49829523309316,
"EXIF:MeteringMode": 5,
"EXIF:Model": "DC-FZ82",
"EXIF:ModifyDate": "2023:08:09 19:33:37",
"EXIF:RelatedImageHeight": 3264,
"EXIF:RelatedImageWidth": 4896,
"EXIF:ResolutionUnit": 2,
"EXIF:Saturation": 0,
"EXIF:SceneCaptureType": 0,
"EXIF:SceneType": 1,
"EXIF:SensingMethod": 2,
"EXIF:SensitivityType": 1,
"EXIF:Sharpness": 0,
"EXIF:Software": "Ver.1.1",
"EXIF:SubSecTime": "060",
"EXIF:SubSecTimeDigitized": "060",
"EXIF:SubSecTimeOriginal": "060",
"EXIF:ThumbnailImage": "(Binary data 1618 bytes, use -b option to extract)",
"EXIF:ThumbnailLength": 1618,
"EXIF:ThumbnailOffset": 5050,
"EXIF:WhiteBalance": 0,
"EXIF:XResolution": 180,
"EXIF:YCbCrPositioning": 2,
"EXIF:YResolution": 180,
"ExifTool:ExifToolVersion": 12.64,
"File:BitsPerSample": 8,
"File:ColorComponents": 3,
"File:CurrentIPTCDigest": "6dedbe66ee1f9e63717e6541369f9774",
"File:Directory": "D:/Photos/Andalousie",
"File:EncodingProcess": 0,
"File:ExifByteOrder": "II",
"File:FileAccessDate": "2023:08:12 09:27:52+02:00",
"File:FileCreateDate": "2023:08:09 19:33:37+02:00",
"File:FileModifyDate": "2023:08:11 10:57:21+02:00",
"File:FileName": "zum.JPG",
"File:FilePermissions": 100666,
"File:FileSize": 4152210,
"File:FileType": "JPEG",
"File:FileTypeExtension": "JPG",
"File:ImageHeight": 2271,
"File:ImageWidth": 3403,
"File:MIMEType": "image/jpeg",
"File:YCbCrSubSampling": "2 1",
"IPTC:ApplicationRecordVersion": 4,
"IPTC:By-line": "Picasa",
"IPTC:CodedCharacterSet": "\u001b%G",
"IPTC:EnvelopeRecordVersion": 4,
"JFIF:JFIFVersion": "1 1",
"JFIF:ResolutionUnit": 0,
"JFIF:XResolution": 1,
"JFIF:YResolution": 1,
"MakerNotes:AFAreaMode": "0 49",
"MakerNotes:AFAssistLamp": 2,
"MakerNotes:AFPointPosition": "0.5 0.5",
"MakerNotes:AccelerometerX": 0,
"MakerNotes:AccelerometerY": 0,
"MakerNotes:AccelerometerZ": 0,
"MakerNotes:AccessorySerialNumber": "0000000",
"MakerNotes:AccessoryType": "NO-ACCESSORY",
"MakerNotes:AdvancedSceneType": 7,
"MakerNotes:Audio": 2,
"MakerNotes:BabyAge": "9999:99:99 00:00:00",
"MakerNotes:BabyName": "",
"MakerNotes:BatteryLevel": 1,
"MakerNotes:BracketSettings": 0,
"MakerNotes:BurstMode": 0,
"MakerNotes:BurstSpeed": 0,
"MakerNotes:CameraOrientation": 0,
"MakerNotes:City": "",
"MakerNotes:City2": "",
"MakerNotes:ClearRetouch": 0,
"MakerNotes:ClearRetouchValue": "undef",
"MakerNotes:ColorEffect": 1,
"MakerNotes:ColorTempKelvin": 5600,
"MakerNotes:Contrast": 0,
"MakerNotes:ContrastMode": 4,
"MakerNotes:ConversionLens": 1,
"MakerNotes:Country": "",
"MakerNotes:DarkFocusEnvironment": 1,
"MakerNotes:DiffractionCorrection": 1,
"MakerNotes:FacesDetected": 0,
"MakerNotes:FacesRecognized": 0,
"MakerNotes:FilterEffect": "0 0",
"MakerNotes:FirmwareVersion": "0 1 1 0",
"MakerNotes:FlashBias": 0,
"MakerNotes:FlashCurtain": 0,
"MakerNotes:FocusBracket": 0,
"MakerNotes:FocusMode": 1,
"MakerNotes:HDR": 0,
"MakerNotes:HDRShot": 0,
"MakerNotes:HighlightShadow": "0 0",
"MakerNotes:HighlightWarning": 1,
"MakerNotes:ImageQuality": 2,
"MakerNotes:ImageStabilization": 2,
"MakerNotes:IntelligentD-Range": 0,
"MakerNotes:IntelligentResolution": 1,
"MakerNotes:InternalNDFilter": 0,
"MakerNotes:InternalSerialNumber": "XHL21061302626/",
"MakerNotes:JPEGQuality": 2,
"MakerNotes:Landmark": "",
"MakerNotes:LensFirmwareVersion": "0 21 21 0",
"MakerNotes:LensSerialNumber": "N/A",
"MakerNotes:LensType": "N/A",
"MakerNotes:LensTypeMake": 0,
"MakerNotes:Location": "",
"MakerNotes:MacroMode": 2,
"MakerNotes:MakerNoteVersion": "0152",
"MakerNotes:MonochromeFilterEffect": 0,
"MakerNotes:MultiExposure": 1,
"MakerNotes:NoiseReduction": 0,
"MakerNotes:NumFacePositions": 0,
"MakerNotes:OpticalZoomMode": 1,
"MakerNotes:PanasonicExifVersion": "0412",
"MakerNotes:PanasonicImageHeight": 0,
"MakerNotes:PanasonicImageWidth": 0,
"MakerNotes:PhotoStyle": 1,
"MakerNotes:PitchAngle": 0,
"MakerNotes:PostFocusMerging": "0 0",
"MakerNotes:ProgramISO": 65535,
"MakerNotes:RedEyeRemoval": 1,
"MakerNotes:RollAngle": 0,
"MakerNotes:Rotation": 1,
"MakerNotes:Saturation": 0,
"MakerNotes:SceneMode": 3,
"MakerNotes:SelfTimer": 0,
"MakerNotes:SequenceNumber": 0,
"MakerNotes:Sharpness": 0,
"MakerNotes:ShootingMode": 3,
"MakerNotes:ShutterType": 0,
"MakerNotes:State": "",
"MakerNotes:SweepPanoramaDirection": 0,
"MakerNotes:SweepPanoramaFieldOfView": 0,
"MakerNotes:TextStamp": 1,
"MakerNotes:TimeLapseShotNumber": 0,
"MakerNotes:TimeSincePowerOn": 557.48,
"MakerNotes:TimeStamp": "2023:08:08 21:37:52",
"MakerNotes:TimerRecording": 0,
"MakerNotes:Title": "",
"MakerNotes:TouchAE": 0,
"MakerNotes:TravelDay": 65535,
"MakerNotes:VideoBurstMode": 1,
"MakerNotes:VideoBurstResolution": 1,
"MakerNotes:WBBlueLevel": 1876,
"MakerNotes:WBGreenLevel": 1024,
"MakerNotes:WBRedLevel": 1727,
"MakerNotes:WBShiftAB": 0,
"MakerNotes:WBShiftCreativeControl": 0,
"MakerNotes:WBShiftGM": 0,
"MakerNotes:WBShiftIntelligentAuto": 0,
"MakerNotes:WhiteBalance": 1,
"MakerNotes:WorldTimeLocation": 2,
"Photoshop:IPTCDigest": "6dedbe66ee1f9e63717e6541369f9774",
"PrintIM:PrintIMVersion": "0250",
"SourceFile": "D:/Photos/Andalousie/zum.JPG",
"XMP:Creator": "Picasa",
"XMP:ModifyDate": "2023:08:09 19:33:37+02:00",
"XMP:XMPToolkit": "XMP Core 5.1.2"

   "QuickTime:MediaDuration": 9.04533333333333,
   "QuickTime:MediaHeaderVersion": 0,
   "QuickTime:MediaLanguageCode": "und",
   "QuickTime:MediaModifyDate": "2023:07:26 08:00:52",
   "QuickTime:MediaTimeScale": 48000,
   "QuickTime:MinorVersion": "0.0.1",
   "QuickTime:ModifyDate": "2023:07:26 08:00:52",
   "QuickTime:MovieHeaderVersion": 0,
   "QuickTime:NextTrackID": 3,
   "QuickTime:OpColor": "0 0 0",
   "QuickTime:PosterTime": 0,
   "QuickTime:PreferredRate": 1,
   "QuickTime:PreferredVolume": 1,
   "QuickTime:PreviewDuration": 0,
   "QuickTime:PreviewTime": 0,
   "QuickTime:SelectionDuration": 0,
   "QuickTime:SelectionTime": 0,
   "QuickTime:SourceImageHeight": 1080,
   "QuickTime:SourceImageWidth": 1920,
   "QuickTime:TimeScale": 180000,
   "QuickTime:TrackCreateDate": "2023:07:26 08:00:52",
   "QuickTime:TrackDuration": 9.009,
   "QuickTime:TrackHeaderVersion": 0,
   "QuickTime:TrackID": 1,
   "QuickTime:TrackLayer": 0,
   "QuickTime:TrackModifyDate": "2023:07:26 08:00:52",
   "QuickTime:TrackVolume": 0,
   "QuickTime:TransferCharacteristics": 1,
   "QuickTime:VideoFrameRate": 59.9400599400599,
   "QuickTime:XResolution": 72,
   "QuickTime:YResolution": 72,
   "SourceFile": "//Freebox_Server/Tera2/Photos/2023Q3/Andalousie 2023/Vid?os/Andalousie 2023 - 0001 - 2023-07-26 08_00_51 - Panasonic DC-FZ82.mp4",
   "XMP:GPSLatitude": 37.1759972221667,
   "XMP:GPSLongitude": -3.59741388883333,
   "XMP:XMPToolkit": "Image::ExifTool 12.64"
}
2023-08-13 10:50:27,325 - renamer - DEBUG - Size = {
   "Composite:AdvancedSceneMode": "DC-FZ82 37 5",
   "Composite:Aperture": 2.8,
   "Composite:AvgBitrate": 27370471,
   "Composite:BlueBalance": 1.8984375,
   "Composite:CircleOfConfusion": "0.00491666083017817",
   "Composite:FOV": 78.5788800977413,
   "Composite:FocalLength35efl": 22,
   "Composite:GPSLatitudeRef": "N",
   "Composite:GPSLongitudeRef": "W",
   "Composite:GPSPosition": "37.1759972221667 -3.59741388883333",
   "Composite:HyperfocalDistance": 0.941405475879389,
   "Composite:ImageSize": "1920 1080",
   "Composite:LightValue": 13.6370776572014,
   "Composite:Megapixels": 2.0736,
   "Composite:RedBalance": 1.546875,
   "Composite:Rotation": 0,
   "Composite:ScaleFactor35efl": 6.11111111111111,
   "Composite:ShutterSpeed": 0.0007692307692,
   "Composite:SubSecCreateDate": "2023:07:26 08:00:51.985",
   "Composite:SubSecDateTimeOriginal": "2023:07:26 08:00:51.985",
   "Composite:SubSecModifyDate": "2023:07:26 08:00:51.985",
   "EXIF:ColorSpace": 1,
   "EXIF:ComponentsConfiguration": "1 2 3 0",
   "EXIF:CompressedBitsPerPixel": 2,
   "EXIF:Compression": 6,
   "EXIF:Contrast": 0,
   "EXIF:CreateDate": "2023:07:26 08:00:51",
   "EXIF:CustomRendered": 0,
   "EXIF:DateTimeOriginal": "2023:07:26 08:00:51",
   "EXIF:DigitalZoomRatio": 0,
   "EXIF:ExifImageHeight": 1080,
   "EXIF:ExifImageWidth": 1920,
   "EXIF:ExifVersion": "0230",
   "EXIF:ExposureCompensation": 0,
   "EXIF:ExposureMode": 0,
   "EXIF:ExposureProgram": 8,
   "EXIF:ExposureTime": 0.0007692307692,
   "EXIF:FNumber": 2.8,
   "EXIF:FileSource": 3,
   "EXIF:Flash": 16,
   "EXIF:FlashpixVersion": "0100",
   "EXIF:FocalLength": 3.6,
   "EXIF:FocalLengthIn35mmFormat": 22,
   "EXIF:GainControl": 0,
   "EXIF:ISO": 80,
   "EXIF:InteropIndex": "R98",
   "EXIF:InteropVersion": "0100",
   "EXIF:LightSource": 0,
   "EXIF:Make": "Panasonic",
   "EXIF:MaxApertureValue": 2.80174979625871,
   "EXIF:MeteringMode": 5,
   "EXIF:Model": "DC-FZ82",
   "EXIF:ModifyDate": "2023:07:26 08:00:51",
   "EXIF:Orientation": 1,
   "EXIF:ResolutionUnit": 2,
   "EXIF:Saturation": 0,
   "EXIF:SceneCaptureType": 0,
   "EXIF:SceneType": 1,
   "EXIF:SensingMethod": 2,
   "EXIF:SensitivityType": 1,
   "EXIF:Sharpness": 0,
   "EXIF:Software": "Ver.1.1",
   "EXIF:SubSecTime": 985,
   "EXIF:SubSecTimeDigitized": 985,
   "EXIF:SubSecTimeOriginal": 985,
   "EXIF:ThumbnailLength": 0,
   "EXIF:ThumbnailOffset": 14668,
   "EXIF:WhiteBalance": 0,
   "EXIF:XResolution": 180,
   "EXIF:YCbCrPositioning": 2,
   "EXIF:YResolution": 180,
   "ExifTool:ExifToolVersion": 12.64,
   "ExifTool:Warning": "FileName encoding not specified",
   "File:Directory": "//Freebox_Server/Tera2/Photos/2023Q3/Andalousie 2023/Vid?os",
   "File:ExifByteOrder": "II",
   "File:FileAccessDate": "2023:08:10 18:06:11+02:00",
   "File:FileCreateDate": "2023:08:10 18:06:11+02:00",
   "File:FileModifyDate": "2023:08:10 18:06:11+02:00",
   "File:FileName": "Andalousie 2023 - 0001 - 2023-07-26 08_00_51 - Panasonic DC-FZ82.mp4",
   "File:FilePermissions": 100666,
   "File:FileSize": 30923773,
   "File:FileType": "MP4",
   "File:FileTypeExtension": "MP4",
   "File:MIMEType": "video/mp4",
   "MakerNotes:AFAreaMode": "240 0",
   "MakerNotes:AFAssistLamp": 2,
   "MakerNotes:AFPointPosition": "0.0546875 0.51171875",
   "MakerNotes:AccelerometerX": 0,
   "MakerNotes:AccelerometerY": 0,
   "MakerNotes:AccelerometerZ": 0,
   "MakerNotes:AccessorySerialNumber": "0000000",
   "MakerNotes:AccessoryType": "NO-ACCESSORY",
   "MakerNotes:AdvancedSceneType": 5,
   "MakerNotes:Audio": 3,
   "MakerNotes:BabyAge": "9999:99:99 00:00:00",
   "MakerNotes:BabyName": "",
   "MakerNotes:BatteryLevel": 0,
   "MakerNotes:BracketSettings": 0,
   "MakerNotes:BurstMode": 0,
   "MakerNotes:BurstSpeed": 0,
   "MakerNotes:CameraOrientation": 0,
   "MakerNotes:City": "",
   "MakerNotes:City2": "",
   "MakerNotes:ClearRetouch": 0,
   "MakerNotes:ClearRetouchValue": "undef",
   "MakerNotes:ColorEffect": 1,
   "MakerNotes:ColorTempKelvin": 5000,
   "MakerNotes:Contrast": 0,
   "MakerNotes:ContrastMode": 1,
   "MakerNotes:ConversionLens": 1,
   "MakerNotes:Country": "",
   "MakerNotes:DarkFocusEnvironment": 1,
   "MakerNotes:DataDump": "(Binary data 8 bytes, use -b option to extract)",
   "MakerNotes:DiffractionCorrection": 1,
   "MakerNotes:FacesDetected": 0,
   "MakerNotes:FacesRecognized": 0,
   "MakerNotes:FilterEffect": "0 0",
   "MakerNotes:FirmwareVersion": "0 1 1 0",
   "MakerNotes:FlashBias": 0,
   "MakerNotes:FlashCurtain": 0,
   "MakerNotes:FocusBracket": 0,
   "MakerNotes:FocusMode": 1,
   "MakerNotes:HDR": 0,
   "MakerNotes:HDRShot": 0,
   "MakerNotes:HighlightShadow": "0 0",
   "MakerNotes:HighlightWarning": 1,
   "MakerNotes:ImageQuality": 11,
   "MakerNotes:ImageStabilization": 2,
   "MakerNotes:IntelligentD-Range": 0,
   "MakerNotes:IntelligentResolution": 0,
   "MakerNotes:InternalNDFilter": 0,
   "MakerNotes:InternalSerialNumber": "XHL21061302626/",
   "MakerNotes:JPEGQuality": 0,
   "MakerNotes:Landmark": "",
   "MakerNotes:LensFirmwareVersion": "0 21 21 0",
   "MakerNotes:LensSerialNumber": "N/A",
   "MakerNotes:LensType": "N/A",
   "MakerNotes:LensTypeMake": 0,
   "MakerNotes:Location": "",
   "MakerNotes:MacroMode": 2,
   "MakerNotes:MakerNoteVersion": "0152",
   "MakerNotes:Model": "DC-FZ82",
   "MakerNotes:MonochromeFilterEffect": 0,
   "MakerNotes:MultiExposure": 0,
   "MakerNotes:NoiseReduction": 0,
   "MakerNotes:NumFacePositions": 0,
   "MakerNotes:OpticalZoomMode": 1,
   "MakerNotes:PanasonicExifVersion": "0412",
   "MakerNotes:PanasonicImageHeight": 0,
   "MakerNotes:PanasonicImageWidth": 0,
   "MakerNotes:PhotoStyle": 1,
   "MakerNotes:PitchAngle": 0,
   "MakerNotes:PostFocusMerging": "0 0",
   "MakerNotes:ProgramISO": 65535,
   "MakerNotes:RedEyeRemoval": 1,
   "MakerNotes:RollAngle": 0,
   "MakerNotes:Rotation": 1,
   "MakerNotes:Saturation": 0,
   "MakerNotes:SceneMode": 37,
   "MakerNotes:SelfTimer": 0,
   "MakerNotes:SequenceNumber": 0,
   "MakerNotes:Sharpness": 0,
   "MakerNotes:ShootingMode": 37,
   "MakerNotes:ShutterType": 0,
   "MakerNotes:State": "",
   "MakerNotes:SweepPanoramaDirection": 0,
   "MakerNotes:SweepPanoramaFieldOfView": 0,
   "MakerNotes:TextStamp": 1,
   "MakerNotes:ThumbnailHeight": 240,
   "MakerNotes:ThumbnailImage": "(Binary data 8561 bytes, use -b option to extract)",
   "MakerNotes:ThumbnailWidth": 416,
   "MakerNotes:TimeLapseShotNumber": 0,
   "MakerNotes:TimeSincePowerOn": 69.6,
   "MakerNotes:TimeStamp": "2023:07:26 16:00:51",
   "MakerNotes:TimerRecording": 0,
   "MakerNotes:Title": "",
   "MakerNotes:TouchAE": 0,
   "MakerNotes:TravelDay": 65535,
   "MakerNotes:VideoBurstMode": 0,
   "MakerNotes:VideoBurstResolution": 3,
   "MakerNotes:WBBlueLevel": 1944,
   "MakerNotes:WBGreenLevel": 1024,
   "MakerNotes:WBRedLevel": 1584,
   "MakerNotes:WBShiftAB": 0,
   "MakerNotes:WBShiftCreativeControl": 0,
   "MakerNotes:WBShiftGM": 0,
   "MakerNotes:WBShiftIntelligentAuto": 0,
   "MakerNotes:WhiteBalance": 1,
   "MakerNotes:WorldTimeLocation": 2,
   "PrintIM:PrintIMVersion": "0250",
   "QuickTime:AudioBitsPerSample": 16,
   "QuickTime:AudioChannels": 2,
   "QuickTime:AudioFormat": "mp4a",
   "QuickTime:AudioSampleRate": 48000,
   "QuickTime:Balance": 0,
   "QuickTime:BitDepth": 24,
   "QuickTime:ColorPrimaries": 1,
   "QuickTime:ColorProfiles": "nclx",
   "QuickTime:CompatibleBrands": [
      "mp42",
      "avc1"
   ],
   "QuickTime:CompressorID": "avc1",
   "QuickTime:CreateDate": "2023:07:26 08:00:52",
   "QuickTime:CurrentTime": 0,
   "QuickTime:Duration": 9.009,
   "QuickTime:GraphicsMode": 0,
   "QuickTime:HandlerType": "soun",
   "QuickTime:ImageHeight": 1080,
   "QuickTime:ImageWidth": 1920,
   "QuickTime:MajorBrand": "mp42",
   "QuickTime:MatrixCoefficients": 1,
   "QuickTime:MatrixStructure": "1 0 0 0 1 0 0 0 1",
   "QuickTime:MediaCreateDate": "2023:07:26 08:00:52",
   "QuickTime:MediaDataOffset": 101201,
   "QuickTime:MediaDataSize": 30822572,
   "QuickTime:MediaDuration": 9.04533333333333,
   "QuickTime:MediaHeaderVersion": 0,
   "QuickTime:MediaLanguageCode": "und",
   "QuickTime:MediaModifyDate": "2023:07:26 08:00:52",
   "QuickTime:MediaTimeScale": 48000,
   "QuickTime:MinorVersion": "0.0.1",
   "QuickTime:ModifyDate": "2023:07:26 08:00:52",
   "QuickTime:MovieHeaderVersion": 0,
   "QuickTime:NextTrackID": 3,
   "QuickTime:OpColor": "0 0 0",
   "QuickTime:PosterTime": 0,
   "QuickTime:PreferredRate": 1,
   "QuickTime:PreferredVolume": 1,
   "QuickTime:PreviewDuration": 0,
   "QuickTime:PreviewTime": 0,
   "QuickTime:SelectionDuration": 0,
   "QuickTime:SelectionTime": 0,
   "QuickTime:SourceImageHeight": 1080,
   "QuickTime:SourceImageWidth": 1920,
   "QuickTime:TimeScale": 180000,
   "QuickTime:TrackCreateDate": "2023:07:26 08:00:52",
   "QuickTime:TrackDuration": 9.009,
   "QuickTime:TrackHeaderVersion": 0,
   "QuickTime:TrackID": 1,
   "QuickTime:TrackLayer": 0,
   "QuickTime:TrackModifyDate": "2023:07:26 08:00:52",
   "QuickTime:TrackVolume": 0,
   "QuickTime:TransferCharacteristics": 1,
   "QuickTime:VideoFrameRate": 59.9400599400599,
   "QuickTime:XResolution": 72,
   "QuickTime:YResolution": 72,
   "SourceFile": "//Freebox_Server/Tera2/Photos/2023Q3/Andalousie 2023/Vid?os/Andalousie 2023 - 0001 - 2023-07-26 08_00_51 - Panasonic DC-FZ82.mp4",
   "XMP:GPSLatitude": 37.1759972221667,
   "XMP:GPSLongitude": -3.59741388883333,
   "XMP:XMPToolkit": "Image::ExifTool 12.64"
"""
