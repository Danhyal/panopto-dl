from __future__ import unicode_literals
import youtube_dl

import urllib.parse
import requests
import json
import os
import argparse
import sys

parser = argparse.ArgumentParser(description='downloads videos from panapto')

parser.add_argument('--cookies', metavar='cookies', type=str,help='path to a netscape cookie file')
parser.add_argument("--url",metavar="url",type=str,help="url to download from")
parser.add_argument("--path",metavar="path",type=str,help="path to download videos to",default=os.getcwd())

args = parser.parse_args()
url=args.url
path=args.path
if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

url_base = "https://{}".format(urllib.parse.urlparse(url).netloc)



def parsecookies(path):
    with open(path) as f:
        cookies=f.readlines()
        for i in cookies:
            if ".ASPXAUTH" in i.split():
                return i.split()[6]



session = requests.session()
session.cookies = requests.utils.cookiejar_from_dict({".ASPXAUTH": parsecookies(args.cookies)})


def singledl(url, dldir=path):
    global url_base
    id = urllib.parse.urlparse(url).query.split("=")[1]
    txt = session.get(url).text
    title = txt[txt.find('<title>') + 7: txt.find('</title>')]
    delivery_info = json.loads(session.get(url_base + "/Panopto/Pages/Viewer/DeliveryInfo.aspx",
                                           **{"data": {"deliveryId": id, "responseType": "json"}}).text)
    creator = delivery_info["Delivery"]["OwnerDisplayName"]
    write_title = "{}".format(title)
    stream = delivery_info["Delivery"]["Streams"]
    dl = stream[0]["StreamUrl"]
    print("Downloading:", write_title)
    ydl_opts = {
        'format': 'bestaudio/best',
        "outtmpl": "{}/{}.%(ext)s".format(dldir, write_title),
        "quiet": True
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([dl])


def jsonadapter(endpoint,base, params=None, post=False, paramtype="params"):
    if params is None:
        params = dict()
    if post:
        request = session.post(base + endpoint, **{paramtype: params})
    else:
        request = session.get(base + endpoint, **{paramtype: params})
    return json.loads(request.text)


def interop(url):
    folders = jsonadapter("/Panopto/Api/Folders",url_base, {"parentId": "null", "folderSet": 1})
    id = urllib.parse.urlparse(url).fragment.split("=")[1]
    for folder in folders:
        if folder["Id"]==id:
            return folder



def folderdl(folder,path=path,parent=""):
    params = {"queryParameters": {"folderID": folder["Id"]}}
    sessions = jsonadapter("/Panopto/Services/Data.svc/GetSessions", url_base,params, True, "json")["d"]["Results"]
    for session in sessions:
        folder_name=str(session["FolderName"]).replace("/","-")
        name=session["SessionName"].replace("/","-")
        dl=session["IosVideoUrl"]
        dldir=r"{}/{}".format(path, "/".join([parent.replace("/","-"),folder_name]))
        os.makedirs(dldir,exist_ok=True)
        if params!="":
            print("Downloading: {}/{}".format(parent,name))
        else:
            print("Downloading: {}".format(name))
        ydl_opts = {
                'format': 'bestaudio/best',
                "outtmpl": "{}/{}.%(ext)s".format(dldir, name),
                "quiet": True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([dl])


    folders = jsonadapter("/Panopto/Api/Folders",url_base, {"parentId": folder["Id"], "folderSet": 1})
    for folder in folders:
        folderdl(folder,parent=folder["Parent"]["Name"])



if "folder" in url:
    folderdl(interop(url),path)
elif "Viewer.aspx" in url:
    singledl(url,path)
else:
    print("invalid url")



