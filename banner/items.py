# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class BannerItem(Item):
    # define the fields for your item here like:
    # name = Field()
    pass

class Course(Item):
    number = Field()
    department = Field()
    url = Field()
    desc = Field()
    prereqs = Field()
