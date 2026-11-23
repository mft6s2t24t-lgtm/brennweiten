# Brennweiten Guide

[Deutsch](LIESMICH.md) · **English**

Brennweiten analyzes the EXIF data of your photos to show which focal lengths you really use, as a basis for lens decisions. It runs entirely locally, without internet. **Photos are only read, never changed, moved or renamed.**

## Install

1. Open `Brennweiten.dmg` and drag **Brennweiten** to **Applications**.
2. Open Brennweiten from the Applications folder. Nothing else needs to be installed. The app runs on Apple silicon and Intel Macs with macOS 12.3 or later.
3. As long as the app is not notarized by Apple, macOS blocks the first launch. Go to **System Settings → Privacy & Security**, click **Open Anyway**, then choose **Allow** once when the app starts.

macOS may ask for permission the first time the app accesses external drives or a NAS. Quit like any Mac app with ⌘Q.

## First setup

1. **Choose photo folders** (⌘-click for several). The scan then starts on its own. The first scan takes a while. Later scans read only new or changed files.
2. Check **Cameras**: All models come from your photos' EXIF data. Smartphones and scanners are off by default and can be enabled with a checkbox. If the crop factor says "please check", enter your camera's value.
3. Check **Lenses**: Suggestions for images without a lens name appear at the top. Adjust the name and click **Confirm**. **Same name = counted together.**

## Analysis

Filters: cameras, lenses, time period, "3+ stars". All focal lengths are shown as full-frame equivalents.

The app has three areas:

- **Analysis:** Overview, Lenses, Cameras, Shooting days, Table
- **Decide:** Check a lens, Compare
- **Manage:** Cameras & lenses, Data quality, Folders & scan

The **Overview** shows your metrics, the distribution across ranges (<17 … >400 mm), a detailed histogram (per mm), your most used lenses and the trend by year.

The **Lenses** page shows zoom limits (for a 24-120: 24–26 and 110–120 mm, measured on the lens), wide-open use in low light (wide open **and** above ISO 3200), ultra-wide use, use around 50 and 85 mm, and keeper rate. Choose a lens and enter a focal length (such as 28) and/or an aperture (such as 2.8) to count exactly those photos.

Under **Export** you can save the filtered images as CSV for Excel or as a PDF report. **Copy summary** puts at most 25 lines of numbers and facts on the clipboard.

## How it calculates

- **Full-frame focal length:** The EXIF value "FocalLengthIn35mmFormat" is used if it fits the camera's crop factor, otherwise focal length × crop factor. Images in **DX mode** are detected.
- **Crop factor:** first from the image data, then from the known sensor size of common camera lines. If neither is possible, 1.0 is used and the app asks you to check it. Your own values are kept.
- **Duplicates** count once: images from the same camera with the same capture time (including sub-seconds) and serial number belong together, such as RAW+JPEG, exports (DxO, Lightroom…) and backups. RAW (NEF/NRW/CR2/CR3) is preferred, then DNG, TIFF, HEIF, JPG. Burst shots within the same second without sub-seconds stay separate if they are different files.
- **Rating:** from the image (EXIF/XMP) or the `.xmp` sidecar (`Image.NEF.xmp` or `Image.xmp`). The sidecar takes priority. For duplicates, the group's highest rating counts.
- **Wide open:** aperture ≤ the maximum aperture at that focal length (from EXIF "MaxApertureValue", otherwise from the lens name or settings).
- **Missing drive:** If a folder is not reachable, it is marked "not reachable" and its data stays in the analysis. Deleted files are removed only after a folder could be read completely.

## Your data

The database, previews and log are stored in `~/Library/Application Support/Brennweiten` (menu **Help → Show Data Folder in Finder**).

**Uninstall:** Quit the app, then move Brennweiten from Applications and this data folder to the Trash. Your photos are not affected.

## More features

- **Language:** The app starts in your Mac's language. Switch between Deutsch and English anytime at the bottom of the sidebar.
- **Metrics:** On the Overview, "Customize metrics" sets up to eight tiles and their order, including custom rules such as "28–35 mm", "ISO 6400 or higher" or "f/2.8 or wider".
- **Lenses and cameras:** A ranking of all lenses or cameras. Click one for the detailed analysis with focal lengths, apertures, ISO, shutter speeds and use per year. Lenses also show zoom limits and wide-open use in low light.
- **Shooting days:** Each day and trip can be analyzed by camera, lens, focal length, aperture, ISO and time of day.
- **Table:** all counted photos, like in Excel. Click a heading to sort, ⇧-click to add another sort column. The ▾ opens value lists, text filters and range filters. Column filters also apply to analyses, CSV and PDF.
- **Check a lens:** Enter up to three lenses. The app shows how often you shot in that range, which of your lenses you used there, what the aperture would have added and what would be new. It does not make a purchase recommendation. Photos only show what was possible with your gear so far. Primes count with a ±6% tolerance. The light gain assumes the same shutter speed and only counts photos taken wide open above ISO 3200.
- **Compare:** two lenses, cameras or time periods side by side, with differences in percentage points.
- **Info buttons:** The ⓘ next to sections, filters and fields explains what you see and can set, by mouse, click or keyboard.
- **Data quality:** missing data, unconfirmed lenses and possible duplicates.
- **Sample images:** blue numbers open the matching photos. Previews are read from the photos and stored in your own data folder under `vorschau`.
- **Views and PDF:** Filters, sorting and columns can be saved under a name. Under "Export", "Save PDF report" creates a report for the current filter.
- **Automatic updates:** reads new photos at launch and when a drive is connected. Can be turned off under "Folders & scan".
- **Teleconverters:** Lenses with a TC or extender are calculated with their actual focal length range and maximum aperture.

## Troubleshooting

- *macOS blocks the launch:* System Settings → Privacy & Security → **Open Anyway**.
- *"Please move to Applications" message:* Drag the app from the DMG to the Applications folder and open it there.
- *NAS folder missing:* Connect the NAS in Finder. The app then reads it automatically.
- *Unreadable files* are listed under "Folders & scan" and retried on the next scan.

## For developers

Build, self-test and structure are described in `README.md`. With `SIGN_ID`, `BUNDLE_ID` and `NOTARY_PROFILE`, `build/baue_app.sh` signs and notarizes the app for distribution.
