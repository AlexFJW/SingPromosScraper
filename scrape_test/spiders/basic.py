# -*- coding: utf-8 -*-
import scrapy
import time
import socket
import logging
import json
import urllib.parse
from scrapy.selector import Selector
from scrapy.loader.processors import MapCompose, Compose
from scrapy.http import Request

from scrape_test.items import Deal
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
        # for now
        return self.parse_deal(response)

    def parse_deal(self, response):
        # if coupon item,
        if False:
            # todo: get the deal id
            deal_id = "123"
            coupon_url = "http://singpromos.com/getcoupon/" + deal_id + "/"
            request = Request(url=coupon_url, callback=self.parse_coupon_deal)
            request.meta["old_response_body"] = response.body
            request.meta["start_url"] = response.meta["start_url"]
            request.meta["prev_url"] = response.url
            yield request
        else:
            yield self.parse_regular_deal(response)

    '''Coupon code result is in json
        Reuse the previous response body to populate DealItem fields
    '''
    def parse_coupon_deal(self, response):
        # todo: change when doing multipage scraping
        self._set_start_url(response)

        old_response = Selector(text=response.meta["old_response_body"])
        loader = DealLoader(item=Deal(), selector=old_response)
        self.add_common_data_to_loader(loader, response.meta["start_url"])
        loader.add_value('page_url', response.meta["prev_url"])

        coupon_code = json.loads(response.body)[0]
        html_content = self._get_html_content(response)
        # todo: strip the click me box, and the text saying "show up here, replace with the code"
        loader.add_value("html_content", html_content)

        def make_url(i): return urllib.parse.urljoin(response.url, i)
        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        loader.add_value("image_urls", image_urls, MapCompose(make_url))

        return loader.load_item()

    def parse_regular_deal(self, response):
        # todo: change when doing multipage scraping
        self._set_start_url(response)

        loader = DealLoader(item=Deal(), response=response)
        self.add_common_data_to_loader(loader, response.meta["start_url"])
        loader.add_value('page_url', response.url)

        html_content = self._get_html_content(response)
        loader.add_value("html_content", html_content)

        def make_url(i): return urllib.parse.urljoin(response.url, i)
        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        loader.add_value("image_urls", image_urls, MapCompose(make_url))

        return loader.load_item()

    def add_common_data_to_loader(self, loader, start_url):
        loader.add_value('project', self.settings.get('BOT_NAME'))
        loader.add_value('spider', self.name)
        loader.add_value('server', socket.gethostname())
        loader.add_value('time_retrieved_epoch', int(time.time()))

        loader.add_xpath("title", '//*[@class="entry-title"]//text()')
        loader.add_xpath("preview_image_url", '//*[@class="entry-thumbnail"]//img[1]/@src')
        loader.add_xpath("description", '//*[@class="hidden description"]//*[@class="value-title"][1]/@title')
        loader.add_xpath("deal_start_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[1]//text()')
        loader.add_xpath("deal_end_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[2]//text()')
        loader.add_xpath("location", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[1]//text()')
        loader.add_xpath("address", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[2]//text()')

        category_urls = loader.selector.xpath('//a[@rel="category tag"]/@href').extract()
        category_urls.append(start_url)
        loader.add_value("categories", category_urls, list_strip, urls_to_categories)

    def _set_start_url(self, response):
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
