# NASALogin — NASA EarthData Authentication

Manages authentication against NASA EarthData / NSIDC.  Validates credentials
against the EarthData token API, writes a `~/.netrc` entry, and creates a
Mozilla-format cookie file (`~/.grimp_download_cookiejar.txt`) that GDAL uses
to store and reuse session cookies during remote COG access.

> **How GDAL auth works:** After `NASALogin` writes the `.netrc` file and
> creates the empty cookie file, GDAL reads credentials from `.netrc` and
> handles the EarthData OAuth2 redirect automatically on its first data
> request.  GDAL then writes a session cookie to the cookie file so subsequent
> requests do not require another login round-trip.

---

## Construction

```python
import grimpfunc as grimp

myLogin = grimp.NASALogin()
```

**Parameters:**
- `cookieFile` — cookie filename (default: `'.grimp_download_cookiejar.txt'`)
- `cookiePath` — directory for the cookie file (default: `'~'`)

---

## Typical usage

```python
import grimpfunc as grimp
import os

# Point GDAL at the cookie file (do this once per session, before any data access)
env = dict(GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/.grimp_download_cookiejar.txt'),
           GDAL_HTTP_COOKIEJAR =os.path.expanduser('~/.grimp_download_cookiejar.txt'))
os.environ.update(env)

# Display the login widget (or print "Already logged in" if already set up)
myLogin = grimp.NASALogin()
myLogin.view()
```

`view()` checks whether `~/.netrc` has an EarthData entry and the cookie file
exists.  If both are present it prints `Already logged in. Proceed.` and
returns immediately.  Otherwise it displays a Panel widget with username and
password fields.

### First-time login

1. Enter your [NASA EarthData](https://urs.earthdata.nasa.gov) username and
   password in the widget.
2. Click **Enter Credentials**.
3. The code validates the credentials against the EarthData token API, writes
   `~/.netrc`, and creates the empty cookie file.
4. On the first GDAL data access GDAL completes the OAuth2 flow and writes a
   session cookie into the file.

---

## Methods

| Method | Description |
|--------|-------------|
| `view()` | Primary entry point.  Checks existing `.netrc` and cookie file; shows the login Panel widget if setup is incomplete. |
| `check_cookie()` | Validate the cookie jar against `urs.earthdata.nasa.gov/profile`.  Useful for debugging; not called automatically by `view()`. |
| `resetCookie()` | Delete the cookie file — useful when a cookie is corrupted or expired.  Call before `view()` to force re-generation. |

**Less commonly needed:**

| Method | Description |
|--------|-------------|
| `get_cookie()` | Load the cookie jar from the cookie file on disk (no network call). |
| `get_new_cookie()` | Validate credentials via EarthData token API and write an empty cookie jar. |
| `updateNetrc()` | Append the current credentials to `~/.netrc`. |
| `checkNetrc(...)` | Check whether the current credentials are already in `~/.netrc`. |
| `loginStatus()` | Return a Panel markdown pane with the current login status. |
| `error()` | Return a Panel markdown pane with any error message. |

---

## GDAL environment variables

GDAL must know where to find the cookie file.  Set these before any remote
data access:

```python
import os
env = dict(
    GDAL_HTTP_COOKIEFILE=os.path.expanduser('~/.grimp_download_cookiejar.txt'),
    GDAL_HTTP_COOKIEJAR =os.path.expanduser('~/.grimp_download_cookiejar.txt'),
)
os.environ.update(env)
```

For QGIS, set these in `Settings → Options → System → Environment`.

---

## Troubleshooting

**Cookie file exists but data access fails:**
```python
myLogin.resetCookie()   # delete old cookie file
myLogin.view()          # re-run login to create a fresh empty cookie jar
```
GDAL will repopulate the cookie on next data access.

**Force re-entering credentials:**
```python
myLogin.resetCookie()
# Delete or edit ~/.netrc to remove the EarthData entry, then:
myLogin.view()
```

---

## Security note

The `~/.netrc` file stores credentials as plain text (permissions set to
`-rw-------`).  This is a minor security risk.  If concerned, delete the file
after each session and regenerate it with `view()` when needed.
