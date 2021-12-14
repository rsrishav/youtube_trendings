import os
import requests
import sys
import time

# List of simple to collect features
SNIPPET_FEATURES = ["title",
                    "publishedAt",
                    "channelId",
                    "channelTitle",
                    "categoryId"]

# Any characters to exclude, generally these are things that become problematic in CSV files
UNSAFE_CHARACTERS = ['\n', '"']

# Used to identify columns, currently hardcoded order
HEADER = ["video_id"] + SNIPPET_FEATURES + ["trending_date", "tags", "view_count", "likes", "dislikes",
                                            "comment_count", "thumbnail_link", "comments_disabled",
                                            "ratings_disabled", "description"]

OUTPUT_DIR, API_KEY, COUNTRY_CODES = "", "", []


def read_country_codes(code_path):
    with open(code_path) as file:
        country_codes = [x.rstrip() for x in file]

    return country_codes


def prepare_feature(feature):
    # Removes any character from the unsafe characters list and surrounds the whole item in quotes
    for ch in UNSAFE_CHARACTERS:
        feature = str(feature).replace(ch, "")
    return f'"{feature}"'


def api_request(page_token, country_code):
    # Builds the URL and requests the JSON from it
    request_url = f"https://www.googleapis.com/youtube/v3/videos?part=id,statistics,snippet{page_token}chart=mostPopular&regionCode={country_code}&maxResults=50&key={API_KEY}"
    request = requests.get(request_url)
    if request.status_code == 429:
        print("Temp-Banned due to excess requests, please wait and continue later")
        sys.exit()
    return request.json()


def get_tags(tags_list):
    # Takes a list of tags, prepares each tag and joins them into a string by the pipe character
    return prepare_feature("|".join(tags_list))


def get_videos(items):
    lines = []
    for video in items:
        comments_disabled = False
        ratings_disabled = False

        # We can assume something is wrong with the video if it has no statistics, often this means it has been deleted
        # so we can just skip it
        if "statistics" not in video:
            continue

        # A full explanation of all of these features can be found on the GitHub page for this project
        video_id = prepare_feature(video['id'])

        # Snippet and statistics are sub-dicts of video, containing the most useful info
        snippet = video['snippet']
        statistics = video['statistics']

        # This list contains all of the features in snippet that are 1 deep and require no special processing
        features = [prepare_feature(snippet.get(feature, "")) for feature in SNIPPET_FEATURES]

        # The following are special case features which require unique processing, or are not within the snippet dict
        description = snippet.get("description", "")
        thumbnail_link = snippet.get("thumbnails", dict()).get("default", dict()).get("url", "")
        trending_date = time.strftime("%Y-%m-%dT00:00:00Z")
        tags = get_tags(snippet.get("tags", ["[None]"]))
        view_count = statistics.get("viewCount", 0)

        # This may be unclear, essentially the way the API works is that if a video has comments or ratings disabled
        # then it has no feature for it, thus if they don't exist in the statistics dict we know they are disabled

        # Dislike was DISABLED by YouTube from 13th-Dec-2021
        if 'likeCount' in statistics:  # and 'dislikeCount' in statistics:
            likes = statistics['likeCount']
            # dislikes = statistics['dislikeCount']
            dislikes = 0
        else:
            ratings_disabled = True
            likes = 0
            dislikes = 0

        if 'commentCount' in statistics:
            comment_count = statistics['commentCount']
        else:
            comments_disabled = True
            comment_count = 0

        # Compiles all of the various bits of info into one consistently formatted line
        line = [video_id] + features + [prepare_feature(x) for x in [trending_date, tags, view_count, likes, dislikes,
                                                                       comment_count, thumbnail_link, comments_disabled,
                                                                       ratings_disabled, description]]
        lines.append(",".join(line))
    return lines


def get_pages(country_code, next_page_token="&"):
    country_data = []

    # Because the API uses page tokens (which are literally just the same function of numbers everywhere) it is much
    # more inconvenient to iterate over pages, but that is what is done here.
    while next_page_token is not None:
        # A page of data i.e. a list of videos and all needed data
        video_data_page = api_request(next_page_token, country_code)

        # Get the next page token and build a string which can be injected into the request with it, unless it's None,
        # then let the whole thing be None so that the loop ends after this cycle
        next_page_token = video_data_page.get("nextPageToken", None)
        next_page_token = f"&pageToken={next_page_token}&" if next_page_token is not None else next_page_token

        # Get all of the items as a list and let get_videos return the needed features
        items = video_data_page.get('items', [])
        country_data += get_videos(items)

    return country_data


def write_to_file(country_code, country_data):

    print(f"> Writing {country_code} data to file...")
    country_data.pop(0)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(f"{OUTPUT_DIR}/{country_code}_youtube_trending_data.csv", "a", encoding='utf-8') as file:
        for row in country_data:
            file.write(f"{row}\n")


def get_data():
    for country_code in COUNTRY_CODES:
        country_data = [",".join(HEADER)] + get_pages(country_code)
        write_to_file(country_code, country_data)
    print("[INFO] Data written to CSV files.")
    return True


def scrap():
    global OUTPUT_DIR, API_KEY, COUNTRY_CODES
    API_KEY = os.environ["YT_API_KEY"]
    OUTPUT_DIR = "datasets"
    COUNTRY_CODES = read_country_codes("country_codes.txt")
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--key_path', help='Path to the file containing the api key, by default will use api_key.txt in the same directory', default='TrendingScraper/api_key.txt')
    # parser.add_argument('--country_code_path', help='Path to the file containing the list of country codes to scrape, by default will use country_codes.txt in the same directory', default='TrendingScraper/country_codes.txt')
    # parser.add_argument('--output_dir', help='Path to save the outputted files in', default='datasets/')
    #
    # args = parser.parse_args()
    #
    # OUTPUT_DIR = args.output_dir
    # API_KEY, COUNTRY_CODES = setup(args.key_path, args.country_code_path)

    return get_data()
