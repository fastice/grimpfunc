#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 14:09:26 2021

@author: ian, based on code by Susanne Dickinson, who based it on an ASF
download script.
"""
import os
import base64
from urllib.request import build_opener, install_opener, Request, urlopen
from urllib.request import HTTPHandler, HTTPSHandler, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import MozillaCookieJar
import param
import panel as pn


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

    def __init__(self, cookieFile='.gimp_download_cookiejar.txt',
                 cookiePath='~'):
        '''
        Init, used to add cookie keywords
        Parameters
        ----------
        cookieFile : str, optional
            Cookie filename. The default is '.gimp_download_cookiejar.txt'.
        cookiePath : str, optional
            Cookie path. The default is '~'.

        Returns
        -------
        '''
        super().__init__()
        # setup for password widget
        self.cookie_jar_path = os.path.expanduser(f'{cookiePath}/{cookieFile}')

    @param.depends('enterCredential', watch=True)
    def getCredentials(self):
        '''
        Get user name and password when enterCredential button is pressed

        Returns
        -------
        markdown object with login status.

        '''
        # We don't have a valid cookie, prompt user for creds
        # Keep trying 'till user gets the right U:P
        count = 0
        while self.check_cookie() is False and count < 10:
            self.get_new_cookie()
            count += 1
        self.loginStatus()

    def resetCookie(self):
        ''' Remove cooking file - for debugging'''
        if os.path.exists(self.cookie_jar_path):
            os.remove(self.cookie_jar_path)

    def check_cookie(self, file_check='https://urs.earthdata.nasa.gov/profile'):
        '''
        Validate cookie before we begin
        Returns
        -------
        bool
            Whether cookie valid.

        '''
        if self.cookie_jar is None:
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
                return False
            # Save cookiejar
            self.cookie_jar.save(self.cookie_jar_path)
            # For security make user accessible only
            os.chmod(self.cookie_jar_path, 0o600)
        except HTTPError:
            # If we get this error, again, it likely means the user has not
            # agreed to current EULA
            print("\nIMPORTANT: ")
            print("User appears to lack permissions to download data from "
                  "the Earthdata Datapool.")
            print("\n\nNew users: you must first have an account at "
                  "Earthdata https://urs.earthdata.nasa.gov")
            exit(-1)
        # These return codes indicate the USER has not been approved to
        # download the data
        if resp_code in (300, 301, 302, 303):
            print(f"Redirect ({resp_code}) occured, invalid cookie value!")
            return False
        # These are successes!
        if resp_code in (200, 307):
            return True
        return False

    def get_new_cookie(self):
        ''' Create the new coookie.
         Returns
        -------
        bool
            Whether new cookie successful.
        '''
        # Start by prompting user to input their credentials
        new_username = self.username
        new_password = self.password
        user_pass = base64.b64encode(
            bytes(new_username+":"+new_password, "utf-8"))
        user_pass = user_pass.decode("utf-8")
        # Authenticate against URS, grab all the cookies
        self.cookie_jar = MozillaCookieJar()
        opener = build_opener(HTTPCookieProcessor(self.cookie_jar),
                              HTTPHandler(), HTTPSHandler(**self.context))
        request = Request('https://daacdata.apps.nsidc.org/pub/DATASETS/',
                          headers={"Authorization": f"Basic {user_pass}"})
        # Watch out cookie rejection!
        try:
            response = opener.open(request)
        except HTTPError as e:
            if e.code == 401:
                return False
            else:
                # If an error happens here, the user most likely has not
                # confirmed EULA.
                print("\nIMPORTANT: There was an error obtaining a download "
                      "cookie!")
                exit(-1)
        except URLError:
            print("\nIMPORTANT: There was a problem communicating with URS, "
                  "unable to obtain cookie. ")
            print("Try cookie generation later.")
            exit(-1)
        # Did we get a cookie?
        if self.check_cookie_is_logged_in(self.cookie_jar):
            # COOKIE SUCCESS!
            self.cookie_jar.save(self.cookie_jar_path)
            return True
        # if we aren't successful generating the cookie, nothing will work.
        # Stop here!
        print("WARNING: Could not generate new cookie! Cannot proceed. "
              "Please try Username and Password again.")
        print(f"Response was {response.getcode()}.")
        exit(-1)

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

    def get_cookie(self):
        '''
        Get a cookies
        Returns
        -------
        bool
            Success.
        '''
        if os.path.isfile(self.cookie_jar_path):
            self.cookie_jar = MozillaCookieJar()
            self.cookie_jar.load(self.cookie_jar_path)
        # make sure cookie is still valid
        if self.check_cookie():
            return True
        else:
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
        3. Click the 'Next' button to continue
        4. Cookie will be maintained for some period for future downloads
        ''', width=550)
        # Get cookie on first try, but not each time view is called
        return text

    def loginStatus(self):
        '''Check login status and print an appropriate message '''
        if self.check_cookie_is_logged_in(self.cookie_jar):
            msg = '### Status: Logged in\n####Continue'
            style = {'color': 'blue'}
        else:
            msg = '### Status: Not logged in\nEnter credentials'
            style = {'color': 'red'}
        # pn.pane.Markdown(msg, style=style)
        return pn.pane.Markdown(msg, style=style)

    def view(self):
        ''' Execute login procedure. First check if logged in. If so, return.
        Else start panel with login window '''
        # First call try to get cookie
        if self.first:
            self.get_cookie()
            self.first = False
        # If logged in already, print message and return
        if self.check_cookie_is_logged_in(self.cookie_jar):
            print('Already logged in. Proceed.')
            return
        # Not logged in so start login panel
        widgetParams = \
            {'password': pn.widgets.PasswordInput,
             'enterCredential': pn.widgets.Button(name='Enter Credentials')}
        widgets = pn.panel(
            self.param, widgets=widgetParams, name='Earth Data Login')
        return pn.Row(self.loginInstructions, widgets, self.loginStatus)
