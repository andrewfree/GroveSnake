#!/usr/bin/env python2.7
# Docs https://github.com/kfdm/gntp/blob/master/docs/index.rst
# import urllib2, httplib, json # Can get json metadata on youtube videos w/ http://gdata.youtube.com/feeds/api/videos/_7gcIbopIPk?v=2&alt=json
# import soundcloud,client = soundcloud.Client(client_id='*',client_secret='*',username='*',password='*')
# TO DO: 
# youtube open json api for more data "http://gdata.youtube.com/feeds/api/videos/%ID?alt=json&v=2" json["entry"]["author"][0]["name"]["$t"]
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
        defaultNotifications = ["New Download"]
    )
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
        callback = callback_url
    )

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
        meta_tagged = False
        meta_flagged = False
        
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
        output = subprocess.Popen(["/usr/local/bin/youtube-dl", "-o", "%(title)s-%(id)s.%(ext)s","--add-metadata", "-f","22/18/download/http_mp3_128_url", "--audio-format","mp3","--audio-quality", "0","-x",clipboard_link], stdout=subprocess.PIPE).communicate()[0] # stderr=subprocess.STDOUT,stdout=subprocess.PIPE
        
        # Search if metadata already added.
        for item in output.split("\n"): # Iterate youtube-dl output line by line (after it finished running)
            if (("ffmpeg" in item) and ("metadata" in item)): # Search of soundcloud pulled data with song title-artist to be tagged by youtube-dl.
                meta_tagged = True # If I want to mess with tags should read file from ffmpeg -i because youtube-dl sets that metadata first

        # Get files in tracks folder.
        track_list = os.listdir(os.getcwd())
        track_list.remove(".DS_Store")
        process_list = []
        for song in track_list:
            if song.split(".")[-1] != "mp3":
                os.remove(song) # Have to do this until they fix bug in youtube-dl
                continue

            r_path = os.path.realpath(song)
            process_list.append((r_path,song)) # Fullpath and filename for ease.

        if len(process_list) <= 0:
            sendGrowlNotify(growl,"No items to download.")
            os._exit(1)

        # Write a lot of tags to stuff.                
        music_file = process_list[0]
        file_path = music_file[0]
        no_https_url = string.join(clipboard_link.split("/")[2:],"/") # Remove httpS out of url. Something about this url breaks OS X and metadata for finder items. 
        readable_size = readable_size_format(os.path.getsize(file_path))
        music_file_id = music_file[1].split("-")[-1].split(".")[0] # Split filename and look at very end for song id since scheme has id.mp3
        
        try:
            title_without_mp3 = music_file[1][0:-len(music_file_id)-5]
            artist,title = title_without_mp3.split("-")[0:2]
        except ValueError:
            meta_flagged = True
            if clipboard_provider == "soundcloud":
                url = "http://api.soundcloud.com/tracks/%s.json?client_id=" % music_file_id
                json = simplejson.load(urllib2.urlopen(url))
                title = title_without_mp3
                artist = json["user"]['username'].encode('utf8')
            elif clipboard_provider == "youtube":
                url = "http://gdata.youtube.com/feeds/api/videos/%s?alt=json&v=2" % music_file_id
                json = simplejson.load(urllib2.urlopen(url))
                artist = json["entry"]["author"][0]["name"]["$t"]
                title = title_without_mp3
        
        # Writing id3v2 comment tags with song url for lookup later. Soundcloud autowrites these tags so I don't tag for them.
        if meta_flagged != True:
            subprocess.Popen(["/opt/local/bin/id3v2", "-t", title, "-a", artist, "-c", no_https_url, music_file[1]],stdout=subprocess.PIPE)
            #subprocess.Popen(["/opt/local/bin/xattr","-s","com.apple.metadata:kMDItemWhereFroms",no_https_url,music_file[1]],stdout=subprocess.PIPE)

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