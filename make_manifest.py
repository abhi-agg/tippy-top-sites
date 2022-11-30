import json
import logging
from io import BytesIO
from urllib.parse import urljoin

import click
import requests
from PIL import Image
from robobrowser import RoboBrowser

LINK_SELECTOR = 'link[rel=apple-touch-icon], link[rel=apple-touch-icon-precomposed], link[rel="icon shortcut"], link[rel="shortcut icon"], link[rel="icon"], link[rel="SHORTCUT ICON"], link[rel="fluid-icon"]'
META_SELECTOR = 'meta[name=apple-touch-icon]'
FIREFOX_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:58.0) Gecko/20100101 Firefox/58.0'
IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Version/10.0 Mobile/14D27 Safari/602.1'
SVG_ICON_WIDTH = "SVG_ICON_WIDTH"

logging.basicConfig(filename='debug.log',level=logging.INFO)

def _fetch_top_sites(topsitesfile):
    with open(topsitesfile) as jsonfile:
        data = json.load(jsonfile)
        topdomains = data["domains"]
        for topdomain in topdomains:
            yield (topdomain["rank"], topdomain["url"])

def top_sites(topsitesfile, count):
    top_sites_generator = _fetch_top_sites(topsitesfile)
    if count:
        return [next(top_sites_generator) for x in range(count)]
    else:
        return list(top_sites_generator)

def is_url_reachable(url):
    try:
        response = requests.get(url, headers={'User-agent': FIREFOX_UA}, timeout=60)
        return True if response.status_code == 200 else False
    except Exception as e:
        logging.info(f'Exception: "{str(e)}" while checking if "{url}" is reachable or not')
        return False

def fetch_icons(url, user_agent=IPHONE_UA):
    logging.info(f'Fetching icons for {url}')
    icons = []
    browser = RoboBrowser(user_agent=user_agent, parser='html.parser')
    try:
        browser.open(url, timeout=60)
        for link in browser.select(LINK_SELECTOR):
            icon = link.attrs
            icon_url = icon['href']
            if icon_url.startswith('data:'):
                continue
            if not icon_url.startswith('http') and not icon_url.startswith('//'):
                icon['href'] = urljoin(browser.url, icon_url)
            icons.append(icon)
        for meta in browser.select(META_SELECTOR):
            icon = meta.attrs
            icon_url = icon['content']
            if icon_url.startswith('data:'):
                continue
            if not icon_url.startswith('http') and not icon_url.startswith('//'):
                icon['href'] = urljoin(browser.url, icon_url)
            else:
                icon['href'] = icon_url
            icons.append(icon)
    except Exception as e:
        logging.info(f'Exception: "{str(e)}" while parsing icon urls from document')
        pass

    # If the document doesn't specify favicon via rel attribute of link tag then check
    # if "favicon.ico" file is present in the root of the domain as some domains keep
    # favicon in their root without specifying them in the document.
    # Add the icon url if this is the case.
    if len(icons) == 0:
        default_favicon_url = f"{url}/favicon.ico"
        if is_url_reachable(default_favicon_url):
            icons.append({"href": default_favicon_url})

    return icons

def fix_url(url):
    fixed = url
    if not url.startswith('http'):
        fixed = 'https:{url}'.format(url=url)
    return fixed

def get_best_icon(images):
    image_url = None
    image_width = 0
    for image in images:
        url = fix_url(image.get('href'))
        width = None
        sizes = image.get('sizes')
        if sizes:
            try:
                width = int(sizes.split('x')[0])
            except:
                pass
        if width is None:
            try:
                response = requests.get(url, headers={'User-agent': FIREFOX_UA}, timeout=60)

                # If it is an SVG, then return this as the best icon because SVG images are scalable,
                # can be printed with high quality at any resolution and SVG graphics do NOT
                # lose any quality if they are zoomed or resized.
                if response.headers.get('Content-Type') == 'image/svg+xml':
                    # Firefox doesn't support masked icons yet.
                    if 'mask' not in image:
                        # If it is not then we want it. We are done here.
                        return (url, SVG_ICON_WIDTH)
                    else:
                        logging.info(f'SVG icon "{image}" is masked')
                        continue
                with Image.open(BytesIO(response.content)) as img:
                    width, height = img.size
                    if width != height:
                        logging.info(f'icon shape "{width}*{height}" is not square')
                        width = min(width, height)
            except Exception as e:
                logging.info(f'Exception: "{str(e)}" fetching (or opening) icon {url}')
                pass
        if width and width > image_width:
            image_url = url
            image_width = width

    return (image_url, image_width)

def collect_icons_for_top_sites(topsitesfile, count):
    results = []

    topsites = top_sites(topsitesfile, count)
    logging.info(f'Fetching icons for {len(topsites)} sites')
    for rank, url in topsites:
        icons = fetch_icons(url)
        best_icon_url, best_icon_width = get_best_icon(icons)
        results.append({
            'url': url,
            'icons': icons,
            'rank': rank,
            'best_icon_url': best_icon_url,
            'best_icon_width': best_icon_width
        })
    logging.info('Done fetching icons')
    return results

@click.command()
@click.option('--count', type=int, help="Number of sites from a list of Top Sites to look for 'rich' favicons ('rich' is configurable). If not specified then the entire top site file is used.")
@click.option('--topsitesfile', required=True, type=click.Path(exists=True), help='A json file containing rank and domain information of the Top Sites.')
@click.option('--minwidth', default=52, help="Minimum width of the site icon to qualify it as 'rich'. Return icons for only those sites that satisfy this requirement. Default is 52.")
@click.option('--saverawsitedata', help='Save the full data to the filename specified')
def main(count, minwidth, topsitesfile, saverawsitedata):
    results = []

    sites_with_icons = collect_icons_for_top_sites(topsitesfile, count)
    if saverawsitedata:
        logging.info(f'Saving raw icon data to {saverawsitedata}')
        with open(saverawsitedata, 'w') as outfile:
            json.dump(sites_with_icons, outfile, indent=4)

    #prepare_output(sites_with_icons)
    with open(topsitesfile) as jsonfile:
        data = json.load(jsonfile)
        topdomains = data["domains"]
        for index in range(len(sites_with_icons)):
            url = sites_with_icons[index].get('url')
            icon = sites_with_icons[index].get('best_icon_url')
            icon_width = sites_with_icons[index].get('best_icon_width')

            # check if there is a best icon that satisfies the minwidth criteria
            if (icon is None) or ((icon_width != SVG_ICON_WIDTH) and (icon_width < minwidth)):
                logging.info(f'No icon for "{url}" (best icon width: {icon_width})')
                icon = ""
            domain = topdomains[index]
            domain["icon"] = icon
            results.append(domain)

    domains_with_icons = {}
    domains_with_icons["domains"] = results
    click.echo(json.dumps(domains_with_icons, indent=4))

if __name__ == "__main__":
    main()
