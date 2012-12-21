# Scrapy settings for banner project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'banner'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['banner.spiders']
NEWSPIDER_MODULE = 'banner.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

ITEM_PIPELINES = [
    'banner.pipelines.BannerPipeline',
    ]
