# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class EquasiscrawlerItem(scrapy.Item):
    # define the fields for your item here like:    
    imo = scrapy.Field()
    ship_name = scrapy.Field()
    call_sign = scrapy.Field()
    mmsi = scrapy.Field()
    gross_tonnage = scrapy.Field()
    dwt = scrapy.Field()
    ship_type = scrapy.Field()
    year_of_build = scrapy.Field()
    flag = scrapy.Field()
    ship_status = scrapy.Field()
    last_update = scrapy.Field()
    
