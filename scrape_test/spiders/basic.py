# -*- coding: utf-8 -*-
import scrapy
import time
import socket
import logging
import urllib.parse
from scrapy.selector import Selector
from scrapy.loader.processors import MapCompose, Compose

from scrape_test.items import DealPage
from scrape_test.loaders import DealLoader
from scrape_test.categories import UrlToCategoryMap


# strips all strings in a list
def list_strip(list_):
    return list(map(str.strip, list_))


# convert a list of urls to a list of categories
def urls_to_categories(list_):
    mapped = set()
    for url in list_:
        if url in UrlToCategoryMap:
            mapped.add(UrlToCategoryMap[url])
    return mapped


class BasicSpider(scrapy.Spider):
    name = "basic"
    allowed_domains = ["singpromos.com"]
    start_urls = ['http://singpromos.com/warehouse-sales/philips-carnival-sale-returns-from-19-21-may-2017-201297/']

    def parse(self, response):
        self.set_start_url(response)

        l = DealLoader(item=DealPage(), response=response)

        # housekeeping
        l.add_value('page_url', response.url)
        l.add_value('project', self.settings.get('BOT_NAME'))
        l.add_value('spider', self.name)
        l.add_value('server', socket.gethostname())
        l.add_value('time_retrieved_epoch', int(time.time()))

        l.add_xpath("title", '//*[@class="entry-title"]//text()')
        l.add_xpath("preview_image_url", '//*[@class="entry-thumbnail"]//img[1]/@src')
        l.add_xpath("description", '//*[@class="hidden description"]//*[@class="value-title"][1]/@title')
        l.add_xpath("deal_start_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[1]//text()')
        l.add_xpath("deal_end_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[2]//text()')
        l.add_xpath("location", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[1]//text()')
        l.add_xpath("address", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[2]//text()')

        html_content = self._get_html_content(response)
        l.add_value("html_content", html_content)

        def make_url(i): return urllib.parse.urljoin(response.url, i)

        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        l.add_value("image_urls", image_urls, MapCompose(make_url))

        category_urls = response.xpath('//a[@rel="category tag"]/@href').extract()
        category_urls.append(response.meta["start_url"])
        l.add_value("categories", category_urls, list_strip, urls_to_categories)

        return l.load_item()

    def set_start_url(self, response):
        if not "start_url" in response.meta:
            response.meta["start_url"] = response.url

    def _get_html_content(self, response):
        content_root = response.xpath('.//*[contains(@class, "entry-content")][1]')

        def should_start_after_this(element):
            node_content = element.xpath('@class').extract()
            node_is_target = node_content and "printDontShow" in node_content[0]
            return element.xpath('.//*[contains(@class, "printDontShow")]') or node_is_target

        def should_stop(element):
            node_content = element.xpath('@id').extract()
            node_is_target = node_content and "shareOnFacebook" in node_content[0]
            return element.xpath('.//*[@id="shareOnFacebook"]') or node_is_target

        started = False

        html_content = ""
        for node in content_root.xpath("./*"):
            if not started and should_start_after_this(node):
                started = True
                continue
            elif not started:
                continue

            if should_stop(node):
                break

            html_content += node.extract()

        return html_content
