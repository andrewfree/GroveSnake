GroveSnake
==========

Downloads and tags music from youtube and soundcloud (from URL on clipboard).

Create a settings.yaml in the root directory with your soundcloud client_id like so
```
soundcloud_client_id: cb6a67u320833e5209d4ec765cft859z
```
Install python library for Growl notifications
```
$ pip install gntp
```
Bind a system hotkey to the grove_snake script.
http://i.imgur.com/nQBE4aC.png
This is just run within BetterTouchTool as a global hotkey (You could do something similar in system prefrences -> services)

The audio files are marked in the comment field with "done" after the program completes so you can use something like Hazel to watch that directory and take actions on the files (like the ability to automatically add it to itunes etc...) 
