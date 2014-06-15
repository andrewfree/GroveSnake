#!/usr/bin/env python2.7
# Docs https://github.com/kfdm/gntp/blob/master/docs/index.rst
# import urllib2, httplib, json # Can get json metadata on youtube videos w/ http://gdata.youtube.com/feeds/api/videos/_7gcIbopIPk?v=2&alt=json
# import soundcloud,client = soundcloud.Client(client_id='*',client_secret='*',username='*',password='*')
import subprocess 
import os
import traceback
import string
import gntp.notifier
import urllib2
import simplejson

def growlInit():
    growl = gntp.notifier.GrowlNotifier(
        applicationName = "GroveSnake",
        notifications = ["Completed","New Download"],
        defaultNotifications = ["New Download"])
    growl.register()
    return growl

def sendGrowlNotify(growl,message,callback_url="http://youtube.com",code="",msg_priority=0,msg_type="New Download"):
        
    growl.notify(
        noteType = msg_type,
        title = "%s" % message,
        description = "%s" % code,
        icon = "http://i.imgur.com/mXcrWGf.png", # http://i.imgur.com/cc0OCEo.png, http://i.imgur.com/Bfz3kgL.png?1
        sticky = False,
        priority = msg_priority,
        callback = callback_url)

def readable_size_format(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

def main():
    try:
        env = os.environ #os.environ.copy()
        env["PATH"] = "/sbin:/sbin:/usr/local/bin:/opt/local/bin:/opt/local/libexec/gnubin:/Users/rever/Documents/customBashExecute/:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/MacGPG2/bin:/Users/rever/.rvm/bin" #env["SHELL"] = '/bin/zsh'
        growl = growlInit()
        clipboard_link = ""
        clipboard_provider = ""
        project_dir = ""
        tagged = False
        
        clipboard_process = subprocess.Popen("pbpaste", stdout=subprocess.PIPE)
        clipboard_link, err = clipboard_process.communicate()

        # Verify link being used is from soundcloud or youtube
        if not (("youtube" in clipboard_link) or ("soundcloud" in clipboard_link)):
            sendGrowlNotify(growl,"Bad Link!")
            os._exit(0)
        else:
            if ("youtube" in clipboard_link):
                clipboard_provider = "youtube"
            elif ("soundcloud" in clipboard_link):
                clipboard_provider = "soundcloud"

        sendGrowlNotify(growl,"Downloading...")

        project_dir = (os.path.join( (os.path.dirname(os.path.realpath(__file__))),'..')) # Project directory, have to go one up out of /lib
        os.chdir(os.path.join(project_dir,"tracks")) # Change into tracks folder for downloading.
        
        # Start download, max quality, safe filenames for handling below. The ID is in the filename so you can do metadata lookups for more info if wanted. Rips to mp3, might want to support native download formats, transcoding again and again lowers quality. 
        output = subprocess.Popen(["/usr/local/bin/youtube-dl", "-o", "%(title)s|id|%(id)s.%(ext)s","--add-metadata", "-f","22/18/download/http_mp3_128_url","--restrict-filenames","--audio-format","mp3","--audio-quality", "0","-x",clipboard_link], stdout=subprocess.PIPE).communicate()[0] # stderr=subprocess.STDOUT,stdout=subprocess.PIPE
        
        # Get files in tracks folder.
        file_list = os.listdir(os.getcwd())
        file_list.remove(".DS_Store")
        song_list = []
        for song in file_list:
            if song.split(".")[-1] != "mp3":
                os.remove(song) # Have to do this until they fix bug in youtube-dl
                continue
            song_list.append((os.path.realpath(song),song)) # Fullpath and filename for ease.

        if len(song_list) <= 0:
            sendGrowlNotify(growl,"No items to download.")
            os._exit(1)
        elif len(song_list) > 1:
            sendGrowlNotify(growl,"Dirty tracks directory. Should only have a single song.")
            os._exit(1)

        # File path variables & url / size of song / song id                
        music_file = song_list[0]
        file_path = music_file[0]
        no_https_url = string.join(clipboard_link.split("/")[2:],"/") # Remove httpS out of url. Something about this url breaks OS X and metadata for finder items. 
        readable_size = readable_size_format(os.path.getsize(file_path))
        music_file_id = music_file[1].split("|id|")[-1].split(".")[0] # Split filename and look at very end for song id since scheme has id.mp3
    
        if clipboard_provider == "soundcloud":
            url = "http://api.soundcloud.com/tracks/%s.json?client_id=key" % music_file_id
            json = simplejson.load(urllib2.urlopen(url))
            title = json["title"].strip()
            artist = json["user"]['username'].encode('utf8').strip()
            tagged = True # youtube-dl supports --add-metadata for this service
        elif clipboard_provider == "youtube":
            url = "http://gdata.youtube.com/feeds/api/videos/%s?alt=json&v=2" % music_file_id
            json = simplejson.load(urllib2.urlopen(url))
            artist = json["entry"]["author"][0]["name"]["$t"].strip()
            title = json["entry"]["title"]["$t"].strip()
            tagged = True # youtube-dl supports --add-metadata for this service
        
        dashes = title.count("-")
        if dashes == 1:
            artist = title.split("-")[0].strip()
            title = title.split("-")[1].strip()
            tagged = False # Above tags are more accurate, retag.
        elif dashes > 1:
            tagged = False # Re-write tags with response from api if song has more than one - in the title.
        elif dashes == 0:
            tagged = False # Testing re-writing all tags.

        # Writing id3v2 comment tags with song url for lookup later.
        if tagged != True:
            subprocess.Popen(["/opt/local/bin/id3v2", "-t", title, "-a", artist, "-c", no_https_url, music_file[1]],stdout=subprocess.PIPE)
            #subprocess.Popen(["/opt/local/bin/xattr","-s","com.apple.metadata:kMDItemWhereFroms",no_https_url,music_file[1]],stdout=subprocess.PIPE) # For setting the Where From for Spotlight

        os.chdir(os.path.join(project_dir,"lib"))
        subprocess.Popen(["/opt/local/bin/bash","setFileComments.sh",file_path],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sendGrowlNotify(growl,"%s - %s" % (artist,title),code="%s" % readable_size, callback_url = clipboard_link, msg_type="Completed")
        os._exit(0)
    
    except Exception as e:
        print traceback.format_exc()
        sendGrowlNotify(growl,'Error: %s' % e,msg_priority=1)
        os._exit(1)
        
if __name__ == "__main__":
    main()