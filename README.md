# kudu-common

Shared code for the KUDU Windows apps: [KUDUNMAP](https://github.com/azeembukhariprivate/kudunmap),
[KUDUCOPY](https://github.com/azeembukhariprivate/kuducopy), [KUDURESCUE](https://github.com/azeembukhariprivate/kudurescue),
[KUDUSYNC](https://github.com/azeembukhariprivate/kudusync) and [KUDUTREE](https://github.com/azeembukhariprivate/kudutree).

The same building blocks used to be copied into each app by hand, so a fix made in one app didn't always reach the
others. Now they live here, and a script copies them into every app.

**You don't need this repository to build an app.** Each app's repository holds its own copy of the shared files,
so downloading or cloning an app is all you need.

## What's shared

| File | What it does |
|---|---|
| `Controls/Ui.cs` | Builds the look in code: buttons (with names for screen readers), cards, chips, text styles |
| `Controls/Glyph.cs` | The line icons |
| `Core/ThemeManager.cs` | Loads the light and dark themes and follows Windows' setting |
| `Core/AppInfo.cs` | Version, links, opening files, folders and web pages (with normal rights when the app runs as administrator) |
| `Core/Admin.cs` | Checks for, and restarts with, administrator rights |
| `Core/Unelevated.cs` | Opens things through File Explorer's desktop with normal rights |
| `Core/UpdateChecker.cs` | Asks GitHub for the latest release |
| `Core/Args.cs` | Quotes and splits command-line arguments |
| `Views/Dialogs.cs` | Message boxes, file and folder pickers |
| `Views/Screenshots.cs` | The self-test's pictures of every window |

Each app keeps for itself:
- `Core/AppDetails.cs`: its name and repository (plus anything only it needs, such as KUDUNMAP's Nmap links).
- Its themes (`Themes/*.xaml`), which hold its own colours.
- Its logo.

The shared files use the namespace `KuduApp`; the copy in each app gets the app's own (for example `Kudutree.Core`).

## Changing shared code

1. Change the file in `shared/` here, commit and push. The **Check** workflow copies the change into every app, then
   builds each one and runs its tests, so a change that breaks an app shows up here first.
2. Copy it into the apps (with the apps cloned next to this folder):

   ```
   python sync.py ../kudunmap ../kuducopy ../kudurescue ../kudusync ../kudutree
   ```

3. Commit and push each app. Its build tests it again on Windows and, if the version number went up, releases it.

`sync.py` also writes a `.kudu-common` file in each app with the commit it copied and the list of shared files;
files that stop being shared are removed from the apps on the next sync.

## The rule

Don't edit a shared file inside an app: each copy starts with a comment saying it comes from here. Every app's build
runs `python sync.py --check .` against the commit in its `.kudu-common` file and **fails if its copy differs**, and
warns when kudu-common has newer changes that haven't been copied into it yet.

## License

[MIT](LICENSE)
