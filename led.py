import spotipy
import spotipy.util as util


username = "Mahershi Bhavsar"
#scope = "user-read-private"
client_id = "41206ef7e8874ffa88c104eaddecb4e4"
client_secret = "db507280bc9d4571843d500ecf914ed5"
redirect_uri = "http://localhost:8000/callback/"

scope = 'user-read-currently-playing user-modify-playback-state user-read-private user-read-email user-read-playback-state'


token = util.prompt_for_user_token(username=username, scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

if token:

    sp = spotipy.Spotify(auth=token)
    #print(sp.currently_playing())
    print(sp.devices())
    for device in sp.devices()['devices']:
        if device['type'] == "Computer":
            id = device['id']
            print(device['id'])

    sp.pause_playback(id)
else:
    print("Can't get token for", username)

