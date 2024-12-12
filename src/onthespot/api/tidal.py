import base64
import uuid
import time
import json
import requests
from ..otsconfig import config
from ..runtimedata import get_logger, account_pool
from ..utils import make_call, conv_list_format

logger = get_logger("api.deezer")
CLIENT_ID = base64.b64decode("elU0WEhWVmtjMnREUG80dA==").decode("iso-8859-1")
CLIENT_SECRET = base64.b64decode("VkpLaERGcUpQcXZzUFZOQlY2dWtYVEptd2x2YnR0UDd3bE1scmM3MnNlND0=").decode("iso-8859-1")
AUTH = (CLIENT_ID, CLIENT_SECRET)
AUTH_URL = "https://auth.tidal.com/v1/oauth2"
BASE_URL = "https://api.tidal.com/v1"
#BASEV2_URL = "https://openapi.tidal.com/v2"


def tidal_add_account_pt1():
    data = {}

    data["client_id"] = CLIENT_ID
    data["scope"] = "r_usr+w_usr+w_sub"
    response = requests.post(f"{AUTH_URL}/device_authorization", data=data)

    if response.status_code != 200:
        logger.info(f"Device authorization pending: {response.json()}")

    auth_data = response.json()
    device_code = auth_data["deviceCode"]
    verification_url = auth_data["verificationUriComplete"]
    return device_code, verification_url


def tidal_add_account_pt2(device_code):
    # Initially written together only seperated so main ui can receive
    # and display url before starting worker in a thread
    #device_code, verification_url = tidal_add_account_pt1
    logger.info(f"Visit the following url to login: {device_code}")
    while True:
        data = {}
        data["client_id"] = CLIENT_ID
        data["device_code"] = device_code
        data["grant_type"] = "urn:ietf:params:oauth:grant-type:device_code"
        data["scope"] = "r_usr+w_usr+w_sub"
        response = requests.post(f"{AUTH_URL}/token", data=data, auth=AUTH)

        if response.status_code != 200:
            logger.info(f"Token request pending: {response.json()}")
            time.sleep(3)
            continue

        auth_status = response.json()

        if "access_token" in auth_status:
            cfg_copy = config.get('accounts').copy()
            new_user = {
                "uuid": str(uuid.uuid4()),
                "service": "tidal",
                "active": True,
                "login": {
                    "username": auth_status["user"]["username"],
                    "country_code": auth_status["user"]["countryCode"],
                    "access_token": auth_status["access_token"],
                    "refresh_token": auth_status["refresh_token"],
                    "token_expiry": auth_status["expires_in"] + time.time()
                }
            }
            cfg_copy.append(new_user)
            config.set_('accounts', cfg_copy)
            config.update()
            return True


def tidal_login_user(account):
    try:
        if time.time() >= account['login']['token_expiry']:
            data = {
                "client_id": CLIENT_ID,
                "refresh_token": account['login']['refresh_token'] ,
                "grant_type": "refresh_token",
                "scope": "r_usr+w_usr+w_sub",
            }

            response = requests.post(f"{AUTH_URL}/token", data=data, auth=AUTH)

            if response.status_code != 200:
                logger.info(f"Token refresh pending: {response.json()}")

            auth_data = response.json()

            cfg_copy = config.get('accounts').copy()
            for acc in cfg_copy:
                if acc["uuid"] == account['uuid']:
                    acc['login']['access_token'] = auth_data["access_token"]
                    acc['login']['expires_in'] = auth_data["expires_in"] + time.time()
                    account = acc
            config.set_('accounts', cfg_copy)
            config.update()

        account_pool.append({
            "uuid": account['uuid'],
            "username": str(account['login']['username']),
            "service": "tidal",
            "status": "active",
            "account_type": "premium",
            "bitrate": '1411k',
            "login": {
                "access_token": account['login']['access_token'],
                "country_code": account['login']['country_code']
            }
        })
        return True
    except Exception as e:
        logger.error(f"Unknown Exception: {str(e)}")
        account_pool.append({
            "uuid": account['uuid'],
            "username": account['login']['username'],
            "service": "tidal",
            "status": "error",
            "account_type": "N/A",
            "bitrate": 'N/A',
            "login": {
                "access_token": 'N/A',
                "country_code": 'N/A'
            }
        })
        return False


def tidal_get_token(parsing_index):
    accounts = config.get("accounts")
    access_token = accounts[parsing_index]['login']["access_token"]
    country_code = accounts[parsing_index]['login']["country_code"]
    return {"access_token": access_token, "country_code": country_code}


def tidal_get_search_results(token, search_term, content_types):
    params = {}
    params["query"] = search_term
    params["limit"] = config.get('max_search_results')
    params["countryCode"] = token['country_code']

    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    search_results = []

    if 'track' in content_types:
        track_search = make_call(f"{BASE_URL}/search/tracks", params=params, headers=headers, skip_cache=True)
        for track in track_search['items']:
            search_results.append({
                'item_id': track['id'],
                'item_name': track['title'],
                'item_by': track['artist']['name'],
                'item_type': "track",
                'item_service': "tidal",
                'item_url': track['url'],
                'item_thumbnail_url': f'https://resources.tidal.com/images/{(track.get("album", "").get("cover", "") or "").replace("-", "/")}/80x80.jpg'
            })

    if 'album' in content_types:
        album_search = make_call(f"{BASE_URL}/search/albums", params=params, headers=headers, skip_cache=True)
        for album in album_search['items']:
            search_results.append({
                'item_id': album['id'],
                'item_name': album['title'],
                'item_by': album['artist']['name'],
                'item_type': "album",
                'item_service': "tidal",
                'item_url': album['url'],
                'item_thumbnail_url': f'https://resources.tidal.com/images/{(album.get("cover", "") or "").replace("-", "/")}/80x80.jpg'
            })

    if 'artist' in content_types:
        artist_search = make_call(f"{BASE_URL}/search/artists", params=params, headers=headers, skip_cache=True)
        for artist in artist_search['items']:
            search_results.append({
                'item_id': artist['id'],
                'item_name': artist['name'],
                'item_by': artist['name'],
                'item_type': "artist",
                'item_service': "tidal",
                'item_url': artist['url'],
                'item_thumbnail_url': f'https://resources.tidal.com/images/{(artist.get("picture", "") or "").replace("-", "/")}/480x480.jpg'
            })

    if 'playlist' in content_types:
        playlist_search = make_call(f"{BASE_URL}/search/playlists", params=params, headers=headers, skip_cache=True)
        for playlist in playlist_search['items']:
            search_results.append({
                'item_id': playlist['uuid'],
                'item_name': playlist['title'],
                'item_by': playlist.get('creator', '').get('name', ''),
                'item_type': "playlist",
                'item_service': "tidal",
                'item_url': playlist['url'],
                'item_thumbnail_url': f'https://resources.tidal.com/images/{(playlist.get("squareImage", "") or "").replace("-", "/")}/480x480.jpg'
            })

    logger.debug(search_results)
    return search_results


def tidal_get_track_metadata(token, item_id):
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["countryCode"] = token['country_code']

    track_data = make_call(f"{BASE_URL}/tracks/{item_id}", headers=headers, params=params)
    if not track_data:
        return
    album_data = make_call(f"{BASE_URL}/albums/{track_data['album']['id']}", headers=headers, params=params)
    album_track_data = make_call(f"{BASE_URL}/albums/{track_data['album']['id']}/tracks", headers=headers, params=params)

    # Artists
    artists = []
    for artist in track_data.get('artists', ''):
        artists.append(artist.get('name', ''))

    # Track Number
    for i, track in enumerate(album_track_data['items']):
        if track['id'] == int(item_id):
            track_number = i + 1
            break
    if not track_number:
        track_number = track_data.get('trackNumber', '')

    info = {}
    info['item_id'] = str(track_data.get('id', ''))
    info['title'] = track_data.get('title', '')
    info['length'] = str(track_data.get('duration', '')) + '000'
    info['track_number'] = track_number
    info['disc_number'] = track_data.get('volumeNumber', '')
    #info['description'] = track_data.get('version', '')
    info['copyright'] = track_data.get('copyright', '')
    bpm = track_data.get('bpm', '')
    info['bpm'] = bpm if bpm else ''
    info['item_url'] = track_data.get('url', '')
    info['isrc'] = track_data.get('isrc', '')
    info['explicit'] = track_data.get('explicit', '')
    info['album_artists'] = track_data.get('artist', '').get('name', '')
    info['artists'] = conv_list_format(artists)
    info['album_name'] = track_data.get('album', '').get('title', '')
    info['total_tracks'] = album_data.get('numberOfTracks', '')
    info['total_discs'] = album_data.get('numberOfVolumes', '')
    info['release_year'] = album_data.get('releaseDate', '').split("-")[0]
    info['image_url'] = f'https://resources.tidal.com/images/{(track_data.get("album", "").get("cover", "") or "").replace("-", "/")}/1280x1280.jpg'
    info['is_playable'] = track_data.get('streamReady', '')

    return info


def tidal_get_lyrics(token, item_id, item_type, metadata, filepath):
    if config.get('inp_enable_lyrics'):
        headers = {}
        headers["Authorization"] = f"Bearer {token['access_token']}"

        params = {}
        params["countryCode"] = token['country_code']

        lyrics = []

        resp = make_call(f'https://listen.tidal.com/v1/tracks/{item_id}/lyrics/', headers=headers, params=params)
        if not resp:
            return False

        if config.get("embed_branding"):
            lyrics.append('[re:OnTheSpot]')

        for key in metadata.keys():
            value = metadata[key]

            if key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
                lyrics.append(f'[ti:{value}]')

            elif key == 'artists' and config.get("embed_artist"):
                lyrics.append(f'[ar:{value}]')

            elif key in ['album_name', 'album'] and config.get("embed_album"):
                lyrics.append(f'[al:{value}]')

            elif key in ['writers'] and config.get("embed_writers"):
                lyrics.append(f'[au:{value}]')

        lyrics.append(f'[by:{resp.get("lyricsProvider", '').title()}]')

        if config.get("embed_length"):
            l_ms = int(metadata['length'])
            if round((l_ms/1000)/60) < 10:
                digit="0"
            else:
                digit=""
            lyrics.append(f'[length:{digit}{round((l_ms/1000)/60)}:{round((l_ms/1000)%60)}]\n')

        default_length = len(lyrics)

        if resp.get('subtitles', ''):
            lyric_data = resp['subtitles']
        elif resp.get('lyrics', ''):
            lyric_data = resp['lyrics']
        else:
            lyric_data = ''

        for line in lyric_data.split('\n'):
            lyrics.append(line)

        merged_lyrics = '\n'.join(lyrics)

        if lyrics:
            logger.debug(lyrics)
            if len(lyrics) <= default_length:
                return False
            if config.get('use_lrc_file'):
                with open(filepath + '.lrc', 'w', encoding='utf-8') as f:
                    f.write(merged_lyrics)
            if config.get('embed_lyrics'):
                return {"lyrics": merged_lyrics}
            else:
                return True
    else:
        return False


def tidal_get_file_url(token, item_id):
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["audioquality"] = "LOSSLESS"  # LOW, HIGH, LOSSLESS, MQA
    params["playbackmode"] = "STREAM"
    params["assetpresentation"] = "FULL"

    playback_info = make_call(f"{BASE_URL}/tracks/{item_id}/playbackinfopostpaywall", params=params, headers=headers)

    manifest = json.loads(base64.b64decode(playback_info["manifest"]).decode("utf-8"))
    flac_url = manifest["urls"][0]
    return flac_url


def tidal_get_artist_album_ids(token, artist_id):
    logger.info(f"Getting album ids for artist: {artist_id}")
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["countryCode"] = token['country_code']
    params["limit"] = '10000'

    artist_albums = make_call(f"{BASE_URL}/artists/{artist_id}/albums", params=params, headers=headers)

    item_ids = []
    for entry in artist_albums['items']:
        item_ids.append(entry['id'])
    return item_ids


def tidal_get_album_track_ids(token, album_id):
    logger.info(f"Getting tracks from album: {album_id}")
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["countryCode"] = token['country_code']
    params["limit"] = '10000'

    album_track_data = make_call(f"{BASE_URL}/albums/{album_id}/tracks", params=params, headers=headers)

    item_ids = []
    for track in album_track_data['items']:
        item_ids.append(track['id'])
    return item_ids


def tidal_get_playlist_track_ids(token, playlist_id):
    logger.info(f"Getting items in playlist: {playlist_id}")
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["countryCode"] = token['country_code']
    params["limit"] = '10000'

    playlist_track_data = make_call(f"{BASE_URL}/playlists/{playlist_id}/tracks", params=params, headers=headers)

    item_ids = []
    for track in playlist_track_data['items']:
        item_ids.append(track['id'])
    return item_ids

def tidal_get_playlist_data(token, playlist_id):
    logger.info(f"Get playlist data for playlist: {playlist_id}")
    headers = {}
    headers["Authorization"] = f"Bearer {token['access_token']}"

    params = {}
    params["countryCode"] = token['country_code']
    params["limit"] = '10000'

    playlist_data = make_call(f"{BASE_URL}/playlists/{playlist_id}", params=params, headers=headers)
    playlist_name = playlist_data.get('title', '')
    playlist_by = playlist_data.get('creator', {}).get('name', 'Tidal')
    return playlist_name, playlist_by
