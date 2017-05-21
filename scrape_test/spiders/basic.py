# -*- coding: utf-8 -*-
import scrapy
import time
import socket
import logging
from scrapy.loader import ItemLoader
from scrapy.selector import Selector

from scrape_test.items import DealPage


class BasicSpider(scrapy.Spider):
    name = "basic"
    allowed_domains = ["singpromos.com"]
    start_urls = ['http://singpromos.com/warehouse-sales/philips-carnival-sale-returns-from-19-21-may-2017-201297/']

    def parse(self, response):
        l = ItemLoader(item=DealPage(), response=response)
        l.add_xpath("title", '//*[@class="entry-title"]//text()')
        l.add_xpath("preview_image_url", '//*[@class="entry-thumbnail"]//img[1]/@src')
        l.add_xpath("description", '//*[@class="hidden description"]//*[@class="value-title"][1]/@title')
        l.add_xpath("deal_start_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[1]//text()')
        l.add_xpath("deal_end_date", '//*[contains(@class, "eventDetailsTable")]//tr[1]/td[2]//text()')
        l.add_xpath("location", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[1]//text()')
        l.add_xpath("address", '//*[contains(@class, "eventDetailsTable")]//tr[2]/td[2]//text()')

        html_content = self._get_html_content(response)
        l.add_value("html_content", html_content)

        image_urls = Selector(text=html_content).xpath('//a/img/../@href').extract()
        l.add_value("image_urls", image_urls)

        # todo: add post processing later
        l.add_xpath("categories", '//a[@rel="category tag"]/@href')

        # todo: do url fixing
        # todo: swap to string(...) rather than ../text(), to prevent <em> problems

        l.add_value('page_url', response.url)
        l.add_value('project', self.settings.get('BOT_NAME'))
        l.add_value('spider', self.name)
        l.add_value('server', socket.gethostname())
        l.add_value('time_retrieved_epoch', int(time.time()))

        return l.load_item()


    def _get_html_content(self, response):
        content_root = response.xpath('.//*[contains(@class, "entry-content")][1]')

        def should_start_after_this(node):
            node_content = node.xpath('@class').extract()
            node_is_target = node_content and "printDontShow" in node_content[0]
            return node.xpath('.//*[contains(@class, "printDontShow")]') or node_is_target

        def should_stop(node):
            node_content = node.xpath('@id').extract()
            node_is_target = node_content and "shareOnFacebook" in node_content[0]
            return node.xpath('.//*[@id="shareOnFacebook"]') or node_is_target

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