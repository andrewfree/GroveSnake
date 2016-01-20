#!/opt/local/bin/python

from __future__ import print_function
import subprocess, os, time, traceback, logging
import string, urllib2, simplejson, yaml, urllib, re

from django.utils.encoding import smart_str, smart_unicode
import gntp.notifier
# from Tkinter import *
# from tkMessageBox import *
logging.basicConfig(level=logging.INFO)

def growl_init():
    growl = gntp.notifier.GrowlNotifier(
        applicationName      = "GroveSnake",
        notifications        = ["Completed","New Download"],
        defaultNotifications = ["New Download"])
    growl.register()
    return growl

def sendGrowlNotify(growl,message,callback_url="http://youtube.com",code="",msg_priority=0,msg_type="New Download"):
    growl.notify(
        noteType    = msg_type,
        title       = "%s" % message,
        description = "%s" % code,
        icon        = "http://i.imgur.com/mXcrWGf.png", # http://i.imgur.com/cc0OCEo.png, http://i.imgur.com/Bfz3kgL.png?1
        sticky      = False,
        priority    = msg_priority,
        callback    = callback_url)

def get_clipboard():
    process             = subprocess.Popen("pbpaste", stdout=subprocess.PIPE)
    clipboard_link, err = process.communicate()
    # Verify source url (soundcloud/youtube)
    if "youtube" in clipboard_link:
        clipboard_provider = "youtube"
    elif "soundcloud" in clipboard_link:
        clipboard_provider = "soundcloud"
    else:
        sendGrowlNotify(growl,"Invalid Link!", callback_url=clipboard_link)
        os._exit(0)
    clipboard_link = clipboard_link.split("&")[0] # Remove arguments from url
    return (clipboard_link,clipboard_provider)

def get_metadata(clipboard_link,clipboard_provider,m_id,soundcloud_client_id, youtube_api_key):
    try:
        artwork = ""
        tags    = ""
        if clipboard_provider == "soundcloud":
            url       = "http://api.soundcloud.com/tracks/%s.json?client_id=%s" % (m_id,soundcloud_client_id)
            json      = simplejson.load(urllib2.urlopen(url))
            title     = json["title"].strip().encode('utf8')
            artist    = json["user"]['username'].encode('utf8').strip()
            tags      = json['tag_list']
            track_url = json["permalink_url"]
            # for item in tags.split(' '):
            #     Button(text=item, command=answer(item)).pack(fill=X)
            # mainloop()
            if json.get("artwork_url") != None:
                artwork   = "-".join(json["artwork_url"].split("-")[0:-1])+"-t300x300.jpg"

        elif clipboard_provider == "youtube":
            url       = "https://www.googleapis.com/youtube/v3/videos?id=%s&key=%s&part=snippet,contentDetails,statistics,status" % (m_id,youtube_api_key)
            json      = simplejson.load(urllib2.urlopen(url))
            title     = json['items'][0]['snippet']['title'].strip()
            artist    = json['items'][0]['snippet']['channelTitle'].strip()
            track_url = "https://youtube.com/watch?v=%s" % m_id

        # Decide title based on dashes. If there dash in the title assume it is "Artist - Title", If muitipile dashes, treat  Title of "Bar - Foo - Foo"  as {artist:"Bar" Title:"Foo - Foo"}
        # If no dashes in the title use provided artist/poster name from API
        if title.find('-') >= 0:
            artist = title.split('-')[0]
            title  = "-".join(title.split('-')[1::]).strip()

        track_url = track_url.split("//")[-1] # Removes http or https part so can match the url better
        if track_url in clipboard_link:
            return {"title": title, "artist": artist,"artwork" : artwork, "tags" : tags}
        return False

    except urllib2.HTTPError:
        sendGrowlNotify(growl,"HTTPError, bad URL")
        sys.exit(1)

def readable_size_format(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

def main():
    try:
        # initialize starting varibles & settings
        os.environ["PATH"]                 = "/opt/local/bin:/usr/bin/:/bin" # The path for youtube-dl and pbpaste.
        os.environ["LC_CTYPE"] = 'en_US.UTF-8' # If don't explicity set eyeD3 detects as latin-1
        project_dir                        = (os.path.join( (os.path.dirname(os.path.realpath(__file__))),'..')) # Root project dir, have to go out of /lib where the code is run fro.
        clipboard_link, clipboard_provider = get_clipboard() # Grabs link from pbpaste
        unique_id                          = str(time.time()).split(".")[0]

        with open(os.path.join(project_dir,'settings.yaml'), 'r') as f: # load API keys from settings
            settings = yaml.load(f)
        os.chdir(os.path.join(project_dir,"tracks")) # Enter tracks folder for downloading.

        # Notify start
        sendGrowlNotify(growl,"Downloading...", callback_url = clipboard_link)

        # Start download, max quality, safe filenames for handling below. The ID is in the filename so you can do metadata lookups for more info if wanted. Rips to mp3, might want to support native source formats, transcoding again (to mp3) and again lowers quality.
        output = subprocess.Popen(["/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin//youtube-dl", "-o", "%(title)s|"+unique_id+"|%(id)s.%(ext)s" ,"--add-metadata", "-f","22/18/download/http_mp3_128_url","--restrict-filenames","--audio-format","mp3","--audio-quality", "0","-x",clipboard_link], stdout=subprocess.PIPE).communicate()[0] # stderr=subprocess.STDOUT,stdout=subprocess.PIPE
        # if HTTP Error 403: Forbidden run youtube-dl --rm-cache-dir

        # List files in tracks folder.
        file_list = os.listdir(os.getcwd())
        file_list.remove(".DS_Store") # OS X Specific hidden file

        x=0
        downloaded_file = ""
        for song in file_list:
            if song.split(".")[-1] != "mp3":
                os.remove(song) # Youtube-dl should remove source file but does not. Bug I believe.
                continue
            elif unique_id in song:
                song_id = song.split("|")[-1].split(".")[0]
                data    = get_metadata(clipboard_link,clipboard_provider,song_id,settings["soundcloud_client_id"],settings['youtube_api_key']) # Check if the id of the file found matches up w/ the url that is on the clipboard. Incase there are muitiple files in the output dir.
                if data:
                    title           = data['title']
                    artist          = data['artist']
                    artwork         = data.get("artwork")
                    tags            = data.get("tags")
                    downloaded_file = (song,os.path.realpath(song)) # Fullpath and filename for ease.
            else:
                if (x == len(file_list)): # There is not a track in the directory with a matching id from what is on the clipboar.
                    sendGrowlNotify(growl,"Dirty tracks directory. Unable to find matching song")
                    sys.exit(1)
                else: # May be muitiple trakcs in directory if software like Hazel has not cleared it, check next track to see if it is last downloaded.
                    x+=1
                    continue

        # File path variables & url / size of song / song id
        music_file    = downloaded_file[0]
        file_path     = downloaded_file[1]
        no_https_url  = string.join(clipboard_link.split("/")[2:],"/") # Remove httpS out of url. Something about this url breaks OS X and metadata for finder items.
        readable_size = readable_size_format(os.path.getsize(file_path)) # Human readble output of filesize for growl
        music_file_id = music_file.split("|id|")[-1].split(".")[0] # Split filename and look at very end for song id since scheme has id.mp3

        # Writing id3v2 comment tags with song url for lookup later.
        if len(artwork) >= 1:

            image,message = urllib.urlretrieve(artwork)
            subprocess.Popen(["/opt/local/bin/eyeD3-2.7", "-t",title, "-a", artist, "-c", "%s\n%s" % (no_https_url,tags), "--add-image","%s:FRONT_COVER" % image, music_file],shell=False,stdout=subprocess.PIPE).communicate()
            os.remove(image)
        else:
            output,err = subprocess.Popen(["/opt/local/bin/eyeD3-2.7", "-t",title, "-a", artist, "-c", "%s\n%s" % (no_https_url,tags), music_file],shell=False,stderr=subprocess.STDOUT,stdout=subprocess.PIPE).communicate()
            # sendGrowlNotify(growl,': %s / %s' % (output,err) )
            # sendGrowlNotify(growl, os.environ["LC_CTYPE"])

            # subprocess.Popen(["/opt/local/bin/id3v2", "-t",title, "-a", artist, "-c", no_https_url, music_file[1]],shell=False,stdout=subprocess.PIPE).communicate() # Different (old) way to set tags)
            # subprocess.Popen(["/opt/local/bin/xattr","-s","com.apple.metadata:kMDItemWhereFroms",no_https_url,music_file[1]],stdout=subprocess.PIPE) # For setting the Where From for Spotlight

        os.chdir(os.path.join(project_dir,"lib"))
        subprocess.Popen(["/bin/bash","setFileComments.sh",file_path],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            sendGrowlNotify(growl,"%s - %s" % (smart_str(artist),smart_str(title)),code="%s" % readable_size, callback_url = clipboard_link, msg_type="Completed")
        except UnicodeDecodeError:
            print("Can't decode unicdoe")
        os._exit(0)

    except Exception as e:
        print(traceback.format_exc())
        sendGrowlNotify(growl,'Error: %s' % e,msg_priority=1)
        os._exit(1)

if __name__ == "__main__":
    growl = growl_init()
    main()