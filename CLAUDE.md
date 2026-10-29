# kudu-common

Shared code for the KUDU Windows apps (KUDUNMAP, KUDUCOPY, KUDURESCUE, KUDUSYNC, KUDUTREE, KUDUDIFF, KUDUPST, KUDUBROWSE). It is a code
repository, not a library or package: `sync.py` copies the files in `shared/` into each app, replacing the namespace
`KuduApp` with the app's own, and records the kudu-common commit in the app's `.kudu-common` file.

## Working with Azeem (the owner)

- **Branches:** work on `main` and push to `main`. Ask before creating any other branch.
- **New features:** first say what you understood, and ask your doubts and suggestions, one question at a time.
  Only start building when Azeem says "build".
- **Look:** keep the app's current look. No redesigns unless asked.
- **About window credit:** "Made by Azeem, with Claude and ♥" (the heart in the accent colour). Keep it.
- **Commits:** author `Azeem Bukhari <12558389+azeembukhariprivate@users.noreply.github.com>`. Clear messages that say
  what changed and why. Don't put AI model names or versions in commits, code or docs.
- **Words:** the app's text, README and release notes use plain everyday words, not technical jargon.
- **Before pushing:** build and run the tests locally, and re-read the diff. After pushing, watch the GitHub Actions
  build until it's green; fix failures, never skip or disable a test to get green.

## How to change shared code

1. Edit the file in `shared/` (keep it free of anything app-specific; apps put their details in `Core/AppDetails.cs`).
2. Commit and push here.
3. Run `python sync.py ../kudunmap ../kuducopy ../kudurescue ../kudusync ../kudutree ../kududiff ../kudupst ../kudubrowse`, then build, test,
   commit and push each app. Each app's build fails if its copy differs from the kudu-common commit it names.
4. `.github/workflows/check.yml` builds and tests every app with the current shared code (not KUDUBROWSE while its
   repository is private: the check can't download it). A new app gets added to its
   matrix (and to the README lists).

KUDUPACK and KUDUCK don't use kudu-common.

## Starting a new KUDU app

Follow the "Starting a new KUDU app" checklist in README.md. Azeem creates the GitHub repository; Claude can't.

## Ideas for later

`IDEAS.md` is the pending list of additions to the apps and possible new apps. Take them one at a time when Azeem asks;
when one is built, move it to "Done" there with its version.
