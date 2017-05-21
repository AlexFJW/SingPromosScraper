# -*- coding: utf-8 -*-
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Compose, Join

class DealLoader(ItemLoader):

    description_in = Compose(Join(separator=""), str.strip)
    deal_end_date_in = Compose(Join(separator=""), str.strip)
    deal_start_date_in = Compose(Join(separator=""), str.strip)
    location_in = Compose(Join(separator=""), str.strip)
    address_in = Compose(Join(separator=""), str.strip)
