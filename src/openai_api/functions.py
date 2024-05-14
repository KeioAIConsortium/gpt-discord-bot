from mediawikiapi import MediaWikiAPI


def get_wikipedia_summary_function(query: str) -> str | None:
    mw = MediaWikiAPI()
    mw.config.language = "ja"
    search_result = mw.search(query)

    if search_result:
        page = mw.page(search_result[0])
        summary = page.summary
        url = page.url

        return f"{summary}\n\n{url}"
    else:
        return None


def get_wikipedia_page_content_function(query: str) -> str | None:
    mw = MediaWikiAPI()
    mw.config.language = "ja"
    search_result = mw.search(query)

    if search_result:
        page = mw.page(search_result[0])
        content = page.content

        return f"{content}"
    else:
        return None
