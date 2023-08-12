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

'''
This script renames files with format YYYY-MM-DD_HHMMSS_<root>
'''

import os
import argparse
from exiftool import ExifToolHelper
import mediatools.utilities as util
import mediatools.log as log
import mediatools.file as fil
from datetime import datetime

def main():
    util.init('renamer')
    parser = argparse.ArgumentParser(description='Stacks images vertically or horizontally')
    parser.add_argument('-f', '--files', nargs='+', help='List of files to rename', required=True)
    parser.add_argument('-r', '--root', help='Root name', required=False)
    parser.add_argument('-g', '--debug', required=False, type=int, help='Debug level')
    kwargs = util.parse_media_args(parser)
    root = kwargs.get('root', None)
    for file in kwargs['files']:
        with ExifToolHelper() as et:
            # for data in et.get_metadata(file):
            #    log.logger.debug("MetaData = %s", util.json_fmt(data))
            for data in et.get_tags(file, tags=["DateTimeOriginal", "Make", "Model"]):
                log.logger.debug("Data = %s", util.json_fmt(data))
                creation_date = datetime.strptime(data["EXIF:DateTimeOriginal"], '%Y:%m:%d %H:%M:%S')
                postfix = data.get("EXIF:Make", "") + " " + data.get("EXIF:Model", "") if root is None or root == "" else root
        log.logger.debug("Postfix = %s", postfix)

        new_filename = fil.dirname(file) + os.sep + creation_date.strftime("%Y-%m-%d %H_%M_%S") + f" {postfix}." + fil.extension(file).lower()
        if new_filename == file:
            log.logger.info("File %s does need to be renamed, skipped...", file)
            continue
        log.logger.info(f"Renaming {file} into {new_filename}")
        try:
            os.rename(file, new_filename)
        except os.error:
            log.logger.warning("Unable to rename")


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
"""
