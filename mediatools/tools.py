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

"""Unified commands: videotool, audiotool, imagetool and pdftool, followed by an action and the parameters of this action.
For instance "videotool crop -i video.mp4 --box 1920x1080 --center" is the same as "media-crop -i video.mp4 --box 1920x1080 --center"."""

import difflib
import importlib
import sys
from collections.abc import Callable

# For each command, the actions with the "module:function" that implements them and a short description
VIDEO_ACTIONS: dict[str, tuple[str, str]] = {
    "crop": ("mediatools.crop:main", "Crops a region of a video"),
    "concat": ("mediatools.concat:main", "Concatenates videos"),
    "cut": ("mediatools.cut:main", "Cuts a time window of a video"),
    "deshake": ("mediatools.deshake:main", "Applies a deshake filter"),
    "encode": ("cli.encode:main", "ffmpeg front-end encoder"),
    "encodeauto": ("mediatools.encodeauto:main", "Encodes automatically with the best settings"),
    "enhance": ("mediatools.video_enhance:main", "Enhances the colors"),
    "metadata": ("mediatools.metadata:main", "Adds metadata"),
    "flip": ("mediatools.flip:main", "Flips a video (swaps left and right, or top and bottom)"),
    "mux": ("mediatools.mux:main", "Muxes a video and audio tracks"),
    "profile-encode": ("mediatools.encode:main", "Encodes with an encoding profile"),
    "reverse": ("mediatools.reverse:main", "Reverses a video"),
    "rotate": ("mediatools.rotate:main", "Rotates a video"),
    "slideshow": ("mediatools.slideshow:main", "Creates a slideshow video from images"),
    "snap": ("mediatools.video_snap:main", "Snaps photos from a video"),
    "specs": ("mediatools.filespecs:main", "Displays the specs of media files"),
    "speed": ("mediatools.speed:main", "Changes the speed"),
    "stabilize": ("mediatools.stabilize:main", "Stabilizes shaky footage"),
    "volume": ("mediatools.volume:main", "Changes the volume"),
}

AUDIO_ACTIONS: dict[str, tuple[str, str]] = {
    "album-art": ("mediatools.album_art:main", "Adds an album art to audio files"),
    "concat": ("mediatools.audioconcat:main", "Concatenates audio files"),
    "cut": ("mediatools.cut:main", "Cuts a time window of an audio file"),
    "denoise": ("mediatools.audio_denoise:main", "Reduces the noise"),
    "encode": ("cli.encode:main", "ffmpeg front-end encoder"),
    "fix-mp3-meta": ("mediatools.fix_mp3_meta:main", "Fixes the metadata of mp3 files"),
    "lib": ("mediatools.audio_lib:main", "Manages an audio library"),
    "list": ("mediatools.audio_list:main", "Lists audio files"),
    "normalize": ("mediatools.audio_normalize:main", "Normalizes the audio files"),
    "profile-encode": ("mediatools.encode:main", "Encodes with an encoding profile"),
    "specs": ("mediatools.filespecs:main", "Displays the specs of media files"),
    "speed": ("mediatools.audiospeed:main", "Changes the speed"),
    "split": ("mediatools.audiosplit:main", "Splits at the detected tune changes"),
    "volume": ("mediatools.volume:main", "Changes the volume"),
}

IMAGE_ACTIONS: dict[str, tuple[str, str]] = {
    "blinds": ("mediatools.blindify:main", "Creates a window blinds effect"),
    "crop-ratio": ("mediatools.crop_ratio:main", "Crops to an aspect ratio"),
    "poster": ("mediatools.poster:main", "Creates a poster from images"),
    "scale": ("mediatools.rescale:main", "Rescales images"),
    "shake": ("mediatools.shake:main", "Creates a shake effect"),
    "specs": ("mediatools.filespecs:main", "Displays the specs of media files"),
    "stack": ("mediatools.stack:main", "Stacks images"),
    "to-video": ("mediatools.image2video:main", "Converts images to videos"),
}

PDF_ACTIONS: dict[str, tuple[str, str]] = {
    "compress": ("mediatools.pdf_compress:main", "Compresses PDF files"),
    "merge": ("mediatools.pdf_merge:main", "Merges PDF files"),
    "split": ("mediatools.pdf_split:main", "Splits PDF files"),
}

COMMANDS: dict[str, dict[str, tuple[str, str]]] = {
    "videotool": VIDEO_ACTIONS,
    "audiotool": AUDIO_ACTIONS,
    "imagetool": IMAGE_ACTIONS,
    "pdftool": PDF_ACTIONS,
}


def usage(command: str) -> str:
    """Returns the usage of a unified command: its actions and their description"""
    actions = COMMANDS[command]
    width = max(len(a) for a in actions)
    lines = [f"usage: {command} <action> [action parameters]", "", "actions:"]
    lines += [f"  {action:<{width}}  {desc}" for action, (_, desc) in actions.items()]
    lines += ["", f"Use '{command} <action> -h' for the parameters of an action"]
    return "\n".join(lines)


def get_action_function(command: str, action: str) -> Callable[[], None]:
    """Returns the main function of an action of a command"""
    module_name, function_name = COMMANDS[command][action][0].split(":")
    return getattr(importlib.import_module(module_name), function_name)


def find_action(module_name: str) -> tuple[str, str] | None:
    """Returns the (command, action) that run the main() of a module, None if there is no such action"""
    target = f"{module_name}:main"
    for command, actions in COMMANDS.items():
        for action, (action_target, _) in actions.items():
            if action_target == target:
                return command, action
    return None


def run(command: str, args: list[str] | None = None) -> None:
    """Runs an action of a command: args is the action followed by its parameters (the command line arguments by default).
    Exits with code 2 if the action is missing or unknown"""
    args = sys.argv[1:] if args is None else args
    if not args or args[0] in ("-h", "--help"):
        print(usage(command))
        sys.exit(0 if args else 2)
    action, action_args = args[0], args[1:]
    if action not in COMMANDS[command]:
        message = f"{command}: unknown action '{action}'"
        close = difflib.get_close_matches(action, COMMANDS[command], n=1)
        if close:
            message += f", did you mean '{close[0]}'?"
        print(f"{message}\n\n{usage(command)}", file=sys.stderr)
        sys.exit(2)
    # The action behaves as if it was run by itself, with its own name in the usage
    sys.argv = [f"{command} {action}", *action_args]
    get_action_function(command, action)()


def videotool() -> None:
    """Runs an action of the videotool command"""
    run("videotool")


def audiotool() -> None:
    """Runs an action of the audiotool command"""
    run("audiotool")


def imagetool() -> None:
    """Runs an action of the imagetool command"""
    run("imagetool")


def pdftool() -> None:
    """Runs an action of the pdftool command"""
    run("pdftool")
