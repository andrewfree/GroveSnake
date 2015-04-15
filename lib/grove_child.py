#!/opt/local/bin/python
# Docs for growl library https://github.com/kfdm/gntp/blob/master/docs/index.rst
# import urllib2, httplib, json # Can get json metadata on youtube videos w/ http://gdata.youtube.com/feeds/api/videos/_7gcIbopIPk?v=2&alt=json
# import soundcloud,client = soundcloud.Client(client_id='*',client_secret='*',username='*',password='*')
from __future__ import print_function
from django.utils.encoding import smart_str, smart_unicode
import gntp.notifier
import subprocess, os, traceback, logging
logging.basicConfig(level=logging.INFO)
import string,urllib2, simplejson, yaml,urllib

# from Tkinter import *
# from tkMessageBox import *

def growlInit():
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

def readable_size_format(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

# Get link from system clipboard and verify it is valid.
def get_link():
    clipboard_process   = subprocess.Popen("pbpaste", stdout=subprocess.PIPE)
    clipboard_link, err = clipboard_process.communicate()

    # Verify link being used is from soundcloud or youtube
    if ("youtube" in clipboard_link):
        clipboard_provider = "youtube"
    elif ("soundcloud" in clipboard_link):
        clipboard_provider = "soundcloud"
    else:
        sendGrowlNotify(growl,"Invalid Link!", callback_url=clipboard_link)
        os._exit(0)
    clipboard_link = clipboard_link.split("&")[0] # Remove extra args from url end
    return (clipboard_link,clipboard_provider)

# def answer(choice):
#     import pdb
#     pdb.set_trace()
#     showerror("Answer", "Sorry, no answer available")

# def callback():
#     if askyesno('Verify', 'Really quit?'):
#         showwarning('Yes', 'Not yet implemented')
#     else:
#         showinfo('No', 'Quit has been cancelled')


def get_metadata(clipboard_link,clipboard_provider,m_id,soundcloud_client_id):
    try:
        artwork = ""
        tags = ""
        if clipboard_provider == "soundcloud":
            url       = "http://api.soundcloud.com/tracks/%s.json?client_id=%s" % (m_id,soundcloud_client_id)
            json      = simplejson.load(urllib2.urlopen(url))
            title     = json["title"].strip().encode('utf8')
            artist    = json["user"]['username'].encode('utf8').strip()
            track_url = json["permalink_url"]
            tags      = json['tag_list']
            # for item in tags.split(' '):
            #     Button(text=item, command=answer(item)).pack(fill=X)
            # mainloop()
            if json.get("artwork_url") != None:
                artwork   = "-".join(json["artwork_url"].split("-")[0:-1])+"-t300x300.jpg"

        elif clipboard_provider == "youtube":
            url       = "http://gdata.youtube.com/feeds/api/videos/%s?alt=json&v=2" % m_id
            json      = simplejson.load(urllib2.urlopen(url))
            artist    = json["entry"]["author"][0]["name"]["$t"].strip()
            title     = json["entry"]["title"]["$t"].strip()
            track_url = json['entry']['link'][0]["href"].split("&")[0]
    except urllib2.HTTPError:
        return False # Wrong id for that provider (so wrong file)

    track_url = track_url.split("//")[-1] # Removes http or https part so can match the url better
    # import pdb
    # pdb.set_trace()
    if track_url in clipboard_link:
        return {"title": title, "artist": artist,"artwork" : artwork, "tags" : tags}
    return False

def main():
    try:
        os.environ["PATH"] = "/opt/local/bin:/usr/bin/:/bin" # The path for youtube-dl and pbpaste. env["SHELL"] = '/bin/zsh'
        project_root_dir = ""
        clipboard_link,clipboard_provider = get_link()

        sendGrowlNotify(growl,"Downloading...", callback_url = clipboard_link)

        project_root_dir = (os.path.join( (os.path.dirname(os.path.realpath(__file__))),'..')) # Project directory, have to go one up out of /lib where the code is run fro.
        with open(os.path.join(project_root_dir,'settings.yaml'), 'r') as f: # load settings, only soundcloud ID for now.
            settings = yaml.load(f)
        os.chdir(os.path.join(project_root_dir,"tracks")) # Change into tracks folder for downloading.

        # Start download, max quality, safe filenames for handling below. The ID is in the filename so you can do metadata lookups for more info if wanted. Rips to mp3, might want to support native download formats, transcoding again and again lowers quality.
        output = subprocess.Popen(["/opt/local/bin/youtube-dl", "-o", "%(title)s|id|%(id)s.%(ext)s","--add-metadata", "-f","22/18/download/http_mp3_128_url","--restrict-filenames","--audio-format","mp3","--audio-quality", "0","-x",clipboard_link], stdout=subprocess.PIPE).communicate()[0] # stderr=subprocess.STDOUT,stdout=subprocess.PIPE

        # Get files in tracks folder.
        file_list = os.listdir(os.getcwd())
        file_list.remove(".DS_Store")
        song_list = []
        artist    = ""
        title     = ""

        for song in file_list:
            if song.split(".")[-1] != "mp3":
                os.remove(song) # Have to do this until they fix bug in youtube-dl
                continue
            else:
                song_id = song.split("|")[-1].split(".")[0]
                data = get_metadata(clipboard_link,clipboard_provider,song_id,settings["soundcloud_client_id"]) # Check if the id of the file found matches up w/ the url that is on the clipboard. Incase there are muitiple files in the output dir.
                if data:
                    title = data['title']
                    artist = data['artist']
                    artwork = data.get("artwork")
                    tags = data.get("tags")
                    song_list.append((os.path.realpath(song),song)) # Fullpath and filename for ease.
                else:
                    sendGrowlNotify(growl,"Dirty tracks directory. Should only have a single song.")
                    print("Skipping, not downloaded track. Messy tracks directory")

        if len(song_list) <= 0:
            sendGrowlNotify(growl,"No items to download.")
            os._exit(0)
        elif len(song_list) > 1:
            sendGrowlNotify(growl,"Shouldn't have muitiple matching tracks.")
            os._exit(0)

        # File path variables & url / size of song / song id
        music_file    = song_list[0]
        file_path     = music_file[0]
        tagged        = True # Youtube-dl should tag by defualt but we will look at the title (dashes in it) to determin if it was correct
        no_https_url  = string.join(clipboard_link.split("/")[2:],"/") # Remove httpS out of url. Something about this url breaks OS X and metadata for finder items.
        readable_size = readable_size_format(os.path.getsize(file_path))
        music_file_id = music_file[1].split("|id|")[-1].split(".")[0] # Split filename and look at very end for song id since scheme has id.mp3

        dashes = title.count("-")
        if dashes == 1:
            artist = title.split("-")[0].strip()
            title  = title.split("-")[1].strip()
            tagged = False # Above tags are more accurate, retag.
        elif dashes > 1:
            tagged = False # Re-write tags with response from api if song has more than one - in the title.
        elif dashes == 0:
            tagged = False # Testing re-writing all tags.

        # Writing id3v2 comment tags with song url for lookup later.
        if tagged != True:
            if len(artwork) >= 1:
                image,message = urllib.urlretrieve(artwork)
                subprocess.Popen(["/opt/local/bin/eyeD3-2.7", "-t",title, "-a", artist, "-c", "%s\n%s" % (no_https_url,tags), "--add-image","%s:FRONT_COVER" % image, music_file[1]],shell=False,stdout=subprocess.PIPE).communicate()
                os.remove(image)
            else:
                subprocess.Popen(["/opt/local/bin/eyeD3-2.7", "-t",title, "-a", artist, "-c", no_https_url, music_file[1]],shell=False,stdout=subprocess.PIPE).communicate()
            # subprocess.Popen(["/opt/local/bin/id3v2", "-t",title, "-a", artist, "-c", no_https_url, music_file[1]],shell=False,stdout=subprocess.PIPE).communicate()
            # subprocess.Popen(["/opt/local/bin/xattr","-s","com.apple.metadata:kMDItemWhereFroms",no_https_url,music_file[1]],stdout=subprocess.PIPE) # For setting the Where From for Spotlight

        os.chdir(os.path.join(project_root_dir,"lib"))
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
    growl = growlInit()
    main()