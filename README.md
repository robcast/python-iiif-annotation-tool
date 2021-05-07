# python-iiif-annotation-tool

A simple command-line tool to manipulate image annotations in IIIF manifests.

* Requires Python 3.7 (or later).
* Reads [IIIF Presentation API](https://iiif.io/technical-details/) V2 or V3 manifests from file or HTTP.
* Extracts inline or standoff annotations from manifests.
* Inserts inline or standoff annotations into manifests.
* Reads and writes IIIF V2 annotations for V2 manifests and V3 annotations for V3 manifests.

## Use

```
iiifanno.py check -i mymanifest.json
```
Reads the manifest file `mymanifest.json` and prints some information about annotations in the manifest. You can also use a HTTP(S) URL instead of the file name.

```
iiifanno.py extract -i mymanifest.json -of myannos.json
```
Reads the manifest file `mymanifest.json` and writes all annotations into the file `myannos.json`. Writes an `oa:AnnotationList` for a IIIF V2 manifest and an `AnnotationPage` for V3 annotations.

```
iiifanno.py insert -i mymanifest.json  -if myannos.json -od newdirectory -om newmanifest.json
```
Reads the manifest file `mymanifest.json` and the annotations from the file `myannos.json` and creates new annotation list files and a new manifest file `newmanifest.json` in the directory `newdirectory`.

For more options see `iiifanno.py -h`:

```
usage: iiifanno.py [-h] [--version] [-i INPUT_MANIFEST] [-if INPUT_FILE] [-of OUTPUT_FILE]
                   [-od OUTPUT_DIRECTORY] [-om OUTPUT_MANIFEST] [--reference-mode {inline,reference}]
                   [--url-prefix URL_PREFIX] [--annolist-name-scheme {canvas,sequence}]
                   [-l {INFO,DEBUG,ERROR}]
                   {check,extract,insert}

Manipulate annotations in IIIF manifests.

positional arguments:
  {check,extract,insert}
                        Action: check=check and print information about annotations in manifest,
                        extract=extract annotations from manifest, insert=insert annotations and create
                        new manifest.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -i INPUT_MANIFEST, --input-manifest INPUT_MANIFEST
                        Input manifest file or URL (JSON)
  -if INPUT_FILE, --input-file INPUT_FILE
                        Input AnnotationPage/List file (JSON)
  -of OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output AnnotationPage/List file (JSON)
  -od OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        Output directory for AnnotationPage/List files (JSON)
  -om OUTPUT_MANIFEST, --output-manifest OUTPUT_MANIFEST
                        Output manifest file (JSON)
  --reference-mode {inline,reference}
                        Mode of storing annotations in manifest.
  --url-prefix URL_PREFIX
                        URL prefix for AnnotationPage/List references and manifest.
  --annolist-name-scheme {canvas,sequence}
                        Naming scheme for generated AnnotationPage/List files.
  -l {INFO,DEBUG,ERROR}, --log {INFO,DEBUG,ERROR}
                        Log level.
```