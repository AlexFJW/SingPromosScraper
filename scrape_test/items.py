# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class DealPage(Item):
    title = Field()
    preview_image_url = Field()
    html_content = Field()
    description = Field()

    categories = Field()

    # may be empty, and may not be a real location
    location = Field()
    address = Field()
    image_urls = Field()

    # initial url which led us to this page
    source_page = Field()

    deal_start_date = Field()
    deal_end_date = Field()

    # Housekeeping
    page_url = Field()
    project = Field()
    spider = Field()
    server = Field()
    date_retrieved = Field()

