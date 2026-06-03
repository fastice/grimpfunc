#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 14:09:26 2021

@author: ian, based on code by Susanne Dickinson, who based it on an ASF
download script.
"""
import os
from urllib.request import build_opener, install_opener, Request, urlopen
from urllib.request import HTTPHandler, HTTPSHandler, HTTPCookieProcessor
from urllib.error import HTTPError
from http.cookiejar import MozillaCookieJar
import param
import panel as pn
import time

site = 'urs.earthdata.nasa.gov'

class NASALogin(param.Parameterized):
    ''' Creates a login panel that prompts for NSIDC (earthdata) credentials
    and produces a cookie file for current and future access
    cookieFile = '''
    username = param.String()
    password = param.String()
    # Param for enter credentianl button
    enterCredential = \
        param.Action(lambda x: x.param.trigger('enterCredential'))
    # Local stash of cookies so we don't always have to ask
    status = False
    # For SSL
    context = {}
    first = True
    cookie_jar_path = None
    cookie_jar = None
    netrcFile = os.path.expanduser('~/.netrc')

    def __init__(self, cookieFile='.grimp_download_cookiejar.txt',
                 cookiePath='~',
                 requestPath='https://daacdata.apps.nsidc.org/pub/DATASETS/'):
        '''
        Init, used to add cookie keywords
        Parameters
        ----------
        cookieFile : str, optional
            Cookie filename. The default is '.grimp_download_cookiejar.txt'.
        cookiePath : str, optional
            Cookie path. The default is '~'.

        Returns
        -------
        '''
        super().__init__()
        self.requestPath = requestPath
        # setup for password widget
        self.cookie_jar_path = os.path.expanduser(f'{cookiePath}/{cookieFile}')
        # print(self.cookie_jar_path)
        self.msg = ''
        self.errorMsg = '                            '
        self.updateStatusMessage()

    @param.depends('enterCredential', watch=True)
    def getCredentials(self, gui=True, updateNetRC=True):
        '''
        Get user name and password when enterCredential button is pressed

        Returns
        -------
        markdown object with login status.

        '''
        # Validate credentials and prepare cookie file; retry a few times
        count = 0
        success = False
        while not success and count < 3:
            success = self.get_new_cookie()
            count += 1
            if not success:
                time.sleep(0.1)
        # Write .netrc if credentials validated and cookie file was created
        if success and updateNetRC:
            self.updateNetrc()  # Create/update .netrc file
        # Update messages if gui
        if gui:
            self.updateStatusMessage()
            self.error()

    def resetCookie(self):
        ''' Remove cooking file - for debugging'''
        if os.path.exists(self.cookie_jar_path):
            os.remove(self.cookie_jar_path)

    def check_cookie(self,
                     file_check='https://urs.earthdata.nasa.gov/profile'):
        '''
        Validate cookie before we begin
        Returns
        -------
        bool
            Whether cookie valid.

        '''
        if self.cookie_jar is None:
            self.errMsg = "No cookie jar"
            return False
        # File we know is valid, used to validate cookie
        # Apply custom Redirect Handler
        opener = build_opener(HTTPCookieProcessor(self.cookie_jar),
                              HTTPHandler(), HTTPSHandler(**self.context))
        install_opener(opener)
        # Attempt a HEAD request
        request = Request(file_check)
        request.get_method = lambda: 'HEAD'
        try:
            response = urlopen(request, timeout=30)
            resp_code = response.getcode()
            # Make sure we're logged in
            if not self.check_cookie_is_logged_in(self.cookie_jar):
                self.errorMsg = 'Not logged in, try again'
                return False
            # Save cookiejar
            self.cookie_jar.save(self.cookie_jar_path)
            # For security make user accessible only
            os.chmod(self.cookie_jar_path, 0o600)
        except HTTPError:
            # If we get this error, again, it likely means the user has not
            # agreed to current EULA
            self.errorMsg = "\nIMPORTANT: User appears to lack permissions" \
                            " to download data from the Earthdata Datapool." \
                            "\n\nNew users must have an account at " \
                            "Earthdata https://urs.earthdata.nasa.gov"
            return False
        # These return codes indicate the USER has not been approved to
        # download the data
        if resp_code in (300, 301, 302, 303):
            self.errorMsg = \
                f"Redirect ({resp_code}) occured, invalid cookie value!"
            return False
        # These are successes!
        if resp_code in (200, 307):
            self.errorMsg = ''
            return True
        return False

    def get_new_cookie(self):
        '''Validate EarthData credentials and prepare the cookie file for GDAL.

        EarthData now uses OAuth2 for data-endpoint authentication, which
        means the old Basic-Auth-to-daacdata approach no longer works (the
        server redirects to the OAuth page and Python drops the Authorization
        header on the cross-host redirect).

        This method instead validates credentials against the EarthData token
        API, which accepts Basic Auth directly.  On success it writes an empty
        MozillaCookieJar to ``cookie_jar_path``; GDAL reads credentials from
        ``~/.netrc`` and populates the cookie file with a session cookie on
        its first data access.

        Returns
        -------
        bool
            True if credentials are valid and the cookie file was written.
        '''
        try:
            import requests as _rq
        except ImportError:
            self.errorMsg = \
                "Error: 'requests' library required — pip install requests"
            return False

        new_username = self.username
        new_password = self.password

        if not new_username or not new_password:
            self.errorMsg = "Error: Username and password required."
            return False

        # EarthData token API accepts Basic Auth — use it to validate creds
        token_url = 'https://urs.earthdata.nasa.gov/api/users/tokens'
        try:
            r = _rq.get(token_url, auth=(new_username, new_password),
                        timeout=30)
        except _rq.exceptions.RequestException as e:
            self.errorMsg = f"Error: Cannot reach EarthData: {e}"
            return False

        if r.status_code == 401:
            self.errorMsg = \
                "Error: Invalid EarthData username or password. " \
                "Check your account at https://urs.earthdata.nasa.gov"
            return False
        if r.status_code not in (200, 201):
            self.errorMsg = \
                f"Error: EarthData returned unexpected status {r.status_code}"
            return False

        # Credentials valid — write an empty cookie jar for GDAL to populate
        self.cookie_jar = MozillaCookieJar()
        try:
            self.cookie_jar.save(self.cookie_jar_path)
            os.chmod(self.cookie_jar_path, 0o600)
        except Exception as e:
            self.errorMsg = f"Error saving cookie file: {e}"
            return False

        self.errorMsg = ''
        return True

    def check_cookie_is_logged_in(self, cj):
        '''
        Make sure we're logged into URS
        Parameters
        ----------
        cj : cookie jar object
            The cookie jar.
        Returns
        -------
        bool
            Logged in status.

        '''
        if cj is None:
            return False
        for cookie in cj:
            if cookie.name == 'urs_user_already_logged':
                # Only get this cookie if we logged in successfully!
                return True
        return False

    def get_cookie(self):
        '''
        Load the cookie jar from the cookie file on disk.

        Validation against EarthData is intentionally skipped here — the
        cookie file may be empty (GDAL has not yet made its first authenticated
        request) and a network round-trip is not needed just to check file
        presence.  Call ``check_cookie()`` explicitly if you need to validate.

        Returns
        -------
        bool
            True if the cookie file exists and was loaded.
        '''
        if os.path.isfile(self.cookie_jar_path):
            self.cookie_jar = MozillaCookieJar()
            try:
                self.cookie_jar.load(self.cookie_jar_path)
            except Exception:
                pass  # Empty or malformed file is fine — GDAL will populate it
            return True
        return False

    def loginInstructions(self):
        '''
        Populate and return mark down with instructions
        Returns
        -------
        text : panel markdown
            Instructions.
        '''
        # view depending on widget values, doesn't really matter here...
        text = pn.pane.Markdown('''
        #### Instructions:
        1. If prompted, Enter your [NASA EarthData Login]
            (https://urs.earthdata.nasa.gov)
        2. Click the 'Enter Credentials' button, which will not be stored,
            saved or logged anywhere
        3. This program will update your ~/.netrc file with plain text
        user name and passwd (user r/w only permissions). This represents a
        minor security risk. If concerned it can be removed later when not
        using QGIS or other application.
        4. Cookie will be maintained for some period for future downloads
        ''', width=550)
        # Get cookie on first try, but not each time view is called
        return text

    def updateStatusMessage(self):
        has_cookie = os.path.exists(self.cookie_jar_path)
        has_netrc = os.path.exists(self.netrcFile)
        if has_cookie and has_netrc:
            self.msg = '### Status: Logged in\n####Continue'
            self.style = {'color': 'blue'}
        elif has_netrc:
            self.msg = '### Status: Credentials saved — call view() to finish'
            self.style = {'color': 'orange'}
        else:
            self.msg = '### Status: Not logged in\nEnter credentials'
            self.style = {'color': 'red'}

    def loginStatus(self):
        '''Check login status and print an appropriate message '''
        # self.updateStatusMessage()
        return pn.pane.Markdown(self.msg, style=self.style)

    def error(self):
        '''Check login status and print an appropriate message '''
        # self.updateStatusMessage()
        return pn.pane.Markdown(self.errorMsg, style={'color': 'red'},
                                width=250)

    def checkNetrc(self, password=None, username=None, setCredential=False):
        # Start with blank or existing lines
        if os.path.exists(self.netrcFile):
            with open(self.netrcFile, 'r') as fpIn:
                for line in fpIn:
                    if site in line and self.username in line:
                        # Case where not known
                        if password is None and  username is None:
                            # Set param values
                            if setCredential: 
                                parts = line.split()
                                credential = dict(
                                    zip([parts[x] for x in [0, 2, 4]],
                                        [parts[x] for x in [1, 3, 5]]))
                                print('Getting login from ~/.netrc')
                                self.setCredential(credential)
                            return True
                        elif password in line and username in line:
                            return True
        return False
    
    def setCredential(self, credential):
        '''
        Set params with user name and password rather than use login panel
        '''
        self.param.update(username=credential['login'])
        self.param.update(password=credential['password'])
        
    def updateNetrc(self):
        ''' Update or create new ~/.netrc to include user name and passwd '''
        if len(self.username) == 0 or len(self.password) == 0:
            return  # Don't attempt for empty user/password
        # Check
        if self.checkNetrc(password=self.password, username=self.username):
            return # Password in files so return
        #
        rcLine = f'machine {site} login {self.username} ' \
            f'password {self.password}'
        # read existing if exists
        if os.path.exists(self.netrcFile):
            with open(self.netrcFile, 'r') as fpIn:
                lines = fpIn.readlines()
        else:
            lines = []
        # append new line
        lines.append(rcLine)
        # Write/overwrite netrc file with update
        with open(self.netrcFile, 'w') as fpOut:
            fpOut.writelines(lines)
        # Ensure file user access only    
        os.chmod(self.netrcFile, 0o600)  
        return    
            
    def view(self):
        ''' Execute login procedure. First check if logged in. If so, return.
        Else start panel with login window '''
        # First call: load cookie jar from disk if present
        if self.first:
            self.get_cookie()
            self.first = False
        # If .netrc has EarthData credentials, set self.username/password
        # and create the cookie file if it is missing (GDAL needs the path
        # to exist before it can write its own session cookie on first access)
        if self.checkNetrc(setCredential=True):
            if not os.path.exists(self.cookie_jar_path):
                self.cookie_jar = MozillaCookieJar()
                self.cookie_jar.save(self.cookie_jar_path)
                os.chmod(self.cookie_jar_path, 0o600)
        # If both .netrc entry and cookie file exist, already set up — done
        if os.path.exists(self.cookie_jar_path) and self.checkNetrc():
            print('Already logged in. Proceed.')
            return
        # Not logged in so start login panel
        widgetParams = \
            {'password': pn.widgets.PasswordInput,
             'enterCredential': pn.widgets.Button(name='Enter Credentials')}
        widgets = pn.panel(
            self.param, widgets=widgetParams, name='Earth Data Login')
        return pn.Row(self.loginInstructions, widgets,
                      pn.Column(self.loginStatus, self.error))
