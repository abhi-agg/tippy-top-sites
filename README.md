# tippy-top-sites
Scripts and tools related to tippy top services 

## make_manifest.py
To run the manifest generator script (note this script only supports Python3). In a new virtualenv:

```
$ pip install -r requirements.txt
$ python make_manifest.py --help
Usage: make_manifest.py [OPTIONS]

Options:
  --count INTEGER         Number of sites from a list of Top Sites to look for
                          'rich' favicons ('rich' is configurable). Default is
                          10.
  --topsitesfile PATH     A json file containing rank and domain information
                          of the Top Sites.  [required]
  --minwidth INTEGER      Minimum width of the site icon to qualify it as
                          'rich'. Return icons for only those sites that
                          satisfy this requirement. Default is 52.
  --saverawsitedata TEXT  Save the full data to the filename specified
  --help                  Show this message and exit.

$ python make_manifest.py --count 100 --topsitesfile TOP_PICK_JSON_FILE > icons.json

(Replace TOP_PICK_JSON_FILE with a top sites file in json format.)
```
