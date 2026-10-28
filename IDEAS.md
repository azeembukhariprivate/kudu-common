# Ideas for later

The pending list for the KUDU apps: additions to the apps already built, and possible new apps. Nothing here is agreed
yet. We take them one at a time: Claude says what it understood, asks its questions one at a time, and builds only when
Azeem says "build". When something is built, move it to "Done" at the end with its version.

## Additions to the apps already built

### KUDUPST (Outlook files)
- [ ] Open several files at once and search across all of them.
- [ ] Find duplicate emails, and export without the copies.
- [ ] Show whole conversations together.
- [ ] Save the results as a new PST file that Outlook can open.

### KUDURESCUE (getting deleted files back)
- [ ] Preview more kinds of files (videos, Office documents) before getting them back.
- [ ] Repair photos and Office files that come back only partly whole.
- [ ] More kinds of drives (memory cards and USB sticks formatted on a Mac or a camera).

### KUDUTREE (what's taking up space)
- [ ] A "safe to clean" list: temporary files, old Windows update leftovers, browser caches, with how much space each
      gives back (to the Recycle Bin).
- [ ] Find photos that look alike, not only exact copies.
- [ ] Watch a folder over time ("Downloads grew 4 GB this month").

### KUDUSYNC (keeping folders in step)
- [ ] Keep earlier versions of changed files, so a backup can go back in time.
- [ ] Back up to a NAS or network share, reconnecting by itself.
- [ ] An email or notification when a scheduled backup fails.

### KUDUCOPY (fast copying)
- [ ] Check copies byte for byte after copying, with a report.
- [ ] A queue for several copy jobs; pause, and carry on after a restart.
- [ ] Limit the speed so the network stays usable.

### KUDUPACK (archives)
- [ ] Repair damaged ZIP files.
- [ ] Open an archive inside an archive in one step.
- [ ] Find which archive in a folder holds a given file.
- [ ] Split and join big archives (for email or USB sticks).

### KUDUDIFF (comparing files)
- [ ] Compare two folders. *(Left out of v1 on purpose: a new scope to agree.)*
- [ ] Compare Word, Excel and PDF files as text.
- [ ] Ignore spaces, upper/lower case, or lines matching a pattern.
- [ ] Three-way merge. *(Left out of v1 on purpose: a new scope to agree.)*

### KUDUNMAP (network scans)
- [ ] Save scans and compare them ("a new device appeared", "port 3389 opened").
- [ ] A drawing of the network.
- [ ] Scheduled scans with alerts.
- [ ] A note in plain words on what each open port could risk.

### KUDUCK (images and PDFs)
- [ ] Copy text from pictures and scanned PDFs (Windows' own text recognition).
- [ ] Fill in and sign PDF forms.
- [ ] Make PDFs smaller.
- [ ] Resize and watermark many photos at once.
- [ ] Put PDF pages in order by dragging.

### All the apps (through kudu-common)
- [ ] Other languages for the apps' text.
- [ ] Command-line options, for scripts.
- [ ] A portable mode that keeps settings next to the app instead of in the registry.

Suggested first: KUDUTREE's "safe to clean" list, KUDUSYNC's earlier versions of files, KUDUPST's search across files.

## New apps

### For everyone (things people usually pay for)
- [ ] **KUDUTEXT**: subtitles and transcripts from any video or recording, offline, in many languages (an open
      speech-recognition model, as KUDUCK uses one for removing backgrounds).
- [ ] **KUDUCLONE**: copy Windows to a new SSD, or make a full disk backup image and restore it. *(Riskiest to build;
      needs the most testing.)*
- [ ] **KUDUSHRINK**: make videos smaller, convert them, cut a clip, take out the sound (built on FFmpeg, with simple
      choices instead of settings).
- [ ] **KUDUHEALTH**: drive and SSD health, battery wear, temperatures, what slows down starting up, in plain words.
- [ ] **KUDUDROP**: send files between your own devices on the same network; no cloud, no account, no size limit.
- [ ] **KUDUSNAP**: screenshots with arrows and blur, whole scrolling pages, short screen recordings, copying text from a
      picture.
- [ ] **KUDUREMOVE**: uninstall apps completely, leftover files and settings included, with an undo.
- [ ] **KUDUMAIL**: back up a Gmail or Outlook.com mailbox to the PC (to read and search with KUDUPST).
- [ ] **KUDUVAULT**: an offline password manager with a strongly encrypted file only you hold. *(Very sensitive: only
      with extra care.)*
- [ ] **KUDURENAME**: rename thousands of files at once by pattern, date taken or music details, with a preview.

### For technical people
- [ ] **KUDULOG**: Windows event logs (.evtx, our own reader) and text logs on one timeline, with instant search, filters,
      ready-made checks (failed sign-ins, new services, unexpected restarts) and export.
- [ ] **KUDUSTART**: everything that starts with Windows (apps, services, scheduled tasks, drivers, add-ons): who signed
      it, turning things off safely with an undo, and comparing with an earlier snapshot.
- [ ] **KUDUDATA**: open huge CSV, JSON and SQLite files straight away: a table, filters, search, saving a filtered part.

Suggested first: KUDUTEXT (nobody's data is at risk), then KUDUCLONE and KUDUSHRINK.

## Done

- **Inaara 1.0** (new app, its own repository `inaara`): a Kerala platform game for the browser, played at
  https://azeembukhariprivate.github.io/inaara/. Inaara's real face from her sheet (Azeem's choice, as her parent or
  guardian) on a body drawn by code; five levels (Backwaters, Munnar Tea Hills, Rainforest Falls, Monsoon Night, The
  Boat Race) and the Monkey Chief; run, jump, spin, wall jump, ledges, banana-leaf glide; jasmine, golden lotuses,
  lamps; music made by code; PC, game controller and phone; keeps working offline.
