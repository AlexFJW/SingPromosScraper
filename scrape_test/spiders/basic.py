# -*- coding: utf-8 -*-
import scrapy
import time
import socket
import re
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
    start_urls = UrlToCategoryMap.keys()
    # for debugging
    # start_urls = ['http://singpromos.com/department-stores/bhg-20-off-storewide-super-sale-from-13-15-may-2016-178949/']
    '''start_urls = ['http://singpromos.com/department-stores/guardian-online-store-20-off-storewide-discount-coupon-code'
                 '-no-min-spend-valid-from-18-21-may-2017-201892/']'''

    # for navigation pages (pages with a list of deals & a pagination bar for more deals)
    def parse(self, response):
        # save the start_url. used to verify the category of each deal
        self._set_start_url(response)

        # handle all deals
        deal_urls = response.xpath('.//*[@class="tabs1Content"]//*[contains(@class, "mh-loop-title")]/a/@href').extract()
        for url in deal_urls:
            full_url = urllib.parse.urljoin(response.url, url)
            request = Request(url=full_url, callback=self.parse_deal)
            request.meta["start_url"] = response.meta["start_url"]
            yield request

        # handle next navigation page
        next_page_url = response.xpath('.//*[@class="next page-numbers"]/@href').extract()
        if next_page_url:
            full_url = urllib.parse.urljoin(response.url, next_page_url[0])
            request = Request(url=full_url, callback=self.parse)
            request.meta["start_url"] = response.meta["start_url"]
            yield request

    def parse_deal(self, response):
        if self.is_coupon_deal_page(response):
            # coupon deal pages retrieve the coupon code through a ajax call
            # make the ajax call & process the deal page's data at that url
            # cache this page's response body to do the above

            deal_id = self.get_deal_id(response.url)
            coupon_url = "http://singpromos.com/getcoupon/" + deal_id + "/"
            request = Request(url=coupon_url, callback=self.parse_coupon_deal)

            request.meta["old_response_body"] = response.body
            request.meta["start_url"] = response.meta["start_url"]
            request.meta["prev_url"] = response.url
            yield request
        else:
            yield self.parse_regular_deal(response)

    @staticmethod
    def get_deal_id(url):
        return re.findall('-(\\d*?)/$', url)[-1]

    def is_coupon_deal_page(self, response):
        return len(response.xpath('.//*[contains(@onclick, "showCouponLinkAjax")]')) > 0


    '''Coupon code result is in json
        Reuse the previous response body to populate DealItem fields
    '''
    def parse_coupon_deal(self, response):
        old_response = Selector(text=response.meta["old_response_body"])
        loader = DealLoader(item=Deal(), selector=old_response)

        # save common data
        self.add_common_data_to_loader(loader, response.meta["start_url"])

        prev_url = response.meta["prev_url"]
        loader.add_value('page_url', prev_url)

        # read the coupon code
        str_response = str(response.body, 'utf-8')
        json_result = json.loads(str_response)
        coupon_code = json_result[0] if (len(json_result) > 0) else ""

        # read & modify the html content
        html_content = self._get_html_content(old_response, True)
        html_content = html_content.replace("(click box above to reveal)", coupon_code)
        loader.add_value("html_content", html_content)

        # save images
        def make_url(i): return urllib.parse.urljoin(prev_url, i)
        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        loader.add_value("image_urls", image_urls, MapCompose(make_url))

        return loader.load_item()

    def parse_regular_deal(self, response):
        loader = DealLoader(item=Deal(), response=response)

        # save common data
        self.add_common_data_to_loader(loader, response.meta["start_url"])
        loader.add_value('page_url', response.url)

        # save html content
        html_content = self._get_html_content(response, False)
        loader.add_value("html_content", html_content)

        # save images
        def make_url(i): return urllib.parse.urljoin(response.url, i)
        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        loader.add_value("image_urls", image_urls, MapCompose(make_url))

        return loader.load_item()

    def add_common_data_to_loader(self, loader, start_url):
        loader.add_value('project', self.settings.get('BOT_NAME'))
        loader.add_value('spider', self.name)
        loader.add_value('server', socket.gethostname())
        loader.add_value('time_retrieved_epoch', int(time.time()))
        loader.add_value('deal_id', self.get_deal_id(start_url))

        loader.add_xpath("title", '//*[@class="entry-title"]//text()')
        loader.add_xpath("preview_image_url", '//*[@class="entry-thumbnail"]//img[1]/@src')
        loader.add_xpath("description", '//*[@class="hidden description"]//*[@class="value-title"][1]/@title')
        loader.add_xpath("deal_start_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[1]//text()')
        loader.add_xpath("deal_end_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[2]//text()')
        loader.add_xpath("location", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[1]//text()')
        loader.add_xpath("address", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[2]//text()')

        # gather category urls from page & convert them to categories
        # insert the start url as well, the category url section is sometimes empty
        category_urls = set(loader.selector.xpath('//a[@rel="category tag"]/@href').extract())
        category_urls.add(start_url)
        loader.add_value("categories", category_urls, list_strip, urls_to_categories)

    def _set_start_url(self, response):
        if not "start_url" in response.meta:
            response.meta["start_url"] = response.url

    def _get_html_content(self, response, is_coupon_deal):
        content_root = response.xpath('.//*[contains(@class, "entry-content")][1]')

        def should_start_after_this(element):
            node_content = element.xpath('@class').extract()
            node_is_target = node_content and "printDontShow" in node_content[0]
            return element.xpath('.//*[contains(@class, "printDontShow")]') or node_is_target

        def should_stop(element):
            node_content = element.xpath('@id').extract()
            node_is_target = node_content and "showSharerPopup" in node_content[0]
            return element.xpath('.//*[@id="showSharerPopup"]') or node_is_target

        def should_skip(element):
            return len(element.xpath('.//*[contains(@onclick, "showCouponLinkAjax")]')) > 0

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

            if is_coupon_deal and should_skip(node):
                continue

            html_content += node.extract()

        return html_content.replace("/redirect/link?url=", "")
