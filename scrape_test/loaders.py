# -*- coding: utf-8 -*-
from scrapy.loader import ItemLoader
from scrapy.loader import processors

'''
l.add_xpath("description", '//*[@class="hidden description"]//*[@class="value-title"][1]/@title')
l.add_xpath("deal_start_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[1]//text()')
l.add_xpath("deal_end_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[2]//text()')
l.add_xpath("location", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[1]//text()')
l.add_xpath("address", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[2]//text()')
'''
class DealLoader(ItemLoader):

    deal_end_date_in = processors.Join

