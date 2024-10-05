import requests
# python3 -m pip install requests
# python3 -m pip install selenium
class GPMLoginAPI(object):
    API_START_PATH = "/api/v3/profiles/start/"
    API_STOP_PATH = "/api/v3/profiles/close/"
    API_CREATE_PATH = "/api/v3/profiles/create"
    API_UPDATE_PROXY_PATH = "/v2/update-proxy"
    API_UPDATE_NOTE_PATH = "/v2/update-note"
    API_PROFILE_LIST_PATH = "/api/v3/profiles"
    API_DELETE_PATH = "/api/v3/profiles/delete/"

    _apiUrl = ''
    def __init__(self, apiUrl: str):
        self._apiUrl = apiUrl

    def GetProfiles(self):
        try:
            url = f"{self._apiUrl}{self.API_PROFILE_LIST_PATH}"
            print(url)
            resp = requests.get(url)
            return resp.json()
        except:
            print('error GetProfiles()')
            return None

    def Create(self, name: str, group : str = 'All', proxy: str = '', isNoiseCanvas: bool = False, fakeFont : bool = True, turnOnWebRTC : bool = True): #, saveType : int = 1):
        """
        Create a new profile
        :param int saveType: 1 => Local, 2 => Cloud
        """
        try:
            # Make api url
            url = f"{self._apiUrl}{self.API_CREATE_PATH}?name={name}&group={group}&proxy={proxy}"
            url += f"&canvas={'on' if isNoiseCanvas else 'off'}"
            url += f"&font={'on' if fakeFont else 'off'}"
            url += f"&webrtc={'on' if turnOnWebRTC else 'off'}"
            # url += f"&save_type={saveType}"
            # Call api
            resp = requests.get(url)
            return resp.json()
        except Exception as e:
            print(e)
            return None

    def UpdateProxy(self, profileId: str, proxy: str = ''):
        try:
            # Make api url
            url = f"{self._apiUrl}{self.API_UPDATE_PROXY_PATH}?id={profileId}&proxy={proxy}"
            # Call api
            resp = requests.get(url)
            return resp.text.lower() == "true"
        except Exception as e:
            print(e)
            return False

    def UpdateNote(self, profileId: str, note: str):
        try:
            # Make api url
            url = f"{self._apiUrl}{self.API_UPDATE_NOTE_PATH}?id={profileId}&note={note}"
            # Call api
            resp = requests.get(url)
            return resp.text.lower() == "true"
        except Exception as e:
            print(e)
            return False

    def Start(self, profileId: str, addinationArgs: str = '', win_pos: str = '', win_size: str = '', win_scale: str = '1'):
        try:
            # Make api url
            url = f"{self._apiUrl}{self.API_START_PATH}{profileId}"
            if(win_scale):
                url += f"?win_scale={win_scale}"
            if(addinationArgs):
                url += f"&addination_args={addinationArgs}"
            if(win_pos):
                url += f"&win_pos={win_pos}"
            if(win_size):
                url += f"&win_size={win_size}"
            # call api
            resp = requests.get(url)
            return resp.json()
        except Exception as e:
            print(e)
            return None

    def Stop(self, profileId: str):
        url = f"{self._apiUrl}{self.API_STOP_PATH}{profileId}"
        requests.get(url)

    def Delete(self, profileId: str, mode: int = 2):
        url = f"{self._apiUrl}{self.API_DELETE_PATH}{profileId}&mode={mode}"
        requests.get(url)