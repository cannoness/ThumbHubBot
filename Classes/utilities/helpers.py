from random import shuffle


def shuffle_list_of_dicts(input_list):
    shuffled_indices = list(range(len(input_list)))
    shuffle(shuffled_indices)
    output_list = [input_list[index_] for index_ in shuffled_indices]
    return output_list


def format_rss_results_for_store(images):
    nl = "\n"
    return [{
        "deviationid": result["id"],
        "url":
            result["link"],
        "src_image":
            result["media_thumbnail"][-1]["url"]
            if "medium" in result["media_content"][-1].keys() and "image" in result["media_content"][-1]["medium"]
            else "None",
        "src_snippet":
            result["summary"][:1024].replace("'", "''").replace("<br />", nl)
            if "medium" in result["media_content"][-1].keys() and "image" not in result["media_content"][-1]["medium"]
            else "None",
        "is_mature":
            False if "nonadult" in result["rating"] else True,
        "published_time":
            result["published"],
        "title":
            f"{result['title']}",
        "author":
            result["media_credit"][0]["content"]
    } for result in images if (True if result["summary"] != "" and "media_content" in result.keys() else False)]


def format_api_image_results(results):
    nl = "\n"
    return [{
        "deviationid": result["deviationid"],
        "url":
            result["url"],
        "src_image":
        # prefer to use thumb over shrinking the content
            result["preview"]["src"] if "preview" in result and "src" in result["preview"]
            else result["thumbs"][-1]["src"] if "thumbs" in result and len(result["thumbs"])
            else result["content"]["src"] if "content" in result and "src" in result["content"]
            else "None",
        "src_snippet":
            result["text_content"]["excerpt"][:1024].replace("'", "''").replace("<br />", nl)
            if "text_content" in result
            else "None",
        "is_mature":
            result["is_mature"],
        "stats":
            result["stats"],
        "published_time":
            result["published_time"],
        "title":
            f"{result['title']}",
        "author":
            result["author"]["username"]
    } for result in results]
