# Listing the KUDU apps in winget (Windows' own package manager).
#
# winget/apps.json holds each app's details (name, short name, licence, description, installer). This script:
#   check [--apps ROOT]  checks those details and the entries made from them (with --apps, also against the apps'
#                        own installers, from a folder holding their checkouts side by side)
#   plan OUT             reads each app's latest release on GitHub, writes its winget entry under OUT/<APP>/<version>,
#                        and lists in OUT/plan.json what should be sent: an app marked "send" whose version isn't in
#                        winget yet and has no pull request waiting (or turned down) at Microsoft
#
# The daily workflow (.github/workflows/winget.yml) runs "check" and "plan", then sends what plan.json lists with
# Microsoft's wingetcreate. Python's standard library only.

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APPS_FILE = os.path.join(HERE, '..', 'winget', 'apps.json')
MANIFEST_VERSION = '1.10.0'  # the layout of the entries (one Microsoft's checks accept)
WINGET_REPO = 'microsoft/winget-pkgs'
LOCALE = 'en-US'


def load_apps():
    """The details in winget/apps.json."""
    with open(APPS_FILE, encoding='utf-8') as f:
        return json.load(f)


def identifier(data, app):
    """The app's full name in winget, like "AzeemBukhari.KUDUCOPY"."""
    return data['publisherId'] + '.' + app['name']


# ------------------------------------------------------------------ writing the entries (YAML)

RESERVED = ('true', 'false', 'yes', 'no', 'null', 'on', 'off', '~')


def scalar(value):
    """A value as YAML: plain when that reads back as the same text, else in single quotes (a ' written twice).
    Versions stay quoted, so "1.10" is never read as a number."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    text = str(value)
    plain = (text and text[0] not in '-?:,[]{}#&*!|>\'"%@` ' and text[-1] not in ': '
             and ': ' not in text and ' #' not in text and text.lower() not in RESERVED
             and not re.match(r'^[0-9.+-]+$', text) and '\n' not in text)
    return text if plain else "'" + text.replace("'", "''") + "'"


def yaml(fields, indent=''):
    """A list of (key, value) pairs as YAML: values are text, lists of text, lists of such pairs, or a dict (a nested
    set of pairs)."""
    lines = []
    for key, value in fields:
        if value is None:
            continue
        if isinstance(value, dict):
            lines.append(f'{indent}{key}:')
            lines.append(yaml(list(value.items()), indent + '  '))
        elif isinstance(value, list):
            lines.append(f'{indent}{key}:')
            for item in value:
                if isinstance(item, list):  # a list of pairs: the first after "- ", the rest under it
                    inner = yaml(item, indent + '  ').split('\n')
                    lines.append(f'{indent}- ' + inner[0][len(indent) + 2:])
                    lines.extend(inner[1:])
                else:
                    lines.append(f'{indent}- {scalar(item)}')
        else:
            lines.append(f'{indent}{key}: {scalar(value)}')
    return '\n'.join(lines)


def manifests(data, app, release):
    """The three files of an app's winget entry for a release: {file name: text}.
    release: {"version", "url", "sha256", "date" (yyyy-mm-dd)}."""
    pid = identifier(data, app)
    version = release['version']
    owner, repo = data['owner'], app['repo']
    head = '# Made by kudu-common/tools/winget.py\n'

    def schema(kind):
        return f'# yaml-language-server: $schema=https://aka.ms/winget-manifest.{kind}.{MANIFEST_VERSION}.schema.json\n\n'

    version_file = yaml([
        ('PackageIdentifier', pid), ('PackageVersion', version), ('DefaultLocale', LOCALE),
        ('ManifestType', 'version'), ('ManifestVersion', MANIFEST_VERSION)])

    # Every app installs for the current user without administrator rights; KUDUNMAP can also install for all users
    # (Inno Setup's /CURRENTUSER and /ALLUSERS), which scheduled scans that need administrator rights ask for.
    scopes = app.get('scopes', ['user'])
    installers = []
    for scope in scopes:
        entry = [('Architecture', app['architecture'])]
        if len(scopes) > 1:
            entry.append(('Scope', scope))
            entry.append(('InstallerSwitches', {'Custom': '/CURRENTUSER' if scope == 'user' else '/ALLUSERS'}))
            if scope == 'machine':
                entry.append(('ElevationRequirement', 'elevatesSelf'))
        entry += [('InstallerUrl', release['url']), ('InstallerSha256', release['sha256'].upper()),
                  ('ProductCode', app['productCode'])]
        installers.append(entry)
    installer_fields = [('PackageIdentifier', pid), ('PackageVersion', version)]
    if app.get('minimumOs'):
        installer_fields.append(('MinimumOSVersion', app['minimumOs']))
    installer_fields += [('InstallerType', 'inno')]
    if len(scopes) == 1:
        installer_fields.append(('Scope', scopes[0]))
    installer_fields += [
        ('InstallModes', ['interactive', 'silent', 'silentWithProgress']),
        ('UpgradeBehavior', 'install'), ('ReleaseDate', release['date']),
        ('Installers', installers), ('ManifestType', 'installer'), ('ManifestVersion', MANIFEST_VERSION)]

    license_url = f'https://github.com/{owner}/{repo}/blob/main/LICENSE'
    locale_file = yaml([
        ('PackageIdentifier', pid), ('PackageVersion', version), ('PackageLocale', LOCALE),
        ('Publisher', data['publisher']), ('PublisherUrl', f'https://github.com/{owner}'),
        ('PublisherSupportUrl', f'https://github.com/{owner}/{repo}/issues'), ('Author', data['publisher']),
        ('PackageName', app['name']), ('PackageUrl', f'https://github.com/{owner}/{repo}'),
        ('License', app['license']), ('LicenseUrl', license_url),
        ('ShortDescription', app['short']), ('Description', app['description']),
        ('Moniker', app['name'].lower()), ('Tags', app['tags']),
        ('ReleaseNotesUrl', f'https://github.com/{owner}/{repo}/releases/tag/v{version}'),
        ('ManifestType', 'defaultLocale'), ('ManifestVersion', MANIFEST_VERSION)])

    return {
        f'{pid}.yaml': head + schema('version') + version_file + '\n',
        f'{pid}.installer.yaml': head + schema('installer') + yaml(installer_fields) + '\n',
        f'{pid}.locale.{LOCALE}.yaml': head + schema('defaultLocale') + locale_file + '\n',
    }


# ------------------------------------------------------------------ checks

def problems(data, release_for=None, apps_root=None):
    """What's wrong with winget/apps.json and the entries made from it (an empty list when all is well).
    release_for(app) gives a release to build each entry from; apps_root is a folder holding the apps' checkouts."""
    found = []
    names, monikers = set(), set()
    if not re.match(r'^[A-Za-z0-9]{2,32}$', data.get('publisherId', '')):
        found.append('publisherId must be letters and digits')
    for app in data['apps']:
        n = app.get('name', '?')
        say = lambda text: found.append(f'{n}: {text}')
        missing = [key for key in ('name', 'repo', 'asset', 'productCode', 'architecture', 'license', 'short',
                                   'description', 'tags') if not app.get(key)]
        if missing:
            say('missing ' + ', '.join(missing))
            continue
        if n in names:
            say('appears twice')
        names.add(n)
        moniker = n.lower()
        if moniker in monikers:
            say('short name used twice')
        monikers.add(moniker)
        if not re.match(r'^[A-Z]+$', n):
            say('the name should be capital letters only')
        if '{version}' not in app['asset'] or not app['asset'].lower().endswith('.exe'):
            say('the installer name needs {version} and must end in .exe')
        if not re.match(r'^\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}_is1$', app['productCode']):
            say('productCode should be Inno Setup\'s "{GUID}_is1"')
        if app['architecture'] not in ('neutral', 'x64', 'x86', 'arm64'):
            say('unknown architecture')
        for scope in app.get('scopes', ['user']):
            if scope not in ('user', 'machine'):
                say(f'unknown scope "{scope}"')
        if not 3 <= len(app['short']) <= 256:
            say('the short description must be 3 to 256 characters')
        if not 3 <= len(app['description']) <= 10000:
            say('the description must be 3 to 10,000 characters')
        if not 3 <= len(app['license']) <= 512:
            say('the licence must be 3 to 512 characters')
        if len(app['tags']) > 16:
            say('at most 16 tags')
        for tag in app['tags']:
            if not re.match(r'^[a-z0-9][a-z0-9+.#-]{0,39}$', tag):
                say(f'tag "{tag}" must be lower case, no spaces, up to 40 characters')
        if not isinstance(app.get('send', False), bool):
            say('"send" must be true or false')

        if release_for is not None:
            files = manifests(data, app, release_for(app))
            if len(files) != 3:
                say('an entry has three files')
            for name, text in files.items():
                for line in text.split('\n'):
                    if len(line) > 0 and ('\t' in line or line != line.rstrip()):
                        say(f'{name}: a line with a tab or trailing spaces')
                if f"ManifestVersion: '{MANIFEST_VERSION}'" not in text:
                    say(f'{name}: no ManifestVersion')
            installer = files[identifier(data, app) + '.installer.yaml']
            if not re.search(r'InstallerSha256: [0-9A-F]{64}\n', installer):
                say('the installer\'s SHA-256 should be 64 hex digits')

        if apps_root:
            folder = os.path.join(apps_root, app['repo'])
            if not os.path.isdir(folder):
                continue
            iss = [os.path.join(folder, 'installer', f) for f in os.listdir(os.path.join(folder, 'installer'))
                   if f.lower().endswith('.iss')] if os.path.isdir(os.path.join(folder, 'installer')) else []
            if not iss:
                say('no installer script (.iss) found')
                continue
            text = open(iss[0], encoding='utf-8-sig').read()
            m = re.search(r'^AppId=\{(\{[0-9A-Fa-f-]{36}\})', text, re.M)
            if not m or (m.group(1) + '_is1').upper() != app['productCode'].upper():
                say('productCode differs from the installer\'s AppId')
            wide = re.search(r'^PrivilegesRequiredOverridesAllowed=.*commandline', text, re.M | re.I)
            if 'machine' in app.get('scopes', []) and not wide:
                say('"machine" needs PrivilegesRequiredOverridesAllowed=commandline in the installer')
            x64 = re.search(r'^ArchitecturesInstallIn64BitMode=', text, re.M | re.I)
            if bool(x64) != (app['architecture'] == 'x64'):
                say('architecture should be x64 exactly when the installer installs in 64-bit mode')
            if not os.path.isfile(os.path.join(folder, 'LICENSE')):
                say('no LICENSE file')
    return found


def sample_release(app):
    """A made-up release, to check the entries without the internet."""
    return {'version': '1.2.3', 'url': 'https://github.com/x/y/releases/download/v1.2.3/' + app['asset'].replace(
        '{version}', '1.2.3'), 'sha256': 'ab' * 32, 'date': '2026-11-24'}


# ------------------------------------------------------------------ GitHub

def github(path, token=None):
    """GET from GitHub's API; None when it isn't there (404)."""
    request = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'kudu-common-winget'})
    if token:
        request.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def latest_release(data, app, token):
    """The app's latest release as {"version", "url", "sha256", "date"}, or None when it has no versioned installer."""
    r = github(f'/repos/{data["owner"]}/{app["repo"]}/releases/latest', token)
    if not r or r.get('draft') or r.get('prerelease'):
        return None
    version = r['tag_name'].lstrip('v')
    wanted = app['asset'].replace('{version}', version)
    for asset in r.get('assets', []):
        if asset['name'] == wanted:
            digest = asset.get('digest') or ''
            if not digest.startswith('sha256:'):
                return None
            return {'version': version, 'url': asset['browser_download_url'], 'sha256': digest[7:],
                    'date': (r.get('published_at') or '')[:10]}
    return None


def winget_versions(data, app, token):
    """The versions of the app winget has, or None when winget doesn't have the app at all."""
    pid = identifier(data, app)
    path = f'manifests/{pid[0].lower()}/{data["publisherId"]}/{app["name"]}'
    listing = github(f'/repos/{WINGET_REPO}/contents/{urllib.parse.quote(path)}', token)
    return None if listing is None else [item.get('name') for item in listing if item.get('type') == 'dir']


def pull_requests(data, app, version, token):
    """Pull requests at Microsoft for this version: [(state, merged)]."""
    pid = identifier(data, app)
    q = f'repo:{WINGET_REPO} is:pr in:title "{pid}" "{version}"'
    found = github('/search/issues?q=' + urllib.parse.quote(q), token) or {}
    result = []
    for item in found.get('items', []):
        title = item.get('title', '')
        if pid in title and re.search(r'(^|\s)' + re.escape(version) + r'(\s|$)', title):
            merged = bool((item.get('pull_request') or {}).get('merged_at'))
            result.append((item.get('state'), merged))
    return result


def plan(out):
    """Writes each app's entry for its latest release under out/, and out/plan.json listing what to send."""
    data = load_apps()
    token = os.environ.get('GITHUB_TOKEN') or None
    os.makedirs(out, exist_ok=True)
    rows = []
    for app in data['apps']:
        pid = identifier(data, app)
        row = {'app': app['name'], 'id': pid, 'send': False}
        release = latest_release(data, app, token)
        if release is None:
            row['note'] = 'no released installer with its SHA-256 found'
            rows.append(row)
            continue
        row['version'] = release['version']
        folder = os.path.join(out, app['name'], release['version'])
        os.makedirs(folder, exist_ok=True)
        for name, text in manifests(data, app, release).items():
            with open(os.path.join(folder, name), 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
        row['folder'] = folder
        versions = winget_versions(data, app, token)
        new = versions is None
        if not new and release['version'] in versions:
            row['note'] = 'already in winget'
        else:
            prs = pull_requests(data, app, release['version'], token)
            if any(state == 'open' for state, _ in prs):
                row['note'] = 'a pull request is waiting at Microsoft'
            elif any(state == 'closed' and not merged for state, merged in prs):
                row['note'] = 'a pull request for this version was closed without merging: look at it first'
            elif any(merged for _, merged in prs):
                row['note'] = 'merged; winget will have it soon'
            elif not app.get('send'):
                row['note'] = 'not marked "send" yet (entry made only to look at)'
            else:
                row['send'] = True
                row['title'] = f'{"New package" if new else "New version"}: {pid} version {release["version"]}'
                row['note'] = 'to send'
        rows.append(row)
    with open(os.path.join(out, 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)
    for row in rows:
        print(f'{row["app"]:<11} {row.get("version", "-"):<9} {row["note"]}')
    return rows


def main(argv):
    if len(argv) >= 1 and argv[0] == 'check':
        root = argv[argv.index('--apps') + 1] if '--apps' in argv else None
        data = load_apps()
        found = problems(data, sample_release, root)
        for p in found:
            print('problem:', p)
        print(f'{len(data["apps"])} apps, ' + ('all fine' if not found else f'{len(found)} problems'))
        return 1 if found else 0
    if len(argv) == 2 and argv[0] == 'plan':
        plan(argv[1])
        return 0
    print('usage: winget.py check [--apps ROOT] | plan OUT')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
